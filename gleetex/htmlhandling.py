# (c) 2013-2021 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""GleeTeX is designed to allow the re-use of the image creation code
independently of the HTML conversion code. Therefore, this module contains the
code required to parse equations from HTML, to write converted HTML documents
back and to handle the exclusion of formulas too long for an HTML alt tag to.

/import
an external file.
The pandoc module contains similar functions for using GleeTeX as a pandoc
filter.

ToDo: completely new doc string
"""

from abc import abstractmethod
import collections
import enum
import html
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

        REturned is the absolute position (so offset + relative match
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


# pylint: disable=too-many-instance-attributes
class ImageFormatter:  # ToDo: localisation
    """ImageFormatter(is_epub=False)

    Format converted formula to be included into HTML. A typical image
    attribute will contain the path to the image, style information, a CSS class
    to be used in custom CSS style sheets and an alternative text (the LaTeX
    source) for people who disabled images or for blind screen reader users.
    If set, LaTeX formulas exceeding a configurable maximum length will be
    excluded. The image will be a link which leads to the excluded image text.
    The alt attribute is a text-only attribute and e.g. line breaks will be lost
    for screen reader users, so it makes sense for longer formulas to be
    external to be easily readable. Furthermore the alt attribute is limited in
    size, so formulas that are too long need to be treated differently.
    If that behavior is not wanted, it can be disabled and
    nothing will be excluded.

    Keyword arguments

    *   `base_path=""`: base path where images are stored, e.g. "images"
    *   `link_prefix=""`: a prefix which should be added to generated links, e.g.
        `"https://example.com/img/"`
    *   `exclusion_file_path=""`: the path which formula descriptions are
        written to which exceed a certain threshold that doesn't fit into the
        alt tag of the `img` tag
    *   `is_epub`: round height/width of the linked images to comply with the
        EPUB standard.

    Intended usage:

    fmt = ImageFormatter() # use one of the children classes
    # values as returned by Tex2img
    fmt.format(pos, formula, img_path, displaymath=False)
    fmt.format(pos2, formula2, img_path2, displaymath=True)
    ...
    img.get_excluded()
    """

    FORMULA_MAXLENGTH = 100

    def __init__(
        self, base_path, link_prefix='', exclusion_file_path='', is_epub=False
    ):
        self.__inline_maxlength = 100
        self._excluded_formulas = collections.OrderedDict()
        self.__url = ''
        self._is_epub = is_epub
        self._css = {'inline': 'inlinemath', 'display': 'displaymath'}
        self.__replace_nonascii = False
        self._link_prefix = link_prefix if link_prefix else ''
        self._exclusion_filepath = posixpath.join(
            base_path, exclusion_file_path)
        if os.path.exists(self._exclusion_filepath) and not os.access(
            self._exclusion_filepath, os.W_OK
        ):
            raise OSError(f'file {self._exclusion_filepath} not writable')

    def get_exclusion_file_path(self):
        """Return the path to the file to which formulas will be excluded too
        if their description exceeds the alt attribute length.

        May be None.
        """
        return self._exclusion_filepath if self._exclusion_filepath else None

    def set_replace_nonascii(self, flag):
        """If True, non-ascii characters will be replaced through their LaTeX
        command.

        Note that alphabetical characters will not be replaced, to allow
        easier readibility.
        """
        self.__replace_nonascii = flag

    def set_max_formula_length(self, length):
        """Set maximum length of a formula before it gets excluded into a
        separate file."""
        self.__inline_maxlength = length

    def set_inline_math_css_class(self, css):
        """set css class for inline math."""
        self._css['inline'] = css

    @abstractmethod
    def _generate_link_label(self, formula):
        """Generate the link to an excluded formula, consisting either of path
        and label or just a label.

        The label is generated uniquely for each label by this function.
        This function needs to be customised by implementors, e.g. to
        return "foo.html#formula" or "#formula", etc.
        """

    def set_display_math_css_class(self, css):
        """set css class for display math."""
        self._css['display'] = css

    def set_is_epub(self, flag):
        """Active rounding of height and weight attribute of the formula images
        to comply with the EPUB standard."""
        self._is_epub = flag

    def set_url(self, prefix):
        """Set URL prefix which is used as a prefix to the image file in the
        HTML link."""
        self.__url = prefix

    def get_excluded(self):
        """Return a list of LaTeX formulas that did not fit the alt tag and
        were hence formatted separately, e.g. into a separate document."""
        return self._excluded_formulas

    def _process_image(self, pos, formula, img_path, displaymath=False):
        """Process positioning of the image and the various URI-related
        parameters into formatting information.

        :param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :param displaymath display or inline math (default False, inline maths)
        :returns a dictionary with the information about the image; its keys
            correspond to HTML image attributes, except for "url" and "image".
        """
        image = {'formula': formula}
        full_url = img_path
        if self.__url:
            full_url = self.__url.rstrip('/') + '/' + img_path
        image['url'] = full_url
        # depth is a negative offset (float, first, str later)
        depth = float(pos['depth']) * -1
        if self._is_epub:
            depth = str(int(depth))
        else:
            depth = f'{depth:.2f}'
        image['style'] = 'vertical-align: {depth}px; margin: 0;'

        image['class'] = self._css['display'] if displaymath else self._css['inline']
        if self._is_epub:
            image.update(
                {'height': str(int(pos['height'])),
                 'width': str(int(pos['width']))}
            )
        else:
            image.update(
                {'height': f"{pos['height']:.2f}",
                    'width': f"{pos['width']:.2f}"}
            )
        return image

    @abstractmethod
    def add_excluded(self, image):
        """Add a formula to the list of excluded formulas."""

    @abstractmethod
    def format_internal(self, image, link_label=None):
        """Format an internal formula for the target output (defined by the
        class).

        :param image formula information as returned by _process_image; formula
            will have been shortened if it were too long
        :param link_label if not None, the formula image will contian a reference
        or link to the long version of the formula (e.g. because it didn't fit
        the alt attribute)
        """

    def format(self, pos, formula, img_path, displaymath=False):
        """This method formats a formula. It invokes the abstract methods
        `format_internal` and `add_excluded`. `add_excluded` is only invoked if
        the formula is too long and if exclusion has been configured. This
        method returns the formatted image. The formatted image will contain a
        reference to the excluded formula source, if applicable. The formatted
        excluded formulas can be retrieved using get_excluded().

        :param pos dictionary containing keys depth, height and width
        :param formula LaTeX alternative text
        :param img_path: path to image
        :param displaymath whether or not formula is in display math (default: no)
        :returns a tuple containing the formatted image and, if applicable, the
            excluded image alternate text.
        """
        formula = typesetting.increase_readability(
            formula, self.__replace_nonascii)
        processed_data = self._process_image(
            pos, formula, img_path, displaymath)
        shortened_processed_data = processed_data.copy()
        shortened_processed_data['formula'] = formula
        link_destination = None
        if len(formula) > ImageFormatter.FORMULA_MAXLENGTH:
            shortened_processed_data['formula'] = (
                formula[: ImageFormatter.FORMULA_MAXLENGTH] + '...'
            )
            link_destination = self._generate_link_destination(processed_data)
        if len(formula) > self.__inline_maxlength:
            # builds up internal list of formatted excluded formulas
            self.add_excluded(processed_data)
        return self.format_internal(shortened_processed_data, link_destination)


class HtmlImageFormatter(ImageFormatter):
    """Format formulas for HTML file output.

    See ImageFormatter for information about the usage of the class.
    """

    def __init__(self, base_path='', link_prefix='', exclusion_file_path='', is_epub=False):
        super().__init__(base_path, link_prefix, exclusion_file_path, is_epub)

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

    An processed image is a former formula converted to an image with
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
