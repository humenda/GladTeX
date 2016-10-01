<nav><ul><li class="active">[Home](index.html)</li>
  <li>[Documentation](documentation.html)</li>
  <li>[Downloads](downloads.html)</li>
<<<<<<< Updated upstream
=======
  <li>[GitHub page](https://github.com/humenda/GladTeX)</li>
>>>>>>> Stashed changes
</ul></nav>

GladTeX
=======

About
-----

GladTeX is a preprocessor that enables the use of LaTeX maths within HTML
files. The maths, embedded in `<EQ>...</EQ>` tags, as if within `\(..\)` in LaTeX (or `$...$` in TeX),
is fed through latex and replaced by images.

Additionally all images get an alt-tag for alternative texts that contains the
LaTeX-equivalent of the image. This is handy for text-mode browsers or blind
people.

Features
--------

-   GladTeX supports caching of formulas in order to enable incremental document
    editing or simply to share formulas across web pages.
-   GladTeX can be used with [Pandoc](http://pandoc.org) in order to convert
    MarkDown to HTML with LaTeX formulas.
-   It also contains a library GleeTeX to custom tailor the generation and
    conversion process to your needs and to embedd it into your (web) application.
-   It allows the usage of umlauts and other non-ASCII characters within
    formulas, by replacing these characters through LaTeX sequences.
-   It is cross-platform, written in Python and comes with Windows executables.
-   Its source code is documented and tested.

Contact
-------

Please feel free to send patches, comments, feature requests or even simply
thanks to `shumenda //at\\ gmx __dot__ de`. Issues can be reported at the
[GitHub issue page](https://github.com/humenda/gladtex/issues) as well.


