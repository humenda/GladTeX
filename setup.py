from distutils.core import setup

setup(name='GladTeX',
      version='0.1',
      description='generate html with LaTeX equations embedded as images',
      author='Sebastian Humenda',
      author_email='shumenda@gmx.de',
      url='https://gladtex.sf.net',
      packages=['gleetex'],
      scripts=['gladtex.py'],
      license = "LGPL3.0"
     )


