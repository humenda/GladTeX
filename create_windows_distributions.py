"""
This file builds windows distributions, zip files with GladTeX and all other
files."""
import os
import shutil
import sys
import zipfile
import gleetex

def clean():
    exec_setup_py('clean')
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.remove('dist')

def exec_setup_py(arg_string):
    ret = None
    if sys.platform.startswith('win'):
        ret = os.system('python setup.py ' + arg_string)
    else:
        ret = os.system('wine python setup.py ' + arg_string)
    if ret:
        print("abborting...")
        sys.exit(7)

def get_python_version():
    import re, subprocess
    args = ['python', '--version']
    if not sys.platform.startswith('win'):
        args = ['wine'] + args
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout = proc.communicate()[0].decode(sys.getdefaultencoding())
    if proc.wait():
        raise TypeError("Abnormal subprocess termination while querying python version.")
    return re.search(r'.*?(\d+\.\d+\.\d+)', stdout).groups()[0]

def bundle_files(src, label):
    output_name = 'gladtex-' + str(gleetex.VERSION) + '-py_' + \
        get_python_version() + '-' + label
    if os.path.exists(output_name):
        shutil.rmtree(output_name)
    os.rename(src, output_name)
    files = [os.path.join(root, file)
            for root, _, files in os.walk(output_name)  for file in files]
    # add README.first
    with open(os.path.join(output_name, 'README.first.txt'), 'w') as f:
            f.write('GladTeX for Windows\r\n=============\r\n\r\n')
            f.write('This program has been compiled with python 3.4.4. If you want to embedd it in binary form with your binary python application, the version numbers HAVE TO match.\r\n')
            f.write('\r\nFor other information, see the file README.md or http://humenda.github.io/GladTeX\r\n')

    # copy README and other files
    for file in ['README.md', 'COPYING', 'ChangeLog']:
        dest = os.path.join(output_name, file)
        if not '.' in dest[-5:]:
            dest += '.txt'
        shutil.copy(file, dest)

    with zipfile.ZipFile(output_name + '.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for file in files:
            z.write(file)
    shutil.rmtree(output_name)

clean()
# build embeddable release, where all files are separate DLL's; if somebody
# distributes a python app, these DLL files can be shared
exec_setup_py('py2exe -i gleetex --bundle-files 3')
bundle_files('dist', 'embeddable')
clean()

# create a stand-alone version of GladTeX
exec_setup_py('py2exe -i gleetex --bundle-files 1')
bundle_files('dist', 'stand-alone')
clean()
