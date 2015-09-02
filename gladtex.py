import argparse
import gleetex
import os
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
    def _parse_args(self, args):
        """Parse command line arguments and return option instance."""
        parser = HelpfulCmdParser()
        parser.add_argument("-a", action="store_true", dest="exclusionfile", help="save text alternatives " +
                "for images which are too long for the alt attribute into a " +
                "single separate file and link images to it")
        parser.add_argument('-d', dest='directory', help="Directory in which to" +
                " store generated images in")
        parser.add_argument('-E', dest='encoding', default="UTF-8",
                help="Overwrite encoding to use (default UTF-8)")
        parser.add_argument('-r', metavar='DPI', dest='dpi', default=100,
                type=int, help="set resolution (size of images) to 'dpi' " + \
                "(100 by default)")
        parser.add_argument("-u", metavar="URL", dest='url',
                help="url to image files (relative links are default)")
        parser.add_argument('input', help="input .htex file with LaTeX " +
                "formulas")
        return parser.parse_args(args)

    def exit(self, status):
        """Exit function. Could be used to register any clean up action."""
        sys.exit(status)

    def run(self, args):
        options = self._parse_args(args[1:])
        doc = None
        with open(options.input, 'r', encoding=options.encoding) as file:
            docparser = gleetex.htmlhandling.EqnParser()
            try:
                docparser.feed(file.read())
            except gleetex.htmlhandling.ParseException as e:
                print('Error while parsing {}: {}', options.input, (str(e[0])
                    if len(e) > 0 else str(e)))
                self.exit(5)
            doc = docparser.get_data()
        formula_number = 0
        img_fmt = gleetex.htmlhandling.HtmlImageFormatter(encoding = \
                options.encoding)
        img_fmt.set_exclude_long_formulas(True)
        if options.url:
            img_fmt.set_url(options.url)
        for i in range(0, len(doc)):
            # two types of chunks: a) str (uninteresting), b) list: formula
            chunk = doc[i]
            if isinstance(chunk, list):
                equation = chunk[2]
                latex = gleetex.document.LaTeXDocument(equation)
                formula_fn = os.path.join(os.path.abspath(os.path.split( \
                    options.input)[0]), 'eqn%03d.png' % formula_number)
                conv = gleetex.image.Tex2img(latex, formula_fn)
                conv.set_dpi(options.dpi)
                try:
                    conv.convert()
                except SubprocessError as e:
                    print("Error while converting the formula: %s" % equation)
                    print("Error: %s" % e.args[0])
                    self.exit(91)
                # replace old chunk with formatted html string
                doc[i] = img_fmt.format(conv.get_positioning_info(),
                        equation, formula_fn)
                formula_number += 1
        html_fn = os.path.splitext(options.input)[0] + '.html'
        with open(html_fn, 'w', encoding=options.encoding) as f:
            f.write(''.join(doc))

if __name__ == '__main__':
    m = Main()
    m.run(sys.argv)
