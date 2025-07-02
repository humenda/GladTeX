import os
import shutil
import tempfile
from unittest import TestCase

from gleetex.__main__ import Main


HTML_SKELETON = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body>
{}
</body>
</html>"""


class MainTest(TestCase):

    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_empty_excluded_descriptions_file_created(self):
        with open('testfile.htex', 'w') as f:
            f.write(HTML_SKELETON.format(r"""
                <p>This is a unremarkable document for <eq>testing</eq>
                purposes <eq>only</eq>.</p>

                <h1>Display Math</h1>
                <p><eq env="displaymath">\lambda x y z = \rho \gamma y^2
                - \sin(3 - 5) + \cos(\tan(xy))
                </eq></p>

                <p>And <eq>soooooooooooooooooooooooooooo on</eq> we
                <eq>go - 32</eq>.</p>
            """))

        Main().run(['prog', 'testfile.htex'])
        self.assertFalse(os.path.exists('excluded-descriptions.html'))

    def test_excluded_descriptions_file_created_when_needed(self):
        with open('testfile.htex', 'w') as f:
            f.write(HTML_SKELETON.format(r"""
                <p>This is a unremarkable document for <eq>testing
                loooooooooooooooooooooooooooooooooooooong fooooooooormuuuuulas
                ooooooooooooooooooooooooooooonly E=mc^2 \cdot \gamma</eq>.</p>

                <h1>Display Math</h1>
                <p><eq env="displaymath">\lambda x y z = \rho \gamma y^2
                - \sin(3 - 5) + \cos(\tan(xy)) \cdot
                \frac{\sin(\frac{\pi}{2}) - 2}{\cos(\phi\frac{pi}{3})}
                </eq></p>

                <p>And <eq>soooooooooooooooooooooooooooo on</eq> we
                <eq>go - 32</eq>.</p>
            """))

        Main().run(['prog', 'testfile.htex'])
        self.assertTrue(os.path.exists('excluded-descriptions.html'))

        with open('excluded-descriptions.html', 'r') as f:
            html = f.read()
        self.assertIn(
            r'loooooooooooooooooooooooooooooooooooooong fooooooooormuuuuulas',
            html,
        )
        self.assertIn(
            r'\frac{\sin(\frac{\pi}{2}) - 2}{\cos(\phi\frac{pi}{3})}',
            html,
        )
