#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest
from gleetex.typesetting import LaTeXDocument
import gleetex.typesetting as typesetting

class test_typesetting(unittest.TestCase):
    def test_formula_is_embedded(self):
        formula = 'E = m \\cdot c^2'
        doc = LaTeXDocument(formula)
        self.assertTrue(formula in str(doc),
                "formula must be contained in LaTeX typesetting as it was inserted.")

    def test_if_displaymath_unset_correct_env_used(self):
        doc = LaTeXDocument(r'A = \pi r^2')
        doc.set_displaymath(False)
        self.assertTrue('\\(' in str(doc))
        self.assertTrue('\\)' in str(doc))

    def test_if_displaymath_is_set_correct_env_used(self):
        doc = LaTeXDocument(r'A = \pi r^2')
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


class test_replace_unicode_characters(unittest.TestCase):
    def test_that_ascii_strings_are_returned_verbatim(self):
        for string in ['abc.\\', '`~[]}{:<>']:
            textmode = typesetting.replace_unicode_characters(string, False)
            self.assertEqual(textmode, string, 'expected %s, got %s' % (string, textmode))
            mathmode = typesetting.replace_unicode_characters(string, True)
            self.assertEqual(textmode, string, 'expected %s, got %s' % (string, mathmode))

    def test_that_alphabetical_characters_are_replaced_by_default(self):
        textmode = typesetting.replace_unicode_characters('ö', False)
        self.assertTrue('\\"' in textmode)
        mathmode = typesetting.replace_unicode_characters('ö', True)
        self.assertTrue('\\ddot' in mathmode)

    def test_that_alphabetical_characters_are_kept_in_text_mode_if_specified(self):
        self.assertEqual(typesetting.replace_unicode_characters('ö', False, # text mode
                replace_alphabeticals=False), 'ö')
        self.assertEqual(typesetting.replace_unicode_characters('æ', False,
                replace_alphabeticals=False), 'æ')

    def test_that_alphanumericals_are_replaced_in_mathmode_even_if_replace_alphabeticals_set(self):
        self.assertNotEqual(typesetting.replace_unicode_characters('öäü', True,
            replace_alphabeticals=True), 'öäü')
        self.assertNotEqual(typesetting.replace_unicode_characters('æø', True,
            replace_alphabeticals=True), 'æø')


    def test_that_charachters_not_present_in_file_raise_exception(self):
        with self.assertRaises(ValueError):
            typesetting.replace_unicode_characters('€', True)

    def test_that_formulas_are_replaced(self):
       self.assertNotEqual(typesetting.replace_unicode_characters('π', True),
           'π')
       self.assertNotEqual(typesetting.replace_unicode_characters('π', False),
           'π')

class test_get_matching_brace(unittest.TestCase):
    def test_closing_brace_found_when_only_one_brace_present(self):
        text = 'text{ok}'
        self.assertEqual(typesetting.get_matching_brace(text, 4), len(text) - 1)
        self.assertEqual(typesetting.get_matching_brace(text + 'foo', 4), len(text) - 1)

    def test_outer_brace_found(self):
        text = 'text{o, bla\\"{o}dfdx.}ds'
        self.assertEqual(typesetting.get_matching_brace(text, 4), len(text)-3)

    def test_inner_brace_is_matched(self):
        text = 'text{o, bla\\"{o}dfdx.}ds'
        self.assertEqual(typesetting.get_matching_brace(text, 13), 15)

    def test_that_unmatched_braces_raise_exception(self):
        with self.assertRaises(ValueError):
            typesetting.get_matching_brace('text{foooooooo', 4)
        with self.assertRaises(ValueError):
            typesetting.get_matching_brace('text{jo\"{o....}', 4)

    def test_wrong_position_for_opening_brace_raises(self):
        with self.assertRaises(ValueError):
            typesetting.get_matching_brace('moo', 1)


class test_escape_unicode_maths(unittest.TestCase):
    """These tests assume that the tests written above work!"""
    def test_that_mathmode_and_textmode_are_treated_differently(self):
        math = typesetting.escape_unicode_maths('ö')
        self.assertNotEqual(math, 'ö')
        text = typesetting.escape_unicode_maths('\\text{ö}')
        self.assertFalse('ö' in text)
        # check whether characters got transcribed differently; it's enough to
        # check one character of the generated sequence, they should differ
        self.assertNotEqual(math[:2], text[6:8])

    def test_that_flag_to_preserve_alphas_is_passed_through(self):
        res = typesetting.escape_unicode_maths('\\text{ö}',
                replace_alphabeticals=False)
        self.assertEqual(res, '\\text{ö}')

    def test_that_all_characters_are_preserved_when_no_replacements_happen(self):
        text = 'This is a \\text{test} mate.'
        self.assertEqual(typesetting.escape_unicode_maths(text), text)
        self.assertEqual(typesetting.escape_unicode_maths(text,
            replace_alphabeticals=False), text)
        text = 'But yeah but no' * 20 + ', oh my god!'
        self.assertEqual(typesetting.escape_unicode_maths(text), text)
        self.assertEqual(typesetting.escape_unicode_maths(text,
            replace_alphabeticals=False), text)

    def test_that_everything_around_surrounded_character_is_preserved(self):
        text = 'This is a \\text{über} test. ;)'
        result = typesetting.escape_unicode_maths(text,
                replace_alphabeticals=True)
        ue_pos = text.index('ü')
        # text in front is unchanged
        self.assertEqual(result[:ue_pos], text[:ue_pos])
        # find b character, which is the start of the remaining string
        b_pos = result[ue_pos:].find('b') + ue_pos
        # check that text after umlaut matches
        self.assertEqual(result[b_pos:], text[ue_pos+1:])

        text = 'But yeah but no' * 20 + ', oh my god!ø'
        o_strok_pos = text.index('ø')
        res = typesetting.escape_unicode_maths(text)
        self.assertEqual(res[:o_strok_pos], text[:o_strok_pos])

    def test_that_unknown_unicode_characters_raise_exception(self):
        # you know that Santa Clause character? Seriously, if you don't know it,
        # you should have a look. LaTeX does indeed not have command for this
        # (2016, one never knows)
        santa = chr(127877)
        with self.assertRaises(typesetting.DocumentSerializationException):
            typesetting.escape_unicode_maths(santa)

    def test_that_two_text_environments_preserve_all_characters(self):
        text = r'a\cdot b \text{equals} b\cdot c} \mbox{ is not equal } u^{v\cdot k}'
        self.assertEqual(typesetting.escape_unicode_maths(text), text)
