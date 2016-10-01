<nav><ul><li class="active">[Home](index.html)</li>
  <li>[Documentation](documentation.html)</li>
  <li>[Downloads](downloads.html)</li>
  <li>[GitHub page](https://github.com/humenda/GladTeX)</li>
</ul></nav>


Documentation
-------------

Documentation For The GladTeX Command Line Program
--------------------------------------------------

The GladTeX executable is self-documenting. You can obtain the help
screen using `gladtex -h` or `gladtex --help`.

If you prefer more verbose help, it is best to read the __manual page__. If you
run GNU/Linux, typing `man gladtex` should be enough. You can view the manual
page [online](manpage.html)
too.
The manual page documents the [file format](manpage.html#file-format) and gives some
[examples](manpage.html#examples) on how to use GladTeX.

GleeTeX -- Embed formulas in your (web) application
----------------------------------------------------

GleeTeX is the library used by GladTeX and is written in Python. It has been
designed to be useful for other applications too. Using it, you can:

-   create images out of formulas
-   custom-tailor the LaTeX document being used for conversion
-   add any pre- and post-processing steps for HTML parsing, output and image
    linking
-   convert your document on-the-fly within your application, if required
    -   formulas can be cached, so that is not such a big overhead

There is no Sphinx-generated documentation yet, mostly due to a lack of time.
However it has been taken care to document the whole source code and to explain
all the important bits in comments. Each class has a `__doc__` string,
explaining its usage.

You are welcome to provide patches or pull requests to add sphinx support.

