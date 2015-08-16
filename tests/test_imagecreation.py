#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
import gleetex.image as image
from subprocess import SubprocessError
from gleetex.document import LaTeXDocument as doc

class test_imagecreation(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dvi_is_created_with_correct_name(self):
        i = image.Tex2img(doc("\\pi"), 'foo.png')
        i.create_dvi('foo.dvi')
        self.assertTrue(os.path.exists("foo.dvi"))

    def test_that_incorrect_latex_formula_raises_subprocess_exception(self):
        i = image.Tex2img(doc("\\foo"), 'foo.png')
        self.assertRaises(SubprocessError, i.create_dvi, 'foo.dvi')

    def test_that_incorrect_formula_is_displayed(self):
        i = image.Tex2img(doc("\\foo"), 'foo.png')
        try:
            i.create_dvi('foo.dvi')
        except SubprocessError as e:
            self.assertTrue('\\foo' in e.args[0])

    def test_that_intermediate_files_are_removed_after_successful_run(self):
        files = ['foo.log', 'foo.aux', 'foo.tex']
        i = image.Tex2img(doc("\\frac\\pi\\tau"), 'foo.png')
        i.create_dvi('foo.dvi')
        for intermediate_file in files:
            self.assertFalse(os.path.exists(intermediate_file), "File " +
                    intermediate_file + " should not exist.")

    def test_that_intermediate_files_are_removed_when_exception_is_raised(self):
        files = ['foo.log', 'foo.aux', 'foo.tex']
        # error case
        i = image.Tex2img(doc("\\foo"), 'foo.png')
        try:
            i.create_dvi('foo.dvi')
        except SubprocessError as e:
            for intermediate_file in files:
                self.assertFalse(os.path.exists(intermediate_file), "File " +
                        intermediate_file + " should not exist.")

    def test_that_png_is_created(self):
        i = image.Tex2img(doc("\\sum\\limits_{i=0}^{\infty} i^ie^i"), 'foo.png')
        i.create_dvi('foo.dvi')
        i.create_png('foo.dvi')
        self.assertTrue(os.path.exists('foo.png'))

    def test_intermediate_files_are_removed(self):
        files = ['foo.tex', 'foo.log', 'foo.aux', 'foo.dvi']
        i = image.Tex2img(doc('\\hat{x}'), 'foo.png')
        i.create_dvi('foo.dvi')
        i.create_png('foo.dvi')
        for intermediate_file in files:
            self.assertFalse(os.path.exists(intermediate_file))

    def test_intermediate_files_are_removed_when_exception_raised(self):
        files = ['foo.tex', 'foo.log', 'foo.aux', 'foo.dvi']
        i = image.Tex2img(doc('\\hat{x}'), 'foo.png')
        try:
            i.create_dvi('foo.dvi')
            # write garbage into file
            with open('foo.dvi', 'wb') as f:
                f.write(b'\xa0\x02\xfd' * 100)
            i.create_png('foo.dvi')
        except SubprocessError:
            for intermediate_file in files:
                self.assertFalse(os.path.exists(intermediate_file))

    def test_that_values_for_positioning_png_are_returned(self):
        i = image.Tex2img(doc("\\sum\\limits_{i=0}^{\infty} i^ie^i"), 'foo.png')
        i.create_dvi('foo.dvi')
        posdata = i.create_png('foo.dvi')
        self.assertTrue('height' in posdata)
        self.assertTrue('width' in posdata)

 
