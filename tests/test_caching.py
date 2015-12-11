#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
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
        self.pos = {'height' : 8, 'depth' : 2, 'width' : 666}
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_differently_spaced_formulas_are_the_smae(self):
        form1 = r'\tau  \pi'
        form2 = '\tau\\pi'
        self.assertTrue(caching.unify_formula(form1),
                caching.unify_formula(form2))

    def test_trailing_and_leading_spaces_and_tabs_are_no_problem(self):
        u = caching.unify_formula
        form1 = '  hi'
        form2 = 'hi  '
        form3 = '\thi'
        self.assertEqual(u(form1), u(form2))
        self.assertEqual(u(form1), u(form3))

    def test_that_empty_braces_are_ignored(self):
        u = caching.unify_formula
        form1 = r'\sin{}x'
        form2 = r'\sin x'
        form3 = r'\sin{} x'
        self.assertEqual(u(form1), u(form2))
        self.assertEqual(u(form1), u(form3))
        self.assertEqual(u(form2), u(form3))

    def test_empty_cache_works_fine(self):
        with open('foo.png', 'wb') as f:
            f.write(b'\x00')
        c = caching.ImageCache('file.png')
        formula = r"f(x) = \ln(x)"
        c.add_formula(formula, self.pos, 'foo.png')
        self.assertTrue(formula in c)

    def test_that_invalid_cach_entries_are_detected(self):
        # entry is invalid if file doesn't exist
        c = caching.ImageCache()
        formula = r"f(x) = \ln(x)"
        self.assertRaises(OSError, c.add_formula, formula, self.pos, 'file.png')

    def test_that_correct_pos_and_path_are_returned_after_writing_the_cache_back(self):
        c = caching.ImageCache()
        formula = r"f(x) = \ln(x)"
        with open('file.png', 'w') as f:
            f.write('dummy')
        c.add_formula(formula, self.pos, 'file.png')
        c.write()
        c = caching.ImageCache()
        self.assertTrue(formula in c)
        self.assertEqual(c.get_data_for(formula)['pos'], self.pos)
        self.assertEqual(c.get_data_for(formula)['path'], 'file.png')
        self.assertEqual(c.get_data_for(formula)['displaymath'], False)


    def test_formulas_are_not_added_twice(self):
        form1 = r'\ln(x) \neq e^x'
        write('spass.png', 'binaryBinary_binary')
        c = caching.ImageCache()
        for i in range(1,10):
            c.add_formula(form1, self.pos, 'spass.png')
        self.assertEqual(len(c), 1)

    def test_that_remove_actually_removes(self):
        form1 = '\\int e^x dy'
        write('happyness.png', 'binaryBinary_binary')
        c = caching.ImageCache()
        c.add_formula(form1, self.pos, 'happyness.png')
        c.remove_formula(form1)
        self.assertEqual(len(c), 0)

    def test_removal_of_non_existing_formula_raises_exception(self):
        c = caching.ImageCache()
        self.assertRaises(KeyError, c.remove_formula, 'Haha!')

    def test_that_invalid_version_is_detected(self):
        c = caching.ImageCache('gladtex.cache')
        c._ImageCache__set_version('invalid.stuff')
        c.write()
        self.assertRaises(caching.JsonParserException, caching.ImageCache, 'gladtex.cache')

    def test_that_invalid_style_is_detected(self):
        with open('foo.png', 'w') as f:
            f.write("dummy")
        c = caching.ImageCache('gladtex.cache')
        c.add_formula('\\tau', self.pos, 'foo.png', False)
        c.add_formula('\\theta', self.pos, 'foo.png', True)
        self.assertRaises(ValueError, c.add_formula, '\\gamma', self.pos, 'foo.png',
                'some stuff')

    def test_that_backslash_in_path_is_replaced_through_slash(self):
        c = caching.ImageCache('gladtex.cache')
        os.mkdir('bilder')
        open('foo.png','w').write(str(0xdeadbeef))
        c.add_formula('\\tau', self.pos, 'bilder\\foo.png', False)
        self.assertTrue('/' in c.get_data_for('\\tau')['path'])

    def test_that_absolute_paths_trigger_OSError(self):
        c = caching.ImageCache('gladtex.cache')
        open('foo.png','w').write("dummy")
        fn = os.path.abspath('foo.png')
        self.assertRaises(OSError, c.add_formula, '\\tau', self.pos,
                fn, False)

