% GLADTEX(1)
% Sebastian Humenda
% 1st of June 2018

# NAME

**GladTeX** - generate HTML with LaTeX formulas embedded as images

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

Furthermore it can be used with Pandoc to convert Markdown documents with LaTeX
formulas to HTML, EPUB and in fact to any HTML-based format, see the option
`-P`.

See [FILE FORMAT](#file-format) for an explanation of the file format and
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

**-K**
:   keep LaTeX file(s) when converting formulas

    By default, the generated LaTeX document, containing the formula to be
    converted, are removed after the conversion (no matter whether it was
    successful or not). If it wasn't successful, it is sometimes helpful to look
    at the complete document. This option will keep the file.

**-l** _CLASS_
:   CSS class to assign to block-level math (default: 'displaymath').

**-n**
:   Purge unreadable caches along with all eqn*.png files.

    Caches can be unreadable if the used GladTeX version is incompatible. If
    this option is unset, GladTeX will simply fail when the cache is unreadable.

**-m**
:     Print error output in machine-readable format (less concise, better parseable).

    Each line will start with a key, followed by a colon, followed by the value,
    i.e. `line: 5`.

**-o** _FILENAME_
:   Set output file name. '-' will print text to stdout. Bydefault, input file
    name is used and the `.htex` extension is replaced by `.html`.

**-p** _`LATEX_STATEMENT`_
:   Add given LaTeX code to preamble of document. That'll affect the conversion
    of every image.

**-P**
:   Act as a pandoc filter. In this mode, input is expected to be a Pandoc JSON
    AST  and the output will be a modified AST, with all formulas replaced
    through HTML image tags. It makes sense to use `-` as the input file for
    this option.

**-r** _DPI_
:   Set resolution (size of images) to 'dpi' (100 by default).

**-R**
:   Replace non-ascii (unicode) characters by LaTeX commands.

    GladTeX can automatically detect non-ascii characters in formulas and
    replace them through their appropriate LaTeX commands. In the alt attribute
    of the resulting image, alphabetical characters won't be replaced. That
    means that the alt text from the image is not exactly the same than the
    code used for generating the image, but it is far more readable.

    For instance, the formula \$\\text{für alle} a\$, would be compiled as
    \$\\text{f\\ddot{u}r alle} a\$ and displayed as "\\text{für alle} a" in the alt
    attribute.


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
<html><head><!-- meta information like charset --></head>
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

## Markdown To HTML

GladTeX can be used together with Pandoc. That can be handy to create an online
version of a scientific paper written in Markdown. The MarkDown document would
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

## Output as EPUB

It is beyond of the scope of this document to introduce Pandoc, but with any
input format, converting to EPUB with GladTeX replacing the images is as easy
as:

    pandoc -f INPUT_FMT -t json FILE.EXT | GLADTEX -P - | PANDOC -F JSON \
        -T EPUB -O BOOK.EPUB

Capitalised parameters should be replaced. This can be used with Markdown as
input format, see previous section.


# KNOWN LIMITATIONS

LaTeX2E is ***not*** unicode aware. if you have any unicode (more precisely,
non-ascii characters) signs in your documents, you have the choice to do one of
the following:

1.  Look up the symbol in one of the many LaTeX formula listings and replace the
    symbol with the appropriate command.
2.  Use the `-r` switch to let GladTeX replace the umlauts for you.

PLEASE NOTE: It is impossible to use GladTeX with LuaLaTeX. At the time of writing, dvipng
does not support the extended font features of the lualatex engine.


# PROJECT HOME

The project home is at <http://humenda.github.io/GladTeX>. The source can be
found at <https://github.com/humenda/gladtex>.

