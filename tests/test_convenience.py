#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
from gleetex import convenience, image
from gleetex.convenience import ConversionException
from gleetex.caching import JsonParserException

def get_number_of_files(path):
    return len(os.listdir(path))

def mk_eqn(eqn, count=0, pos=(1,1)):
    """Create formula. Each formula must look like this:
    (eqn, pos, path, dsp, count) for self._convert_concurrently, this is a
    shorthand with mocking a few values."""
    return (eqn, pos, 'eqn%03d.png' % count, False, count)

def turn_into_orig_formulas(formulas):
    """Turn a list of formulas as accepted by
    CachedConverter._convert_concurrently() into a list accepted by
    CachedConverter._get_formulas_to_convert()."""
    return [(e[1], e[3], e[0]) for e in formulas]

def write(path, content='dummy'):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

class Tex2imgMock():
    """Could use a proper mock, but this one allows a bit more tricking."""
    def __init__(self, _tex_document, output_fn, _encoding="UTF-8"):
        self.output_name = output_fn
        base_name = os.path.split(output_fn)[0]
        if base_name and not os.path.exists(base_name):
            os.makedirs(base_name)
        self.set_dpi = self.set_transparency = self.set_foreground_color \
                = self.set_background_color = lambda x: None # do nothing

    def create_dvi(self, dvi_fn):
        """
        Call LaTeX to produce a dvi file with the given LaTeX document.
        Temporary files will be removed, even in the case of a LaTeX error.
        This method raises a SubprocessError with the helpful part of LaTeX's
        error output."""
        with open(dvi_fn, 'w') as f:
            f.write('dummy')

    def create_png(self, dvi_fn):
        if os.path.exists(dvi_fn):
            os.remove(dvi_fn)
        write(self.output_name)

    def convert(self):
        self.create_png(self.output_name)

    def get_positioning_info(self):
        return {'depth': 9, 'height': 8, 'width': 7}

    def parse_log(self, _logdata):
        return {}


class TestCachedConverter(unittest.TestCase):
    #pylint: disable=protected-access
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        convenience.CachedConverter._converter = Tex2imgMock


    #pylint: disable=protected-access
    def tearDown(self):
        # restore static reference to converter
        convenience.CachedConverter._converter = image.Tex2img
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)



    def test_that_subdirectory_is_created(self):
        c = convenience.CachedConverter(os.getcwd(), 'subdirectory')
        formula = '\\textbf{FOO!}'
        c.convert(formula, 'subdirectory/eqn000.png')
        # one directory exists
        self.assertEqual(get_number_of_files('.'), 1,
                "Found the following files, expected only 'subdirectory': " + \
                ', '.join(os.listdir('.')))
        # subdirectory contains 1 image and a cache
        self.assertEqual(get_number_of_files('subdirectory'), 1, "expected one"+\
            " files, found only " + repr(os.listdir('subdirectory')))

    def test_that_unknown_options_trigger_exception(self):
        c = convenience.CachedConverter('subdirectory')
        self.assertRaises(ValueError, c.set_option, 'cxzbiucxzbiuxzb', 'muh')

    def test_that_invalid_caches_trigger_error_by_default(self):
        with open('gladtex.cache', 'w') as f:
            f.write('invalid cache')
        with self.assertRaises(JsonParserException):
            c = convenience.CachedConverter('')

    def test_that_invalid_caches_get_removed_if_specified(self):
        formulas = [mk_eqn('tau')]
        with open('gladtex.cache', 'w') as f:
            f.write('invalid cache')
        c = convenience.CachedConverter('', keep_old_cache=False)
        c._convert_concurrently(formulas)
        # cache got overridden
        with open('gladtex.cache') as f:
            self.assertFalse('invalid' in f.read())

    def test_that_converted_formulas_are_cached(self):
        formulas = [mk_eqn('tau')]
        c = convenience.CachedConverter('')
        c._convert_concurrently(formulas)
        formulas.append(mk_eqn('\\gamma'))
        formulas = turn_into_orig_formulas(formulas)
        self.assertTrue(len(c._get_formulas_to_convert('', formulas)), 1)


    def test_that_file_names_are_correctly_picked(self):
        formulas = turn_into_orig_formulas([mk_eqn('\\tau')])
        write('eqn000.png')
        write('eqn001.png')
        c = convenience.CachedConverter('')
        to_convert = c._get_formulas_to_convert('', formulas)
        self.assertTrue(len(to_convert), 1)
        self.assertEqual(to_convert[0][2], 'eqn002.png')

    def test_that_all_converted_formulas_are_in_cache_and_meta_info_correct(self):
        formulas = [mk_eqn('a_{%d}' % i, pos=(i,i), count=i) for i in range(100)]
        c = convenience.CachedConverter('')
        c._convert_concurrently(formulas)
        # expect all formulas and a gladtex cache to exist
        self.assertEqual(get_number_of_files('.'), len(formulas)+1)
        for formula, pos, fn, dsp, count in formulas:
            data = c.get_data_for(formula, False)
            self.assertEqual(data['pos'], {'depth': 9, 'height': 8, 'width': 7},
                    "expected the pos as defined in the dummy class")

    def test_that_inline_math_and_display_math_results_in_different_formulas(self):
        # two formulas, second is displaymath
        formula = r'\sum_{i=0}^n x_i'
        formulas = [((1,1), False, formula), ((3,1), True, formula)]
        c = convenience.CachedConverter('.')
        c.convert_all('.', formulas)
        # expect all formulas and a gladtex cache to exist
        self.assertEqual(get_number_of_files('.'), len(formulas)+1)

