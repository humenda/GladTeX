# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""This module contains functionality to parse formulas from a given Pandoc
document AST and to replace these through formatted HTML equations.

It works in these parsses:

1.  Extract all math elements from the Pandoc AST.
2.  Convert all formulas to images
    *   LaTeX is the slowest bit in this process, therefore the formulas are
        collected and then converted in parallel.
3.  Replace all math tags in the pandoc AST by raw HTML inline formatting
    instructions that reference the converted images and position them
    correctly. Note that this cannot made HTML-independent because of the
    requirement to use vertical alignment that is not supported by the Pandoc
    AST and is hence expressed as a CSS styling instruction.
"""

import json
import posixpath

from .htmlhandling import ImageFormatter, ParseException, generate_label


def __extract_formulas(formulas, ast):
    """Recursively extract 'Math' elements from the given AST and add them to
    `formulas (list)`."""
    if isinstance(ast, list):
        for item in ast:
            __extract_formulas(formulas, item)
    elif isinstance(ast, dict):
        if 't' in ast and ast['t'] == 'Math':
            style, formula = ast['c']
            # style = {'t': 'blah'} -> we want blah
            style = next(iter(style.values()))
            if style not in ['InlineMath', 'DisplayMath']:
                raise ParseException(
                    '[pandoc] unknown formula formatting: ' + repr(ast['c'])
                )
            style = True if style == 'DisplayMath' else False
            # position is None (only applicable for HTML parsing)
            formulas.append((None, style, formula))
        elif 'c' in ast:
            __extract_formulas(formulas, ast['c'])
    #    ^ all other cases do not matter


def extract_formulas(ast):
    """Extract formulas from a given Pandoc document AST. The returned formulas
    are typed like those form the HTML parser, therefore the first argument of
    the tuple is unused and hence None.

    :param  ast  Structure of lists and dicts representing a Pandoc document AST
    :return a list of formulas where each formula is (None, style, formula)
    """
    formulas = []
    __extract_formulas(formulas, ast['blocks'])
    return formulas


def replace_formulas_in_ast(formatter, ast, formulas):
    """Replace 'Math' elements from the given AST with a formatted variant.

    Each 'Math' element found in the Pandoc AST will directly be
    replaced by the image link AST element returned by
    `formatter.format()`, which means the `formatter` has to produce a
    valid Pandoc AST element.

    The formulas are taken from the supplied formulas list. The number
    of formulas in the document has to match the number of formulas form
    the list.
    """
    if not formulas:
        return
    if isinstance(ast, list):
        for item in ast:
            replace_formulas_in_ast(formatter, item, formulas)
    elif isinstance(ast, dict):
        if 't' in ast and ast['t'] == 'Math':
            eqn = formulas.pop(0)
            ast.clear()
            ast.update(formatter.format(
                eqn['pos'], eqn['formula'], eqn['path'], eqn['displaymath'],
            ))
        elif 'c' in ast:
            replace_formulas_in_ast(formatter, ast['c'], formulas)
    # ^ ignore all other cases


def _generate_excluded_formula_blocks(formatter, excluded_formulas_heading):
    """Return the `<aside>` section Pandoc AST blocks with all excluded formulas."""
    formula_paragraphs = []
    for label, formula in formatter.get_excluded().items():
        formula_paragraphs.append(
            {
                "t": "Para",
                "c": [
                    {
                        "t": "Link",
                        "c": [
                            [label, [], []],
                            [
                                {
                                    "t": "Code",
                                    "c": [
                                        ["", [], []],
                                        formula,
                                    ],
                                },
                            ],
                            [
                                "#"
                                + ImageFormatter.IMG_ID_PREFIX
                                + generate_label(formula),
                                "",
                            ],
                        ],
                    },
                ],
            },
        )

    return [
        {"t": "RawBlock", "c": ["html", "<aside>"]},
        {
            "t": "Header",
            "c": [
                1,
                ["", [], []],
                [
                    {"t": "Str", "c": excluded_formulas_heading},
                ],
            ],
        },
        *formula_paragraphs,
        {"t": "RawBlock", "c": ["html", "</aside>"]},
    ]

def write_pandoc_ast(file, document, formatter, excluded_formulas_heading):
    """Replace 'Math' elements from a Pandoc AST with the formatted elements.

    :param formatter    A formatter offering the "format" method (see ImageFormatter)
    :param formulas     A list of formulas with the information (pos, formula, path, displaymath)
    :param ast          Document ast to modified

    If the value returned by `formatter.get_exclusion_file_path()` is
    `None` and there are excluded formulas, the excluded formulas will
    be embedded at the end of the document in an HTML `<aside>` element
    with the heading `excluded_formulas_heading`.
    """
    ast, formulas = document
    replace_formulas_in_ast(formatter, ast['blocks'], formulas)

    if formatter.get_exclusion_file_path() is None and formatter.get_excluded():
        ast['blocks'].extend(
            _generate_excluded_formula_blocks(formatter, excluded_formulas_heading)
        )

    file.write(json.dumps(ast))


class PandocAstImageFormatter(ImageFormatter):
    """Format formulas for the Pandoc (JSON) AST."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _generate_link_destination(self, formula):
        id = generate_label(formula['formula'])
        exclusion_filelink = posixpath.join(
            self._link_prefix, self._exclusion_filepath,
        ) if self._exclusion_filepath is not None else ''
        return f'{exclusion_filelink}#{id}'

    def format_internal(self, image, full_formula, link_label=None):
        ast_node = {
            "t": "Image",
            "c": [
                [
                    "",
                    [image["class"]],
                    [
                        ["style", image["style"]],
                        ["width", image["width"]],
                        ["height", image["height"]],
                    ],
                ],
                [{"t": "Str", "c": image["formula"]}],
                [image["url"], ""],
            ],
        }
        if link_label:
            ast_node = {
                "t": "Link",
                "c": [
                    [
                        ImageFormatter.IMG_ID_PREFIX
                        + generate_label(full_formula),
                        [],
                        [],
                    ],
                    [ast_node],
                    [link_label, ""],
                ],
            }
        return ast_node

    def add_excluded(self, image):
        self._excluded_formulas[generate_label(image['formula'])] = image[
            'formula'
        ]
