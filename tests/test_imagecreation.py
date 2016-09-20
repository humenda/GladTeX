#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
from subprocess import SubprocessError

import gleetex.image as image
from gleetex.document import LaTeXDocument as doc

LATEX_ERROR_OUTPUT = r"""
This is pdfTeX, Version 3.14159265-2.6-1.40.17 (TeX Live 2016/Debian) (preloaded format=latex)
 restricted \write18 enabled.
entering extended mode
(./bla.tex
LaTeX2e <2016/03/31> patch level 3
Babel <3.9r> and hyphenation patterns for 10 language(s) loaded.
(/usr/share/texlive/texmf-dist/tex/latex/base/article.cls
Document Class: article 2014/09/29 v1.4h Standard LaTeX document class
(/usr/share/texlive/texmf-dist/tex/latex/base/size10.clo)) (./bla.aux)
! Undefined control sequence.
<recently read> \foo 
                     
l.3 $\foo
         $
No pages of output.
Transcript written on bla.log.
"""


def call_dummy(_lklklklklk, cwd=None):
    """Dummy to prohibit subprocess execution."""
    return str(cwd)





#pylint: disable=unused-argument
def latex_error_mock(_cmd, cwd=None):
    """Mock an error case."""
    raise SubprocessError(LATEX_ERROR_OUTPUT)

#pylint: disable=unused-argument
def dvipng_mock(cmd, cwd=None):
    """Mock an error case."""
    fn = None
    try:
        fn = next(e for e in cmd if e.endswith('.png'))
    except StopIteration:
        try:
            fn = next(e for e in cmd if e.endswith('.dvi'))
        except StopIteration:
            pass
    if fn:
        with open(fn, 'w') as f:
            f.write("test case")
    return 'This is dvipng 1.14 Copyright 2002-2010 Jan-Ake Larsson\n ' + \
       'depth=3 height=9 width=22'

class test_imagecreation(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        image.Tex2img.call = call_dummy

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_that_incorrect_latex_formula_raises_subprocess_exception(self):
        i = image.Tex2img(doc("\\foo"), 'foo.png')
        image.Tex2img.call = latex_error_mock
        self.assertRaises(SubprocessError, i.create_dvi, 'useless.dvi')

    def test_that_incorrect_formula_is_displayed(self):
        i = image.Tex2img(doc("\\foo"), 'foo.png')
        try:
            i.create_dvi('foo.dvi')
        except SubprocessError as e:
            # expect undefined control sequence in error output
            self.assertTrue('Undefined' in e.args[0])

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
        i = image.Tex2img(doc("\\sum\\limits_{i=0}^{\\infty} i^ie^i"), 'foo.png')
        i.create_dvi('foo.dvi')
        image.Tex2img.call = dvipng_mock
        i.create_png('foo.dvi')
        self.assertTrue(os.path.exists('foo.png'))
    def create_intermediate_files(self, file_name):
        files = ['tex', 'log', 'aux', 'dvi']
        for ending in files:
            with open(file_name + '.' + ending, 'w') as f:
                f.write("blah blah")


    def test_intermediate_files_are_removed(self):
        files = ['foo.tex', 'foo.log', 'foo.aux', 'foo.dvi']
        i = image.Tex2img(doc('\\hat{x}'), 'foo.png')
        self.create_intermediate_files('foo')
        i.create_dvi('foo.dvi')
        image.Tex2img.call = dvipng_mock
        i.create_png('foo.dvi')
        for intermediate_file in files:
            self.assertFalse(os.path.exists(intermediate_file))

    def test_intermediate_files_are_removed_when_exception_raised(self):
        files = ['foo.tex', 'foo.log', 'foo.aux', 'foo.dvi']
        i = image.Tex2img(doc('\\hat{x}'), 'foo.png')
        self.create_intermediate_files('foo') # pretend that LaTeX was run
        # let call() raise an arbitrari SubprocessError
        image.Tex2img.call = latex_error_mock

        try:
            i.create_dvi('foo.dvi')
        except SubprocessError:
            self.assertFalse(os.path.exists('foo.tex'))
            self.assertFalse(os.path.exists('foo.dvi'))
            self.assertFalse(os.path.exists('foo.log'))
            self.assertFalse(os.path.exists('foo.aux'))

        try:
            i.create_png('foo.dvi')
        except SubprocessError:
            self.assertFalse(os.path.exists('foo.dvi'))


    def test_that_values_for_positioning_png_are_returned(self):
        i = image.Tex2img(doc("\\sum\\limits_{i=0}^{\\infty} i^ie^i"), 'foo.png')
        i.create_dvi('foo.dvi')
        # set dvi output call
        image.Tex2img.call = lambda x, y=9: \
                'This is dvipng 1.14 Copyright 2002-2010 Jan-Ake Larsson\n depth=3 height=9 width=22'
        posdata = i.create_png('foo.dvi')
        self.assertTrue('height' in posdata)
        self.assertTrue('width' in posdata)


    def test_that_output_file_names_with_paths_are_ok_and_log_is_removed(self):
        t = image.Tex2img(doc(r"\hat{es}\pi\pi\ldots"), "bilder/farce.png")
        image.Tex2img.call = dvipng_mock
        t.convert()
        self.assertFalse(os.path.exists("farce.log"))
        self.assertTrue(os.path.exists("bilder/farce.png"))

    def test_whether_lualatex_is_used_if_set(self):
        lualatex_used = False
        def fake_subprocess(cmd, cwd=None):
            nonlocal lualatex_used
            if 'lualatex' in cmd:
                lualatex_used = True
            return 'stuff'
        t = image.Tex2img(doc(r"\hat{es}\pi\pi\ldots"), "bilder/farce.png")
        t.set_use_lualatex(True)
        image.Tex2img.call = fake_subprocess
        t.create_dvi('cat.dvi')
        self.assertTrue(lualatex_used, ("LuaLaTeX was not used, even though it "
            "was configured to do so."))

    def test_whether_latex2e_is_used_if_lualatex_not_enabled(self):
        lualatex_used = False
        def fake_subprocess(cmd, cwd=None):
            nonlocal lualatex_used
            if 'lualatex' in cmd:
                lualatex_used = True
            return 'stuff'
        t = image.Tex2img(doc(r"\hat{es}\pi\pi\ldots"), "bilder/farce.png")
        image.Tex2img.call = fake_subprocess
        t.create_dvi('cow.dvi')
        self.assertFalse(lualatex_used, "LuaLaTeX was used, even though it was disabled.")

