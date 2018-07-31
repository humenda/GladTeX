"""This module takes care of the actual image creation process.

Each formula is saved as an image, either as PNG or SVG. SVG is advised, since
it is a properly scalable format.
"""
import enum
import os
import re
import shutil
import subprocess
import sys

DVIPNG_REGEX = re.compile(r"^ depth=(-?\d+) height=(\d+) width=(\d+)")
DVISVGM_REGEX = re.compile(r"^\s*width=(.*?)pt, height=(.*?)pt, depth=(.*?)pt")

def remove_all(*files):
    """Guarded remove of files (rm -f); no exception is thrown if a file
    couldn't be removed."""
    for file in files:
        try:
            os.remove(file)
        except OSError as e:
            pass


def proc_call(cmd, cwd=None, install_recommends=True):
    """Execute cmd (list of arguments) as a subprocess. Returned is a tuple with
    stdout and stderr, decoded if not None. If the return value is not equal 0, a
    subprocess error is raised. Timeouts will happen after 20 seconds."""
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            bufsize=1, universal_newlines=False, cwd=cwd) as proc:
        data = []
        try:
            data = [d.decode(sys.getdefaultencoding(), errors="surrogateescape")
                    for d in proc.communicate(timeout=20) if d]
            if proc.wait():
                raise subprocess.SubprocessError("Error while executing %s\n%s\n" %
                    (' '.join(cmd), '\n'.join(data)))
        except subprocess.TimeoutExpired as e:
            proc.kill()
            note = 'Subprocess expired with time out: ' + str(cmd) + '\n'
            poll = proc.poll()
            if poll:
                note += str(poll) + '\n'
            if data:
                raise subprocess.SubprocessError(str(data + '\n' + note))
            else:
                raise subprocess.SubprocessError('execution timed out after ' +
                        str(e.args[1]) + ' s: ' + ' '.join(e.args[0]))
        except KeyboardInterrupt as e:
            sys.stderr.write("\nInterrupted; ")
            import traceback
            traceback.print_exc(file=sys.stderr)
        except FileNotFoundError:
            # program missing, try to help
            text = "Command `%s` not found." % cmd[0]
            if install_recommends and shutil.which('dpkg'):
                text += ' Install it using `sudo apt install ' + install_recommends
            else:
                text += ' Install a TeX distribution of your choice, e.g. MikTeX or TeXlive.'
            raise subprocess.SubprocessError(text) from None
        if isinstance(data, list):
            return '\n'.join(data)
        return data

#pylint: disable=too-few-public-methods
class Format(enum.Enum):
    """Chose the image output format."""
    Png = 'png'
    Svg = 'svg'

class Tex2img:
    """Convert a TeX document string into a png file.
    This class interacts with the LaTeX and dvipng sub processes. Upon error
    the methods throw a SubprocessError with all necessary information to fix
    the issue.
    The background of the PNG files will be transparent by default.
    """
    def __init__(self, fmt, encoding="UTF-8"):
        if not isinstance(fmt, Format):
            raise ValueError("Enumeration of type Format expected."+str(fmt))
        self.__format = fmt


        self.__encoding = encoding
        self.__format = Format.Png
        self.__parsed_data = None
        self.__dpi = 100
        self.__background = 'transparent'
        self.__foreground = 'rgb 0 0 0'
        self.__keep_latex_source = False
        # create directory for image if that doesn't exist

    def set_dpi(self, dpi):
        """Set output resolution for formula images."""
        if not isinstance(dpi, (int, float)):
            raise TypeError("Dpi must be an integer or floating point number")
        self.__dpi = int(dpi)

    def set_transparency(self, flag):
        """Set whether or not the background of an image is transparent."""
        if not isinstance(flag, bool):
            raise ValueError("Argument must be of type bool!")
        self.__background = ('transparent' if flag else 'rgb 1 1 1')

    def __check_rgb(self, rgb_list):
        """DVIPNG takes RGB colours in the same format as LaTeX, as a
        space-delimited list of broken decimals."""
        if not isinstance(rgb_list, (list, tuple)) or len(rgb_list) != 3:
            raise ValueError("A list with three broken decimals between 0 and 1 expected.")
        if not all(map((lambda x: x >= 0 and x <= 1), rgb_list)):
            raise ValueError("RGB values must between 0 and 1")

    def set_background_color(self, rgb_list):
        """set_background_color(rgb_values)
        The list rgb_values must contain three broken decimals between 0 and 1."""
        self.__check_rgb(rgb_list)
        self.__background = 'rgb {0[0]} {0[1]} {0[2]}'.format(rgb_list)

    def set_foreground_color(self, rgb_list):
        """set_background_color(rgb_values)
        The list rgb_values must contain three broken decimals between 0 and 1."""
        self.__check_rgb(rgb_list)
        self.__foreground = 'rgb {0[0]} {0[1]} {0[2]}'.format(rgb_list)

    def set_keep_latex_source(self, flag):
        """Set whether LaTeX source document should be kept."""
        if not isinstance(flag, bool):
            raise TypeError("boolean object required, got %s." % repr(flag))
        self.__keep_latex_source = flag


    def create_dvi(self, tex_document, dvi_fn):
        """Call LaTeX to produce a dvi file with the given LaTeX document.
        Temporary files will be removed, even in the case of a LaTeX error.
        This method raises a SubprocessError with the helpful part of LaTeX's
        error output."""
        path = os.path.dirname(dvi_fn)
        if path and not os.path.exists(path):
            os.makedirs(path)
        if not path:
            path = os.getcwd()
        new_extension = lambda x: os.path.splitext(dvi_fn)[0] + '.' + x

        tex_fn = new_extension('tex')
        aux_fn = new_extension('aux')
        log_fn = new_extension('log')
        cmd = None
        cmd = ['latex', '-halt-on-error', os.path.basename(tex_fn)]
        encoding = self.__encoding
        with open(tex_fn, mode='w', encoding=encoding) as tex:
            tex.write(str(tex_document))
        try:
            proc_call(cmd, cwd=path, install_recommends='texlive-recommended')
        except subprocess.SubprocessError as e:
            remove_all(dvi_fn)
            msg = ''
            if e.args:
                data = self.parse_latex_log(e.args[0])
                if data:
                    msg += data
                else:
                    msg += str(e.args[0])
            raise subprocess.SubprocessError(msg) # propagate subprocess error
        finally:
            if self.__keep_latex_source:
                remove_all(aux_fn, log_fn)
            else:
                remove_all(tex_fn, aux_fn, log_fn)

    def create_image(self, dvi_fn):
        """Create the image containing the formula, using either dvisvgm or
        dvipng."""
        dirname = os.path.dirname(dvi_fn)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

        output_fn = os.path.splitext(dvi_fn)[0] + self.__format.value
        if self.__format == Format.Png:
            return create_png(dvi_fn, output_fn, str(self.__dpi),
                    self.__background, self.__foreground)
        return create_svg(dvi_fn, output_fn, self.__background,
                self.__foreground)

    def convert(self, tex_document, base_name):
        """Convert the given TeX document into an image. The base name is used
        to create the required intermediate files and the resulting file will be
        made of the base_name and the format-specific file extension.
        This function returns the positioning information used in the CSS style
        attribute."""
        dvi = '%s.dvi' % base_name
        try:
            self.create_dvi(tex_document, dvi)
            return self.create_image(dvi)
        except OSError:
            remove_all('%s.%s' % (base_name, self.__format.value))
            raise

    def parse_latex_log(self, logdata):
        """Parse the LaTeX error output and return the relevant part of it."""
        if not logdata:
            return None
        line = None
        for line in logdata.split('\n'):
            if line.startswith('! '):
                line = line[2:]
                break
        if line: # try to remove LaTeX line numbers
            lineno = re.search(r'\s*on input line \d+', line)
            if lineno:
                line = line[:lineno.span()[0]] + line[lineno.span()[1]:]
            return line
        return None

