# (c) 2013-2018 Sebastian Humenda
# This code is licenced under the terms of the LGPL-3+, see the file COPYING for
# more details.
"""
Wrapper functionality to extract formulas from a given document. At the moment,
supported formats are HTML and Pandoc's JSON AST."""

import enum
import json
import sys

from . import htmlhandling
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
        elif format == 'pandocfilter':
            return Format.PANDOCFILTER
        else:
            raise ValueError("unrecognised format: %s" % format)

def extract_formulas(doc, format):
    """ToDo that returns chunks or for json ast + formulas"""
    if isinstance(format, str):
        format = Format.parse(format)
    encoding = None
    if format == Format.HTML:
        docparser = htmlhandling.EqnParser()
        docparser.feed(doc)
        encoding = docparser.get_encoding()
        encoding = (encoding if encoding else 'utf-8')
        doc = docparser.get_data()
    elif format == Format.PANDOCFILTER:
        if isinstance(doc, bytes):
            doc = doc.decode(sys.getdefaultencoding())
        doc = json.loads(doc)
        raise NotImplementedError()
    if not encoding:
        encoding = sys.getdefaultencoding()
    return encoding, doc

