# pylint: disable=too-many-public-methods
from functools import reduce
import io
import os
import re
import shutil
import tempfile
import unittest
from gleetex import htmlhandling, sink


excl_filename = sink.EXCLUSION_FILE_NAME

HTML_SKELETON = """<html><head><meta http-equiv="Content-Type" content="text/html; charset={0}" />
</head><body>{1}</body>"""


def read(file_name, mode='r', encoding='utf-8'):
    """Read the file, return the string.

    Close file properly.
    """
    with open(file_name, mode, encoding=encoding) as handle:
        return handle.read()


class HtmlparserTest(unittest.TestCase):
    def setUp(self):
        self.p = htmlhandling.EqnParser()

    def test_start_tags_are_parsed_literally(self):
        self.p.feed("<p   i='o'>")
        self.assertEqual(
            self.p.get_data()[0],
            "<p   i='o'>",
            'The HTML parser should copy start tags literally.',
        )

    def test_that_end_tags_are_copied_literally(self):
        self.p.feed('</ p></P>')
        self.assertEqual(''.join(self.p.get_data()), '</ p></P>')

    def test_entities_are_unchanged(self):
        self.p.feed('&#xa;')
        self.assertEqual(self.p.get_data()[0], '&#xa;')

    def test_charsets_are_copied(self):
        self.p.feed('&gt;&rarr;')
        self.assertEqual(''.join(self.p.get_data()[0]), '&gt;&rarr;')

    def test_without_eqn_all_blocks_are_strings(self):
        self.p.feed('<html>\n<head/><body><p>42</p><h1>blah</h1></body></html>')
        self.assertTrue(
            reduce(lambda x, y: x and isinstance(y, str), self.p.get_data()),
            'all chunks have to be strings',
        )

    def test_equation_is_detected(self):
        self.p.feed('<eq>foo \\pi</eq>')
        self.assertTrue(isinstance(self.p.get_data()[0], (tuple, list)))
        self.assertEqual(self.p.get_data()[0][2], 'foo \\pi')

    def test_tag_followed_by_eqn_is_correctly_recognized(self):
        self.p.feed('<p foo="bar"><eq>bar</eq>')
        self.assertEqual(self.p.get_data()[0], '<p foo="bar">')
        self.assertTrue(
            isinstance(self.p.get_data(), list),
            'second item of data must be equation data list',
        )

    def test_document_with_tag_then_eqn_then_tag_works(self):
        self.p.feed('<div style="invalid">bar</div><eq>baz</eq><sometag>')
        eqn = None
        # test should not depend on a specific position of equation, search for
        # it
        data = self.p.get_data()
        for chunk in data:
            if isinstance(chunk, (tuple, list)):
                eqn = chunk
                break
        self.assertTrue(isinstance(data[0], str))
        self.assertTrue(
            eqn is not None, 'No equation found, must be tuple/list object.'
        )
        self.assertTrue(isinstance(data[-1], str))

    def test_equation_is_copied_literally(self):
        self.p.feed('<eq ignore="me">my\nlittle\n\\tau</eq>')
        self.assertEqual(self.p.get_data()[0][2], 'my\nlittle\n\\tau')

    def test_unclosed_eqns_are_detected(self):
        self.assertRaises(
            htmlhandling.ParseException, self.p.feed, '<p><eq>\\endless\\formula'
        )

    def test_nested_formulas_trigger_exception(self):
        self.assertRaises(
            htmlhandling.ParseException, self.p.feed, '<eq>\\pi<eq></eq></eq>'
        )
        self.assertRaises(
            htmlhandling.ParseException, self.p.feed, '<eq>\\pi<eq></p></eq>'
        )

    def test_formulas_without_displaymath_attribute_are_detected(self):
        self.p.feed('<p><eq>\frac12</eq><br /><eq env="inline">bar</eq></p>')
        formulas = [c for c in self.p.get_data() if isinstance(c,
                                                               (tuple, list))]
        self.assertEqual(len(formulas), 2)  # there should be _2_ formulas
        self.assertEqual(formulas[0][1], False)  # no displaymath
        self.assertEqual(formulas[1][1], False)  # no displaymath

    def test_that_unclosed_formulas_detected(self):
        self.assertRaises(htmlhandling.ParseException,
                          self.p.feed, '<eq>\\pi<eq></p>')
        self.assertRaises(htmlhandling.ParseException, self.p.feed, '<eq>\\pi')

    def test_formula_contains_only_formula(self):
        p = htmlhandling.EqnParser()
        p.feed('<p><eq>1<i<9</eq></p>')
        formula = next(e for e in p.get_data() if isinstance(e, (list, tuple)))
        self.assertEqual(formula[-1], '1<i<9')

        p = htmlhandling.EqnParser()
        p.feed('<p><eq env="displaymath">test</eq></p>')
        formula = next(e for e in p.get_data() if isinstance(e, (list, tuple)))
        self.assertEqual(formula[-1], 'test')

        p = htmlhandling.EqnParser()
        p.feed('<p><eq>1<i<9</eq></p>')
        formula = next(e for e in p.get_data() if isinstance(e, (list, tuple)))
        self.assertEqual(formula[-1], '1<i<9')

    def test_formula_with_html_sequences_are_unescaped(self):
        self.p.feed('<eq>a&gt;b</eq>')
        formula = self.p.get_data()[0]
        self.assertEqual(formula[-1], 'a>b')

    def test_displaymath_is_recognized(self):
        self.p.feed(
            '<eq env="displaymath">\\sum\limits_{n=1}^{e^i} a^nl^n</eq>')
        self.assertEqual(self.p.get_data()[0][1], True)  # displaymath flag set

    def test_encoding_is_parsed_from_HTML4(self):
        iso8859_1 = HTML_SKELETON.format(
            'iso-8859-15', 'öäüß').encode('iso-8859-1')
        self.p.feed(iso8859_1)
        self.assertEqual(self.p._EqnParser__encoding, 'iso-8859-15')

    def test_encoding_is_parsed_from_HTML5(self):
        document = r"""<!DOCTYPE html>
            <html xmlns="http://www.w3.org/1999/xhtml" lang="" xml:lang="">
            <head><meta charset="utf-8" />
              <meta name="generator" content="pandoc" />
              </head><body><p>hi</p></body></html>"""
        self.p.feed(document.encode('utf-8'))
        self.assertEqual(self.p._EqnParser__encoding.lower(), 'utf-8')

    def test_strings_can_be_passed_tO_parser_as_well(self):
        # no exception - everything is working as expected
        self.p.feed(HTML_SKELETON.format('utf-8', 'æø'))


