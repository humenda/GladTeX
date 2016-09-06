import distutils.command.install_scripts, distutils.command.build
from distutils.core import setup, Command
from gleetex import VERSION
import os
import shutil
import sys
try:
    import py2exe # only works on windows
except ImportError:
    pass

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

#class BuildCommandProxy(distutils.command.build.build):
#    def __init__(self):
#        print("test")


class CleanCommand(Command):
    description = "clean all build files, including __pycache__ and others"
    user_options = []
    def initialize_options(self):
        self.cwd = None

    def finalize_options(self):
        self.cwd = os.getcwd()

    def run(self):
        assert os.getcwd() == self.cwd, 'Must be in package root: %s' % self.cwd
        for directory in ['build', '__pycache__', 'dist',
                os.path.join('gleetex', '__pycache')]:
            if os.path.exists(directory):
                shutil.rmtree(directory)
        if os.path.exists('gladtex.1'):
            os.remove('gladtex.1')

setup(name='GladTeX',
      version=VERSION,
      description='generate html with LaTeX equations embedded as images',
      author='Sebastian Humenda',
      setup_requires=['py2app'],
      author_email='shumenda |at| gmx |dot| de',
      url='https://humenda.github.io/GladTeX',
      packages=['gleetex'],
      console=['gladtex.py'],
      scripts=['gladtex.py'],
      license = "LGPL3.0",
      cmdclass = {"install_scripts": my_install,
          'clean': CleanCommand}
     )


