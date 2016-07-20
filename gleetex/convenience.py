"""In order to convert images only if they are not already cached, the cached
converter sacrifices customizability for convenience and provides a class
converting a formula directly to a png file."""

import concurrent.futures
import os
import subprocess

from . import caching, document, image
from .caching import unify_formula

class ConversionException(Exception):
    """This exception is raised whenever a problem occurs during conversion.
    Example:
    c = ConversionException("cause", 10, 38, 5)
    assert c.cause == cause
    assert c.src_line_number == 10 # line number in source document (counting from 1)
    assert c.src_pos_on_line == 38 # position of formula in source line, counting from 1
    assert c.formula_count == 5 # fifth formula in document (starting from 1)
    """
    def __init__(self, cause, src_line_number, src_pos_on_line, formula_count):
        # provide a default error message
        super().__init__("LaTeX failed at formula line {}, {}, no. {}: {}".format(
            src_line_number, src_pos_on_line, formula_count, cause))
        # provide attributes for upper level error handling
        self.cause = cause
        self.src_line_number = src_line_number
        self.src_pos_on_line = src_pos_on_line
        self.formula_count = formula_count

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

    #pylint: disable=too-many-locals
    def convert_all(self, base_path, formulas):
        """convert_all(formulas)
        Convert all formulas using self.convert using concurrently. Each
        element of `formulas` must be a tuple containing (formula, displaymath,
        Formulas already contained in the cache are not convered.
        """
        formulas_to_convert = self._get_formulas_to_convert(base_path, formulas)
        self._convert_concurrently(formulas, formulas_to_convert)

    def _get_formulas_to_convert(self, base_path, formulas):
        """Return a list of formulas to convert, along with their count in the
        global list of formulas of the document being converted and the file
        name. Function was decomposed for better testability."""
        formulas_to_convert = [] # find as many file names as equations
        file_name_count = 0
        eqn_path = lambda x: '%s/eqn%03d.png' % (base_path, x)

        formula_was_converted = lambda x: unify_formula(x) in \
                (unify_formula(u[0]) for u in formulas_to_convert)
        # find enough free file names
        for formula_count, (_pos, dsp, formula) in enumerate(formulas):
            if not self.__cache.contains(formula, dsp) and not formula_was_converted(formula):
                while os.path.exists(eqn_path(file_name_count)):
                    file_name_count += 1
                formulas_to_convert.append((formula, eqn_path(file_name_count),
                    dsp, formula_count + 1))
        return formulas_to_convert


    def _convert_concurrently(self, formulas, formulas_to_convert):
        """The actual concurrent conversion process. Method is intended to be
        called from convert_all()."""
        # convert missing formulas
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # start conversion and mark each thread with it's formula
            jobs = {executor.submit(self.convert, eqn, path, dsp): (eqn, count)
                for (eqn, path, dsp, count) in formulas_to_convert}
            for future in concurrent.futures.as_completed(jobs):
                formula, formula_count = jobs[future]
                try:
                    data = future.result()
                except subprocess.SubprocessError as e:
                    # retrieve the position (line, pos on line) in the source
                    # document from original formula list
                    pos = next(pos for pos, _d, f in formulas
                        if unify_formula(f) == unify_formula(formula))
                    raise ConversionException(str(e.args[0]), *pos, formula_count)
                else:
                    self.__cache.add_formula(formula, data['pos'], data['path'],
                        data['displaymath'])
                    self.__cache.write()




    def convert(self, formula, output_path, displaymath=False):
        """convert(formula, output_path, displaymath=False)
        Convert given formula with displaymath/inlinemath.
        :param formula formula to convert
        :param output_path image output path
        :param displaymath whether or not to use displaymath during the conversion
        :return dictionary with position (pos), image path (path) and formula
            style (displaymath, boolean) as a dictionary with the keys in
            parenthesis
        """
        latex = document.LaTeXDocument(formula)
        latex.set_displaymath(displaymath)
        if self.__options['preamble']: # add preamble to LaTeX document
            latex.set_preamble_string(self.__options['preamble'])
        if self.__options['latex_maths_env']:
            latex.set_latex_environment(self.__options['latex_maths_env'])
        conv = image.Tex2img(latex, os.path.join(self.__base_path, output_path))
        # apply configured image output options
        for option, value in self.__options.items():
            if value and hasattr(conv, 'set_' + option):
                getattr(conv, 'set_' + option)(value)
        conv.convert()
        pos = conv.get_positioning_info()
        return {'pos' : pos, 'path' : output_path, 'displaymath' :
            displaymath}

    def get_data_for(self, formula, display_mat):
        """Simple wrapper around ImageCache."""
        return self.__cache.get_data_for(formula, display_mat)

