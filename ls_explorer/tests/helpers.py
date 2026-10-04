"""Shared helpers for the ls_explorer test suite."""
import io
import os
import sys
import tempfile
import shutil
import unittest
from contextlib import redirect_stdout

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def run_silently(func, *args, **kwargs):
    """Run func with stdout captured; returns (result, printed_text)."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


class SandboxCase(unittest.TestCase):
    """Builds a real directory tree to act as the simulated filesystem:

        root/
            alpha/
                note.txt
                inner/
            beta/
    """

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='ls_explorer_test_')
        self.alpha = os.path.join(self.root, 'alpha')
        self.inner = os.path.join(self.alpha, 'inner')
        self.beta = os.path.join(self.root, 'beta')
        for directory in (self.alpha, self.inner, self.beta):
            os.makedirs(directory)
        with open(os.path.join(self.alpha, 'note.txt'), 'w') as handle:
            handle.write('hello')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
