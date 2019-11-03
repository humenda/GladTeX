# (c) 2013-2019 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""GleeTeX is designed to allow the re-use of the image creation code
independently of the HTML conversion code. Therefore, this modules contains the
code required to parse equations from HTML, to write converted HTML documents
back and to handle the outsourcing of formulas too long for an HTML alt tag to
an external file.
The pandoc module contains similar functions for using GleeTeX as a pandoc
filter."""

import collections
import enum
import html.parser
import os
import posixpath
import re

from . import typesetting

# match HTML 4 and 5
CHARSET_PATTERN = re.compile(
        rb'(?:content="text/html; charset=(.*?)"|charset="(.*?)")')

class ParseException(Exception):
    """Exception to propagate a parsing error."""
    def __init__(self, msg, pos=None):
        self.msg = msg
        self.pos = pos
        super().__init__(msg, pos)

    def __str__(self):
        return ('line {0.pos[0]}, {0.pos[1]}: {0.msg}'.format(self)
                if self.pos else self.msg)

def get_position(document, index):
    """This returns the line number and position on line for the given String.
    Note: lines and positions are counted from 0."""
    line = document[:index+1].count('\n')
    if document[index] == '\n':
        return (line, 0)
    newline = document[:index+1].rfind('\n')
    newline = (newline if newline >= 0 else 0)
    return (line, len(document[newline:index]))


def find_anycase(where, what):
    """Find with both lower or upper case."""
    lower = where.find(what.lower())
    upper = where.find(what.upper())
    if lower >= 0:
        return lower
    return upper

class EqnParser:
    """This parser parses <eq>...</eq> our of a document. It's not an HTML
    parser, because the content within <eq>.*<eq> is parsed verbatim.
    It also parses comments, to not consider formulas within comments. All other
    cases are unhandled. Especially CData is problematic, although it seems like
    a rare use case."""
    class State(enum.Enum): # ([\s\S]*?) also matches newlines
        Comment = re.compile(r'<!--([\s\S]*?)-->', re.MULTILINE)
        Equation = re.compile(r'<\s*(?:eq|EQ)\s*(.*?)?>([\s\S.]+?)<\s*/\s*(?:eq|EQ)>',
                re.MULTILINE)

    HTML_ENTITY = re.compile(r'(&(:?#\d+|[a-zA-Z]+);)')

    def __init__(self):
        self.__document = None
        self.__data = []
        self.__encoding = None

    def feed(self, document):
        """Feed a string or a bytes instance and start parsing. If a bytes
        instance is fed, an HTML encoding header has to be present, so that the
        encoding can be extracted."""
        if isinstance(document, bytes): # try to guess encoding
            try:
                encoding = next(filter(bool, CHARSET_PATTERN.search(document)
                        .groups())).decode('ascii')
                document = document.decode(encoding)
            except AttributeError:
                raise ParseException(("Could not determine encoding of "
                        "document, no charset information in the HTML header "
                        "found."))
            self.__encoding = encoding
        self.__document = document[:]
        self._parse()

    def find_with_offset(self, doc, start, what):
        """This find method searches in the document for a given string, staking
        the offset into account. REturned is the absolute position (so offset +
        relative match position) or -1 for no hit."""
        if isinstance(what, str):
            pos = doc[start:].find(what)
        else:
            match = what.search(doc[start:])
            pos = (-1 if not match else match.span()[0])
        return (pos if pos == -1 else pos + start)


    def _parse(self):
        """This function parses the document, while maintaining state using the
        State enum."""
        in_document = lambda x: not x == -1
        # maintain a lower-case copy, which eases searching, but doesn't affect
        # the handler methods
        doc = self.__document[:].lower()

        end = len(self.__document) - 1
        eq_start = re.compile(r'<\s*eq\s*(.*?)>')

        start_pos = 0
        while start_pos < end:
            comment = self.find_with_offset(doc, start_pos, '<!--')
            formula = self.find_with_offset(doc, start_pos, eq_start)
            if in_document(comment) and in_document(formula): # both present, take closest
                if comment < formula:
                    self.__data.append(self.__document[start_pos:comment])
                    start_pos = self.handle_comment(comment)
                else:
                    self.__data.append(self.__document[start_pos:formula])
                    start_pos = self.handle_equation(formula)
            elif in_document(formula):
                self.__data.append(self.__document[start_pos:formula])
                start_pos = self.handle_equation(formula)
            elif in_document(comment):
                self.__data.append(self.__document[start_pos:comment])
                start_pos = self.handle_comment(comment)
            else: # only data left
                self.__data.append(self.__document[start_pos:])
                start_pos = end


    def handle_equation(self, start_pos):
        """Parse an equation. The given offset should mark the beginning of this
        equation."""
        # get line and column of `start_pos`
        lnum, pos = get_position(self.__document, start_pos)

        match = EqnParser.State.Equation.value.search(self.__document[start_pos:])
        if not match:
            next_eq = find_anycase(self.__document[start_pos+1:], '<eq')
            closing = find_anycase(self.__document[start_pos:], '</eq>')
            if -1 < next_eq < closing and closing > -1:
                raise ParseException("Unclosed tag found", (lnum, pos))
            raise ParseException("Malformed equation tag found", (lnum, pos))
        end = start_pos + match.span()[1]
        attrs, formula = match.groups()
        if '<eq>' in formula or '<EQ' in formula:
            raise ParseException("Invalid nesting of formulas detected.", (lnum,
                pos))

        # replace HTML entities
        entity = EqnParser.HTML_ENTITY.search(formula)
        while entity:
            formula = re.sub(EqnParser.HTML_ENTITY,
                    html.unescape(entity.groups()[0]), formula)
            entity = EqnParser.HTML_ENTITY.search(formula)
        attrs = attrs.lower()
        displaymath = bool(attrs) and 'env' in attrs and 'displaymath' in attrs
        self.__data.append(((lnum, pos), # let line number count from 0 as well
                displaymath, formula))
        return end


    def handle_comment(self, start_pos):
        match = EqnParser.State.Comment.value.search(self.__document[start_pos:])
        if not match:
            lnum, pos = get_position(self.__document, start_pos)
            # this could be a parser issue, too
            raise ParseException("Improperly formatted comment found", (lnum,
                pos))
        self.__data.append('<!--%s-->' % match.groups()[0])
        return start_pos + match.span()[1] # return end of match

    def get_encoding(self):
        """Return the parsed encoding from the HTML meta data. If none was set,
        UTF-8 is assumed."""
        return self.__encoding

    def get_data(self):
        """Return parsed chunks. These are either strings or tuples with formula
        information, see class documentation."""
        return list(x for x in self.__data if x) # filter empty bits


def gen_id(formula):
    """Generate an id for identifying a formula as an anchor in a document.
    The generated ID is guaranteed to be valid in an XML attribute and it won't
    exceed a certain length.
    If you happen to have a lot of formulas > 150 characters with exactly
    the same content in the document, that'll cause a clash of id's."""
    # for some characters we just use a simple replacement (otherwise the
    # would be lost)
    mapped = {'{':'_', '}':'_', '(':'-', ')':'-', '\\':'.', '^':',', '*':'_'}
    id = []
    prevchar = ''
    for c in formula:
        if prevchar == c:
            continue # avoid multiple same characters
        if c in mapped:
            id.append(mapped[c])
        elif c.isalpha() or c.isdigit():
            id.append(c)
        prevchar = c
    # id's must start with an alphabetical character, so prefix the formula with
    # "formula" to make it a valid html id
    if id and not id[0].isalpha():
        id = ['f', 'o', 'r', 'm', '_'] + id
    if not id: # is empty
        raise ValueError("For the formula '%s' no referencable id could be generated." \
                    % formula)
    return ''.join(id[:150])


class OutsourcedFormulaParser(html.parser.HTMLParser):
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
        super().__init__(convert_charrefs=False)

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

    def error(self, message):
        raise ParseException(message, ('unknown', 'unknown'))

def format_formula_paragraph(formula):
    """Format a formula to appear as if it would have been outsourced into an
    external file."""
    return '<p id="%s"><pre>%s</pre></span></p>\n' % \
            (gen_id(formula), formula)


class HtmlImageFormatter: # ToDo: localisation
    """HtmlImageFormatter(exclusion_filepath='outsourced_formulas.html',
            encoding="UTF-8")
    Format converted formula to be included into the HTML. A typical image
    attribute will contain the path to the image, style information, a CSS class
    to be used in custom CSS style sheets and an alternative text (the LaTeX
    source) for people who disabled images or for blind screen reader users.
    If set, LaTeX formulas exceeding a configurable maximum length will be
    excluded. The image will be a link which leads to the excluded image text.
    The alt attribute is a text-only attribute and e.g. line breaks will be lost
    for screen reader users, so it makes sense for longer formulas to be
    external to be easily readable. Furthermore the alt attribute is limited to
    255 characters, so formula blocks exceeding that limit need to be treated
    differently anyway. If that behavior is not wanted, it can be disabled and
    nothing will be excluded."""

    EXCLUSION_FILE_NAME = 'outsourced-descriptions.html'
    HTML_TEMPLATE_HEAD = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"' +
        '\n  "http://www.w3.org/TR/html4/strict.dtd">\n<html>\n<head>\n' +
        '<meta http-equiv="content-type" content="text/html; charset=utf-8"/>' +
        '\n<title>Outsourced Formulas</title>\n</head>\n<!-- ' +
        'DO NOT MODIFY THIS FILE, IT IS AUTOMATICALLY GENERATED -->\n<body>\n')
    def __init__(self, base_path='', link_prefix=None):
        self.__exclude_descriptions = False
        self.__link_prefix = (link_prefix if link_prefix else '')
        self.__base_path = (base_path if base_path else '')
        self.__exclusion_filepath = posixpath.join(self.__base_path, HtmlImageFormatter.EXCLUSION_FILE_NAME)
        if os.path.exists(self.__exclusion_filepath):
            if not os.access(self.__exclusion_filepath, os.W_OK):
                raise OSError('The file %s is not writable!' %
                        self.__exclusion_filepath)
        self.__inline_maxlength=100
        self.__file_head = HtmlImageFormatter.HTML_TEMPLATE_HEAD
        self.__cached_formula_pars = collections.OrderedDict()
        self.__url = ''
        self.initialized = False
        self.initialize() # read already written file, if any
        self.__css = {'inline' : 'inlinemath', 'display' : 'displaymath'}
        self.__replace_nonascii = False

    def set_replace_nonascii(self, flag):
        """If True, non-ascii characters will be replaced through their LaTeX
        command. Note that alphabetical characters will not be replaced, to
        allow easier readibility."""
        self.__replace_nonascii = flag

    def set_max_formula_length(self, length):
        """Set maximum length of a formula before it gets outsourced into a
        separate file."""
        self.__inline_maxlength = length

    def set_inline_math_css_class(self, css):
        """set css class for inline math."""
        self.__css['inline'] = css

    def set_display_math_css_class(self, css):
        """set css class for display math."""
        self.__css['display'] = css

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
        with open(self.__exclusion_filepath, 'r', encoding='UTF-8') as f:
            document = f.read()
        # parse html document:
        parser = OutsourcedFormulaParser()
        parser.feed(document)
        self.__file_head = parser.get_head()
        self.__cached_formula_pars = parser.get_formulas()
        return self

    def __enter__(self):
        return self

    def __exit__(self, useless, unused, not_applicable):
        self.close()

    def close(self):
        """Write back file with excluded image descriptions, if any."""
        def formula2paragraph(frml):
            return '<p id="%s"><pre>%s</pre></p>' % (gen_id(frml), frml)
        if not self.__cached_formula_pars:
            return
        with open(self.__exclusion_filepath, 'w', encoding='utf-8') as f:
            f.write(self.__file_head)
            f.write('\n<hr />\n'.join([formula2paragraph(formula) \
                    for formula in self.__cached_formula_pars.values()]))
            f.write('\n</body>\n</html>\n')

    def get_html_img(self, pos, formula, img_path, displaymath=False):
        """:param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :param displaymath display or inline math (default False, inline maths)
        :returns a string with the formatted HTML"""
        full_url = img_path
        if self.__url:
            if self.__url.endswith('/'): self.__url = self.__url[:-1]
            full_url = self.__url + '/' + img_path
        # depth is a negative offset
        depth = float(pos['depth']) * -1
        css = (self.__css['display'] if displaymath else self.__css['inline'])
        return ('<img src="{0}" style="vertical-align: {3:.2f}px; margin: 0;" '
                'height="{2[height]:.2f}" width="{2[width]:.2f}" alt="{1}" '
                'class="{4}" />').format(full_url, formula, pos, depth, css)

    def format_excluded(self, pos, formula, img_path, displaymath=False):
        """This method formats a formula and an formula image in HTML and
        additionally writes the formula to an external (configured) file to
        which the image links to. That's useful for blind screen reader users
        who can then easily have a look at the formula.
        :param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :param displaymath if set to true, image is treated as display math formula (default False)
        :returns string with formatted HTML image which also links to excluded
        formula"""
        shortened = (formula[:100] + '...'  if len(formula) > 100 else formula)
        img = self.get_html_img(pos, shortened, img_path, displaymath)
        identifier = gen_id(formula)
        # write formula out to external file
        if identifier not in self.__cached_formula_pars:
            self.__cached_formula_pars[identifier] = formula
        exclusion_filelink = posixpath.join(self.__link_prefix, self.__exclusion_filepath)
        return '<a href="{}#{}">{}</a>'.format(exclusion_filelink,
                gen_id(formula), img)

    def format(self, pos, formula, img_path, displaymath=False):
        """This method formats a formula. If self.__exclude_descriptions is set
        and the formula igreater than the configured length, the formula will be
        outsourced, otherwise it'll be included in the IMG's alt tag. In either
        case, a string for the current document containing the formatted HTML is returned.
        :param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :param displaymath whether or not formula is in display math (default: no)
        :returns string with formatted HTML image which also links to excluded
        formula"""
        formula = typesetting.increase_readability(formula,
                self.__replace_nonascii)
        if self.__exclude_descriptions and \
                len(formula) > self.__inline_maxlength:
            return self.format_excluded(pos, formula, img_path, displaymath)
        return self.get_html_img(pos, formula, img_path, displaymath)

def write_html(file, document, formatter):
    """Processed HTML documents are made up of raw HTML chunks which are written
    back unaltered and of processed image. An processed image is a former
    formula converted to an image with additional meta data. This is passed to
    the format function of the supplied formatter and the result is written to
    the given (open) file handle."""
    for chunk in document:
        if isinstance(chunk, dict):
            is_displaymath = chunk['displaymath']
            file.write(formatter.format(chunk['pos'], chunk['formula'],
                    chunk['path'], is_displaymath))
        else:
            file.write(chunk)
