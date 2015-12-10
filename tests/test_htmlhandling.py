from functools import reduce
import os, re, shutil, tempfile
import unittest
from gleetex import htmlhandling


excl_filename = htmlhandling.HtmlImageFormatter.EXCLUSION_FILE_NAME


def read(file_name, mode='r', encoding='utf-8'):
    """Read the file, return the string. Close file properly."""
    with open(file_name, mode, encoding=encoding) as handle:
        return handle.read()


class HtmlparserTest(unittest.TestCase):
    def setUp(self):
        self.p = htmlhandling.EqnParser()

    def test_start_tags_are_parsed_literally(self):
        self.p.feed("<p   i='o'>")
        self.assertEqual(self.p.get_data()[0], "<p   i='o'>",
                "The HTML parser should copy start tags literally.")

    def test_that_end_tags_are_copied_mostly_literally(self):
        self.p.feed("</ p></P>")
        self.assertEqual(self.p.get_data()[0], "</p>")
        self.assertEqual(self.p.get_data()[1], "</p>")

    def test_entities_are_unchanged(self):
        self.p.feed("&#xa;")
        self.assertEqual(self.p.get_data()[0], '&#xa;')

    def test_charsets_are_copied(self):
        self.p.feed('&gt;&rarr;')
        self.assertEqual(self.p.get_data()[0], '&gt;')
        self.assertEqual(self.p.get_data()[1], '&rarr;')

    def test_without_eqn_all_blocks_are_strings(self):
        self.p.feed("<html>\n<head/><body><p>42</p><h1>blah</h1></body></html>")
        self.assertTrue(reduce(lambda x,y: x and isinstance(y, str),
            self.p.get_data()), "all chunks have to be strings")

    def test_equation_is_detected(self):
        self.p.feed('<eq>foo \\pi</eq>')
        self.assertTrue(isinstance(self.p.get_data()[0], list))
        self.assertEqual(self.p.get_data()[0][2], 'foo \\pi')

    def test_tag_followed_by_eqn_is_correctly_recognized(self):
        self.p.feed('<p foo="bar"><eq>bar</eq>')
        self.assertEqual(self.p.get_data()[0], '<p foo="bar">')
        self.assertTrue(isinstance(self.p.get_data(), list), "second item of data must be equation data list")
    
    def test_document_with_tag_then_eqn_then_tag_works(self):
        self.p.feed('<div style="invalid">bar</div><eq>baz</eq><sometag>')
        eqn = None
        # test should not depend on a specific position of equation, search for
        # it
        data = self.p.get_data()
        for chunk in data:
            if isinstance(chunk, list):
                eqn = chunk
                break
        self.assertTrue(isinstance(data[0], str))
        self.assertTrue(isinstance(eqn, list),
                "equation chunk must be a list, otherwise it doesn't exist")
        self.assertTrue(isinstance(data[-1], str))

    def test_equation_is_copied_literally(self):
        self.p.feed('<eq ignore="me">my\nlittle\n\\tau</eq>')
        self.assertEqual(self.p.get_data()[0][2], 'my\nlittle\n\\tau')

    def test_unclosed_eqns_are_detected(self):
        self.assertRaises(htmlhandling.ParseException, self.p.feed,
                '<p><eq>\\endless\\formula')

    def test_nested_formulas_trigger_exception(self):
        self.assertRaises(htmlhandling.ParseException, self.p.feed,
                "<eq>\\pi<eq></eq></eq>")

    def test_formulas_without_displaymath_attribute_are_detected(self):
        self.p.feed('<p><eq>\frac12</eq><br /><eq env="inline">bar</eq></p>')
        formulas = [c for c in self.p.get_data() if isinstance(c, list)]
        self.assertEqual(len(formulas), 2) # there should be _2_ formulas
        self.assertEqual(formulas[0][1], False) # no displaymath
        self.assertEqual(formulas[1][1], False) # no displaymath

    def test_displaymath_is_recognized(self):
        self.p.feed('<eq env="displaymath">\\sum\limits_{n=1}^{e^i} a^nl^n</eq>')
        self.assertEqual(self.p.get_data()[0][1], True) # displaymath flag set

