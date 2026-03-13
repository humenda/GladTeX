import contextlib
import io
import json
import os
import shutil
import tempfile
from unittest import TestCase
from unittest.mock import patch

from gleetex import cachedconverter
from gleetex.__main__ import Main
from gleetex.pandoc import ast as pandoc_ast


HTML_SKELETON = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body>
{}
</body>
</html>"""


class MockCachedConverter:
    """Mock converter used to test conversion behavior without LaTeX tooling."""

    def __init__(self, *_args, **_kwargs):
        self._cache = {}
        self._path_count = 0
        self._failed_keys = set()

    def set_option(self, *_args, **_kwargs):
        return None

    def set_replace_nonascii(self, *_args, **_kwargs):
        return None

    def convert_all(self, formulas, skip_faults=False):
        self._failed_keys = set()
        for formula_count, (_pos, displaymath, formula) in enumerate(formulas, start=1):
            if "BAD_FORMULA" in formula:
                err = cachedconverter.ConversionException(
                    "Mocked conversion failure", formula, formula_count
                )
                if skip_faults:
                    self._failed_keys.add((formula, displaymath))
                    continue
                raise err
            key = (formula, displaymath)
            if key in self._cache:
                continue
            self._cache[key] = {
                "pos": {"depth": 1, "height": 2, "width": 3},
                "path": f"eqn{self._path_count:03d}.svg",
                "displaymath": displaymath,
            }
            self._path_count += 1

    def get_skipped_formulas(self, formulas):
        failures = []
        for formula_count, (pos, displaymath, formula) in enumerate(formulas, start=1):
            if (formula, displaymath) not in self._failed_keys:
                continue
            failures.append(
                cachedconverter.ConversionException(
                    "Mocked conversion failure",
                    formula,
                    formula_count,
                    pos[0] + 1 if pos else None,
                    pos[1] + 1 if pos else None,
                )
            )
        return failures

    def get_data_for(self, formula, display_math):
        data = self._cache[(formula, display_math)].copy()
        data.update({"formula": formula, "displaymath": display_math})
        return data


class MainTest(TestCase):

    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_empty_excluded_descriptions_file_created(self):
        with open('testfile.htex', 'w') as f:
            f.write(HTML_SKELETON.format(r"""
                <p>This is a unremarkable document for <eq>testing</eq>
                purposes <eq>only</eq>.</p>

                <h1>Display Math</h1>
                <p><eq env="displaymath">\lambda x y z = \rho \gamma y^2
                - \sin(3 - 5) + \cos(\tan(xy))
                </eq></p>

                <p>And <eq>soooooooooooooooooooooooooooo on</eq> we
                <eq>go - 32</eq>.</p>
            """))

        Main().run(['prog', 'testfile.htex'])
        self.assertFalse(os.path.exists('excluded-descriptions.html'))

    def test_excluded_descriptions_file_created_when_needed(self):
        with open('testfile.htex', 'w') as f:
            f.write(HTML_SKELETON.format(r"""
                <p>This is a unremarkable document for <eq>testing
                loooooooooooooooooooooooooooooooooooooong fooooooooormuuuuulas
                ooooooooooooooooooooooooooooonly E=mc^2 \cdot \gamma</eq>.</p>

                <h1>Display Math</h1>
                <p><eq env="displaymath">\lambda x y z = \rho \gamma y^2
                - \sin(3 - 5) + \cos(\tan(xy)) \cdot
                \frac{\sin(\frac{\pi}{2}) - 2}{\cos(\phi\frac{pi}{3})}
                </eq></p>

                <p>And <eq>soooooooooooooooooooooooooooo on</eq> we
                <eq>go - 32</eq>.</p>
            """))

        Main().run(['prog', 'testfile.htex'])
        self.assertTrue(os.path.exists('excluded-descriptions.html'))

        with open('excluded-descriptions.html', 'r') as f:
            html = f.read()
        self.assertIn(
            r'loooooooooooooooooooooooooooooooooooooong fooooooooormuuuuulas',
            html,
        )
        self.assertIn(
            r'\frac{\sin(\frac{\pi}{2}) - 2}{\cos(\phi\frac{pi}{3})}',
            html,
        )

    def _write_pandoc_json(self, blocks, file_name='input.json'):
        document = {
            "pandoc-api-version": pandoc_ast.SUPPORTED_AST_VERSION,
            "meta": {},
            "blocks": blocks,
        }
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(document, f)
        return file_name

    @patch('gleetex.__main__.cachedconverter.CachedConverter', MockCachedConverter)
    def test_skip_faulty_formulas_continues_conversion(self):
        input_file = self._write_pandoc_json(
            [
                {
                    "t": "Para",
                    "c": [
                        {"t": "Math", "c": [{"t": "InlineMath"}, r"BAD_FORMULA_{\frac{1}{"]},
                        {"t": "Space"},
                        {"t": "Math", "c": [{"t": "InlineMath"}, "x + 1"]},
                    ],
                },
            ]
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            Main().run(
                [
                    'prog',
                    '-P',
                    '--skip-faulty-formulas',
                    '-o',
                    'out.json',
                    input_file,
                ]
            )

        with open('out.json', 'r', encoding='utf-8') as f:
            ast = json.load(f)
        inlines = ast["blocks"][0]["c"]

        self.assertEqual(inlines[0]["t"], "Span")
        self.assertEqual(inlines[0]["c"][0][1], ["gladtex-error"])
        self.assertEqual(inlines[0]["c"][1], [{"t": "Str", "c": "[LaTeX error]"}])
        self.assertEqual(inlines[2]["t"], "Image")

        err = stderr.getvalue()
        self.assertIn("Warning: failed to convert formula 1", err)
        self.assertIn("1 formulas failed; placeholders inserted.", err)

    @patch('gleetex.__main__.cachedconverter.CachedConverter', MockCachedConverter)
    def test_default_mode_remains_fail_fast(self):
        input_file = self._write_pandoc_json(
            [{"t": "Para", "c": [{"t": "Math", "c": [{"t": "InlineMath"}, "BAD_FORMULA"]}]}]
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                Main().run(['prog', '-P', '-o', 'out.json', input_file])
        self.assertEqual(cm.exception.code, 91)

    @patch('gleetex.__main__.cachedconverter.CachedConverter', MockCachedConverter)
    def test_display_math_errors_use_div_placeholder(self):
        input_file = self._write_pandoc_json(
            [
                {
                    "t": "Para",
                    "c": [{"t": "Math", "c": [{"t": "DisplayMath"}, "BAD_FORMULA_DISPLAY"]}],
                }
            ]
        )
        with contextlib.redirect_stderr(io.StringIO()):
            Main().run(
                [
                    'prog',
                    '-P',
                    '--skip-faulty-formulas',
                    '-o',
                    'out.json',
                    input_file,
                ]
            )

        with open('out.json', 'r', encoding='utf-8') as f:
            ast = json.load(f)
        placeholder = ast["blocks"][0]

        self.assertEqual(placeholder["t"], "Div")
        self.assertEqual(placeholder["c"][0][1], ["gladtex-error"])
        self.assertEqual(
            placeholder["c"][1][0]["c"],
            [{"t": "Str", "c": "[LaTeX error]"}],
        )
