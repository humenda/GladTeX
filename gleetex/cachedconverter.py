# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""In order to convert images only if they are not already cached, the cached
converter sacrifices customizability for convenience and provides a class
converting a formula directly to a png file."""

import concurrent.futures
import multiprocessing
import os
import subprocess

from . import caching, image, typesetting
from .caching import normalize_formula
from .image import Format

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
    # mind your own business mr. pylint:
    #pylint: disable=too-many-arguments
    def __init__(self, cause, formula, formula_count, src_line_number=None,
            src_pos_on_line=None):
        # provide a default error message
        if src_line_number and src_pos_on_line:
            super().__init__("LaTeX failed at formula line {}, {}, no. {}: {}".format(
                src_line_number, src_pos_on_line, formula_count, cause))
        else:
            super().__init__("LaTeX failed at formula no. {}: {}".format(
                formula_count, cause))
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

    :param base_path directory of the output HTML file; link references in the
            HTML document will link relative to it
    :param keep_old_cache If an existing cache cannot be read (incompatible
        GladTeX version, ...) Aand the flag is set, the program will simply
        crash and tell the user to remove the cache (default). If set to False,
        the program will instead remove the cache and all eqn* files and
        recreate the cache.
    :param encoding The encoding for the LaTeX document, default None
    :param img_dir directory for images (default ., equivalent to base_path)
            For example "images" would put it in `base_path`/images and "../img"
            would put it in "base_path/../img"
    """
    GLADTEX_CACHE_FILE_NAME = 'gladtex.cache'

    def __init__(self, base_path, keep_old_cache=True, encoding=None,
            img_dir=''):
        empty_path = lambda p: ('' if not p or p.strip(os.sep) == '.' else p)
        self.__output_path = empty_path(base_path) # path where converted document will be
        self.__img_dir = empty_path(img_dir) # relative to base_path
        # cache path is **relative** to base_path
        cache_path = os.path.join(self.__img_dir,
                CachedConverter.GLADTEX_CACHE_FILE_NAME)
        self.__cache = caching.ImageCache(cache_path,
                keep_old_cache=keep_old_cache,
                base_path=empty_path(self.__output_path))
        self.__converter = None
        self.__options = {'dpi': None, 'transparency': None, 'fontsize': None,
                'background_color': None, 'foreground_color': None,
                'preamble': None, 'latex_maths_env': None,
                'keep_latex_source': False, 'png': False}
        self.__encoding = encoding
        self.__replace_nonascii = False


    def set_option(self, option, value):
        """Set one of the options accepted for gleetex.image.Tex2img. It is a
        proxy function.
        `option` must be one of dpi, fontsize, transparency, background_color,
        foreground_color, preamble, latex_maths_env, keep_latex_source, png."""
        if not option in self.__options.keys():
            raise ValueError("Option must be one of " + \
                    ', '.join(self.__options.keys()))
        self.__options[option] = value

    def set_replace_nonascii(self, flag):
        """If set, GladTeX will convert all non-ascii character to LaTeX
        commands. This setting is passed through to typesetting.LaTeXDocument."""
        self.__replace_nonascii = flag


    def convert_all(self, formulas):
        """convert_all(formulas)
        Convert all formulas using self.convert concurrently. Each element of
        `formulas` must be a tuple containing (formula, displaymath,
        Formulas already contained in the cache are not converted."""
        formulas_to_convert = self._get_formulas_to_convert(formulas)
        if formulas_to_convert:
            self.__converter = image.Tex2img(Format.Png
                    if self.__options['png'] else Format.Svg)
            # apply configured image output options
            for option, value in self.__options.items():
                if value and hasattr(self.__converter, 'set_' + option):
                    if isinstance(value, str): # only try string -> number
                        try: # some values are numbers
                            value = float(value)
                        except ValueError:
                            pass
                    getattr(self.__converter, 'set_' + option)(value)
            self._convert_concurrently(formulas_to_convert)

    def _get_formulas_to_convert(self, formulas):
        """Return a list of formulas to convert, along with their count in the
        global list of formulas of the document being converted and the file
        name. Function was decomposed for better testability."""
        formulas_to_convert = [] # find as many file names as equations
        file_ext = (Format.Png.value if self.__options['png']
                else Format.Svg.value)
        eqn_path = lambda x: os.path.join(self.__img_dir,
                'eqn%03d.%s' % (x, file_ext))
        abs_eqn_path = lambda x: os.path.join(self.__img_dir, eqn_path(x))

        # is (formula, display_math) already in the list of formulas to convert;
        # displaymath is important since formulas look different in inline maths
        formula_was_converted = lambda f, dsp: (normalize_formula(f), dsp) in \
                ((normalize_formula(u[0]), u[3]) for u in formulas_to_convert)
        # find enough free file names
        file_name_count = 0
        used_file_names = [] # track which file names have been assigned
        for formula_count, (pos, dsp, formula) in enumerate(formulas):
            # ToDo: this belongs in the cache
            if not self.__cache.contains(formula, dsp) and \
                    not formula_was_converted(formula, dsp):
                while os.path.exists(abs_eqn_path(file_name_count)) or \
                    eqn_path(file_name_count) in used_file_names:
                    file_name_count += 1
                used_file_names.append(eqn_path(file_name_count))
                formulas_to_convert.append((formula, pos, eqn_path(file_name_count),
                    dsp, formula_count + 1))
        return formulas_to_convert


    def _convert_concurrently(self, formulas_to_convert):
        """The actual concurrent conversion process. Method is intended to be
        called from convert_all()."""
        imgdir_full = os.path.join(self.__output_path, self.__img_dir)
        if imgdir_full and not os.path.exists(imgdir_full):
            # create directory *before* it is required in the concurrent
            # formulacreation step
            os.makedirs(imgdir_full)

        thread_count = int(multiprocessing.cpu_count() * 2.5)
        # convert missing formulas
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            # start conversion and mark each thread with its formula, position
            # in the source file and formula_count (index into a global list of
            # formulas)
            jobs = {executor.submit(self.__convert, eqn, path, dsp): (eqn, pos, count)
                for (eqn, pos, path, dsp, count) in formulas_to_convert}
            error_occurred = None
            for future in concurrent.futures.as_completed(jobs):
                if error_occurred and not future.done():
                    future.cancel()
                    continue
                formula, pos_in_src, formula_count = jobs[future]
                try:
                    data = future.result()
                except subprocess.SubprocessError as e:
                    # retrieve the position (line, pos on line) in the source
                    # document from original formula list
                    if pos_in_src: # missing for the pandocfilter case
                        pos_in_src = list(p+1 for p in pos_in_src) # user expects lines/pos_in_src' to count from 1
                    self.__cache.write() # write back cache with valid entries
                    if not pos_in_src: # pandocfilter case:
                        error_occurred = ConversionException(str(e.args[0]),
                                formula, formula_count)
                    else:
                        error_occurred = ConversionException(str(e.args[0]), formula,
                            formula_count, pos_in_src[0], pos_in_src[1])
                else:
                    self.__cache.add_formula(formula, data['pos'],
                            data['path'],
                            data['displaymath'])
                    self.__cache.write()
            #pylint: disable=raising-bad-type
            if error_occurred:
                raise error_occurred



    def __convert(self, formula, img_path, displaymath=False):
        """convert(formula, img_path, displaymath=False)
        Convert given formula with displaymath/inlinemath.
        This method wraps the formula in a tex document, executes all the steps
        to produce a image and return the positioning information for the
        HTML output. It does not check the cache.
        :param formula formula to convert
        :param img_path image output path (relative to the configured base_path,
                    see __init__)
        :param displaymath whether or not to use displaymath during the conversion
        :return dictionary with position (pos), image path (path) and formula
            style (displaymath, boolean) as a dictionary with the keys in
            parenthesis"""
        latex = typesetting.LaTeXDocument(formula)
        latex.set_displaymath(displaymath)
        def set(opt, setter):
            if self.__options[opt]:
                getattr(latex, 'set_' + setter)(self.__options[opt])
        set('preamble', 'preamble_string')
        set('latex_maths_env', 'latex_environment')
        set('background_color', 'background_color')
        set('foreground_color', 'foreground_color')
        if self.__encoding:
            latex.set_encoding(self.__encoding)
        if self.__replace_nonascii:
            latex.set_replace_nonascii(True)
        # dvipng needs the additionalindication of transparency (enabled by
        # default) when setting a background colour
        if self.__options['background_color']:
            self.__converter.set_transparency(False)
        pos = self.__converter.convert(latex,
                os.path.join(self.__output_path, os.path.splitext(img_path)[0]))
        return {'pos': pos,
                'path': img_path, # relative to self.__base_name(!)
                'displaymath': displaymath}

    def get_data_for(self, formula, display_math):
        """Simple wrapper around ImageCache, enriching the returned data with
        the information provided as arguments to this function. This helps when
        using a formula without its context."""
        data = self.__cache.get_data_for(formula, display_math).copy()
        data.update({'formula': formula, 'displaymath': display_math})
        return data
