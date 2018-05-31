# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.

def __extract_formulas(formulas, ast):
    if isinstance(ast, list):
        for item in ast:
            __extract_formulas(formulas, item)
    elif isinstance(ast, dict):
        if 't' in ast and ast['t'] == 'Math':
            style, formula = ast['c']
            # style = {'t': 'blah'} -> we want blah
            style = next(iter(style.values()))
            formulas.append((style, formula))
        else:
            __extract_formulas(formulas, ast['c'])
    else:
        raise NotImplementedError("Unimplemented AST type.")

def extract_formulas(formulas, ast):
    formulas = []
    __extract_formulas(formulas, ast['blocks'])
    return formulas

def __replace_formulas_in_ast(formatter, ast, formulas):
    if not formulas:
        return
    if isinstance(ast, list):
        for item in ast:
            __replace_formulas_in_ast(formatter, formulas, item)
    elif isinstance(ast, dict):
        if 't' in ast and ast['t'] == 'Math':
            ast['t'] = 'RawInline' # raw HTML
            pos, formula, path, is_displaymath = formulas.pop(0)
            ast['c'] = formatter.format(pos, formula, path, is_displaymath)
        else:
            __replace_formulas_in_ast(formatter, formulas, ast['c'])
    else:
        raise NotImplementedError("Unimplemented AST type: %s" % ast)


