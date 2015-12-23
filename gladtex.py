import argparse
import gleetex
import os
import posixpath
import re
import sys
from subprocess import SubprocessError


class HelpfulCmdParser(argparse.ArgumentParser):
    """This variant of arg parser always prints the full help whenever an error
    occurs."""
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)



class Main:
    """This class parses command line arguments and deals with the
    conversion. Only the run method needs to be called."""
    def __init__(self):
        self.__encoding = "utf-8"
        self.__equations = []

    def _parse_args(self, args):
        """Parse command line arguments and return option instance."""
        epilog = "GladTeX %s, http://humenda.github.io/GladTeX" % gleetex.VERSION
        description = ("GladTeX is a preprocessor that enables the use of LaTeX"
            " maths within HTML files. The maths, embedded in <EQ>...</EQ> "
            "tags, as if within \\(..\\) in LaTeX (or $...$ in TeX), is fed "
            "through latex and replaced by images.")
        parser = HelpfulCmdParser(epilog=epilog, description=description)
        parser.add_argument("-a", action="store_true", dest="exclusionfile", help="save text alternatives " +
                "for images which are too long for the alt attribute into a " +
                "single separate file and link images to it")
        parser.add_argument('-b', dest='background_color',
                help="Set background color for resulting images (default transparent)")
        parser.add_argument('-c', dest='foreground_color',
                help="Set foreground color for resulting images (default 0,0,0)")
        parser.add_argument('-d', dest='directory', help="Directory in which to" +
                " store generated images in (relative path)")
        parser.add_argument('-e', dest='latex_maths_env',
                help="set custom maths environment to surround the formula" + \
                        " (e.g. flalign)")
        parser.add_argument('-E', dest='encoding', default="UTF-8",
                help="Overwrite encoding to use (default UTF-8)")
        parser.add_argument('-i', metavar='CLASS', dest='inlinemath',
                help="CSS class to assign to inline math (default: 'inlinemath')")
        parser.add_argument('-l', metavar='CLASS', dest='displaymath',
                help="CSS class to assign to block-level math (default: 'displaymath')")
        parser.add_argument('-o', metavar='FILENAME', dest='output',
                help=("set output file name; '-' will print text to stdout (by"
                    "default input file name is used and .htex extension changed "
                    "to .html)"))
        parser.add_argument('-p', metavar='LATEX_STATEMENT', dest="preamble",
                help="add given LaTeX code to preamble of document; that'll " +\
                    "affect the conversion of every image")
        parser.add_argument('-r', metavar='DPI', dest='dpi', default=100, type=int,
                help="set resolution (size of images) to 'dpi' (100 by " + \
                    "default)")
        parser.add_argument("-u", metavar="URL", dest='url',
                help="url to image files (relative links are default)")
        parser.add_argument('input', help="input .htex file with LaTeX " +
                "formulas (if omitted or -, stdin will be read)")
        return parser.parse_args(args)

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
        color_regex = re.compile(r"^\d(?:\.\d+)?,\d(?:\.\d+)?,\d(?:\.\d+)?")
        if opts.background_color and not color_regex.match(opts.background_color):
            print("Option -b requires a string in the format " +
                        "num,num,num where num is a broken decimal between 0 " +
                        "and 1.")
            sys.exit(12)
        if opts.foreground_color and not color_regex.match(opts.foreground_color):
            print("Option -c requires a string in the format " +
                        "num,num,num where num is a broken decimal between 0 " +
                        "and 1.")
            sys.exit(13)

    def get_input_output(self, options):
        """Determine whether GladTeX is reading from stdin/file, writing to
        stdout/file and determine base_directory if files are in another
        directory. If no output file name is given and there is a input file to
        read from, output is written to a file ending on .html instead of .htex."""
        data = None
        base_path = ''
        output = '-'
        if options.input == '-':
            data = sys.stdin.read()
        else:
            try:
                with open(options.input, 'r', encoding=options.encoding) as file:
                    data = file.read()
            except UnicodeDecodeError as e:
                self.exit(('Error while reading from %s: %s\nProbably this file'
                    ' has a different encoding, try specifying -E.') % \
                            (options.input, str(e)), 88)
            except IsADirectoryError:
                self.exit("Error: cannot open %s for reading: is a directory." \
                        % options.input, 19)
            base_path = os.path.split(options.input)[0]
        # check which output file name to use
        if options.output:
            base_path = os.path.split(options.output)[0]
            output = options.output
        else:
            if options.input != '-':
                base_path = os.path.split(options.input)[0]
                output = os.path.splitext(options.input)[0] + '.html'
        link_path = ''
        if options.directory:
            link_path = posixpath.join(*(options.directory.split('\\')))
        return (data, base_path, link_path, output)


    def run(self, args):
        options = self._parse_args(args[1:])
        self.validate_options(options)
        self.__encoding = options.encoding
        doc, base_path, link_path, output = self.get_input_output(options)
        docparser = gleetex.htmlhandling.EqnParser()
        try:
            docparser.feed(doc)
        except gleetex.htmlhandling.ParseException as e:
            input_fn = ('stdin' if options.input == '-' else options.input)
            self.exit('Error while parsing {}: {}'.format(input_fn,
                str(e)), 5)
        doc = docparser.get_data()
        processed = self.convert_images(doc, base_path, link_path, options)
        with gleetex.htmlhandling.HtmlImageFormatter(base_path=base_path,
                link_path=link_path, encoding=self.__encoding)  as img_fmt:
            img_fmt.set_exclude_long_formulas(True)
            if options.url:
                img_fmt.set_url(options.url)
            if options.inlinemath:
                img_fmt.set_inline_math_css_class(options.inlinemath)
            if options.displaymath:
                img_fmt.set_display_math_css_class(options.displaymath)

            if output == '-':
                self.write_html(sys.stdout, processed, img_fmt)
            else:
                with open(output, 'w', encoding=self.__encoding) as file:
                    self.write_html(file, processed, img_fmt)

    def write_html(self, file, processed, formatter):
        """Write back altered HTML file with given formatter."""
        # write data back
        for chunk in processed:
            if isinstance(chunk, dict):
                is_displaymath = chunk['displaymath']
                file.write(formatter.format(chunk['pos'], chunk['formula'],
                    chunk['path'], is_displaymath))
            else:
                print(chunk)
                file.write(chunk)

    def convert_images(self, parsed_htex_document, base_path, link_path, options):
        """Convert all formulas to images and store file path and equation in a
        list to be processed later on."""
        base_path = ('' if not base_path or base_path == '.' else base_path)
        result = []
        try:
            conv = gleetex.convenience.CachedConverter(base_path, link_path)
        except gleetex.caching.JsonParserException as e:
            self.exit(e.args[0], 78)
        options_to_query = ['dpi', 'preamble', 'latex_maths_env']
        for option_str in options_to_query:
            option = getattr(options, option_str)
            if option:
                conv.set_option(option_str, option)
        # colors need special handling
        for option_str in ['foreground_color', 'background_color']:
            option = getattr(options, option_str)
            if option:
                conv.set_option(option_str, tuple(map(float, option.split(','))))
        formula_count = 0
        for chunk in parsed_htex_document:
            # chunk == an entity parsed by EqnParser; type 'str' will be taken
            # literally, 'list' will be treated as formula
            if isinstance(chunk, list):
                formula_count += 1
                equation = chunk[2]
                displaymath = chunk[1]
                try:
                    data = conv.convert(equation, displaymath=displaymath)
                    # add data for formatting to `result`
                    data['formula'] = equation
                    data['displaymath'] = displaymath
                    result.append(data)
                except SubprocessError as e:
                    pos = chunk[0]
                    self.exit(("Error while converting the formula at line %d, "
                        "pos %d (no. %d):\n    %s\n\n%s") % (pos[0], pos[1]+1,
                            formula_count, equation, str(e.args[0])), 91)
            else:
                result.append(chunk)
        return result


if __name__ == '__main__':
    m = Main()
    m.run(sys.argv)
