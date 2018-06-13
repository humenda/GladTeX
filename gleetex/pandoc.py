# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""This module contains functionality to parse formulas from a given Pandoc
document AST and to replace these through formatted HTML equations. Even
though this could be done in a single run, this would conflict with the internal
GleeTeX structure and allows for an easy parallelisation of the formula
conversion."""

import json

from .htmlhandling import ParseException

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
                raise ParseException("[pandoc] unknown formula formatting: " + \
                        repr(ast['c']))
            style = (True if style == 'DisplayMath' else False)
            # position is None (only applicable for HTML parsing)
            formulas.append((None, style, formula))
        elif 'c' in ast:
            __extract_formulas(formulas, ast['c'])
    #    ^ all other cases do not matter

def extract_formulas(ast):
    """Extract formulas from a given Pandoc document AST.
    The returned formulas are typed like those form the HTML parser, therefore
    the first argument of the tuple is unused and hence None.
    :param  ast  Structure of lists and dicts representing a Pandoc document AST
    :return a list of formulas where each formula is (None, style, formula)"""
    formulas = []
    __extract_formulas(formulas, ast['blocks'])
    return formulas

def replace_formulas_in_ast(formatter, ast, formulas):
    """replace 'Math' elements from the given AST with a formatted variant
    Each 'Math' element found in the Pandoc AST will be replaced through a
    formatted (HTML) image link. The formulas are taken from the supplied
    formulas list. The number of formulas in the document has to match the
    number of formulas form the list."""
    if not formulas:
        return
    if isinstance(ast, list):
        for item in ast:
            replace_formulas_in_ast(formatter, item, formulas)
    elif isinstance(ast, dict):
        if 't' in ast and ast['t'] == 'Math':
            ast['t'] = 'RawInline' # raw HTML
            eqn = formulas.pop(0)
            ast['c'] = ['html',formatter.format(eqn['pos'], eqn['formula'], eqn['path'],
                    eqn['displaymath'])]
        elif 'c' in ast:
            replace_formulas_in_ast(formatter, ast['c'], formulas)
    # ^ ignore all other cases

def write_pandoc_ast(file, document, formatter):
    """Replace 'Math' elements from a Pandoc AST with 'RawInline' elements,
    containing formatted HTML image tags.
    :param formatter    A formatter offering the "format" method (see ImageFormatter)
    :param formulas     A list of formulas with the information (pos, formula, path, displaymath)
    :param ast          Document ast to modified"""
    ast, formulas = document
    replace_formulas_in_ast(formatter, ast['blocks'], formulas)
    file.write(json.dumps(ast))

