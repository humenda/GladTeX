# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import pprint
import shutil
import tempfile
import unittest
from unittest.mock import patch
from subprocess import SubprocessError

import gleetex.image as image
from gleetex.image import Format
from gleetex.typesetting import LaTeXDocument as doc

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


def call_dummy(_lklklklklk, **blah):
    """Dummy to prohibit subprocess execution."""
    return str(blah)


# pylint: disable=unused-argument
def latex_error_mock(_cmd, **quark):
    """Mock an error case."""
    raise SubprocessError(LATEX_ERROR_OUTPUT)


# pylint: disable=unused-argument
def dvipng_mock(cmd, **kwargs):
    """Mock an error case."""
    fn = None
    try:
        fn = next(e for e in cmd if e.endswith(".png"))
    except StopIteration:
        try:
            fn = next(e for e in cmd if e.endswith(".dvi"))
        except StopIteration:
            pass
    if fn:
        with open(fn, "w") as f:
            f.write("test case")
    return (
        "This is dvipng 1.14 Copyright 2002-2010 Jan-Ake Larsson\n "
        + "depth=3 height=9 width=22"
    )


def touch(files):
    for file in files:
        dirname = os.path.dirname(file)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(file, "w") as f:
            f.write("\n")


class test_imagecreation(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        image.Tex2img.call = call_dummy

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("gleetex.image.proc_call", latex_error_mock)
    def test_that_error_of_incorrect_formula_is_parsed_correctly(self):
        i = image.Tex2img(Format.Png)
        try:
            i.create_dvi(doc("\\foo"), "foo.png")
        except SubprocessError as e:
            # expect undefined control sequence in error output
            self.assertTrue("Undefined" in e.args[0])

    @patch("gleetex.image.proc_call", call_dummy)
    def test_that_intermediate_files_are_removed_after_successful_run(self):
        files = ["foo.log", "foo.aux", "foo.tex"]
        touch(files)
        i = image.Tex2img(Format.Png)
        i.create_dvi(doc("\\frac\\pi\\tau"), "foo.png")
        for intermediate_file in files:
            self.assertFalse(
                os.path.exists(intermediate_file),
                "File " + intermediate_file + " should not exist.",
            )

    @patch("gleetex.image.proc_call", latex_error_mock)
    def test_that_intermediate_files_are_removed_when_exception_is_raised(self):
        files = ["foo.log", "foo.aux", "foo.tex"]
        touch(files)
        # error case
        i = image.Tex2img(Format.Png)
        try:
            i.convert(doc("\\foo"), "foo")
        except SubprocessError as e:
            for intermediate_file in files:
                self.assertFalse(
                    os.path.exists(intermediate_file),
                    "File " + intermediate_file + " should not exist.",
                )

    @patch("gleetex.image.proc_call", dvipng_mock)
    def test_intermediate_files_are_removed(self):
        files = ["foo.tex", "foo.log", "foo.aux", "foo.dvi"]
        touch(files)
        i = image.Tex2img(Format.Png)
        i.convert(doc("\\hat{x}"), "foo")
        for intermediate_file in files:
            self.assertFalse(os.path.exists(intermediate_file))

    @patch("gleetex.image.proc_call", latex_error_mock)
    def test_intermediate_files_are_removed_when_exception_raised(self):
        files = ["foo.tex", "foo.log", "foo.aux", "foo.dvi"]
        touch(files)
        i = image.Tex2img(Format.Png)
        try:
            i.convert(doc("\\hat{x}"), "foo")
        except SubprocessError:
            self.assertFalse(os.path.exists("foo.tex"))
            self.assertFalse(os.path.exists("foo.dvi"))
            self.assertFalse(os.path.exists("foo.log"))
            self.assertFalse(os.path.exists("foo.aux"))

    @patch(
        "gleetex.image.proc_call",
        lambda *x, **y: "This is dvipng 1.14 "
        + "Copyright 2002-2010 Jan-Ake Larsson\n depth=3 height=9 width=22",
    )
    def test_that_values_for_positioning_png_are_returned(self):
        i = image.Tex2img(Format.Png)
        posdata = i.create_image("foo.dvi")
        self.assertTrue("height" in posdata)
        self.assertTrue("width" in posdata)

    @patch("gleetex.image.proc_call", dvipng_mock)
    def test_that_output_file_names_with_paths_are_ok_and_log_is_removed(self):
        fname = lambda f: os.path.join("bilder", "farce." + f)
        touch([fname("log"), fname("png")])
        t = image.Tex2img(Format.Png)
        t.convert(doc(r"\hat{es}\pi\pi\ldots"), fname("")[:-1])
        self.assertFalse(os.path.exists("farce.log"))
        self.assertTrue(
            os.path.exists(fname("png")),
            "couldn't find file {}, directory structure:\n{}".format(
                fname("png"), "".join(pprint.pformat(list(os.walk("."))))
            ),
        )
        self.assertFalse(os.path.exists(fname("log")))


class TestImageResolutionCorrectlyCalculated(unittest.TestCase):
    def test_sizes_are_correctly_calculated(self):
        self.assertEqual(int(image.fontsize2dpi(12)), 115)
        self.assertEqual(int(image.fontsize2dpi(10)), 96)
