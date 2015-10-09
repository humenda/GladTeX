"""In order to convert images only if they are not already cached, the cached
converter sacrifices customizability for convenience and provides a class
converting a formula directly to a png file."""

import os
import posixpath
from . import caching, document, image

class CachedConverter:
    """Convert formulas to images.

    c = CachedConverter(base_path)
    for formula in [... formulas ...]:
        pos, file_path = c.convert(formula)
        ...

    The formula is either converted  or retrieved from a cache in the same
    directory like the images."""
    GLADTEX_CACHE_FILE_NAME = 'gladtex.cache'
    def __init__(self, base_path=''):
        cache_path = os.path.join(base_path,
                CachedConverter.GLADTEX_CACHE_FILE_NAME)
        # on Windows, links in HTML pages should still use /
        self.__basepath = posixpath.join(*(base_path.split('\\')))
        self.__cache = caching.ImageCache(cache_path)
        self.__options = {'dpi' : None, 'transparency' : None,
                'background_color' : None, 'foreground_color' : None,
                'preamble' : None}


    def set_option(self, option, value):
        """Set one of the options accepted for gleetex.image.Tex2img. `option`
        must be one of self.__options without `set_`."""
        if not option in self.__options.keys():
            raise ValueError("Option must be one of " + \
                    ', '.join(self.__options.keys()))
        self.__options[option] = value

    def convert(self, formula, displaymath=False):
        """convert(formula, displaymath=False)
        Convert given formula with displaymath/inlinemath or retrieve data from
        cache.
        :param formula formula to convert
        :param displaymath whether or not to use displaymath during the conversion
        :return dictionary with position (pos), image path (path) and formula
            style (displaymath, boolean) as a dictionary with the keys in
            parenthesis
        """
        if formula in self.__cache:
            return self.__cache.get_data_for(formula)
        else:
            eqnpath = lambda x: posixpath.join(self.__basepath, 'eqn%03d.png' % x)
            num = 0
            while os.path.exists(eqnpath(num)):
                num += 1
            latex = document.LaTeXDocument(formula)
            latex.set_displaymath(displaymath)
            if self.__options['preamble']: # add preamble to LaTeX document
                latex.set_preamble_string(self.__options['preamble'])
            conv = image.Tex2img(latex, eqnpath(num))
            for option, value in self.__options.items():
                if value and hasattr(conv, 'set_' + option):
                    getattr(conv, 'set_' + option)(value)
            conv.convert()
            pos = conv.get_positioning_info()
            self.__cache.add_formula(formula,  pos, eqnpath(num), displaymath)
            self.__cache.write()
            return {'pos' : pos, 'path' : eqnpath(num), 'displaymath' :
                displaymath}

