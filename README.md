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

