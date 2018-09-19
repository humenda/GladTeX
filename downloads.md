<nav><ul><li class="active">[Home](index.html)</li>
  <li>[Documentation](documentation.html)</li>
  <li>[Downloads](downloads.html)</li>
  <li>[GitHub page](https://github.com/humenda/GladTeX)</li>
</ul></nav>

Downloads
---------

<small>For source code, see section below</small>

The latest version is [version 3.0](https://github.com/humenda/GladTeX/tree/v3.0).
If you are upgrading from a previous version, please make sure that you have
read the list of changes below.

**New Features And Incompatible Changes:**

-   add SVG support for scalable images
    -   use SVG output by default
    -   `gleetex.htmlhandling.HtmlImageFormatter`: rename link_path to link_prefix
-   add `-P` command-line switch to be used as a Pandoc document filter, see
    <https://pandoc.org/filters.html>
-   add environment variable `GLADTEX_ARGS` to pass command-line switches when
    used as pandocfilter where passing additional arguments is impossible
-   redefine colour handling: use xcolor package, therefore handling text and
    background colour the same way for both PNG and SVG (use hexadecimal colours
    now)

**Bug fixes:**

-   correctly parse HTML5 file encoding declarations
-   add more exceptions to the unicode table for the unicode replacement mode
    (see `-R`)
-   treat `-d` as a relative path

Binary Distributions
--------------------

For Windows and Debian GNU/Linux distributions, there are official binaries that
you can use.

### Windows

Version 3.0.0 can be downloaded
[here](/humenda/GladTeX/releases/download/v3.0.0/gladtex-3.0.0_win32.zip). The
zip-Archive contains all files to run GladTeX, no installation required.

Please note that this is a command-line utility, you need to launch it from a
console window such as _cmd_ or from the PowerShell.

### Debian/Ubuntu And Other Derivatives

GladTeX is officially part of Debian and all its derivatives (such as Ubuntu or
Mint). Just type

    sudo apt install gladtex

and proceed with `man gladtex`.

Source Code And Source Install
------------------------------

A source code archive for the latest stable release can be found at the
[releases page](https://github.com/humenda/GladTeX/releases). The latest source
code can be obtained using Git:

    $ git clone https://github.com/humenda/gladtex.git


