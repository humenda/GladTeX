# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""Top-level API to parse input documents.

The main point of the parsing is to extract formulas from a given input
document, while preserving the remaining formatting.
The returned parsed document structure is highly dependent on the input format
and hence document in their respective functions."""

import enum
import json
import sys

from . import htmlhandling
from . import pandoc
ParseException = htmlhandling.ParseException # re-export for consistent API from outside

class Format(enum.Enum):
    HTML = 0
    # while this is json, we never know what other applications might decide to
    # use json as their intermediate representation ;)
    PANDOCFILTER = 1

    @staticmethod
    def parse(string):
        string = string.lower()
        if string == 'html':
            return Format.HTML
        elif string == 'pandocfilter':
            return Format.PANDOCFILTER
        else:
            raise ValueError("unrecognised format: %s" % string)

def parse_document(doc, fmt):
    """This function parses an input document (string or bytes) with the given
    format specifier. For HTML, the returned "parsed" document is a list of
    chunks, where raw chunks are just plain HTML instructions and data and
    formula chunks are parsed from the '<eq/>' tags.
    If the input document is a pandoc AST, the formulas will be extracted and
    the document is a tuple of (pandoc AST, formulas).

    :param doc  input of bytes or string to parse
    :param fmt  either the enum type `Format` or a string understood by Format.parse
    :return     (encoding, document) (a tuple)"""
    if isinstance(fmt, str):
        fmt = Format.parse(fmt)
    encoding = None
    if fmt == Format.HTML:
        docparser = htmlhandling.EqnParser()
        docparser.feed(doc)
        encoding = docparser.get_encoding()
        encoding = (encoding if encoding else 'utf-8')
        doc = docparser.get_data()
    elif fmt == Format.PANDOCFILTER:
        if isinstance(doc, bytes):
            doc = doc.decode(sys.getdefaultencoding())
        ast = json.loads(doc)
        formulas = pandoc.extract_formulas(ast)
        doc = (ast, formulas) # ← see doc string
    if not encoding:
        encoding = sys.getdefaultencoding()
    return encoding, doc

