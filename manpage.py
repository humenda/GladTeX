#!/usr/bin/env python
"""
This tiny script converts the MarkDown man page to a "proper" groff man page.
"""

import os
import subprocess
import sys

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

destdir = '.'
if __name__ == '__main__':
    if '-h' in sys.argv or '--help' in sys.argv:
        print('%s [--dest output_directory]\n\n' % sys.argv[0])
        print("convert manpage.md to gladtex.1, which is either moved to the specified dest orput into the current working directory.")
    elif '--dest' in sys.argv:
        index = sys.argv.index('--dest')
        if index == (len(sys.argv)-1):
            print("error: destination required.")
        destdir = sys.argv[index + 1]
        if not os.path.exists(destdir) or os.path.isfile(destdir):
            print("an existing directory as destination is required.")
            sys.exit(5)
    markdown2man('manpage.md', os.path.join(destdir, 'gladtex.1'))
