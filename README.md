GladTeX
=======

GladTeX is a utility and library to display formulas on the Web and in
HTML-based formats such as EPUB. Formulas are embedded within `<eq>…</eq>` tags
and
converted automatically to a scalable SVG image using LaTeX. The images
integrate seamlessly into the output documents, work with any browser and are
accessible for visually impaired and blind users as well.

Features
--------

-   LaTeX-quality formulas with partial unicode maths support
-   [Pandoc](http://pandoc.org) support to convert from any format with
    LaTeX-formulas (MarkDown, …) to any HTML-based format, e.g. EPUB
-   Cache formulas to speed up subsequent document conversion
-   Python library GleeTeX to embed into other applications or to tailor to a
    specific workflow
-   cross-platform, written in Python, comes with Windows executables.

License
-------

- (C) 1999-2010 Martin G. Gulbrandsen
- (C) 2011-2013 Jonathan Daugherty (especially release 1.3)
- (C) 2013-2018 Sebastian Humenda

This program is distributed under the LGPL-3, or at your option, any later
version of the license; for details see the accompanying file COPYING.

The official project homepage is at <http://humenda.github.io/GladTeX>

Installation
============

### Debian/Ubuntu

On all derivatives of Debian (as Ubuntu/Mint, etc.), installing GladTeX is as
easy as

    # apt-get install gladtex

### Windows

If you want to use the program without the Python library, you should download a
pre-compiled binary from <https://github.com/humenda/GladTeX/releases>.

Just unzip the archive and move the files to a directory within `%PATH%`.

### From Source

The following is required for installing GladTeX:

-   Python >= 3.4
-   LaTeX (2e), dvisvgm (optionally png)
-   the LaTeX package preview.sty


#### Debian / Ubuntu

On Debian/Ubuntu systems the following commands will satisfy the dependencies:

    # apt-get install python3-all texlive-fonts-recommended texlive-latex-recommended preview-latex-style dvipng
    
The package can then be installed using

    # python3 setup.py install

Note: If your system ships `python` as the command for Python3 you have to use
`python in` the above command instead.

#### OS X

You need to install a LaTeX distribution on your Mac. GladTeX was successfully
run with [MacTex](http://www.tug.org/mactex/).

You can download a zip source archive from
[GitHub](https://github.com/humenda/GladTeX) or use git:

    $ git clone https://github.com/humenda/GladTeX.git

Use `cd` to change to the GladTeX source directory and issue

    $ python setup.py install



Documentation
-------------

Please use `man gladtex` for further instructions or have a look at the file
[manpage.md](manpage.md).

