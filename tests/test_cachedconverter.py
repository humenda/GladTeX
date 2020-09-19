# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
from gleetex import cachedconverter, image
from gleetex.caching import JsonParserException
from gleetex.image import remove_all


def get_number_of_files(path):
    return len(os.listdir(path))


def mk_eqn(eqn, count=0, pos=(1, 1)):
    """Create formula. Each formula must look like this:
    (eqn, pos, path, dsp, count) for self._convert_concurrently, this is a
    shorthand with mocking a few values."""
    return (pos, False, eqn)


def write(path, content="dummy"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(content))


class Tex2imgMock:
    """Could use a proper mock, but this one allows a bit more tricking."""

    def __init__(self, fmt):
        self.__format = fmt
        self.set_dpi = (
            self.set_transparency
        ) = (
            self.set_foreground_color
        ) = self.set_background_color = lambda x: None  # do nothing

    def create_dvi(self, dvi_fn):
        with open(dvi_fn, "w") as f:
            f.write("dummy")

    def create_image(self, dvi_fn):
        if os.path.exists(dvi_fn):
            os.remove(dvi_fn)
        write(os.path.splitext(dvi_fn)[0] + "." + self.__format.value)

    def convert(self, tx, basename):
        write(basename + ".tex", tx)
        dvi = basename + ".dvi"
        self.create_dvi(dvi)
        self.create_image(dvi)
        remove_all(dvi, basename + ".tex", basename + ".log", basename + ".aux")
        return {"depth": 9, "height": 8, "width": 7}

    def parse_log(self, _logdata):
        return {}


class TestCachedConverter(unittest.TestCase):
    # pylint: disable=protected-access
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    # pylint: disable=protected-access
    def tearDown(self):
        # restore static reference to converter
        cachedconverter.CachedConverter._converter = image.Tex2img
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("gleetex.image.Tex2img", Tex2imgMock)
    def test_that_subdirectory_is_created(self):
        c = cachedconverter.CachedConverter("subdirectory")
        formula = ({}, True, "\\textbf{FOO!}")
        c.convert_all([formula])
        # one directory exists
        self.assertEqual(
            get_number_of_files("."),
            1,
            "Found the following files, expected only 'subdirectory': "
            + ", ".join(os.listdir(".")),
        )
        # subdirectory contains 1 image and a cache
        self.assertEqual(
            get_number_of_files("subdirectory"),
            2,
            "expected two"
            + " files, found instead "
            + repr(os.listdir("subdirectory")),
        )

    def test_that_unknown_options_trigger_exception(self):
        c = cachedconverter.CachedConverter("subdirectory")
        self.assertRaises(ValueError, c.set_option, "cxzbiucxzbiuxzb", "muh")

    def test_that_invalid_caches_trigger_error_by_default(self):
        with open("gladtex.cache", "w") as f:
            f.write("invalid cache")
        with self.assertRaises(JsonParserException):
            c = cachedconverter.CachedConverter("")

    @patch("gleetex.image.Tex2img", Tex2imgMock)
    def test_that_invalid_caches_get_removed_if_specified(self):
        formulas = [mk_eqn("tau")]
        with open("gladtex.cache", "w") as f:
            f.write("invalid cache")
        c = cachedconverter.CachedConverter(".", keep_old_cache=False)
        c.convert_all(formulas)
        # cache got overridden
        with open("gladtex.cache") as f:
            self.assertFalse("invalid" in f.read())

    @patch("gleetex.image.Tex2img", Tex2imgMock)
    def test_that_converted_formulas_are_cached(self):
        formulas = [mk_eqn("\\tau")]
        c = cachedconverter.CachedConverter(".")
        c.convert_all(formulas)
        self.assertTrue(c.get_data_for("\\tau", False))

    @patch("gleetex.image.Tex2img", Tex2imgMock)
    def test_that_file_names_are_correctly_picked(self):
        formulas = [mk_eqn("\\tau")]
        write("eqn000.svg")
        write("eqn001.svg")
        c = cachedconverter.CachedConverter("")
        to_convert = c._get_formulas_to_convert(formulas)
        self.assertTrue(len(to_convert), 1)
        self.assertEqual(to_convert[0][2], "eqn002.svg")

    @patch("gleetex.image.Tex2img", Tex2imgMock)
    def test_that_all_converted_formulas_are_in_cache_and_meta_info_correct(self):
        formulas = [mk_eqn("a_{%d}" % i, pos=(i, i), count=i) for i in range(4)]
        c = cachedconverter.CachedConverter(".")
        c.convert_all(formulas)
        # expect all formulas and a gladtex cache to exist
        self.assertEqual(
            get_number_of_files("."),
            len(formulas) + 1,
            "present files:\n" + ", ".join(os.listdir(".")),
        )
        for pos, dsp, formula in formulas:
            data = c.get_data_for(formula, False)
            self.assertEqual(
                data["pos"],
                {"depth": 9, "height": 8, "width": 7},
                "expected the pos as defined in the dummy class",
            )

    @patch("gleetex.image.Tex2img", Tex2imgMock)
    def test_that_inline_math_and_display_math_results_in_different_formulas(self):
        # two formulas, second is displaymath
        formula = r"\sum_{i=0}^n x_i"
        formulas = [((1, 1), False, formula), ((3, 1), True, formula)]
        c = cachedconverter.CachedConverter(".")
        c.convert_all(formulas)
        # expect all formulas and a gladtex cache to exist
        self.assertEqual(
            get_number_of_files("."),
            len(formulas) + 1,
            "present files:\n%s" % ", ".join(os.listdir(".")),
        )