class HtmlImageTest(unittest.TestCase):
    def setUp(self):
        self.pos = {'depth':'99', 'height' : '88', 'width' : '77'}
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_that_no_file_is_written_if_no_content(self):
        with htmlhandling.HtmlImageFormatter('foo.html'):
            pass
        self.assertFalse(os.path.exists('foo.html')        )

    def test_file_if_written_when_content_exists(self):
        with htmlhandling.HtmlImageFormatter() as img:
            img.format_excluded(self.pos, '\\tau\\tau', 'foo.png')
        self.assertTrue(os.path.exists(excl_filename)        )

    def test_written_file_starts_and_ends_more_or_less_properly(self):
        with htmlhandling.HtmlImageFormatter('.') as img:
            img.format_excluded(self.pos, '\\tau\\tau', 'foo.png')
        data = read(htmlhandling.HtmlImageFormatter.EXCLUSION_FILE_NAME, 'r', encoding='utf-8')
        self.assertTrue('<html' in data and '</html>' in data)
        self.assertTrue('<body' in data and '</body>' in data)
        # make sure encoding is specified
        self.assertTrue('<meta' in data and 'charset=' in data)

    def test_id_contains_no_special_characters(self):
        data = htmlhandling.gen_id('\\tau!\'{}][~^')
        for character in {'!', "'", '\\', '{', '}'}:
            self.assertFalse(character in data)

    def test_that_empty_ids_raise_exception(self):
        self.assertRaises(ValueError, htmlhandling.gen_id, '')

    def test_that_same_characters_are_not_repeated(self):
        id = htmlhandling.gen_id("jo{{{{{{{{ha")
        self.assertEqual(id, "jo_ha")

    def test_that_ids_are_max_150_characters_wide(self):
        id = htmlhandling.gen_id('\\alpha\\cdot\\gamma + ' * 999)
        self.assertTrue(len(id) == 150)

    def test_that_ids_start_with_letter(self):
        id = htmlhandling.gen_id('{}\\[]ÖÖÖö9343...·tau')
        self.assertTrue(id[0].isalpha())

    def test_that_link_to_external_image_points_to_file_and_formula(self):
        expected_id = None
        formatted_img = None
        with htmlhandling.HtmlImageFormatter() as img:
            formatted_img = img.format_excluded(self.pos, '\\tau\\tau', 'foo.png')
            expected_id = htmlhandling.gen_id('\\tau\\tau')
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
        self.assertTrue('<p id' in external_file)
        self.assertTrue('="'+expected_id in external_file)

    def test_height_and_width_is_in_formatted_html_img_tag(self):
        data = None
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            data = img.get_html_img(self.pos, '\\tau\\tau', 'foo.png')
        self.assertTrue('height=' in data and self.pos['height'] in data)
        self.assertTrue('width=' in data and self.pos['width'] in data)

    def test_no_formula_gets_lost_when_reparsing_external_formula_file(self):
        with htmlhandling.HtmlImageFormatter() as img:
            img.format_excluded(self.pos, '\\tau' * 999, 'foo.png')
        with htmlhandling.HtmlImageFormatter() as img:
            img.format_excluded(self.pos, '\\pi' * 666, 'foo_2.png')
        data = read(excl_filename)
        self.assertTrue('\\tau' in data)
        self.assertTrue('\\pi' in data)

    def test_too_long_formulas_are_not_outsourced_if_not_configured(self):
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            img.format(self.pos, '\\tau' * 999, 'foo.png')
        self.assertFalse(os.path.exists('foo.html'))

    def test_that_too_long_formulas_get_outsourced_if_configured(self):
        with htmlhandling.HtmlImageFormatter() as img:
            img.set_max_formula_length(90)
            img.set_exclude_long_formulas(True)
            img.format(self.pos, '\\tau' * 999, 'foo.png')
        self.assertTrue(os.path.exists(excl_filename))
        data = read(htmlhandling.HtmlImageFormatter.EXCLUSION_FILE_NAME)
        self.assertTrue('\\tau\\tau' in data)

    def test_url_is_included(self):
        prefix = "http://crustulus.de/blog"
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            img.set_url(prefix)
            data = img.format(self.pos, '\epsilon<0', 'foo.png')
            self.assertTrue( prefix in data)

    def test_url_doesnt_contain_double_slashes(self):
        prefix = "http://crustulus.de/blog/"
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            img.set_url(prefix)
            data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png')
            self.assertFalse('//' in data.replace('http://','ignore'))

    # depth is used as negative offset, so negative depth should result in
    # positive offset
    def test_that_negative_depth_results_in_positive_offset(self):
        self.pos['depth'] = '-999'
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png')
            self.assertTrue('align: ' + str(self.pos['depth'])[1:] in data)

    def test_that_displaymath_is_set_or_unset(self):
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png',
                    True)
            self.assertTrue('="displaymath' in data)
            data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png',
                    False)
            self.assertTrue('="inlinemath' in data)

    def test_that_alternative_css_class_is_set_correctly(self):
        with htmlhandling.HtmlImageFormatter('foo.html') as img:
            img.set_display_math_css_class('no1')
            img.set_inline_math_css_class('no2')
            data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png',
                    True)
            self.assertTrue('="no1"' in data)
            data = img.format(self.pos, r'\gamma\text{strahlung}', 'foo.png',
                    False)
            self.assertTrue('="no2' in data)
        
 

