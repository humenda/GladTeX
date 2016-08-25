import distutils.command.install_scripts
from distutils.core import setup
from gleetex import VERSION
import shutil
import sys

class my_install(distutils.command.install_scripts.install_scripts):
    """Custom script installer. Stript .py extension if not on Windows."""
    def run(self):
        distutils.command.install_scripts.install_scripts.run(self)
        for script in self.get_outputs():
            if script.endswith(".py") and not ('wind' in sys.platform or 'win32'
                    in sys.platform):
                # strip file ending (if not on windows) to make it executable as
                # a command
                shutil.move(script, script[:-3])


setup(name='GladTeX',
      version=VERSION,
      description='generate html with LaTeX equations embedded as images',
      author='Sebastian Humenda',
      setup_requires=['py2app'],
      author_email='shumenda |at| gmx |dot| de',
      url='https://humenda.github.io/GladTeX',
      packages=['gleetex'],
      scripts=['gladtex.py'],
      license = "LGPL3.0",
      cmdclass = {"install_scripts": my_install}
     )


