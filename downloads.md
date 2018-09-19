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

For Windows and Debian GNU/Linux distributions, it is very easy to install
GladTeX.

### Windows

There are two zip archives At the
[release page](https://github.com/humenda/GladTeX/tree/v2.1).
The file labelled with `stand-alone` is the one to pick, if
GladTeX should be run as a stand-alone binary or within a non-python project.
The file containing `embeddable` in its name, is meant for python applications,
build with py2exe and python3.4, so that they can share the DLL files.

### Debian/Ubuntu And Other Derivatives

On one of the mentioned systems, just type

    apt-get install gladtex

and proceed with `man gladtex`.

Source Code And Source Install
------------------------------

A source code archive for the latest stable release can be found at the
[releases page](https://github.com/humenda/GladTeX/releases). The latest source
code can be obtained using Git:

    $ git clone https://github.com/humenda/gladtex.git


