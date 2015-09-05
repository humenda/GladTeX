GladTeX
=======

GladTeX is a preprocessor that enables the use of LaTeX formulas within HTML
files. The formulas, embedded in <eq>...</eq> tags, as if within $$..$$ in LaTeX,
is fed through latex and replaced by images.

Additionally all images get an alt-tag for alternative texts that contains the
LaTeX-equivalent of the image. This is handy for text-mode browsers or blind
people.

This is a complete rewrite of the old GladTeX which was implemented in Perl and
in C. One major issue was that it wasn't easily portable across platforms. The
new version is purely implemented in Python, gets rid of the Ghostscript
dependency and additionally offers the GladTeX functionality in a Python module
called gleetex.  
It is not feature-complete yet.


*contents*
----------

* License
* Installation
* Documentation

License
-------

_Copyright:_

About the old perl version (located in `attic/`):

- (C) 1999-2010 Martin G. Gulbrandsen
- (C) 2011-2013 Jonathan Daugherty (especially release 1.3)
- (C) 2013-2015 Sebastian Humenda

Credits go to

- 2013 Patrick Spendrin (patches for cmake and eqn2img to build it on Windows)



About the rewritten (new) version:

-   (c) 2015 Sebastian Humenda
    -   credits go to Martin G. Gulbrandsen who had the idea in the first place

This program is distributed under the GNU GPL; for details
see the accompanying file COPYING.

Project homepage is at http://gladtex.sourceforge.net

Installation
============

### Debian/Ubuntu

On all derivatives of Debian, installing GladTeX is as easy as

    # apt-get install gladtex

### From Source

The following is required for installing GladTeX:

-   Python >= 3.4
-   LaTeX, dvipng
-   the LaTeX package preview.sty

On Debian systems the following commands will satisfy the dependencies:

    # apt-get install python3.4 texlive-latex-base preview-latex-style dvipng

The package can then be installed using

    # python3 setup.py install

Note: If your system ships `python` as the command for Python3 you have to use
`python in` the above command instead.

### Compilation On Windows

Compiling GladTeX into a binary executable is as easy as:

    setup.py bdist

That'll create a `dist/` folder with all files required to run GladTeX.

NOTE: the above command only works if you've installed Python as a native
Windows program and when the file type `.py` is associated with the Python
interpreter.


Documentation
-------------

Please use `man gladtex` for further instructions.

