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
    directory like the images.

    :param base_path directory to place files in (relative to the file
            converted. So if the file being converted is foo/bar.htex and the
            base_path is set to img, the image will be placed in foo/img/.
    :param linkpath path to be prepended to each of the generated files; useful
        if the document is placed on a server and the image directory resides
        somewhere else
    :param keep_old_cache If an existing cache cannot be read (incompatible
        GladTeX version, ...) Aand the flag is set, the program will simple
        crash and tell the user to remove the cache (default). If set to False,
        the program will instead remove the cache and all eqn* files and
        recreate the cache.
    """
    GLADTEX_CACHE_FILE_NAME = 'gladtex.cache'
    def __init__(self, base_path='', linkpath='', keep_old_cache=False):
        if not os.path.exists(os.path.join(base_path, linkpath)) and (base_path
                or linkpath):
            os.makedirs(os.path.join(base_path, linkpath))
        cache_path = os.path.join(base_path, linkpath,
                CachedConverter.GLADTEX_CACHE_FILE_NAME)
        self.__base_path = base_path
        # on Windows, links in HTML pages should still use /
        self.__linkpath = linkpath
        self.__cache = caching.ImageCache(cache_path,
                keep_old_cache=keep_old_cache)
        self.__options = {'dpi' : None, 'transparency' : None,
                'background_color' : None, 'foreground_color' : None,
                'preamble' : None, 'latex_maths_env' : None}


    def set_option(self, option, value):
        """Set one of the options accepted for gleetex.image.Tex2img. `option`
        must be one of dpi, transparency, background_color, foreground_color,
        preamble, latex_maths_env."""
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
            eqnpath = lambda x: posixpath.join(self.__linkpath, 'eqn%03d.png' % x)
            num = 0
            while os.path.exists(os.path.join(self.__base_path, eqnpath(num))):
                num += 1
            latex = document.LaTeXDocument(formula)
            latex.set_displaymath(displaymath)
            if self.__options['preamble']: # add preamble to LaTeX document
                latex.set_preamble_string(self.__options['preamble'])
            if self.__options['latex_maths_env']:
                latex.set_latex_environment(self.__options['latex_maths_env'])
            conv = image.Tex2img(latex, os.path.join(self.__base_path,
                eqnpath(num)))
            for option, value in self.__options.items():
                if value and hasattr(conv, 'set_' + option):
                    getattr(conv, 'set_' + option)(value)
            conv.convert()
            pos = conv.get_positioning_info()
            self.__cache.add_formula(formula, pos, eqnpath(num), displaymath)
            self.__cache.write()
            return {'pos' : pos, 'path' : eqnpath(num), 'displaymath' :
                displaymath}

