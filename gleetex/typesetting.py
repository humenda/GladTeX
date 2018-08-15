# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""This module contains functionality to typeset formuas for the usage in a
LaTeX document (e.g. creating the preamble, replacing non-ascii letters) and to
typeset LaTeX formulas in a more readable way as alternate description of the
resulting image. """

from . import unicode

FORMATTING_COMMANDS = ['\\ ', '\\,', '\\;', '\\big', '\\Big', '\\left',
        '\\right', '\\limits']



class DocumentSerializationException(Exception):
    """This error is raised whenever a non-ascii character contained in a
    formula could not be replaced by a LaTeX command.
    It provides the following attributes:
    formula - the formula
    index - position in formula
    upoint - unicode point."""
    def __init__(self, formula, index, upoint):
        self.formula = formula
        self.index = index
        self.upoint = upoint
        super().__init__(formula, index, upoint)

    def __str__(self):
        return ("could not find LaTeX replacement command for unicode "
                "character %d, index %d in formula %s") % (self.upoint,
                    self.index, self.formula)


def escape_unicode_maths(formula, replace_alphabeticals=True):
    """This function uses the unicode table to replace any non-ascii character
    (identified with its unicode code point)  with a LaTeX command.
    It also parses the formula for commands as e.g. \\\text or \\mbox and
    applies text-mode commands within them.
    This allows the conversion of formulas with unicode maths with old-style
    LaTeX2e, which gleetex depends on."""
    if not any(ord(ch) > 160 for ch in formula):
        return formula # no umlauts, no replacement

    # characters in math mode need a different replacement than in text mode.
    # Therefore, the string has to be split into parts of math and text mode.
    chunks = []
    if not ('\\text' in formula or '\\mbox' in formula):
        #    no text mode, so tread a
        chunks = [formula]
    else:
        start = 0
        while '\\text' in formula[start:] or '\\mbox' in formula[start:]:
            index = formula[start:].find('\\text')
            if index < 0:
                index = formula[start:].find('\\mbox')
            opening_brace = formula[start + index:].find('{') + start + index
            # add text before text-alike command and the command itself to chunks
            chunks.append(formula[start:opening_brace])
            closing_brace = get_matching_brace(formula, opening_brace)
            # add text-mode stuff
            chunks.append(formula[opening_brace:closing_brace + 1])
            start = closing_brace + 1
        # add last chunk
        chunks.append(formula[start:])

    is_math = True
    for index, chunk in enumerate(chunks):
        try:
            chunks[index] = replace_unicode_characters(chunk, is_math,
                    replace_alphabeticals=replace_alphabeticals)
        except ValueError as e: # unicode point missing
            index = int(e.args[0])
            raise DocumentSerializationException(formula, index,
                    ord(formula[index])) from None
        is_math = not is_math
    return ''.join(chunks)


def replace_unicode_characters(characters, is_math, replace_alphabeticals=True):
    """Replace all non-ascii characters within the given string with their LaTeX
    equivalent. The boolean is_math indicates, whether text-mode commands (like
    in \\text{}) or the amsmath equivalents should be used.
    When replace_alphabeticals is False, alphabetical characters will not be
    replaced through their LaTeX command when in text mode, so that text within
    \\text{} (and similar) is not garbled. For instance, \\text{für} is be
    replaced by \\text{f\"{u}r} when replace_alphabeticals=True. This is useful
    for the alt attribute of an image, where the reader might want to read
    the normal text as such.
    This function raises a ValueError if a unicode point is not in the table.
    The first argument of the ValueError is the index within the string, where
    the unknown unicode character has been encountered."""
    result = []
    for idx, character in enumerate(characters):
        if ord(character) < 168: # ignore normal ascii character and unicode control sequences
            result.append(character)
        # treat alphanumerical characters differently when in text mode, see doc
        # string; don't replace alphabeticals if specified
        elif character.isalpha() and not replace_alphabeticals:
            result.append(character)
        else:
            mode = (unicode.LaTeXMode.mathmode if is_math else
                    unicode.LaTeXMode.textmode)
            commands = unicode.unicode_table.get(ord(character))
            if not commands: # unicode point missing in table
                # is catched one level above; provide index for more concise error output
                raise ValueError(characters.index(character))
            # if math mode and only a text alternative exists, add \\text{}
            # around it
            if mode == unicode.LaTeXMode.mathmode and mode not in commands:
                result.append('\\text{%s}' % commands[unicode.LaTeXMode.textmode])
            else:
                result.append(commands[mode])
                # if the next character is alphabetical, add space
                if (idx+1) < len(characters) and characters[idx+1].isalpha() \
                        and commands[mode][-1].isalpha():
                    result.append(' ')
    return ''.join(result)

def get_matching_brace(string, pos_of_opening_brace):
    if string[pos_of_opening_brace] != '{':
        raise ValueError("index %s in string %s: not a opening brace" % \
            (pos_of_opening_brace, repr(string)))
    counter = 1
    for index, ch in enumerate(string[pos_of_opening_brace + 1:]):
        if ch == '{':
            counter += 1
        elif ch == '}':
            counter -= 1
            if counter == 0:
                return pos_of_opening_brace + index + 1
    if counter != 0:
        raise ValueError("Unbalanced braces in formula " + repr(string))



#pylint: disable=too-many-instance-attributes
class LaTeXDocument:
    """This class represents a LaTeX document. It is intended to contain an
    equation as main content and properties to customize it. Its main purpose is
    to provide a str method which will serialize it to a full LaTeX document.
    """
    def __init__(self, eqn):
        self.__encoding = None
        self.__equation = eqn
        self.__displaymath = False
        self.__fontsize = 12
        self.__background_color = None
        self.__foreground_color = None
        self._preamble = ''
        self.__maths_env = None
        self.__replace_nonascii = False

    def _parse_color(self, color):
        # could be a valid color name
        try: # hex number?
            return int(color, 16)
        except ValueError:
            return color # treat as normal dvips compatible colour name

    def set_background_color(self, color):
        """Set the background color. The `color` can be either a valid dvips
        name or a tuple with RGB values between 0 and 1. If unset, the image
        will be transparent."""
        self.__background_color = self._parse_color(color)

    def set_foreground_color(self, color):
        """Set the foreground color. The `color` can be either a valid dvips
        name or a tuple with RGB values between 0 and 1. If unset, the text
        will be black."""
        self.__foreground_color = self._parse_color(color)

    def set_replace_nonascii(self, flag):
        """If True, all non-ascii character will be replaced through a LaTeX
        command."""
        self.__replace_nonascii = flag

    def set_latex_environment(self, env):
        """Set maths environment name like `displaymath` or `flalign*`."""
        self.__maths_env = env

    def get_latex_environment(self):
        return self.__maths_env

    def get_encoding(self):
        """Return encoding for the document (or None)."""
        return self.__encoding

    def set_preamble_string(self, p):
        """Set the string to add to the preamble of the LaTeX document."""
        self._preamble = p

    def set_encoding(self, encoding):
        """Set the encoding as used by the inputenc package."""
        if encoding.lower().startswith('utf') and '8' in encoding:
            self.__encoding = 'utf8'
        elif (encoding.lower().startswith('iso') and '8859' in encoding) or \
                encoding.lower() == 'latin1':
            self.__encoding = 'latin1'
        else:
            # if you plan to add an encoding, you have to adjust the str
            # function, which also loads the  fontenc package
            raise ValueError(("Encoding %s is not supported at the moment. If "
                "you want to use LaTeX 2e, you should report a bug at the home "
                "page of GladTeX.") % encoding)

    def set_displaymath(self, flag):
        """Set whether the formula is set in displaymath."""
        if not isinstance(flag, bool):
            raise TypeError("Displaymath parameter must be of type bool.")
        self.__displaymath = flag

    def is_displaymath(self):
        return self.__displaymath

    def _get_encoding_preamble(self):
        # first check whether there are umlauts within the formula and if so, an
        # encoding has been set
        if any(ord(ch) > 128 for ch in self.__equation) and \
                not self.__replace_nonascii:
            if not self.__encoding:
                raise ValueError(("No encoding set, but non-ascii characters "
                        "present. Please specify an encoding."))
        encoding_preamble = ''
        if self.__encoding:
            # try to guess language and hence character set (fontenc)
            import locale
            language = locale.getdefaultlocale()
            if language and language[0]: # extract just the language code
                language = language[0].split('_')[0]
            if not language or not language[0]:
                language = 'en'
            # check whether language on computer is within T1 and hence whether
            # it should be loaded; I know that this can be a misleading
            # assumption, but there's no better way that I know of
            if language in ['fr', 'es', 'it', 'de', 'nl', 'ro', 'en']:
                encoding_preamble += '\n\\usepackage[T1]{fontenc}'
            else:
                raise ValueError(("Language not supported by T1 fontenc "
                    "encoding; please report this to the GladTeX project."))
        return encoding_preamble

    def set_fontsize(self, size_in_pt):
        """Set fontsize in pt, 12 pt by default."""
        self.__fontsize = size_in_pt

    def get_fontsize(self, size_in_pt):
        return self.__fontsize

    def __str__(self):
        preamble = self._get_encoding_preamble() + \
                ('\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath, amssymb}'
                '\n') + (self._preamble if self._preamble else '')
        return self._format_document(preamble)

    def _format_color_definition(self, which):
        color = getattr(self, '_%s__%s_color' % (self.__class__.__name__,
            which))
        if not color or isinstance(color, str):
            return ''
        return ('\\definecolor{%s}{HTML}{%s}' % (which,
                    hex(color)[2:].upper().zfill(6)))

    def _format_colors(self):
        color_defs = (self._format_color_definition('background'),
                self._format_color_definition('foreground'),)
        color_body = ''
        if self.__background_color:
            color_body += ('\\pagecolor{%s}' % ('background' if color_defs[0]
                        else self.__background_color))
        if self.__foreground_color:
            # opening brace isn't required here, inserted automatically
            color_body += ('\\color{%s}' % ('foreground' if color_defs[1]
                    else self.__foreground_color))
        return (''.join(color_defs), color_body)


    def _format_document(self, preamble):
        """Return a formatted LaTeX document with the specified formula
        embedded."""
        opening, closing = None,None
        if self.__maths_env:
            opening = '\\begin{%s}' % self.__maths_env
            closing = '\\end{%s}' % self.__maths_env
        else:
            # determine characters with which to surround the formula
            opening = '\\[' if self.__displaymath else '\\('
            closing = '\\]' if self.__displaymath else '\\)'
        formula = self.__equation.lstrip().rstrip()
        if self.__replace_nonascii:
            formula = escape_unicode_maths(formula, replace_alphabeticals=True)
        fontsize = 'fontsize=%ipt' % self.__fontsize
        color_preamble, color_body = self._format_colors()
        return ("\\documentclass[%s, fleqn]{scrartcl}\n\n%s\n"
            "\\usepackage[dvipsnames]{xcolor}\n"
            "%s\n" # color definitions, if applicable
            "\\usepackage[active,textmath,displaymath,tightpage]{preview} "
            "%% must be last one, see doc\n\n\\begin{document}\n"
            "\\noindent%%\n"
            "\\begin{preview}{%s"
            "%s%s%s}\\end{preview}\n"
            "\\end{document}\n") % (fontsize, preamble, color_preamble,
                    color_body, opening, formula, closing)


def increase_readability(formula, replace_nonascii=False):
    """In alternate texts for non-image users or those using a screen reader,
    the LaTeX code should be as readable as possible. Therefore the formula
    should not contain unicode characters or formatting instructions."""
    if replace_nonascii:
        # keep umlauts, etc; makes the alt more readable, yet wouldn't compile
        formula = escape_unicode_maths(formula, replace_alphabeticals=False)
    # replace formatting-only symbols which distract the reader
    formula_changed = True
    while formula_changed:
        formula_changed = False
        for command in FORMATTING_COMMANDS:
            idx = formula.find(command)
            # only replace if it's not after a \\ and not part of a longer command
            if (idx > 0 and formula[idx-1] != '\\') or idx == 0:
                end = idx + len(command)
                # following conditions for replacement must be met:
                # command doesn't end on alphabet. char. and is followed by same
                # category OR end of string reached OR command does not # end on
                # alphabetical char. at all
                if end >= len(formula) or not command[-1].isalpha() \
                        or not formula[end].isalpha():
                    formula = formula[:idx] + ' ' + formula[idx + len(command):]
                    formula = formula.replace('  ', ' ')
                    formula_changed = True
    return formula
