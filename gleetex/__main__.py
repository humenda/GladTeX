# (c) 2013-2019 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
import argparse
import multiprocessing
import os
import posixpath
import sys
from . import *
from .htmlhandling import HtmlImageFormatter


class HelpfulCmdParser(argparse.ArgumentParser):
    """This variant of arg parser always prints the full help whenever an error
    occurs."""
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)



def format_ordinal(number):
    endings = ['th', 'st', 'nd', 'rd'] + ['th'] * 6
    return '%d%s' % (number, endings[number%10])

class Main:
    """This class parses command line arguments and deals with the
    conversion. Only the run method needs to be called."""
    def __init__(self):
        self.__encoding = "utf-8"

    def _parse_args(self, args):
        """Parse command line arguments and return option instance."""
        epilog = "GladTeX %s, http://humenda.github.io/GladTeX" % VERSION
        description = ("GladTeX is a preprocessor that enables the use of LaTeX"
            " maths within HTML files. The maths, embedded in <EQ>...</EQ> "
            "tags, as if within \\(..\\) in LaTeX (or $...$ in TeX), is fed "
            "through latex and replaced by images.\n\nPlease also see the "
            "documentation on the web or from the manual page for more "
            "information, especially on environment variables.")
        cmd = HelpfulCmdParser(epilog=epilog, description=description)
        cmd.add_argument("-a", action="store_true", dest="exclusionfile", help="save text alternatives " +
                "for images which are too long for the alt attribute into a " +
                "single separate file and link images to it")
        cmd.add_argument('-b', dest='background_color',
                help=("Set background color for resulting images "
                    "(default transparent, use hex)"))
        cmd.add_argument('-c', dest='foreground_color',
                help=("Set foreground color for resulting images (default "
                    "000000, hex)"))
        cmd.add_argument('-d', dest='img_directory', help="Directory in which to" +
                " store generated images in (relative to the output file)")
        cmd.add_argument('-e', dest='latex_maths_env',
                help="Set custom maths environment to surround the formula" + \
                        " (e.g. flalign)")
        cmd.add_argument('-f', metavar='SIZE', dest='fontsize', default=12,
                help="Set font size in pt (default 12)")
        cmd.add_argument('-E', dest='encoding', default=None,
                help="Overwrite encoding to use (default UTF-8)")
        cmd.add_argument('-i', metavar='CLASS', dest='inlinemath',
                help="CSS class to assign to inline math (default: 'inlinemath')")
        cmd.add_argument('-l', metavar='CLASS', dest='displaymath',
                help="CSS class to assign to block-level math (default: 'displaymath')")
        cmd.add_argument('-K', dest='keep_latex_source', action="store_true",
                default=False, help="keep LaTeX file(s) when converting formulas (useful for debugging)")
        cmd.add_argument('-m', dest='machinereadable', action="store_true",
                default=False,
                help="Print output in machine-readable format (less concise, better parseable)")
        cmd.add_argument("-n", action="store_true", dest="notkeepoldcache",
                    help=("Purge unreadable caches along with all eqn*.png files. "
                        "Caches can be unreadable if the used GladTeX version is "
                        "incompatible. If this option is unset, GladTeX will "
                        "simply fail when the cache is unreadable."))
        cmd.add_argument('-o', metavar='FILENAME', dest='output',
                help=("Set output file name; '-' will print text to stdout (by"
                    "default input file name is used and .htex extension changed "
                    "to .html)"))
        cmd.add_argument('-p', metavar='LATEX_STATEMENT', dest="preamble",
                help="Add given LaTeX code to preamble of document; that'll " +\
                    "affect the conversion of every image")
        cmd.add_argument('-P', dest="pandocfilter", action='store_true',
                help="Use GladTeX as a Pandoc filter: read a Pandoc JSON AST "
                    "from stdin, convert the images, change math blocks to "
                    "images and write JSON to stdout")
        cmd.add_argument('--png', action='store_true', dest='png',
                help="Use PNG instead of SVG for images")
        cmd.add_argument('-r', '--resolution', metavar='DPI', dest='dpi',
                default=None,
                help=("Set resolution in DPI, only available if PNG output "
                    "selected; also see `-f`"))
        cmd.add_argument('-R', action="store_true", dest='replace_nonascii',
                default=False, help="Replace non-ascii characters in formulas "
                    "through their LaTeX commands")
        cmd.add_argument("-u", metavar="URL", dest='url',
                help="URL to image files (relative links are default)")
        cmd.add_argument('input', help="Input .htex file with LaTeX " +
                "formulas (if omitted or -, stdin will be read)")
        return cmd.parse_args(args)

    def exit(self, text, status):
        """Exit function. Could be used to register any clean up action."""
        sys.stderr.write(text)
        if not text.endswith('\n'):
            sys.stderr.write('\n')
        sys.exit(status)

    def validate_options(self, opts):
        """Validate certain arguments suppliedon the command line. The user will
        get a (hopefully) helpful error message if he/she gave an invalid
        parameter."""
        if opts.fontsize and opts.dpi:
            print("Options -f and -d can't be used at the same time.")
            sys.exit(14)
        if opts.dpi and not opts.png:
            print(("Impossible to set resolution when using SVG as output, "
                "try -f"))
            sys.exit(14)

    def get_input_output(self, options):
        """Determine whether GladTeX is reading from stdin/file, writing to
        stdout/file and determine base_directory if files are in another
        directory.
        If no output file name is given and there is a input file to read
        from, output is written to a file ending on .html instead of .htex.
        The returned document is either string or byte, the latter if encoding
        is unknown."""
        data = None
        output = '-'
        if options.input == '-':
            data = sys.stdin.read()
        else:
            try:
                # if encoding was specified or if a pandoc filter is supplied,
                # read document with default encoding
                if options.encoding or options.pandocfilter:
                    encoding = ('UTF-8' if options.pandocfilter else options.encoding)
                    with open(options.input, encoding=encoding) as f:
                        data = f.read()
                else: # read as binary and guess from HTML meta charset
                    with open(options.input, 'rb') as file:
                        data = file.read()
            except UnicodeDecodeError as e:
                self.exit(('Error while reading from %s: %s\nProbably this file'
                    ' has a different encoding, try specifying -E.') % \
                            (options.input, str(e)), 88)
            except IsADirectoryError:
                self.exit("Error: cannot open %s for reading: is a directory." \
                        % options.input, 19)
            except FileNotFoundError:
                self.exit("Error: file %s not found." % options.input, 20)

        # check which output file name to use
        base_path = ''
        if options.output:
            output = options.output
            base_path = os.path.dirname(options.output)
        elif options.input != '-':
            output = os.path.splitext(options.input)[0] + '.html'
            base_path = os.path.dirname(options.input)

        if base_path: # if finally a basepath found:, strip \\ if on Windows
            base_path = posixpath.join(*(base_path.split('\\')))
        # the basepath needs to be relative to the output file
        return (data, base_path, output)


    def run(self, args):
        options = self._parse_args(args[1:])
        self.validate_options(options)
        self.__encoding = options.encoding
        fmt = ('pandocfilter' if options.pandocfilter else 'html')
        doc, base_path, output = self.get_input_output(options)
        try:
            # doc is either a list of raw HTML chunks and formulas or a tuple of
            # (document AST, list of formulas) if options.pandocfilter
            self.__encoding, doc = parser.parse_document(doc, fmt)
        except parser.ParseException as e:
            input_fn = ('stdin' if options.input == '-' else options.input)
            self.exit('Error while parsing {}: {}'.format(input_fn,
                str(e)), 5)

        processed = self.convert_images(doc, base_path, options.img_directory,
                options)
        img_dir = ('' if not options.img_directory or \
                options.img_directory == '.' else options.img_directory)
        with HtmlImageFormatter(base_path=os.path.join(base_path, img_dir),
                link_prefix=options.url) as img_fmt:
            img_fmt.set_exclude_long_formulas(True)
            if options.replace_nonascii:
                img_fmt.set_replace_nonascii(True)
            if options.url:
                img_fmt.set_url(options.url)
            if options.inlinemath:
                img_fmt.set_inline_math_css_class(options.inlinemath)
            if options.displaymath:
                img_fmt.set_display_math_css_class(options.displaymath)

            with (sys.stdout if output == '-'
                    else open(output, 'w', encoding=self.__encoding)) as file:
                if options.pandocfilter:
                    pandoc.write_pandoc_ast(file, processed, img_fmt)
                else:
                    htmlhandling.write_html(file, processed, img_fmt)

    def convert_images(self, parsed_document, base_path, img_dir, options):
        """Convert all formulas to images and store file path and equation in a
        list to be processed later on."""
        base_path = ('' if not base_path or base_path == '.' else base_path)
        img_dir = ('' if not img_dir or img_dir == '.' else img_dir)
        result = []
        try:
            conv = cachedconverter.CachedConverter(base_path,
                    not options.notkeepoldcache, encoding=self.__encoding,
                    img_dir=img_dir)
        except caching.JsonParserException as e:
            self.exit(e.args[0], 78)

        self.set_options(conv, options)
        if options.pandocfilter:
            formulas = parsed_document[1]
        else: # HTML chunks from EqnParser
            formulas = [c for c in parsed_document if isinstance(c, (tuple,
                list))]
        try:
            conv.convert_all(formulas)
        except cachedconverter.ConversionException as e:
            self.emit_latex_error(e, options.machinereadable,
                    options.replace_nonascii)

        if options.pandocfilter:
            # return (ast, formulas), just with formulas being replaced with the
            # conversion data
            return (parsed_document[0], [conv.get_data_for(eqn, style)
                    for _p, style, eqn in formulas])
        for chunk in parsed_document:
            # output of EqnParser: list-alike is formula, str is raw HTML
            if isinstance(chunk, (tuple, list)):
                _p, displaymath, formula = chunk
                try:
                    result.append(conv.get_data_for(formula, displaymath))
                except KeyError as e:
                    # formula is usually tuple(str, bool)
                    formula = e.args[0]
                    if isinstance(formula, (list, tuple)):
                        formula = e.args[0][0] # ignore bool(displaymath)
                    raise KeyError(("formula '{}' not found; that means it was "
                            "not converted which should usually not happen.")
                        .format(formula))
            else:
                result.append(chunk)
        return result


    def set_options(self, conv, options):
        """Apply options from command line parser to the converter."""
        # set options
        options_to_query = ['preamble', 'latex_maths_env',
                'png', 'keep_latex_source', 'foreground_color',
                'background_color']
        for option_str in options_to_query:
            option = getattr(options, option_str)
            if option:
                if option in ('True', 'False', 'false', 'true'):
                    option = bool(option)
                conv.set_option(option_str, option)
        if options.dpi:
            conv.set_option("dpi", float(options.dpi))
        elif options.fontsize:
            conv.set_option("fontsize", options.fontsize)
        if options.replace_nonascii:
            conv.set_replace_nonascii(True)

    def emit_latex_error(self, err, machine_readable, escape):
        """Format a LaTeX error in a meaningful way. The argument escape
        specifies, whether the -R switch had been passed. If the pandocfilter
        mode is active, formula positions will be omitted; this makes the code
        more complex."""
        if 'DEBUG' in os.environ and os.environ['DEBUG'] == '1':
            raise err
        escaped = err.formula
        if escape:
            escaped = typesetting.escape_unicode_maths(err.formula)
        msg = None
        additional = ''
        if 'Package inputenc' in err.args[0]:
            additional += ('Add the switch `-R` to automatically replace unicode '
                'characters with LaTeX command sequences.')
        if machine_readable:
            msg = 'Number: {}\nFormula: {}{}\nMessage: {}'.format(err.formula_count,
                    err.formula,
                    ('' if escaped == err.formula
                        else '\nLaTeXified formula: %s' % escaped),
                    err.cause)
            if err.src_line_number and err.src_pos_on_line:
                msg = ('Line: {}, {}\n' + msg).format(err.src_line_number,
                        err.src_pos_on_line)
            if additional:
                msg += '; ' + additional
        else:
            formula = '    ' + err.formula.replace('\n', '\n    ')
            escaped = ('    ' + escaped.replace('\n', '\n    ') if escaped !=
                    err.formula else '')
            msg = "Error while converting formula %d\n" % err.formula_count
            if err.src_line_number and err.src_pos_on_line:
                msg += " at line %d, %d:\n" % (err.src_line_number,
                        err.src_pos_on_line,)
            msg += '%s%s\n%s' % (formula, (''
                if not escaped or escaped == err.formula
                else '\nFormula without unicode symbols:\n%s' % escaped),
                   err.cause)
            if additional:
                import textwrap
                msg += ' undefined.\n' + '\n'.join(textwrap.wrap(additional, 80))
        self.exit(msg, 91)


def main():
    """Entry point for setuptools."""
    # enable multiprocessing on Windows, see python docs
    multiprocessing.freeze_support()
    m = Main()
    # run as pandoc filter?
    args = sys.argv # fallback if no environment variable set
    if 'GLADTEX_ARGS' in os.environ:
        args = [sys.argv[0]] + os.environ['GLADTEX_ARGS'].split(' ')
        if '-P' not in args:
            args = [args[0]] + ['-P'] + args[1:] + ['-']
    m.run(args)

if __name__ == '__main__':
    main()
