"""In order to convert images only if they are not already cached, the cached
converter sacrifices customizability for convenience and provides a class
converting a formula directly to a png file."""

import os
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
        self.__basepath = base_path
        cache_path = os.path.join(base_path,
                CachedConverter.GLADTEX_CACHE_FILE_NAME)
        self.__cache = caching.ImageCache(cache_path)
        self.__options = {'dpi' : None, 'transparency' : None,
                'background_color' : None, 'foreground_color' : None}


    def set_option(self, option, value):
        """Set one of the options accepted for gleetex.image.Tex2img. `option`
        must be one of the setters without `set_`."""
        if not option in self.__options.keys():
            raise ValueError("Option must be one of " + \
                    ', '.join(self.__options.keys()))
        self.__options[option] = value

    def convert(self, formula):
        """Convert formula / retrieve formula from cache; the action is done
        transparently.
        :param formula formula to convert
        :return tuple with positioning information and file name
        """
        if formula in self.__cache:
            return self.__cache.get_formula_data(formula)
        else:
            eqnpath = lambda x: os.path.join(self.__basepath, 'eqn%03d.png' % x)
            num = 0
            while os.path.exists(eqnpath(num)):
                num += 1
            latex = document.LaTeXDocument(formula)
            conv = image.Tex2img(latex, eqnpath(num))
            for option, value in self.__options.items():
                if value:
                    getattr(conv, 'set_' + option)(value)
            conv.convert()
            pos = conv.get_positioning_info()
            self.__cache.add_formula(formula,  pos, eqnpath(num))
            self.__cache.write()
            return (pos, eqnpath(num))

