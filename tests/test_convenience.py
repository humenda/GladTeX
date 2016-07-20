#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import distutils
import os
import shutil
import tempfile
import unittest
from gleetex import convenience, image

def get_number_of_files(path):
    return len(os.listdir(path))

class Tex2imgMock():
    """Could use a proper mock, but this one allows a bit more tricking."""
    def __init__(self, _tex_document, output_fn, _encoding="UTF-8"):
        self.output_name = output_fn
        base_name = os.path.split(output_fn)[0]
        if base_name and not os.path.exists(base_name):
            distutils.dir_util.mkpath(base_name)
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
        with open(os.path.splitext(dvi_fn)[0] + '.png', 'w') as f:
            f.write('dummy')

    def convert(self):
        self.create_png(self.output_name)

    def get_positioning_info(self):
        return {}

    def parse_log(self, _logdata):
        return {}


class test_caconvenience(unittest.TestCase):
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

