<nav><ul><li class="active">[Home](index.html)</li>
  <li>[Documentation](documentation.html)</li>
  <li>[Downloads](downloads.html)</li>
  <li>[GitHub page](https://github.com/humenda/GladTeX)</li>
</ul></nav>

Downloads
---------

<small>For source code, see section below</small>

Binary Distributions
--------------------

The latest release is
[version 2.1](https://github.com/humenda/GladTeX/tree/v2.1). Its new features
are:

Add support for unicode math with translation table
:   LaTeX formulas may now contain non-ascii characters. It is possible to
    translate these non-ascii characters with an internal look-up table, so that
    the formula can be converted using LaTeX2e.

Handle subprocess stdin and stdout encoding properly
:   Sometimes the encoding of stdin or stdout is not set, fall back to the
    systems default in this case. This is only applied when using the new `-R`
    switch.

Set UTF-8 as encoding for all LaTeX documents
:   By setting UTF-8 as default encoding for LaTeX documents, it is easiest to
    convert the documents in a cross-platform manner.



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


