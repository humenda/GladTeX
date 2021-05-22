#!/usr/bin/env python3
"""This demo script converts from markdown to Epub using GladTeX. It requires
Pandoc for the conversion.

Throughout this script, the abbreviation AST for Abstract Syntax Tree is used."""

import json
import os
import shutil
import subprocess
import sys

import gleetex


def transform_ast(ast):
    # extract formulas from Pandoc document AST
    formulas = gleetex.pandoc.extract_formulas(ast)
    # converter using cache, helps avoiding the same formula twice
    conv = gleetex.cachedconverter.CachedConverter(".", True, encoding="UTF-8")
    # automatically handle unicode
    conv.set_replace_nonascii(True)
    # go parallel
    conv.convert_all(".", formulas)

    # an converted image has information like image depth and height, adjust
    # data structure for write-back
    formulas = [conv.get_data_for(eqn, style) for _p, style, eqn in formulas]
    # get a formatter instance
    with gleetex.htmlhandling.HtmlImageFormatter(".") as img_fmt:
        # non-ascii sequences will be replaced in the laternative text
        img_fmt.set_replace_nonascii(True)
        # this alters the AST reference, so no return value required
        gleetex.pandoc.replace_formulas_in_ast(img_fmt, ast["blocks"], formulas)


def cleanup(path):
    # remove images and ache, relevant data is included within the EPUB
    for file in os.listdir(path):
        if file.endswith(".png") or file.endswith(".cache"):
            os.remove(os.path.join(path, file))


def main():
    for prog in ("pandoc", "gladtex"):
        if not shutil.which(prog):
            sys.stderr.write(
                ("This script requires %s, please install and rerun " "this script.")
                % prog
            )
            sys.exit(1)

    usage = False
    if len(sys.argv) < 2:
        print("Missing command arguments.")
        usage = True
    elif len(sys.argv) > 2 or (len(sys.argv) == 2 and not os.path.exists(sys.argv[1])):
        print("Exactly one input path required")
        usage = True
    if usage:
        print(
            "%s <INPUTFILE>\n\nConvert given file to epub using GladTeX." % sys.argv[0]
        )
        sys.exit(0)

    inputfile = sys.argv[1]
    outputfile = "%s.epub" % os.path.splitext(inputfile)[0]
    # get the document AST
    proc = subprocess.Popen(["pandoc", "-t", "json", inputfile], stdout=subprocess.PIPE)
    ast = json.loads(proc.communicate()[0].decode(sys.getdefaultencoding()))
    if proc.wait() != 0:
        sys.exit(2)

    # the actual GleeTeX calls are here
    transform_ast(ast)

    # write back to stdin of pandoc
    proc = subprocess.Popen(
        ["pandoc", "-o", outputfile, "-f", "json", "-t", "epub"], stdin=subprocess.PIPE
    )
    proc.communicate(json.dumps(ast).encode(sys.getdefaultencoding()))
    if proc.wait():
        sys.exit(2)
    cleanup(".")


if __name__ == "__main__":
    main()
