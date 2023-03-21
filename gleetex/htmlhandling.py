# (c) 2013-2023 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""
GleeTeX is designed to allow the re-use of the image creation code
independently of the HTML conversion code. Therefore, this module contains the
code required to parse equations from HTML, to write converted HTML documents
back and to handle the exclusion of formulas too long for an HTML alt tag to
an external HTML file.
The pandoc module contains similar functions for using GleeTeX as a pandoc
filter, without using HTML as destination format.
"""

import enum
import html
import posixpath
import re

from . import sink

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
        if self.pos:
            return f'line {self.pos[0]}, {self.pos[1]}: {self.msg}'
        else:
            return self.msg


def get_position(document, index):
    """This returns the line number and position on line for the given String.

    Note: lines and positions are counted from 0.
    """
    line = document[: index + 1].count('\n')
    if document[index] == '\n':
        return (line, 0)
    newline = document[: index + 1].rfind('\n')
    newline = newline if newline >= 0 else 0
    return (line, len(document[newline:index]))


def find_anycase(where, what):
    """Find with both lower or upper case."""
    lower = where.find(what.lower())
    upper = where.find(what.upper())
    if lower >= 0:
        return lower
    return upper


class EqnParser:
    """This parser parses <eq>...</eq> in an HTML of a document.

    It's not an HTML parser, because the content within <eq>.*<eq> is
    parsed verbatim. It also parses comments, to not consider formulas
    within comments. All other cases are unhandled. Especially CData is
    problematic, although it seems like a rare use case.
    """

    class State(enum.Enum):  # ([\s\S]*?) also matches newlines
        Comment = re.compile(r'<!--([\s\S]*?)-->', re.MULTILINE)
        Equation = re.compile(
            r'<\s*(?:eq|EQ)\s*(.*?)?>([\s\S.]+?)<\s*/\s*(?:eq|EQ)>', re.MULTILINE
        )

    HTML_ENTITY = re.compile(r'(&(:?#\d+|[a-zA-Z]+);)')

    def __init__(self):
        self.__document = None
        self.__data = []
        self.__encoding = None

    def feed(self, document):
        """Feed a string or a bytes instance and start parsing.

        If a bytes instance is fed, an HTML encoding header has to be
        present, so that the encoding can be extracted.
        """
        if isinstance(document, bytes):  # try to guess encoding
            try:
                encoding = next(
                    filter(bool, CHARSET_PATTERN.search(document).groups())
                ).decode('ascii')
                document = document.decode(encoding)
            except AttributeError as e:
                raise ParseException(
                    (
                        'Could not determine encoding of '
                        'document, no charset information in the HTML header '
                        'found.'
                    )
                ) from e
            self.__encoding = encoding
        self.__document = document[:]
        self._parse()

    def find_with_offset(self, doc, start, what):
        """This find method searches in the document for a given string,
        staking the offset into account.

        Returned is the absolute position (so offset + relative match
        position) or -1 for no hit.
        """
        if isinstance(what, str):
            pos = doc[start:].find(what)
        else:
            match = what.search(doc[start:])
            pos = -1 if not match else match.span()[0]
        return pos if pos == -1 else pos + start

    def _parse(self):
        """This function parses the document, while maintaining state using the
        State enum."""
        def in_document(x): return not x == -1
        # maintain a lower-case copy, which eases searching, but doesn't affect
        # the handler methods
        doc = self.__document[:].lower()

        end = len(self.__document) - 1
        eq_start = re.compile(r'<\s*eq\s*(.*?)>')

        start_pos = 0
        while start_pos < end:
            comment = self.find_with_offset(doc, start_pos, '<!--')
            formula = self.find_with_offset(doc, start_pos, eq_start)
            if in_document(comment) and in_document(
                formula
            ):  # both present, take closest
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
            else:  # only data left
                self.__data.append(self.__document[start_pos:])
                start_pos = end

    def handle_equation(self, start_pos):
        """Parse an equation.

        The given offset should mark the beginning of this equation.
        """
        # get line and column of `start_pos`
        lnum, pos = get_position(self.__document, start_pos)

        match = EqnParser.State.Equation.value.search(
            self.__document[start_pos:])
        if not match:
            next_eq = find_anycase(self.__document[start_pos + 1:], '<eq')
            closing = find_anycase(self.__document[start_pos:], '</eq>')
            if -1 < next_eq < closing and closing > -1:
                raise ParseException('Unclosed tag found', (lnum, pos))
            raise ParseException('Malformed equation tag found', (lnum, pos))
        end = start_pos + match.span()[1]
        attrs, formula = match.groups()
        if '<eq>' in formula or '<EQ' in formula:
            raise ParseException(
                'Invalid nesting of formulas detected.', (lnum, pos))

        # replace HTML entities
        entity = EqnParser.HTML_ENTITY.search(formula)
        while entity:
            formula = re.sub(
                EqnParser.HTML_ENTITY, html.unescape(
                    entity.groups()[0]), formula
            )
            entity = EqnParser.HTML_ENTITY.search(formula)
        attrs = attrs.lower()
        displaymath = bool(attrs) and 'env' in attrs and 'displaymath' in attrs
        self.__data.append(
            # let line number count from 0 as well
            ((lnum, pos), displaymath, formula)
        )
        return end

    def handle_comment(self, start_pos):
        match = EqnParser.State.Comment.value.search(
            self.__document[start_pos:])
        if not match:
            lnum, pos = get_position(self.__document, start_pos)
            # this could be a parser issue, too
            raise ParseException(
                'Improperly formatted comment found', (lnum, pos))
        self.__data.append('<!--%s-->' % match.groups()[0])
        return start_pos + match.span()[1]  # return end of match

    def get_encoding(self):
        """Return the parsed encoding from the HTML meta data.

        If none was set, UTF-8 is assumed.
        """
        return self.__encoding

    def get_data(self):
        """Return parsed chunks.

        These are either strings or tuples with formula information, see
        class documentation.
        """
        return [x for x in self.__data if x]  # filter empty bits


def generate_label(formula):
    """Generate an id for identifying a formula as an anchor in a document.

    The generated ID is guaranteed to be valid in an XML attribute and
    it won't exceed a certain length. If you happen to have a lot of
    formulas > 150 characters with exactly the same content in the
    document, that'll cause a clash of id's.
    """
    # for some characters we just use a simple replacement (otherwise the
    # would be lost)
    mapped = {'{': '_', '}': '_',
              '(': '-', ')': '-', '\\': '.', '^': ',', '*': '_'}
    id = []
    prevchar = ''
    for c in formula:
        if prevchar == c:
            continue  # avoid multiple same characters
        if c in mapped:
            id.append(mapped[c])
        elif c.isalpha() or c.isdigit():
            id.append(c)
        prevchar = c
    # id's must start with an alphabetical character, so prefix the formula with
    # "formula" to make it a valid html id
    if id and not id[0].isalpha():
        id = ['f', 'o', 'r', 'm', '_'] + id
    if not id:  # is empty
        raise ValueError(
            "For the formula '%s' no referencable id could be generated." % formula
        )
    return ''.join(id[:150])


def format_formula_paragraph(formula):
    """Format a formula to appear as if it would have been excluded into an
    external HTML file."""
    return '<p id="%s"><pre>%s</pre></span></p>\n' % (generate_label(formula), formula)


class HtmlImageFormatter(sink.ImageFormatter):
    """Format formulas for HTML file output.

    See ImageFormatter for information about the usage of the class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _generate_link_destination(self, formula):
        html_label = generate_label(formula['formula'])
        exclusion_filelink = posixpath.join(
            self._link_prefix, self._exclusion_filepath
        )
        return f'{exclusion_filelink}#{html_label}'

    def format_internal(self, image, link_label=None):
        link_start, link_end = ('', '')
        if link_label:
            link_start = f'<a href="{link_label}">' if link_label else ''
            link_end = '</a>' if link_label else ''
        escaped_formula = html.escape(image['formula'], quote=True)
        return (
            link_start
            + (
                f'<img src="{image["url"]}" style="{image["style"]}" '
                f'alt="{escaped_formula}" height="{image["height"]}" '
                f'width="{image["width"]}" class="{image["class"]}" />'
            )
            + link_end
        )

    # Todo: this function is useless: if should be merged with format and it
    # should build up a dictionary of id, full formula; the formatting should go
    # to a separate function; link prefix and such details should be part of
    # super class; ToDo, btw, link prefix also for image paths, probably not
    # used yet in format strings of format_internal
    def add_excluded(self, image):
        self._excluded_formulas[generate_label(
            image['formula'])] = image['formula']


def write_html(file, document, formatter):
    """Processed HTML documents are made up of raw HTML chunks which are
    written back unaltered and of a processed image.

    A processed image is a former formula converted to an image with
    additional meta data. This is passed to the format function of the
    supplied formatter and the result is written to the given (open)
    file handle.
    """
    for chunk in document:
        if isinstance(chunk, dict):
            is_displaymath = chunk['displaymath']
            file.write(
                formatter.format(
                    chunk['pos'], chunk['formula'], chunk['path'], is_displaymath
                )
            )
        else:
            file.write(chunk)
