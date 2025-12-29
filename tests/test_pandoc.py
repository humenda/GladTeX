from unittest import TestCase

from gleetex.pandoc import PandocAstImageFormatter as Formatter
from gleetex.pandoc import ast


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


class PandocAstTest(TestCase):
    def test_inline_text(self):
        self.assertEqual(ast.InlineText().to_json(), {"t": "Str", "c": ""})

        it = ast.InlineText("Teasdfkj")
        self.assertEqual(it.to_json(), {"t": it.pandoc_ast_name(), "c": it.text})

    def test_inline_code(self):
        self.assertEqual(
            ast.InlineCode().to_json(),
            {"t": "Code", "c": [["", [], []], ""]}
        )

        ic = ast.InlineCode("asdf=35 ;sdf")
        self.assertEqual(
            ic.to_json(),
            {"t": ic.pandoc_ast_name(), "c": [["", [], []], ic.code]},
        )

        ic = ast.InlineCode(
            "23-a;f';lsdf=3df",
            id="superid",
            classes=["saint", "clon"],
            key_values={"sauce": "claude", "51": "route99"},
        )
        self.assertEqual(
            ic.to_json(),
            {
                "t": "Code",
                "c": [
                    [ic.id, ic.classes, [["sauce", "claude"], ["51", "route99"]]],
                    ic.code,
                ],
            },
        )

    def test_inline_link(self):
        self.assertEqual(
            ast.InlineLink().to_json(),
            {"t": "Link", "c": [["", [], []], [], ["", ""]]},
        )

        il = ast.InlineLink(
            [ast.InlineText("description")], url="url:example.com", title="link title"
        )
        self.assertEqual(
            il.to_json(),
            {
                "t": "Link",
                "c": [["", [], []], [il.inlines[0].to_json()], [il.url, il.title]],
            },
        )

        il = ast.InlineLink(
            [ast.InlineText("description")],
            url="url:example.com",
            title="link title",
            id="superid3-248",
            classes=["aint", "clon"],
            key_values={"sauce": "clade", "51": "roe98", "rocky": "0"},
        )
        self.assertEqual(
            il.to_json(),
            {
                "t": il.pandoc_ast_name(),
                "c": [
                    [
                        il.id,
                        il.classes,
                        [["sauce", "clade"], ["51", "roe98"], ["rocky", "0"]],
                    ],
                    [il.inlines[0].to_json()],
                    [il.url, il.title],
                ],
            },
        )

    def test_inline_image(self):
        self.assertEqual(
            ast.InlineImage().to_json(),
            {"t": "Image", "c": [["", [], []], [], ["", ""]]},
        )

        ii = ast.InlineImage(
            [ast.InlineText("description")], url="url:example.com", title="image title"
        )
        self.assertEqual(
            ii.to_json(),
            {
                "t": "Image",
                "c": [["", [], []], [ii.inlines[0].to_json()], [ii.url, ii.title]],
            },
        )

        ii = ast.InlineImage(
            [ast.InlineText("description")],
            url="url:example.com",
            title="image title",
            id="superid3-248",
            classes=["aint", "clon"],
            key_values={"sauce": "clade", "51": "roe98", "rocky": "0"},
        )
        self.assertEqual(
            ii.to_json(),
            {
                "t": ii.pandoc_ast_name(),
                "c": [
                    [
                        ii.id,
                        ii.classes,
                        [["sauce", "clade"], ["51", "roe98"], ["rocky", "0"]],
                    ],
                    [ii.inlines[0].to_json()],
                    [ii.url, ii.title],
                ],
            },
        )

    def test_math_to_json(self):
        self.assertEqual(ast.Math().to_json(), {"t": "Math", "c": [{"t": "InlineMath"}, ""]})

        m = ast.Math("E = mc^2", ast.MathType.INLINE)
        self.assertEqual(
            m.to_json(),
            {"t": m.pandoc_ast_name(), "c": [{"t": ast.MathType.INLINE}, m.formula]},
        )

        m = ast.Math("F = ma", ast.MathType.DISPLAY)
        self.assertEqual(m.to_json(), {"t": "Math", "c": [{"t": m.type}, m.formula]})

    def test_math_from_valid_json(self):
        self.assertEqual(
            ast.Math.from_json({"t": "Math", "c": [{"t": "InlineMath"}, ""]}),
            ast.Math(),
        )

        self.assertEqual(
            ast.Math.from_json({"t": "Math", "c": [{"t": ast.MathType.DISPLAY}, ""]}),
            ast.Math(type=ast.MathType.DISPLAY),
        )

        self.assertEqual(
            ast.Math.from_json(
                {"t": "Math", "c": [{"t": ast.MathType.DISPLAY}, r"y = \lambda \rho^2"]}
            ),
            ast.Math(r"y = \lambda \rho^2", ast.MathType.DISPLAY),
        )

    def test_math_from_invalid_json(self):
        json_ast = {"t": "Math", "c": [{"t": "InlieMath"}, r"y = \lambda \rho^2"]}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

        json_ast = {"t": "Match", "c": [{"t": "InlineMath"}, r"y = \lambda \rho^2"]}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

        json_ast = {"c": [{"t": "InlineMath"}, r"y = \lambda \rho^2"]}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

        json_ast = {"t": "Math", "c": [{"t": "InlineMath"}]}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

        json_ast = {"t": "Math", "c": ["formula"]}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

        json_ast = [1, 3, 4]
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

        json_ast = {}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.Math.from_json(json_ast)
        self.assertEqual(cm.exception.ast, json_ast)

    def test_paragraph(self):
        self.assertEqual(ast.Paragraph().to_json(), {"t": "Para", "c": []})

        p = ast.Paragraph([ast.InlineImage()])
        self.assertEqual(
            p.to_json(), {"t": p.pandoc_ast_name(), "c": [p.inlines[0].to_json()]}
        )

        p = ast.Paragraph(
            [ast.InlineText("text"), ast.InlineImage([ast.InlineCode("code")])]
        )
        self.assertEqual(
            p.to_json(),
            {
                "t": p.pandoc_ast_name(),
                "c": [p.inlines[0].to_json(), p.inlines[1].to_json()],
            },
        )

    def test_raw_block(self):
        self.assertEqual(
            ast.RawBlock(ast.RawFormat.HTML).to_json(),
            {"t": "RawBlock", "c": ["html", ""]},
        )

        self.assertEqual(
            ast.RawBlock(ast.RawFormat.TEX).to_json(),
            {"t": "RawBlock", "c": [ast.RawFormat.TEX, ""]},
        )

        rb = ast.RawBlock(ast.RawFormat.TEX, "lsakdfj039jlkkjlaskdjf")
        self.assertEqual(rb.to_json(), {"t": "RawBlock", "c": [ast.RawFormat.TEX, rb.content]})

    def test_heading(self):
        self.assertEqual(
            ast.Heading().to_json(),
            {"t": "Header", "c": [1, ["", [], []], []]},
        )

        h = ast.Heading([ast.InlineText("description")], level=2)
        self.assertEqual(
            h.to_json(),
            {
                "t": "Header",
                "c": [h.level, ["", [], []], [h.inlines[0].to_json()]],
            },
        )

        h = ast.Heading(
            [ast.InlineText("description")],
            level=4,
            id="superid3-248",
            classes=["aint", "clon"],
            key_values={"sauce": "clade", "51": "roe98", "rocky": "0"},
        )
        self.assertEqual(
            h.to_json(),
            {
                "t": h.pandoc_ast_name(),
                "c": [
                    h.level,
                    [
                        h.id,
                        h.classes,
                        [["sauce", "clade"], ["51", "roe98"], ["rocky", "0"]],
                    ],
                    [h.inlines[0].to_json()],
                ],
            },
        )

    def test_foreach_element(self):
        partial_ast = [
            e.to_json()
            for e in (
                ast.Paragraph(
                    [
                        ast.InlineCode("blabla"),
                        ast.Math("formula!"),
                        ast.InlineLink(
                            [
                                ast.InlineText("a string and"),
                                ast.Math("a formula", ast.MathType.DISPLAY),
                            ],
                            id="image-id",
                            url="example.com",
                        ),
                    ]
                ),
                ast.Math(),
                ast.Heading(
                    [
                        ast.InlineText("my heading"),
                        ast.Math("with math", ast.MathType.DISPLAY),
                    ]
                ),
                ast.InlineImage(
                    [
                        ast.InlineLink(
                            [
                                ast.Math("nested formula"),
                                ast.InlineText("inside"),
                            ]
                        )
                    ]
                ),
            )
        ]

        formula_list = []
        displaymath_count = 0

        def update(node):
            nonlocal displaymath_count

            math = ast.Math.from_json(node)
            formula_list.append(math.formula)
            displaymath_count += math.type == ast.MathType.DISPLAY

        ast.foreach_element(ast.Math, update, partial_ast)
        self.assertEqual(
            formula_list, ["formula!", "a formula", "", "with math", "nested formula"]
        )
        self.assertEqual(displaymath_count, 2)

        # Check that elements are replaced when requested.
        ast.foreach_element(
            ast.Paragraph, lambda node: ast.InlineText().to_json(), partial_ast
        )
        ast.foreach_element(
            ast.Heading, lambda node: ast.InlineText().to_json(), partial_ast
        )
        ast.foreach_element(
            ast.InlineImage, lambda node: ast.InlineText().to_json(), partial_ast
        )
        self.assertEqual(
            partial_ast,
            [
                e.to_json()
                for e in (
                    ast.InlineText(),
                    ast.Math(),
                    ast.InlineText(),
                    ast.InlineText(),
                )
            ],
        )

    def test_supported_ast_version(self):
        self.assertTrue(ast.is_supported_ast_version(ast.SUPPORTED_AST_VERSION + [43, 5]))
        self.assertTrue(ast.is_supported_ast_version(ast.SUPPORTED_AST_VERSION + [0]))

        self.assertFalse(ast.is_supported_ast_version(ast.SUPPORTED_AST_VERSION[:1] + [ast.SUPPORTED_AST_VERSION[1] + 1]))
        self.assertFalse(ast.is_supported_ast_version(ast.SUPPORTED_AST_VERSION[:1] + [ast.SUPPORTED_AST_VERSION[1] - 1]))

        self.assertFalse(ast.is_supported_ast_version([ast.SUPPORTED_AST_VERSION[1] + 1] + ast.SUPPORTED_AST_VERSION[1:]))
        self.assertFalse(ast.is_supported_ast_version([ast.SUPPORTED_AST_VERSION[1] - 1] + ast.SUPPORTED_AST_VERSION[1:]))

    def test_ast_root_version_check(self):
        self.assertEqual(
            ast.ast_root_blocks(
                {
                    "pandoc-api-version": ast.SUPPORTED_AST_VERSION,
                    "blocks": [ast.Paragraph()],
                }
            ),
            [ast.Paragraph()],
        )

        unsupported_version = ast.SUPPORTED_AST_VERSION[:1] + [ast.SUPPORTED_AST_VERSION[1] + 1]
        with self.assertRaises(ast.UnsupportedPandocJsonAstVersionError) as cm:
            ast.ast_root_blocks(
                {
                    "pandoc-api-version": unsupported_version,
                    "blocks": [ast.Paragraph()],
                }
            )
        self.assertEqual(cm.exception.version, unsupported_version)

        ast_root = {"pandoc-api-version": ast.SUPPORTED_AST_VERSION}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.ast_root_blocks(ast_root)
        self.assertEqual(cm.exception.ast, ast_root)

        ast_root = {"blocks": [ast.Paragraph()]}
        with self.assertRaises(ast.PandocJsonAstParseError) as cm:
            ast.ast_root_blocks(ast_root)
        self.assertEqual(cm.exception.ast, ast_root)
