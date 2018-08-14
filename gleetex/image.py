# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
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

from .typesetting import LaTeXDocument

DVIPNG_REGEX = re.compile(r"^ depth=(-?\d+) height=(\d+) width=(\d+)")
DVISVGM_DEPTH_REGEX = re.compile(r"^\s*width=.*?pt, height=.*?pt, depth=(.*?)pt")
DVISVGM_SIZE_REGEX = re.compile(r"^\s*graphic size: (.*?)pt x (.*?)pt")

def remove_all(*files):
    """Guarded remove of files (rm -f); no exception is thrown if a file
    couldn't be removed."""
    for file in files:
        try:
            os.remove(file)
        except OSError:
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

    The background of the PNG files will be transparent by default. If you set a
    background colour within the LaTeX document, you need to turn off
    transparency in this converter manually."""
    def __init__(self, fmt, encoding="UTF-8"):
        if not isinstance(fmt, Format):
            raise ValueError("Enumeration of type Format expected."+str(fmt))
        self.__format = fmt
        self.__encoding = encoding
        self.__parsed_data = None
        self.__size = [115, None]
        self.__background = 'transparent'
        self.__keep_latex_source = False

    def set_dpi(self, dpi):
        """Set output resolution for formula images. This has no effect ifthe
        output format is SVG. It will automatically overwrite a font size, if
        set."""
        if not isinstance(dpi, (int, float)):
            raise TypeError("Dpi must be an integer or floating point number")
        self.__size[0] = int(dpi)

    def set_fontsize(self, size):
        """Set font size for formulas. This will be automatically translated
        into a DPI resolution for PNG images and taken literally for SVG
        graphics."""
        if not isinstance(size, (int, float)):
            raise TypeError("Dpi must be an integer or floating point number")
        self.__size[1] = float(size)

    def set_transparency(self, flag):
        """Set whether or not to use background colour information from the DVI
        file. This is only relevant for PNG output and if a background colour
        other than "transparent" is required, in this case this set'r should be
        set to false. It is set to True, resulting in a transparent
        background."""
        self.__background = ('transparent' if flag else 'not transparent')
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

        if self.__size[1]: # font size in pt
            tex_document.set_fontsize(self.__size[1])
        tex_fn = new_extension('tex')
        aux_fn = new_extension('aux')
        log_fn = new_extension('log')
        cmd = None
        encoding = self.__encoding
        with open(tex_fn, mode='w', encoding=encoding) as tex:
            tex.write(str(tex_document))
        cmd = ['latex', '-halt-on-error', os.path.basename(tex_fn)]
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

        output_fn = '%s.%s' % (os.path.splitext(dvi_fn)[0], self.__format.value)
        if self.__format == Format.Png:
            dpi = (fontsize2dpi(self.__size[1])  if self.__size[1]
                    else self.__size[0])
            return create_png(dvi_fn, output_fn,dpi,
                    self.__background)
        if not self.__size[1]:
            self.__size[1] = 12 # 12 pt
        return create_svg(dvi_fn, output_fn)

    def convert(self, tex_document, base_name):
        """Convert the given TeX document into an image. The base name is used
        to create the required intermediate files and the resulting file will be
        made of the base_name and the format-specific file extension.
        This function returns the positioning information used in the CSS style
        attribute."""
        if not isinstance(tex_document, LaTeXDocument):
            raise TypeError(("expected object of type typesetting.LaTeXDocument,"
                    " got %s") % type(tex_document))
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

def create_png(dvi_fn, output_name, dpi, background):
    """Create a PNG file from a given dvi file. The side effect is the PNG file
    being written to disk.
    By default, the background of the resulting image is transparent, setting
    any other value will make it use whatever was is set in the DVI file.
    :param dvi_fn       Dvi file name
    :param output_name  Output file name
    :param dpi          Output resolution
    :param background   Background colour (default: transparent)
    :return dimensions for embedding into an HTML document
    :raises ValueError raised whenever dvipng output coudln't be parsed"""
    if not output_name:
        raise ValueError("Empty output_name")
    cmd = ['dvipng', '-q*', '-D', str(dpi)]
    if background == 'transparent':
        cmd += ['-bg', background]
    cmd += ['--height*', '--depth*', '--width*', # print information for embedding
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
            return dict(zip(['depth', 'height', 'width'],
                map(float, found.groups())))
    raise ValueError("Could not parse dvi output: " + repr(data))

def create_svg(dvi_fn, output_name):
    """Create a SVG file from a given dvi file. The side effect is the SVG file
    being written to disk.
    :param dvi_fn       Dvi file name
    :param output_name  Output file name
    :param size         font size in pt
    :return dimensions for embedding into an HTML document
    :raises ValueError raised whenever dvipng output coudln't be parsed"""
    if not output_name:
        raise ValueError("Empty output_name")
    cmd = ['dvisvgm', '--exact', '--no-fonts', '-o', output_name,
            '--bbox=preview', dvi_fn]
    data = None
    try:
        data = proc_call(cmd, install_recommends='texlive-binaries')
    except subprocess.SubprocessError:
        remove_all(output_name)
        raise
    finally:
        remove_all(dvi_fn)
    pos = {}
    for line in data.split('\n'):
        if not pos:
            found = DVISVGM_DEPTH_REGEX.search(line)
            if found:
                # convert from pt to px (assuming 96 dpi)
                pos['depth'] = float(found.groups()[0]) * 1.3333333
        else:
            found = DVISVGM_SIZE_REGEX.search(line)
            if found:
                pos.update(dict(zip(['width', 'height'],
                                    # convert from pt to px (assuming 96 dpi)
                                    (float(v) * 1.3333333 for v in found.groups()))))
                return pos
    raise ValueError("Could not parse dvisvgm output: " + repr(data))