def fontsize2dpi(size_pt):
    """This function calculates the DPI for the resulting image. Depending on
    the font size, a different resolution needs to be used. According to the
    dvipng manual page, the formula is:
    <dpi> = <font_px> * 72.27 / 10 [px * TeXpt/in / TeXpt]"""
    size_px = size_pt * 1.3333333 # and more 3s!
    return size_px * 72.27 / 10

def create_png(dvi_fn, output_name, dpi, background='transparent',
        foreground='rgb 0 0 0'):
    """Create a PNG file from a given dvi file. The side effect is the PNG file
    being written to disk.
    :param dvi_fn       Dvi file name
    :param output_name  Output file name
    :param dpi          Output resolution
    :param background   Background colour (default: transparent)
    :param foreground   Foreground Colour (default black == 'rgb 0 0 0')
    :return dimensions for embedding into an HTML document
    :raises ValueError raised whenever dvipng output coudln't be parsed"""
    if not output_name:
        raise ValueError("Empty output_name")
    cmd = ['dvipng', '-q*', '-D', str(dpi),
            # colors
            '-bg', background, '-fg', foreground,
            '--height*', '--depth*', '--width*', # print information for embedding
            '-o', output_name, dvi_fn]
    data = None
    try:
        data = proc_call(cmd, install_recommends='dvipng')
    except subprocess.SubprocessError:
        remove_all(output_name)
        raise
    finally:
        remove_all(dvi_fn)
    for line in data.split('\n'):
        found = DVIPNG_REGEX.search(line)
        if found:
            return dict(zip(['depth', 'height', 'width'], found.groups()))
    raise ValueError("Could not parse dvi output: " + repr(data))

def create_svg(dvi_fn, output_name, background='transparent',
        foreground='rgb 0 0 0'):
    """Create a SVG file from a given dvi file. The side effect is the SVG file
    being written to disk.
    :param dvi_fn       Dvi file name
    :param output_name  Output file name
    :param background   Background colour (default: transparent)
    :param foreground   Foreground Colour (default black == 'rgb 0 0 0')
    :return dimensions for embedding into an HTML document
    :raises ValueError raised whenever dvipng output coudln't be parsed"""
    if not output_name:
        raise ValueError("Empty output_name")
    cmd = ['dvisvgm', '-o', output_name, dvi_fn, '--bbox=preview']
    #ToDo: colour handling
    #'-bg', background, '-fg', foreground,
    data = None
    try:
        data = proc_call(cmd, install_recommends='texlive-binaries')
    except subprocess.SubprocessError:
        remove_all(output_name)
        raise
    finally:
        remove_all(dvi_fn)
    for line in data.split('\n'):
        found = DVISVGM_REGEX.search(line)
        if found:
            pos = dict(zip(['width', 'height', 'depth'],
                # convert from pt to px
                (float(v) * 1.3333333 for v in found.groups())))
            return pos
    raise ValueError("Could not parse dvisvgm output: " + repr(data))

