# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
from gleetex import caching


def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


class test_caching(unittest.TestCase):
    def setUp(self):
        self.pos = {'height': 8, 'depth': 2, 'width': 666}
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_differently_spaced_formulas_are_the_same(self):
        form1 = r'\tau  \pi'
        form2 = '\tau\\pi'
        self.assertTrue(
            caching.normalize_formula(form1), caching.normalize_formula(form2)
        )

    def test_trailing_and_leading_spaces_and_tabs_are_no_problem(self):
        u = caching.normalize_formula
        form1 = '  hi'
        form2 = 'hi  '
        form3 = '\thi'
        self.assertEqual(u(form1), u(form2))
        self.assertEqual(u(form1), u(form3))

    def test_that_empty_braces_are_ignored(self):
        u = caching.normalize_formula
        form1 = r'\sin{}x'
        form2 = r'\sin x'
        form3 = r'\sin{} x'
        self.assertEqual(u(form1), u(form2))
        self.assertEqual(u(form1), u(form3))
        self.assertEqual(u(form2), u(form3))

    def test_empty_cache_works_fine(self):
        write('foo.png', 'muha')
        c = caching.ImageCache('file.png')
        formula = r'f(x) = \ln(x)'
        c.add_formula(formula, self.pos, 'foo.png')
        self.assertTrue(c.contains(formula, False))

    def test_that_invalid_cach_entries_are_detected(self):
        # entry is invalid if file doesn't exist
        c = caching.ImageCache()
        formula = r'f(x) = \ln(x)'
        self.assertRaises(OSError, c.add_formula,
                          formula, self.pos, 'file.png')

    def test_that_correct_pos_and_path_are_returned_after_writing_the_cache_back(self):
        c = caching.ImageCache()
        formula = r'g(x) = \ln(x)'
        write('file.png', 'dummy')
        c.add_formula(formula, self.pos, 'file.png', displaymath=False)
        c.write()
        c = caching.ImageCache()
        self.assertTrue(c.contains(formula, False))
        data = c.get_data_for(formula, False)
        self.assertEqual(data['pos'], self.pos)
        self.assertEqual(data['path'], 'file.png')

    def test_formulas_are_not_added_twice(self):
        form1 = r'\ln(x) \neq e^x'
        write('spass.png', 'binaryBinary_binary')
        c = caching.ImageCache()
        for i in range(1, 10):
            c.add_formula(form1, self.pos, 'spass.png')
        self.assertEqual(len(c), 1)

    def test_that_remove_actually_removes(self):
        form1 = '\\int e^x dy'
        write('happyness.png', 'binaryBinary_binary')
        c = caching.ImageCache()
        c.add_formula(form1, self.pos, 'happyness.png')
        c.remove_formula(form1, False)
        self.assertEqual(len(c), 0)

    def test_removal_of_non_existing_formula_raises_exception(self):
        c = caching.ImageCache()
        self.assertRaises(KeyError, c.remove_formula, 'Haha!', False)

    def test_that_invalid_version_is_detected(self):
        c = caching.ImageCache('gladtex.cache')
        c._ImageCache__set_version('invalid.stuff')
        c.write()
        self.assertRaises(
            caching.JsonParserException, caching.ImageCache, 'gladtex.cache'
        )

    def test_that_invalid_style_is_detected(self):
        write('foo.png', 'dummy')
        c = caching.ImageCache('gladtex.cache')
        c.add_formula('\\tau', self.pos, 'foo.png', False)
        c.add_formula('\\theta', self.pos, 'foo.png', True)
        self.assertRaises(
            ValueError, c.add_formula, '\\gamma', self.pos, 'foo.png', 'some stuff'
        )

    def test_that_backslash_in_path_is_replaced_through_slash(self):
        c = caching.ImageCache('gladtex.cache')
        os.mkdir('bilder')
        write(os.path.join('bilder', 'foo.png'), str(0xDEADBEEF))
        c.add_formula('\\tau', self.pos, 'bilder\\foo.png', False)
        self.assertTrue('/' in c.get_data_for('\\tau', False)['path'])

    def test_that_absolute_paths_trigger_OSError(self):
        c = caching.ImageCache('gladtex.cache')
        write('foo.png', 'dummy')
        fn = os.path.abspath('foo.png')
        self.assertRaises(OSError, c.add_formula, '\\tau', self.pos, fn, False)

    def test_that_invalid_caches_are_removed_automatically_if_desired(self):
        def file_was_removed(x): return self.assertFalse(
            os.path.exists(x),
            'expected that file %s was removed, but it still exists' % x,
        )
        write('gladtex.cache', 'some non-json rubbish')
        c = caching.ImageCache('gladtex.cache', keep_old_cache=False)
        file_was_removed('gladtex.cache')
        # try the same in a subdirectory
        os.mkdir('foo')
        cache_path = os.path.join('foo', 'gladtex.cache')
        eqn1_path = os.path.join('foo', 'eqn000.png')
        eqn2_path = os.path.join('foo', 'eqn003.png')
        write(cache_path, 'some non-json rubbish')
        write(eqn1_path, 'binary')
        write(eqn2_path, 'more binary')
        c = caching.ImageCache(cache_path, keep_old_cache=False)
        file_was_removed(cache_path)
        file_was_removed(eqn1_path)
        file_was_removed(eqn2_path)

    def test_that_formulas_in_cache_with_no_file_raise_key_error(self):
        c = caching.ImageCache('gladtex.cache', keep_old_cache=False)
        write('foo.png', 'dummy')
        c.add_formula('\\tau', self.pos, 'foo.png')
        c.write()
        os.remove('foo.png')
        c = caching.ImageCache('gladtex.cache', keep_old_cache=False)
        with self.assertRaises(KeyError):
            c.get_data_for('foo.png', 'False')
