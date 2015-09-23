from distutils.core import setup
from gleetex import VERSION

setup(name='GladTeX',
      version=VERSION,
      description='generate html with LaTeX equations embedded as images',
      author='Sebastian Humenda',
      author_email='shumenda |at| gmx |dot| de',
      url='https://humenda.github.io/GladTeX',
      packages=['gleetex'],
      scripts=['gladtex.py'],
      license = "LGPL3.0"
     )


