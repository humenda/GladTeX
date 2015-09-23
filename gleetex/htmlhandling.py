"""Everything regarding parsing, generating and writing HTML belongs in here."""

import collections
from html.parser import HTMLParser
import os



class ParseException(Exception):
    """Exception to propagate an parsing error."""
    def __init__(self, msg):
        super().__init__(msg)


class EqnParser(HTMLParser):
    """This HTML parser parses a given document and tries to preserve the
    original document as much as possible. It is saved in chunks which
    reconstruct the whole document, when joined. An exception are formulas from
    the <eq /> equation tag. Instead of saving those into a chunk too, a list is
    added, where the first element is the position the formula was encountered,
    the second is whether is displaymath 8set to True in this case) and the
    third is the actual text chunk. so for getting all equations, one would do:

            eqns = [e for e in parser.get_data()   if isinstance(e, list)]

    NOTE: The document is slightly altered. Tags will be lower case and some
    spacing can be lost. The parser tries to preserve as much as possible, but
    e.g. stand-alone tags like `<br />` would loose the space."""
    def __init__(self):
        self.__data = []
        self.__lastchunk = []
        super().__init__(self, convert_charrefs=False)
        self.in_eqn = False

    def feed(self, arg):
        """Overwrite to run a final step after parsing was completed."""
        super().feed(arg)
        if self.in_eqn:
            started_at = ''
            if isinstance(self.__data[-1], list):
                started_at = ' Equation started on line ' + \
                        str(self.__data[-1][0][0])
            raise ParseException("Unclosed equation environment." + started_at)
        self.__data += self.__lastchunk
        self.__lastchunk = []

    def handle_starttag(self, tag, attrs):
        if not tag == 'eq':
            self.__lastchunk.append(self.get_starttag_text())
        else:
            if self.in_eqn:
                raise ParseException("Opening eq tag encountered at line " +
                        str(self.getpos()[0]) + ", while the previous one wasn't closed.")
            attrs = dict((k.lower(), v.lower()) for k,v in attrs)
            displaymath = (True if 'env' in attrs and attrs['env'] == 'displaymath'
                    else False)
            # add already parsed elements:
            self.__data += self.__lastchunk
            self.__lastchunk = []
            # initialize list item in self.__data for equation
            self.__data.append([self.getpos(), displaymath, None])
            self.in_eqn = True

    def handle_startendtag(self, tag, attrs):
        if attrs:
            self.__lastchunk.append('<{} {} />'.format(tag,
                ' '.join(['%s="%s"' % (x[0], x[1]) for x in attrs])))
        else:
            self.__lastchunk.append('<%s />' % tag)

    def handle_endtag(self, tag):
        if self.in_eqn:
            self.in_eqn = False
            # add last chunk(s) to already saved eqn position in self.__data
            if isinstance(self.__lastchunk, list):
                self.__data[-1][2] = ''.join(self.__lastchunk)
            else:
                self.__data[-1][2] = self.__lastchunk
            self.__lastchunk = [] # clear last chunk  for further processing
        else:
            self.__lastchunk.append('</%s>' % tag)

    def handle_data(self, data):
        self.__lastchunk.append(data)

    def handle_entityref(self, name):
        self.__lastchunk.append('&%s;' % name)

    def handle_charref(self, name):
        self.__lastchunk.append('&#%s;' % name)

    def handle_comment(self, blah):
        self.__lastchunk.append('<!--%s-->' % blah)

    def handle_pi(self, instruction):
        """Handle processing instruction."""
        self.__lastchunk.append('<? %s>' % instruction)

    def handle_unknown_decl(self, declaration):
        self.__lastchunk.append('<!%s>' % declaration)

    def get_data(self):
        return self.__data[:]


def gen_id(formula):
    """Generate an id for identifying a formula."""
    # for some characters we just use a simple replacement (otherwise the
    # would be lost)
    mapped = {'{':'_', '}':'_', '(':'-', ')':'-', '\\':'.', '^':','}
    id = []
    for c in formula:
        if mapped.get(c):
            id.append(mapped[c])
        elif c.isalpha() or c.isdigit():
            id.append(c)
    return ''.join(id)


class OutsourcedFormulaParser(HTMLParser):
    """This HTML parser parses the head and tries to keep it close to the
    original document as possible. As soon as a formula is encountered, only
    the formulas  are parsed. Everything in between and after the them will be
    fully ignored.
    A sample formula would look like:

        <p id="id_as_generated_by_gen_id"><pre>stuff</pre></p>
    """
    def __init__(self):
        self.__head = []
        self.__id = None
        self.__passed_head = False
        self.__equations = collections.OrderedDict()
        super().__init__(self, convert_charrefs=False)

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            attrs = dict(attrs)
            if attrs.get('id'):
                self.__id = attrs['id'] # marks beginning of a formula paragraph
                self.__equations[self.__id] = ''
                return
        elif tag == 'body':
            self.__passed_head = True
            self.__head.append('\n<body>\n')
        if not self.__passed_head:
            self.__head.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self.__id or self.__passed_head: return # skip everything inside a formula
        if attrs:
            self.__head.append('<{} {} />'.format(tag,
                ' '.join(['%s="%s"' % (x[0], x[1]) for x in attrs])))
        else:
            self.__head.append('<%s />' % tag)

    def handle_endtag(self, tag):
        if self.__id: # inside a formula
            if tag == 'p':
                self.__id = None # end formula block
        elif not self.__passed_head:
            formatted = '</%s>' % tag
            self.__head.append(formatted)

    def handle_data(self, data):
        if self.__id:
            self.__equations[self.__id] += data
        elif not self.__passed_head:
            self.__head.append(data)

    def handle_entityref(self, name):
        if self.__id:
            self.__equations[self.__id] += '&%s;' % name
        elif not self.__passed_head:
            self.__head.append('&%s;' % name)

    def handle_charref(self, name):
        if self.__id:
            self.__equations[self.__id] += '&#%s;' % name
        elif not self.__passed_head:
            self.__head.append('&#%s;' % name)

    def handle_comment(self, blah):
        if not self.__passed_head:
            self.__head.append('<!--%s-->' % blah)

    def handle_decl(self, declaration):
        if not self.__passed_head:
            self.__head.append('<!%s>' % declaration)


    def get_head(self):
        """Return a string containing everything before the first formula."""
        return ''.join(self.__head)

    def get_formulas(self):
        """Return an ordered dictionary with id : formula paragraph."""
        return self.__equations

