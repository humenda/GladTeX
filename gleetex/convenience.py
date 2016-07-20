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
    c = ConversionException("cause", "\\tau", 10, 38, 5)
    assert c.cause == cause
    assert c.formula == '\\tau'
    assert c.src_line_number == 10 # line number in source document (counting from 1)
    assert c.src_pos_on_line == 38 # position of formula in source line, counting from 1
    assert c.formula_count == 5 # fifth formula in document (starting from 1)
    """
    def __init__(self, cause, formula, src_line_number, src_pos_on_line, formula_count):
        # provide a default error message
        super().__init__("LaTeX failed at formula line {}, {}, no. {}: {}".format(
            src_line_number, src_pos_on_line, formula_count, cause))
        # provide attributes for upper level error handling
        self.cause = cause
        self.formula = formula
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
    :param keep_old_cache If an existing cache cannot be read (incompatible
        GladTeX version, ...) Aand the flag is set, the program will simple
        crash and tell the user to remove the cache (default). If set to False,
        the program will instead remove the cache and all eqn* files and
        recreate the cache.
    """
    GLADTEX_CACHE_FILE_NAME = 'gladtex.cache'
    _converter = image.Tex2img # can be statically altered for testing purposes

    def __init__(self, base_path='', keep_old_cache=True):
        if base_path and not os.path.exists(base_path):
            os.makedirs(base_path)
        cache_path = os.path.join(base_path,
                CachedConverter.GLADTEX_CACHE_FILE_NAME)
        self.__base_path = base_path
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

    def convert_all(self, base_path, formulas):
        """convert_all(formulas)
        Convert all formulas using self.convert concurrently. Each element of
        `formulas` must be a tuple containing (formula, displaymath,
        Formulas already contained in the cache are not converted.
        """
        formulas_to_convert = self._get_formulas_to_convert(base_path, formulas)
        self._convert_concurrently(formulas_to_convert)

    def _get_formulas_to_convert(self, base_path, formulas):
        """Return a list of formulas to convert, along with their count in the
        global list of formulas of the document being converted and the file
        name. Function was decomposed for better testability."""
        formulas_to_convert = [] # find as many file names as equations
        eqn_path = lambda x: os.path.join(base_path, 'eqn%03d.png' % x)

        formula_was_converted = lambda x: unify_formula(x) in \
                (unify_formula(u[0]) for u in formulas_to_convert)
        # find enough free file names
        file_name_count = 0
        used_file_names = [] # track which file names have been assigned
        for formula_count, (pos, dsp, formula) in enumerate(formulas):
            if not self.__cache.contains(formula, dsp) and not formula_was_converted(formula):
                while os.path.exists(eqn_path(file_name_count)) or \
                    eqn_path(file_name_count) in used_file_names:
                    file_name_count += 1
                used_file_names.append(eqn_path(file_name_count))
                formulas_to_convert.append((formula, pos, eqn_path(file_name_count),
                    dsp, formula_count + 1))
        return formulas_to_convert


    def _convert_concurrently(self, formulas_to_convert):
        """The actual concurrent conversion process. Method is intended to be
        called from convert_all()."""
        # convert missing formulas
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # start conversion and mark each thread with it's formula, position
            # in the source file and formula_count (index into a global list of
            # formulas)
            jobs = {executor.submit(self.convert, eqn, path, dsp): (eqn, pos, count)
                for (eqn, pos, path, dsp, count) in formulas_to_convert}
            cancel_requested = False
            for future in concurrent.futures.as_completed(jobs):
                if cancel_requested:
                    future.cancel()
                formula, pos_in_src, formula_count = jobs[future]
                try:
                    data = future.result()
                except subprocess.SubprocessError as e:
                    # retrieve the position (line, pos on line) in the source
                    # document from original formula list
                    pos_in_src = list(p+1 for p in pos_in_src) # user expects lines/pos_in_src' to count from 1
                    executor.shutdown(wait=False)
                    cancel_requested = True
                    self.__cache.write() # write back cache with valid entries
                    raise ConversionException(str(e.args[0]), formula,
                            *pos_in_src, formula_count + 1)
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
        conv = self._converter(latex, os.path.join(self.__base_path, output_path))
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