def htmleqn(formula, hr=True):
    """Format a formula to appear as if it would have been outsourced into an
    external file."""
    return '%s\n<p id="%s"><pre>%s</pre></span></p>\n' % (\
            ('<hr/>' if hr else ''), htmlhandling.gen_id(formula), formula)


class OutsourcingParserTest(unittest.TestCase):
    def setUp(self):
        self.html = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"' +
        '\n  "http://www.w3.org/TR/html4/strict.dtd">\n<html>\n<head>\n' +
        '<meta http-equiv="content-type" content="text/html; charset=utf-8"/>' +
        '<title>Outsourced Formulas</title></head>\n<body>\n<h1>heading</h1>')

    def get_html(self, string):
        """Create html string with head / tail und put the specified string into
        it."""
        return self.html + string + '\n</body>\n</html>'


    def test_formulas_are_recognized(self):
        data = self.get_html(htmleqn('\\tau'))
        parser = htmlhandling.OutsourcedFormulaParser()
        parser.feed(data)
        self.assertEqual(len(parser.get_formulas()), 1)

    def test_formula_doesnt_contain_surrounding_rubbish(self):
        data = self.get_html(htmleqn('\\gamma'))
        parser = htmlhandling.OutsourcedFormulaParser()
        parser.feed(data)
        self.assertEqual(len(parser.get_formulas()), 1)
        key = next(iter(parser.get_formulas()))
        par = parser.get_formulas()[key]
        self.assertFalse('<h1' in par)
        self.assertFalse('body>' in par)
        self.assertFalse('hr' in par)

    def test_that_header_is_parsed_correctly(self):
        p = htmlhandling.OutsourcedFormulaParser()
        p.feed(self.get_html(htmleqn('test123', False)))
        head = p.get_head()
        self.assertTrue('DOCTYPE' in head)
        self.assertTrue('<html' in head)
        self.assertTrue('<title' in head)
        self.assertTrue('</title' in head)
        self.assertTrue('</head' in head)
        self.assertTrue('<meta' in head)
        self.assertTrue('charset=' in head)

    def test_multiple_formulas_are_recognized_correctly(self):
        p = htmlhandling.OutsourcedFormulaParser()
        p.feed(self.get_html(htmleqn('\\tau', False) + '\n' + 
            htmleqn('\\gamma') + '\n' + htmleqn('\\epsilon<0')))
        forms = p.get_formulas()
        self.assertEqual(len(forms), 3)
        self.assertTrue('\\gamma' in forms.values())
        self.assertTrue('\\gamma' in forms.values())
        self.assertTrue('\\epsilon<0' in forms.values())

