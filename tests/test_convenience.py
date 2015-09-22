#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
from gleetex import convenience

def get_number_of_files(path):
    return len(os.listdir(path))

class test_caconvenience(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)



    def test_file_is_cached(self):
        c = convenience.CachedConverter()
        formula = '\\log\\log\\log'
        c.convert(formula)
        self.assertTrue(os.path.exists('gladtex.cache'))
        c.convert(formula)
        # one png and one cache file should exist
        self.assertEqual(get_number_of_files('.'), 2)

    def test_that_subdirectory_is_created(self):
        c = convenience.CachedConverter('subdirectory')
        formula = '\\textbf{FOO!}'
        c.convert(formula)
        # one directory exists
        self.assertEqual(get_number_of_files('.'), 1)
        # subdirectory contains 1 image and a cache
        self.assertEqual(get_number_of_files('subdirectory'), 2)

    def test_that_unknown_options_trigger_exception(self):
        c = convenience.CachedConverter('subdirectory')
        self.assertRaises(ValueError, c.set_option, 'cxzbiucxzbiuxzb', 'muh')