def format_formula_paragraph(formula):
    """Format a formula to appear as if it would have been outsourced into an
    external file."""
    return '<p id="%s"><pre>%s</pre></span></p>\n' % \
            (gen_id(formula), formula)


class HtmlImageFormatter: # ToDo: localisation
    """Create the HTML markup for given formula and image file."""
    HTML_TEMPLATE_HEAD = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"' +
        '\n  "http://www.w3.org/TR/html4/strict.dtd">\n<html>\n<head>\n' +
        '<meta http-equiv="content-type" content="text/html; charset=utf-8"/>' +
        '\n<title>Outsourced Formulas</title>\n</head>\n<!-- ' +
        'Do not modify this file, it is automatically generated -->\n<body>\n')
    def __init__(self, exclusion_filepath='outsourced_formulas.html',
            encoding="UTF-8"):
        self.__exclude_descriptions = False
        if os.path.exists(exclusion_filepath):
            if not os.access(exclusion_filepath, os.W_OK):
                raise OSError('The file %s is not writable!' %
                        exclusion_filepath)
        self.__exclusion_filepath = exclusion_filepath
        self.__inline_maxlength=100
        self.__file_head = HtmlImageFormatter.HTML_TEMPLATE_HEAD
        self.__cached_formula_pars = collections.OrderedDict()
        self.__url = ''
        self.initialized = False
        self.encoding = encoding
        self.initialize() # read already written file, if any

    def set_max_formula_length(self, length):
        """Set maximum length of a formula before it gets outsourced into a
        separate file."""
        self.__inline_maxlength = length

    def set_exclude_long_formulas(self, flag):
        """When set, the LaTeX code of a formula longer than the configured
        maxlength will be excluded and written + linked into a separate file."""
        self.__exclude_descriptions = flag

    def set_url(self, prefix):
        """Set URL prefix which is used as a prefix to the image file in the
        HTML link."""
        self.__url = prefix

    def initialize(self):
        """Initialize the image writer. If a file with already written image
        descriptions exists, this one will be parsed first and new formulas
        appended to it. Otherwise a new file will be written upon ending the
        with-resources block."""
        if self.initialized:
            return
        self.initialized = True
        if not os.path.exists(self.__exclusion_filepath):
            return self
        document = None
        with open(self.__exclusion_filepath, 'r', encoding=self.encoding) as f:
            document = f.read()
        # parse html document:
        parser = OutsourcedFormulaParser()
        parser.feed(document)
        self.__file_head =parser.get_head()
        self.__cached_formula_pars = parser.get_formulas()
        return self

    def __enter__(self):
        return self

    def __exit__(self, useless, unused, not_applicable):
        """Write back file with excluded image descriptions, if any."""
        def formula2paragraph(frml):
            return '<p id="%s"><pre>%s</pre></p>' % (gen_id(frml), frml)
        if not len(self.__cached_formula_pars):
            return
        with open(self.__exclusion_filepath, 'w', encoding=self.encoding) as f:
            f.write(self.__file_head)
            f.write('\n<hr />\n'.join([formula2paragraph(formula) \
                    for formula in self.__cached_formula_pars.values()]))
            f.write('\n</body>\n</html>\n')

    def get_html_img(self, pos, formula, img_path):
        """:param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :returns a string with the formatted HTML string"""
        full_url = img_path
        if self.__url:
            if self.__url.endswith('/'): self.__url = self.__url[:-1]
            full_url = self.__url + '/' + img_path
        # depth is a negative offset
        depth = str(int(pos['depth']) * -1)
        return ('<img src="{0}" style="vertical-align: {3}" '
                'height="{2[height]}" width="{2[width]}" alt="{1}" />').\
                format(full_url, formula, pos, depth)

    def format_excluded(self, pos, formula, img_path):
        """This method formats a formula and an formula image in HTML and
        additionally writes the formula to an external (configured) file to
        which the image links to. That's useful for blind screen reader users
        who can then easily have a look at the formula.
        :param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :returns string with formatted HTML image which also links to excluded
        formula"""
        shortened = (formula[:100] + '...'  if len(formula) > 100 else formula)
        img = self.get_html_img(pos, shortened, img_path)
        ext_formula = format_formula_paragraph(formula)
        # write formula out to external file
        identifier = gen_id(formula)
        if not identifier in self.__cached_formula_pars:
            self.__cached_formula_pars[identifier] = ext_formula
        return '<a href="{}#{}">{}</a>'.format(self.__exclusion_filepath,
                gen_id(formula), img)

    def format(self, pos, formula, img_path):
        """This method formats a formula. If self.__exclude_descriptions is set
        and the formula igreater than the configured length, the formula will be
        outsourced, otherwise it'll be included in the IMG's alt tag. In either
        case, a string for the current document containing the formatted HTML is returned.
        :param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :returns string with formatted HTML image which also links to excluded
        formula"""
        if self.__exclude_descriptions and \
                len(formula) > self.__inline_maxlength:
            return self.format_excluded(pos, formula, img_path)
        else:
            return self.get_html_img(pos, formula, img_path)

