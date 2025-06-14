from unittest import TestCase

from gleetex.pandoc import PandocAstImageFormatter as Formatter


class PandocAstImageFormatterTest(TestCase):
    # As most things are already tested in `test_htmlhandling.HtmlImageTest`,
    # we only test things specific to the Pandoc AST handling here.

    def test_height_width_depth_formula_imgpath_included(self):
        formula = r'a = b^2 + x^3 - \frac{3x^7 \cdot 3}{\alpha \beta \gamma}'
        path = 'foo.png'
        ast = str(Formatter().format(
            {'depth': 99, 'height': 88, 'width': 77}, formula, path,
        ))
        self.assertIn("['height', '88", ast)
        self.assertIn("['width', '77", ast)
        self.assertIn('99', ast)
        self.assertIn(formula.replace('\\', '\\\\'), ast)
        self.assertIn(path, ast)

        formula = r'\lambda x - 52\rho = 33^\alpha^\beta'
        ast = str(Formatter().format(
            {'depth': 39, 'height': 21, 'width': 2}, formula, path,
        ))
        self.assertIn("['height', '21", ast)
        self.assertIn("['width', '2", ast)
        self.assertIn('39', ast)
        self.assertIn(formula.replace('\\', '\\\\'), ast)
        self.assertIn(path, ast)

        formula = r'\phi \sin(\gamma x) \cos(xyz - 3)'
        path = 'bar.svg'
        ast = str(Formatter(is_epub=True).format(
            {'depth': 24, 'height': 11, 'width': 53}, formula, path,
        ))
        self.assertIn("['height', '11", ast)
        self.assertIn("['width', '53", ast)
        self.assertIn('24', ast)
        self.assertIn(formula.replace('\\', '\\\\'), ast)
        self.assertIn(path, ast)

    def test_outsourced_descriptions_are_link(self):
        ast = Formatter().format(
            {'depth': 39, 'height': 21, 'width': 2}, 'a + b +' * 100,
            'foo.png',
        )
        self.assertEqual(ast['t'], 'Link')

        ast = Formatter().format(
            {'depth': 12, 'height': 1, 'width': 24}, r'\lambda x - q +' * 100,
            'foo.png',
        )
        self.assertEqual(ast['t'], 'Link')

    def test_outsourced_descriptions_contain_all_information(self):
        formula = r'a = b^2 + x^3 - \frac{3x^7 \cdot 3}{\alpha \beta \gamma}' * 100
        path = 'foo.png'
        ast = str(Formatter().format(
            {'depth': 99, 'height': 88, 'width': 77}, formula, path,
        ))
        self.assertIn("['height', '88", ast)
        self.assertIn("['width', '77", ast)
        self.assertIn('99', ast)
        self.assertIn(formula[:20].replace('\\', '\\\\'), ast)
        self.assertIn(path, ast)

        formula = r'\lambda x - 52\rho = 33^\alpha^\beta' * 100
        ast = str(Formatter(is_epub=True).format(
            {'depth': 39, 'height': 21, 'width': 2}, formula, path,
        ))
        self.assertIn("['height', '21", ast)
        self.assertIn("['width', '2", ast)
        self.assertIn('39', ast)
        self.assertIn(formula[:20].replace('\\', '\\\\'), ast)
        self.assertIn(path, ast)
