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

class ScriptInstaller(distutils.command.install_scripts.install_scripts):
    """Custom script installer. Stript .py extension if not on Windows."""
    def run(self):
        distutils.command.install_scripts.install_scripts.run(self)
        for script in self.get_outputs():
            if script.endswith(".py") and not ('wind' in sys.platform or 'win32'
                    in sys.platform):
                # strip file ending (if not on windows) to make it executable as
                # a command
                shutil.move(script, script[:-3])

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

class CustomBuild(distutils.command.build.build):
    """Also build manpage to build/gladtex.1; it is not installed
    automatically."""
    def initialize_options(self):
        self.cwd = None
        super().initialize_options()

    def finalize_options(self):
        self.cwd = os.getcwd()
        super().finalize_options()

    def run(self):
        if not cwd:
            if not 'manpage.md' in os.listdir('.'):
                print("setup.py must be run from the source root")
                sys.exit(91)
        else:
            assert os.getcwd() == self.cwd, 'Must be in package root: %s' % self.cwd
        super().run()
        if shutil.which('pandoc'): # only build man page, if pandoc present
            import manpage
            manpage.markdown2man('manpage.md', os.path.join('build', 'gladtex.1'))
        else:
            print("w: pandoc not found, skipping man page conversion.")

setup(name='GladTeX',
      version=VERSION,
      description='generate html with LaTeX equations embedded as images',
      author='Sebastian Humenda',
      author_email='shumenda |at| gmx |dot| de',
      url='https://humenda.github.io/GladTeX',
      packages=['gleetex'],
      console=['gladtex.py'], # Windows-only option, use python instead of pythonw
      setup_requires=['py2app'], # require py2app on Mac OS
      scripts=['gladtex.py'],
      license = "LGPL3.0",
      cmdclass = {"install_scripts": ScriptInstaller,
          'clean': CleanCommand,
          'build': CustomBuild}
     )


