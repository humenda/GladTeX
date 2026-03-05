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

from ..htmlhandling import ImageFormatter
from .ast import (
    Div,
    Heading,
    InlineCode,
    InlineImage,
    InlineLink,
    InlineText,
    Math,
    MathType,
    Paragraph,
    RawBlock,
    RawFormat,
    Span,
    ast_root_blocks,
    foreach_element,
)


__all__ = [
    "create_error_placeholder",
    "extract_formulas",
    "replace_formulas_in_ast",
    "write_pandoc_ast",
    "PandocAstImageFormatter",
]

ERROR_PLACEHOLDER_CLASS = "gladtex-error"
ERROR_PLACEHOLDER_DISPLAY_CLASS = "gladtex-error-display"
ERROR_PLACEHOLDER_TEXT = "[LaTeX error]"


def create_error_placeholder(displaymath):
    """Return a placeholder marker for a failed formula conversion."""
    return {
        "is_error_placeholder": True,
        "displaymath": bool(displaymath),
    }


def extract_formulas(ast):
    """Extract formulas from the given Pandoc document `ast`.

    `ast` is expected to be a valid and known Pandoc JSON AST root with a
    supported version (see `.ast.SUPPORTED_AST_VERSION`), if not, a
    `PandocJsonAstParseError` or a `UnsupportedPandocJsonAstVersionError` is
    raised, respectively.

    The returned formulas are typed like those form the HTML parser,
    therefore the first argument of the tuple is unused and hence `None`.

    If an invalid or unknown `Math` element is encountered, a
    `PandocJsonAstParseError` is raised.

    :param  ast  Structure of lists and dicts representing a Pandoc document AST
    :return a list of formulas where each formula is (None, style, formula)
    """
    formulas = []

    def append_to_formulas(ast_node):
        math = Math.from_json(ast_node)
        # `position` is `None` (only applicable for HTML parsing).
        formulas.append((None, math.type == MathType.DISPLAY, math.formula))

    foreach_element(Math, append_to_formulas, ast_root_blocks(ast))

    return formulas


def replace_formulas_in_ast(formatter, ast, formulas):
    """Replace `Math` elements from the given AST with a formatted variant.

    Each `Math` element found in the Pandoc AST will directly be
    replaced by the image link AST element returned by
    `formatter.format()`, which means the `formatter` has to produce a
    valid Pandoc JSON AST element.

    The formulas are taken from the supplied formulas list. The number
    of formulas in the document has to match the number of formulas form
    the list.
    """
    if not formulas:
        return

    def error_placeholder_as_inline(displaymath):
        classes = [ERROR_PLACEHOLDER_CLASS]
        if displaymath:
            classes.append(ERROR_PLACEHOLDER_DISPLAY_CLASS)
        return Span(
            [InlineText(ERROR_PLACEHOLDER_TEXT)],
            classes=classes,
        ).to_json()

    def replace_with_image(_math):
        eqn = formulas.pop(0)
        if eqn.get("is_error_placeholder"):
            return error_placeholder_as_inline(eqn["displaymath"])
        return formatter.format(
            eqn['pos'], eqn['formula'], eqn['path'], eqn['displaymath'],
        )

    foreach_element(Math, replace_with_image, ast)
    _promote_display_error_placeholders(ast)


def _promote_display_error_placeholders(ast):
    """Promote standalone display placeholders from inline `Span` to `Div`."""

    def build_display_placeholder_block():
        return Div(
            classes=[ERROR_PLACEHOLDER_CLASS],
            blocks=[Paragraph([InlineText(ERROR_PLACEHOLDER_TEXT)])],
        ).to_json()

    def is_display_placeholder_span(node):
        match node:
            case {
                "t": "Span",
                "c": [
                    [_id, classes, _attributes],
                    [{"t": "Str", "c": text}],
                ],
            }:
                return (
                    ERROR_PLACEHOLDER_DISPLAY_CLASS in classes
                    and text == ERROR_PLACEHOLDER_TEXT
                )
            case _:
                return False

    def traverse(ast_node):
        match ast_node:
            case [*_] as array:
                for idx, node in enumerate(array):
                    match node:
                        case {
                            "t": block_type,
                            "c": [placeholder],
                        } if (
                            block_type in ("Para", "Plain")
                            and is_display_placeholder_span(placeholder)
                        ):
                            array[idx] = build_display_placeholder_block()
                            continue
                    traverse(array[idx])
            case {"c": content}:
                traverse(content)
            case _:
                return

    traverse(ast)


def _generate_excluded_formula_blocks(formatter, excluded_formulas_heading):
    """Return the `<aside>` section Pandoc AST blocks with all excluded formulas."""
    formula_paragraphs = [
        Paragraph([
            InlineLink(
                [InlineCode(formula)],
                url=f"#{formatter.get_excluded_image_anchor_id(label)}",
                id=label,
            ),
        ])
        for label, formula in formatter.get_excluded().items()
    ]

    return [block.to_json() for block in (
        RawBlock(RawFormat.HTML, "<aside>"),
        Heading([InlineText(excluded_formulas_heading)], level=1),
        *formula_paragraphs,
        RawBlock(RawFormat.HTML, "</aside>"),
    )]

def write_pandoc_ast(file, document, formatter, excluded_formulas_heading):
    """Replace `Math` elements from a Pandoc AST with the formatted elements.

    :param file         The file the modified AST is written to
    :param formatter    A formatter offering the "format" method (see ImageFormatter)
    :param document     A pair (ast, formulas), where `ast` is the document AST and
                        `formulas` is a tuple (pos, formula, path, displaymath)

    The `ast` in `document` is expected to be a valid Pandoc JSON AST root
    with a supported version (see `ast.SUPPORTED_AST_VERSION`), if not, a
    `PandocJsonAstParseError` or a `UnsupportedPandocJsonAstVersionError` is
    raised, respectively.

    If the value returned by `formatter.get_exclusion_file_path()` is
    `None` and there are excluded formulas, the excluded formulas will
    be embedded at the end of the document in an HTML `<aside>` element
    with the heading `excluded_formulas_heading`.
    """
    ast, formulas = document
    ast_blocks = ast_root_blocks(ast)
    replace_formulas_in_ast(formatter, ast_blocks, formulas)

    if formatter.get_exclusion_file_path() is None and formatter.get_excluded():
        ast_blocks.extend(
            _generate_excluded_formula_blocks(formatter, excluded_formulas_heading)
        )

    file.write(json.dumps(ast))


class PandocAstImageFormatter(ImageFormatter):
    """Format formulas for the Pandoc (JSON) AST."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _generate_link_destination(self, excluded_label):
        exclusion_filelink = posixpath.join(
            self._link_prefix, self._exclusion_filepath,
        ) if self._exclusion_filepath is not None else ''
        return f'{exclusion_filelink}#{excluded_label}'

    def format_internal(self, image, full_formula, link_label=None, image_id=None):
        ast_node = InlineImage(
            [InlineText(image["formula"])],
            url=image["url"],
            classes=[image["class"]],
            key_values={key: image[key] for key in ("style", "width", "height")},
        )

        if link_label:
            ast_node = InlineLink(
                [ast_node],
                url=link_label,
                id=image_id,
            )

        return ast_node.to_json()

    def add_excluded(self, label, image):
        self._excluded_formulas[label] = image['formula']
