"""
This module takes care of the actual image creation process.
"""
import os
import re
import subprocess
import sys
from gleetex.document import LaTeXDocument

def remove_all(*files):
    """Guarded remove of files (rm -f); no exception is thrown if a file
    couldn't be removed."""
    try:
        for file in files:
            os.remove(file)
    except OSError:
        pass


def call(cmd):
    """Execute cmd (list of arguments) as a subprocess. Returned is a tuple with
    stdin and stdout, decoded if not None. If the return value is not equal 0, a
    subprocess error is raised."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = [d.decode(sys.getdefaultencoding()) for d in proc.communicate()
            if d]
    if proc.wait():
        # include stderr, if it exists
        raise subprocess.SubprocessError("Error while executing %s%s" %
                (' '.join(cmd), '\n'.join(data)))
    return data

class Tex2img:
    """
    Convert a TeX document string into a png file.
    This class interacts with the LaTeX and dvipng sub processes. Upon error
    the methods throw a SubprocessError with all necessary information to fix
    the issue.
    """
    DVIPNG_REGEX = re.compile(r"^ depth=(\d+) height=(\d+) width=(\d+)")
    def __init__(self, tex_document, output_fn):
        """tex_document should be either a full TeX document as a string or a
        class which implements the __str__ method."""
        self.tex_document = tex_document 
        self.output_name = output_fn
        self.__parsed_data = None
        self.__dpi = 100
        self.__keep_log = False

    def set_dpi(self, dpi):
        """Set output resolution for formula images."""
        if not isinstance(dpi, int):
            raise TypeError("Dpi must be an integer")
        self.__dpi = dpi

    def create_dvi(self, dvi_fn):
        """
        Call LaTeX to produce a dvi file with the given LaTeX document.
        Temporary files will be removed, even in the case of a LaTeX error.
        This method raises a SubprocessError with the helpful part of LaTeX's
        error output."""
        path, basename = os.path.split(dvi_fn)
        tex_fn = os.path.join(path, os.path.splitext(basename)[0] + '.tex')
        aux_fn = os.path.join(path, os.path.splitext(basename)[0] + '.aux')
        log_fn = os.path.join(path, os.path.splitext(basename)[0] + '.log')
        with open(tex_fn, mode='w', encoding='utf-8') as tex:
            tex.write(str(self.tex_document))
        cmd = ['latex', '-halt-on-error', tex_fn]
        cwd = os.getcwd()
        if cwd != path and path != '':
            os.chdir(path)
        logdata = None
        try:
            call(cmd)
        except subprocess.SubprocessError as e:
            remove_all(dvi_fn)
            if not self.__keep_log:
                remove_all(log_fn)
            msg = ''
            if e.args:
                data = self.parse_log(e.args[0])
                if data:
                    msg += data
            raise subprocess.SubprocessError(msg) # propagate subprocess error
        finally:
            remove_all(tex_fn, aux_fn)
            os.chdir(cwd)
        remove_all(log_fn)

    def create_png(self, dvi_fn):
        """Return parsed HTML dimensions.""" # ToDo: more descriptive
        cmd = ['dvipng', '-q*', '-q', '-D', str(self.__dpi),
                '--height*', '--depth*', '--width*', # print information for embedding
            '-o', self.output_name, dvi_fn]
        data = None
        try:
            data = call(cmd)
        except subprocess.SubprocessError as e:
            remove_all(self.output_name)
            raise # error message already contained
        finally:
            remove_all(dvi_fn)
        for line in data[0].split('\n'):
            found = Tex2img.DVIPNG_REGEX.search(line)
            if found:
                return dict(zip(['depth', 'height', 'width'], found.groups()))
        raise ValueError("Could not parse dvi output")

    def convert(self):
        """Convert the TeX document into an image.
        This calls create_dvi and create_png but will not return anything. Thre
        result should be retrieved using get_positioning_info()."""
        dvi = os.path.join(os.path.splitext(self.output_name)[0] + '.dvi')
        data = ''
        try:
            self.create_dvi(dvi)
            self.__parsed_data = self.create_png(dvi)
        except OSError:
            remove_all(self.output_name)
            raise

    def get_positioning_info(self):
        """Return positioning information to position created image in the HTML
        page."""
        return self.__parsed_data

    def parse_log(self, logdata):
        """Parse the LaTeX error output and return the relevant part of it."""
        if not logdata:
            return None
        lines = []
        copy = False
        for line in logdata.split('\n'):
            if line.startswith('! '):
                line = line[2:]
                copy = True
            else:
                if copy:
                    if line.startswith('No pages of') or \
                        line.startswith('Output written') or \
                        line.startswith('!  ==> Fatal error o'):
                        copy = False
                        break
                    else:
                        lines.append(line)
        return '\n'.join(lines)