class GetPositionTest(unittest.TestCase):
    def test_that_line_number_is_correct(self):
        self.assertEqual(htmlhandling.get_position('jojo', 0)[0], 0)
        self.assertEqual(htmlhandling.get_position('jojo', 3)[0], 0)
        self.assertEqual(htmlhandling.get_position('a\njojo', 3)[0], 1)
        self.assertEqual(htmlhandling.get_position('a\n\njojo', 3)[0], 2)

    def test_that_position_on_line_is_correct(self):
        self.assertEqual(htmlhandling.get_position('jojo', 0)[1], 0)
        self.assertEqual(htmlhandling.get_position('jojo', 3)[1], 3)
        self.assertEqual(htmlhandling.get_position('a\njojo', 3)[1], 2)
        self.assertEqual(htmlhandling.get_position('a\n\njojo', 3)[1], 1)


class HtmlImageTest(unittest.TestCase):
    def setUp(self):
        self.pos = {'depth': 99, 'height': 88, 'width': 77}
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_that_no_file_is_written_if_no_content(self):
        ht = htmlhandling.HtmlImageFormatter('foo')
        self.assertFalse(os.path.exists('foo.html'))

    def test_file_if_written_when_content_exists(self):
        img = htmlhandling.HtmlImageFormatter()
        img.format(self.pos, '\\tau\\tau' * 20, 'foo.png')
        self.assertTrue(len(img.get_excluded()) == 1)

    def test_id_contains_no_special_characters(self):
        data = htmlhandling.generate_label("\\tau!'{}][~^")
        for character in {'!', "'", '\\', '{', '}'}:
            self.assertFalse(character in data)

    def test_formula_can_consist_only_of_numbers_and_id_is_generated(self):
        data = htmlhandling.generate_label('9*8*7=504')
        self.assertTrue(data.startswith('form'))
        self.assertTrue(data.endswith('504'))

    def test_that_empty_ids_raise_exception(self):
        self.assertRaises(ValueError, htmlhandling.generate_label, '')

    def test_that_same_characters_are_not_repeated(self):
        id = htmlhandling.generate_label('jo{{{{{{{{ha')
        self.assertEqual(id, 'jo_ha')

    def test_that_ids_are_max_150_characters_wide(self):
        id = htmlhandling.generate_label('\\alpha\\cdot\\gamma + ' * 999)
        self.assertTrue(len(id) == 150)

    def test_that_ids_start_with_letter(self):
        id = htmlhandling.generate_label('{}\\[]ÖÖÖö9343...·tau')
        self.assertTrue(id[0].isalpha())

    def test_that_link_to_external_image_points_to_file_and_formula(self):
        formula = '\\tau\\tau\gamma\delta' * 42
        img = htmlhandling.HtmlImageFormatter()
        formatted_img = img.format(self.pos, formula, 'foo.png')
        expected_id = htmlhandling.generate_label(formula)
        sink.html_write_excluded_file(excl_filename, img.get_excluded())
        external_file = read(excl_filename, 'r', encoding='utf-8')
        # find linked formula path
        href = re.search('href="(.*?)"', formatted_img)
        self.assertTrue(href != None)
        # extract path and id from it
        self.assertTrue('#' in href.groups()[0])
        path, id = href.groups()[0].split('#')
        self.assertEqual(path, excl_filename)
        self.assertEqual(id, expected_id)

        # check external file
        self.assertTrue('<p' in external_file and 'id="' in external_file)
        self.assertTrue('="' + expected_id in external_file)

    def test_that_link_to_external_image_points_to_file_basepath_and_formula(self):
        os.mkdir('basepath')
        formula = '\\tau\\tau\delta\gamma\epsilon' * 42
        img = htmlhandling.HtmlImageFormatter('basepath')
        formatted_img = img.format(
            self.pos, formula, 'foo.png')
        # find linked formula path
        href = re.search('href="(.*?)"', formatted_img)
        self.assertTrue(href != None)
        # extract path and id from it
        self.assertTrue('#' in href.groups()[0])
        path, id = href.groups()[0].split('#')
        self.assertEqual(path, 'basepath/' + excl_filename)
        expected_id = htmlhandling.generate_label(formula)
        self.assertEqual(id, expected_id)

    def test_height_and_width_is_in_formatted_html_img_tag(self):
        data = None
        img = htmlhandling.HtmlImageFormatter('foo.html')
        data = img.format(self.pos, '\\tau\\tau', 'foo.png')
        self.assertTrue('height=' in data and str(self.pos['height']) in data)
        self.assertTrue('width=' in data and str(self.pos['width']) in data)

    def test_no_formula_gets_lost_when_reparsing_external_formula_file(self):
        img = htmlhandling.HtmlImageFormatter(exclusion_file_path=excl_filename)
        img.format(self.pos, '\\tau' * 999, 'foo.png')
        img = htmlhandling.HtmlImageFormatter(exclusion_file_path=excl_filename)
        img.format(self.pos, '\\pi\\tau' * 666, 'foo_2.png')
        sink.html_write_excluded_file(excl_filename, img.get_excluded())
        data = read(excl_filename)
        self.assertTrue('\\tau' in data)
        self.assertTrue('\\pi' in data)

    def test_too_long_formulas_are_not_outsourced_if_not_configured(self):
        img = htmlhandling.HtmlImageFormatter('foo.html')
        img.format(self.pos, '\\tau' * 999, 'foo.png')
        self.assertFalse(os.path.exists('foo.html'))

    def test_that_too_long_formulas_get_excluded(self):
        img = htmlhandling.HtmlImageFormatter()
        img.set_max_formula_length(90)
        img.format(self.pos, '\\tau' * 999, 'foo.png')
        self.assertEqual(len(img.get_excluded()), 1)

    def test_url_is_included(self):
        prefix = 'http://crustulus.de/blog'
        img = htmlhandling.HtmlImageFormatter('foo.html')
        img.set_url(prefix)
        data = img.format(self.pos, '\epsilon<0', 'foo.png')
        self.assertTrue(prefix in data)

    def test_url_doesnt_contain_double_slashes(self):
        prefix = 'http://crustulus.de/blog/'
        img = htmlhandling.HtmlImageFormatter('foo.html')
        img.set_url(prefix)
        data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png')
        self.assertFalse('//' in data.replace('http://', 'ignore'))

    # depth is used as negative offset, so negative depth should result in
    # positive offset
    def test_that_negative_depth_results_in_positive_offset(self):
        self.pos['depth'] = '-999'
        img = htmlhandling.HtmlImageFormatter('foo.html')
        data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png')
        self.assertTrue('align: ' + str(self.pos['depth'])[1:] in data)

    def test_that_displaymath_is_set_or_unset(self):
        img = htmlhandling.HtmlImageFormatter('foo.html')
        data = img.format(
            self.pos, r'\gamma\text{strahlung}', 'foo.png', True)
        self.assertTrue('="displaymath' in data)
        data = img.format(
            self.pos, r'\gamma\text{strahlung}', 'foo.png', False)
        self.assertTrue('="inlinemath' in data)

    def test_that_alternative_css_class_is_set_correctly(self):
        img = htmlhandling.HtmlImageFormatter('foo.html')
        img.set_display_math_css_class('no1')
        img.set_inline_math_css_class('no2')
        data = img.format(
            self.pos, r'\gamma\text{strahlung}', 'foo.png', True)
        self.assertTrue('="no1"' in data)
        data = img.format(
            self.pos, r'\gamma\text{strahlung}', 'foo.png', False)
        self.assertTrue('="no2' in data)

    def test_that_unicode_is_replaced_if_requested(self):
        img = htmlhandling.HtmlImageFormatter('foo.html')
        img.set_replace_nonascii(True)
        data = img.format(self.pos, '←', 'foo.png')
        self.assertTrue(
                '\\leftarrow' in data, 'expected: "\\leftarrow" to be in "%s"' % data
            )

    def test_that_unicode_is_kept_if_not_requested_to_replace(self):
        img = htmlhandling.HtmlImageFormatter('foo.html')
        img.set_replace_nonascii(False)
        data = img.format(self.pos, '←', 'foo.png')
        self.assertTrue('←' in data)

    def test_formatting_commands_are_stripped(self):
        img = htmlhandling.HtmlImageFormatter('test_basedir')
        data = img.format(self.pos, 'a\,b\,c\,d', 'foo.png')
        self.assertTrue('a b c d' in data)
        data = img.format(self.pos, 'a\,b\;c\ d', 'foo.png')
        self.assertTrue('a b c d' in data)

        data = img.format(self.pos, '\Big\{foo\Big\}', 'foo.png')
        self.assertTrue('\{foo' in data and '\}' in data)
        data = img.format(self.pos, r'\left\{foo\right\}', 'foo.png')
        self.assertTrue('\{' in data)
        self.assertTrue('foo' in data)
        self.assertTrue('\}' in data)
