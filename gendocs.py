#!/usr/bin/python3
import os
import subprocess
import sys
import pydoc

import gleetex
from gleetex.image import call


basepath = os.path.abspath(os.getcwd())

class DocReformatter:
    """Instead of rewriting pydoc, use pandoc to renice the output. That might
    seem like a dirthack, but allows portability to other formats in the long
    run."""
    def __init__(self, base):
        self.basepath = base
        import shutil
        if not shutil.which('pandoc'):
            print("Warning: proper documentation can only be formatted using pandoc.")
            self.__format = False
        else:
            self.__format = True

    def parse(self, path):
        if not self.__format:
            return
        stdout = call(['pandoc', '-f', 'html', '-t', 'markdown', path])
        if isinstance(stdout, (list, tuple)):
            stdout = stdout[0]
        blocks = [[]] # each block is a list of lines
        for line in stdout.split('\n'):
            # strip spaces and non-breaking chars
            stripped = ''.join(c for c in line.strip() if not c == '\xa0')
            if stripped == '``' or stripped == '<!---->':
                continue # skip useless lines
            elif line.startswith('-----') and line.endswith('-------'):
                blocks.append([])
            else:
                blocks[-1].append(line)
        return blocks

    def __remove_base_path(self, blocks):
        """Remove file:`cwd` from the file name which is shown in the
        documentation. The given references is mutated directly."""
        for block in blocks:
            for index, line in enumerate(block):
                block[index] = line.replace('file:' + self.basepath + os.sep, '').\
                        replace(self.basepath + os.sep, '')
        return blocks

    def __strip_unwanted_blocks(self, blocks):
        """Strip blocks like "methods inherited", etc. In my opinion they're not
        really useful."""
        boring = ['Data descriptors defined', 'Methods inherited from', 'Data descriptors inherited from']
        index = 0
        while index < (len(blocks)-1):
            block = blocks[index]
            for token in boring:
                if block[0].startswith(token) or block[1].startswith(token):
                    del blocks[index]
                    continue
            index += 1
        return blocks

    def cleanup(self, blocks):
        """Apply clean up functions and return `blocks`."""
        if not self.__format:
            return
        blocks = [block[:] for block in blocks] # get a full copy
        blocks = self.__remove_base_path(blocks)
        blocks = self.__strip_unwanted_blocks(blocks)
        return blocks

    def write(self, path, blocks):
        """Write document as HTML file."""
        if not self.__format:
            return
        md = '\n* * * * *\n'.join('\n'.join(block) for block in blocks)
        with subprocess.Popen(['pandoc', '-s', '-f', 'markdown', '-t', 'html', '-o',
                path], stdin=subprocess.PIPE) as proc:
            proc.communicate(md.encode(sys.getdefaultencoding()))
        if proc.wait():
            raise OSError("Abnormal termination of pandoc.")


if not os.path.exists('gleetex'):
    raise OSError("script must be run from source root")

if not os.path.exists('doc'):
    os.mkdir('doc')

os.chdir('doc')

reformatter = DocReformatter(basepath)

# handle index file
pydoc.writedoc('gleetex')
os.rename('gleetex.html', 'index.html')
doc = reformatter.parse('index.html')
doc = reformatter.cleanup(doc)
reformatter.write('index.html', doc)

for module in (m for m in gleetex.__all__ if m!= 'VERSION'):
    fn = 'gleetex.%s.html' % module
    pydoc.writedoc('gleetex.' + module)
    doc = reformatter.parse(fn)
    doc = reformatter.cleanup(doc)
    reformatter.write(fn, doc)


