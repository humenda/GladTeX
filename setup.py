import os
import setuptools

with open(os.path.join('gleetex', '__init__.py')) as f:
    global VERSION
    import re
    for line in f.read().split('\n'):
        vers = re.search(r'^VERSION\s+=\s+.(\d+\.\d+\.\d+)', line)
        if vers:
            VERSION = vers.groups()[0]
    if not VERSION:
        class SetupError(Exception):
            pass
        raise SetupError("Error parsing package version")

setuptools.setup(name='GladTeX',
      version=VERSION,
      description="Formula typesetting for the web using LaTeX",
      long_description="""Formula typesetting for the web

This package (and command-line application) allows to create web documents with
properly typeset formulas. It uses the embedded LaTeX formulas from the source
document to place SVG images at the right positions on the web page. For people
not able to see the images (due to a poor internet connection or because of a
disability), the LaTeX formula is preserved in the alt tag of the SVG image.
GladTeX hence combines proper math typesetting on the web with the creation of
accessible scientific documents.""",
      long_description_content_type = "text/markdown",
      author='Sebastian Humenda',
      author_email='shumenda@gmx.de',
      url='https://humenda.github.io/GladTeX',
      packages=['gleetex'],
      entry_points={
       "console_scripts": [
           "gladtex = gleetex.__main__:main"
        ]
      },
      license = "LGPL3.0",
     )
