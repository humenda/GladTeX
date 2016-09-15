#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest
from gleetex.document import LaTeXDocument, LuaLaTeXDocument

class test_document(unittest.TestCase):
    def test_formula_is_embedded(self):
        formula = 'E = m \\cdot c^2'
        doc = LaTeXDocument(formula)
        self.assertTrue(formula in str(doc),
                "formula must be contained in LaTeX document as it was inserted.")

    def test_if_displaymath_unset_correct_env_used(self):
        doc = LaTeXDocument('A = \pi r^2')
        doc.set_displaymath(False)
        self.assertTrue('\\(' in str(doc))
        self.assertTrue('\\)' in str(doc))

    def test_if_displaymath_is_set_correct_env_used(self):
        doc = LaTeXDocument('A = \pi r^2')
        doc.set_displaymath(True)
        self.assertTrue('\\[' in str(doc))
        self.assertTrue('\\]' in str(doc))

    def test_preamble_is_included(self):
        preamble = '\\usepackage{eurosym}'
        doc = LaTeXDocument('moooo')
        doc.set_preamble_string(preamble)
        self.assertTrue(preamble in str(doc))

    def test_obviously_wrong_encoding_trigger_exception(self):
        doc = LaTeXDocument('f00')
        self.assertRaises(ValueError, doc.set_encoding, 'latin1:')
        self.assertRaises(ValueError, doc.set_encoding, 'utf66')
        # the following passes (assertRaisesNot)
        doc.set_encoding('utf-8')

    def test_that_latex_maths_env_is_used(self):
        doc = LaTeXDocument('f00')
        doc.set_latex_environment('flalign*')
        self.assertTrue(r'\begin{flalign*}' in str(doc))
        self.assertTrue(r'\end{flalign*}' in str(doc))

################################################################################

class test_lualatex_document(unittest.TestCase):
    def test_formula_is_embedded(self):
        formula = 'E = m \\cdot c^2'
        doc = LuaLaTeXDocument(formula)
        self.assertTrue(formula in str(doc),
                "formula must be contained in LaTeX document as it was inserted.")

    def test_if_displaymath_unset_correct_env_used(self):
        doc = LuaLaTeXDocument('A = \pi r^2')
        doc.set_displaymath(False)
        self.assertTrue('\\(' in str(doc))
        self.assertTrue('\\)' in str(doc))

    def test_if_displaymath_is_set_correct_env_used(self):
        doc = LuaLaTeXDocument('A = \pi r^2')
        doc.set_displaymath(True)
        self.assertTrue('\\[' in str(doc))
        self.assertTrue('\\]' in str(doc))

    def test_preamble_is_included(self):
        preamble = '\\usepackage{eurosym}'
        doc = LuaLaTeXDocument('moooo')
        doc.set_preamble_string(preamble)
        self.assertTrue(preamble in str(doc))

    def test_that_latex_maths_env_is_used(self):
        doc = LuaLaTeXDocument('f00')
        doc.set_latex_environment('flalign*')
        self.assertTrue(r'\begin{flalign*}' in str(doc))
        self.assertTrue(r'\end{flalign*}' in str(doc))

