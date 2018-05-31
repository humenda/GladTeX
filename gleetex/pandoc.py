# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""This module contains functionality to parse formulas from a given Pandoc
document AST and another to replace these through formatted HTML equations. Even
though this could be done in a single run, this would conflict with the internal
GleeTeX structure. Since conversion of the images is more compute-intens, it
makes sense to parallelise the process with the same mechanisms  as used for the
HTML formatting."""

import json

from .htmlhandling import ParseException

def __extract_formulas(formulas, ast):
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
    :param formulas A reference to a list to add the formulas to
    :param ast      Structure of lists and dicts representing a Pandoc document
    AST."""
    formulas = []
    __extract_formulas(formulas, ast['blocks'])
    return formulas

def __replace_formulas_in_ast(formatter, ast, formulas):
    if not formulas:
        return
    if isinstance(ast, list):
        for item in ast:
            __replace_formulas_in_ast(formatter, item, formulas)
    elif isinstance(ast, dict):
        if 't' in ast and ast['t'] == 'Math':
            ast['t'] = 'RawInline' # raw HTML
            eqn = formulas.pop(0)
            ast['c'] = ['html',formatter.format(eqn['pos'], eqn['formula'], eqn['path'],
                    eqn['displaymath'])]
        elif 'c' in ast:
            __replace_formulas_in_ast(formatter, ast['c'], formulas)
    # ^ ignore all other cases

def write_pandoc_ast(file, document, formatter):
    """Replace 'Math' elements from a Pandoc AST with 'RawInline' elements,
    containing formatted HTML image tags.
    :param formatter    A formatter offering the "format" method (see ImageFormatter)
    :param formulas     A list of formulas with the information (pos, formula, path, displaymath)
    :param ast          Document ast to modified"""
    ast, formulas = document
    __replace_formulas_in_ast(formatter, ast['blocks'], formulas)
    file.write(json.dumps(ast))

