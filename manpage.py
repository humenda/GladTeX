#!/usr/bin/env python
"""
This tiny script converts the MarkDown man page to a "proper" groff man page.
"""

import subprocess

def markdown2man(input_fn, output_fn):
    """Convert a given input file (path to a markdown file) to a given output
    file (path to man page)."""
    try:
        cmd = ['pandoc', input_fn, '-s', '-t', 'man', '-o', output_fn]
        proc = subprocess.Popen(cmd)
        ret = proc.wait()
        if ret:
            raise subprocess.SubprocessError("Exit status %d when running '%s'" % (ret,
                ' '.join(cmd)))
    except FileNotFoundError:
        sys.stderr.write("Pandoc was not found on the system, skipping man " +
                "page creation.")
        return # pandoc is not present

markdown2man('manpage.md', 'gladtex.1')
