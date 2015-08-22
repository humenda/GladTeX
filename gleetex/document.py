"""Create a LaTeX document around a formula."""

from functools import reduce
import textwrap

class LaTeXDocument:
    """This class represents a LaTeX document. It is intended to contain an
    equation as main content and properties to customize it. Its main purpose is
    to provide a str method which will serialize it to a full LaTeX document."""
    def __init__(self, eqn):
        self.preamble = ""
        self.__encoding = None
        self.__equation = eqn
        self.__displaymath = False

    def get_encoding(self):
        """Return encoding for the document (or None)."""
        return self.__encoding

    def set_encoding(self, enc):
        """Set the encoding as used by the inputenc package."""
        # test whether encoding only onsists of letters, numbers and dashes
        valid_char = lambda x: x == '-' or x.isdigit() or x.isalpha()
        if not reduce(lambda x, y: x == y, map(valid_char, enc)):
            raise ValueError("Encoding may only consist of alphanumerical characters and dashes.")
        self.__encoding = enc

    def set_displaymath(self, flag):
        """Set whether the formula is set in displaymath."""
        if not isinstance(flag, bool):
            raise TypeError("Displaymath parameter must be of type bool.")
        self.__displaymath = flag

    def is_displaymath(self):
        return self.__displaymath

    def __str__(self):
        encoding = ''
        if self.__encoding:
            encoding = r'\usepackage[%s]{fontenc}'
        # determine characters with which to soround the formula
        opening = '\\[' if self.__displaymath else '\\('
        closing = '\\]' if self.__displaymath else '\\)'
        return textwrap.dedent("""
        \\documentclass[fontsize=12pt]{scrartcl}\n
        %s
        \\usepackage{amsmath, amssymb}
        %s
        \\usepackage[active,textmath,displaymath,tightpage]{preview} %% must be last one, see doc\n
        \\begin{document}\n%s%s%s\\end{document}""" % (
            encoding, self.preamble,
            opening, self.__equation, closing))


