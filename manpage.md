% GLADTEX(1)
% Sebastian Humenda
% 27th December 2015

# NAME

GladTeX – generate HTML with LaTeX formulas embedded as images

# SYNOPSIS

**gladtex** [OPTIONS] [INPUT  FILE NAME]


# DESCRIPTION

**GladTeX** is a formula preprocessor for HTML files. It recognizes a special tag
(`<eq>...</eq>`) and will convert the contained LaTeX formulas into images. The
resulting images will be linked into the resulting HTML document.  This eases
the process of creating HTML
documents (or web sites) containing formulas.\
The generated images are saved in a cache to not render the same image over
and over again. This speeds up the process when formulas occur multiple times or
when a document is extended gradually.

The LaTeX formulas are preserved in the alt attribute of the embedded images.
Hence screen reader users benefit from an accessible HTML version of the
document.

Furthermore it can be used with Pandoc to convert MarkDown documents with LaTeX
formulas to HTML.

See [FILE FORMAT('file-format) for an explanation of the file format and
[EXAMPLES](#examples) for examples on how to use GladTeX on its own or with
Pandoc.

# OPTIONS

**INPUT FILE NAME**
:   Input .htex file with LaTeX formulas (if omitted or -, stdin will be read).

**-h** **--help**
:   Show this help message and exit.

**-a**
:   Save text alternatives for images which are too long for the alt attribute
    into a single separate file and link images to it.

**-b** _BACKGROUND_COLOR_
:   Set background color for resulting images (default transparent).

**-c** _`FOREGROUND_COLOR`_
:   Set foreground color for resulting images (default 0,0,0).

**-d** _DIRECTORY_
:   Directory in which to store the generated images in (relative path).

**-e** _`LATEX_MATHS_ENV`_
:   Set custom maths environment to surround the formula (e.g. flalign).

**-E** _ENCODING_
:   Overwrite encoding to use (default UTF-8).

**-i** _CLASS_
:   CSS class to assign to inline math (default: 'inlinemath').

**-l** _CLASS_
:   CSS class to assign to block-level math (default: 'displaymath').

**-m**
:     Print error output in machine-readable format (less concise).

    Each line will start with a key, followed by a colon, followed by the value,
    i.e. `line: 5`.

**-o** _FILENAME_
:   Set output file name. '-' will print text to stdout. Bydefault, input file
    name is used and .htex extension is replaced by .html.

**-p** _`LATEX_STATEMENT`_
:   Add given LaTeX code to preamble of document. That'll affect the conversion
    of every image.

**-r** _DPI_
:   Set resolution (size of images) to 'dpi' (100 by default).

**-u** _URL_
:   Base URL to image files (relative links are default).

# FILE FORMAT

A .htex file is essentially a HTML file containing LaTeX formulas. The formulas
have to be surrounded by `<eq>` and `</eq>`.

By default, formulas are rendered as inline maths, so they are squeezed to the
height of the line. It is possible to render a formula as display maths by
setting the env attribute to displaymath, i.e. `<eq env="displaymath">...</eq>`.

# EXAMPLES

## Sample HTEX document

A sample HTEX document could look like this:

~~~~
<html><head><!-- meta information --></head>
<body>
<h1>Some text</h1>
<p>Circumference of a circle: <eq>u = \pi\cdot d</eq><p>
<p>A useful matrix: <eq env="displaymath">\begin{pmatrix}
1 &2 &3 &4\\
5 &6 &7 &8\\
9 &10&11&12
\end{pmatrix}</eq></p>
</body></html>
~~~~

This can be converted using 

    gladtex file.htex

and the result will be a HTML document called `file.html` along with two files
`eqn0000.png` and `eqn0001.png` in the same directory.

## MarkDown to HTML

GladTeX can be used together with Pandoc. That can be handy to create an online
version of a scientific paper written in MarkDown. The MarkDown document would
look like this:

~~~~
Some text
=========

Circumference of a circle: $u = \pi\cdot d$

A useful matrix: $$\begin{pmatrix}
1 &2 &3 &4\\
5 &6 &7 &8\\
9 &10&11&12 \end{pmatrix}$$
~~~~

The conversion is as easy as:

    pandoc -s -t html --gladtex file.md | gladtex -o file.html

# KNOWN LIMITATIONS

LaTeX is *****NOT***** unicode aware. If you have any unicode signs in your
documents, please look up the amsmath documentation (or similar) to find a LaTeX
command replacing the unicode character.

# PROJECT HOME

The project home is at <http://humenda.github.io/GladTeX>. The source can be
found at <https://github.com/humenda/gladtex>.

