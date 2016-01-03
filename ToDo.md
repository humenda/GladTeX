To Do
=====

This list contains things to be implemented in GladTeX. If you have additions or
even feel like you want to do it, feel free to drop me an email: `shumenda |aT|
gmx //dot-- de`.

Gettext
-------


Gettext should be integrated to localize messages (especially errors).

Support LuaLaTeX
----------------

Advantages:

-   unicode / UTF-8-aware
    -   hence would support umlauts in formulas
-   modern

### Changes for preamble:

~~~~
% remove inputenc - LuaTeX is UTF-8 aware
\usepackage{amsmath, amssymb}
\usepackage{lualatex-math}
\usepackage{unicode-math}
\setmathfont{xits-math.otf}
~~~~
% remove inputenc - LuaTeX is UTF-8 aware

### Packages on Debian:

    sudo apt-get install texlive-maths-extra texlive-luatex texlive-xetex texlive-fonts-extra

