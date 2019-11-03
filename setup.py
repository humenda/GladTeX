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
      description='generate html with LaTeX equations embedded as images',
      author='Sebastian Humenda',
      author_email='shumenda |at| gmx |dot| de',
      url='https://humenda.github.io/GladTeX',
      packages=['gleetex'],
      entry_points={
       "console_scripts": [
           "gladtex = gleetex.__main__:main"
        ]
      },
      license = "LGPL3.0",
     )
