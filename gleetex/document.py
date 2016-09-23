"""Create a LaTeX document around a formula."""


class LaTeXDocument:
    """This class represents a LaTeX document. It is intended to contain an
    equation as main content and properties to customize it. Its main purpose is
    to provide a str method which will serialize it to a full LaTeX document."""
    def __init__(self, eqn):
        self.__encoding = None
        self.__equation = eqn
        self.__displaymath = False
        self._preamble = ''
        self.__maths_env = None

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
        if any(ord(ch) > 128 for ch in self.__equation):
            if not self.__encoding:
                raise ValueError(("No encoding set, but non-ascii characters "
                        "present. Please specify an encoding."))
        encoding_preamble = ''
        if self.__encoding:
            # try to guess language and hence character set (fontenc)
            import locale
            language = locale.getdefaultlocale()
            if language: # extract just the language code
                language = language[0].split('_')[0]
            # check whether language on computer is within T1 and hence whether
            # it should be loaded; I know that this can be a misleading
            # assumption, but there's no better way that I know of
            if language in ['fr', 'es', 'it', 'de', 'nl', 'ro']:
                encoding_preamble += '\n\\usepackage[T1]{fontenc}'
            else:
                raise ValueError(("Language not supported by T1 fontenc "
                    "encoding; please report this to the GladTeX project."))
        return encoding_preamble

    def __str__(self):
        preamble = self._get_encoding_preamble() + \
                ('\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath, amssymb}'
                '\n') + (self._preamble if self._preamble else '')
        return self._format_document(preamble)

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
        return ("\\documentclass[fontsize=12pt]{scrartcl}\n\n%s\n"
            "\\usepackage[active,textmath,displaymath,tightpage]{preview} "
            "%% must be last one, see doc\n\n\\begin{document}\n%s%s%s\n"
            "\\end{document}\n") % (preamble, opening,
                    self.__equation.lstrip().rstrip(), closing)



