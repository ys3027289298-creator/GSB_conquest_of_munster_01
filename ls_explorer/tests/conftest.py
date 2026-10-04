import os
import sys

import pytest

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


@pytest.fixture
def fs_tree(tmp_path):
    '''A small real directory tree for the simulated filesystem to mirror.'''
    (tmp_path / 'castle').mkdir()
    (tmp_path / 'castle' / 'tower').mkdir()
    (tmp_path / 'forest').mkdir()
    (tmp_path / 'README.txt').write_text('welcome')
    (tmp_path / 'castle' / 'note.txt').write_text('hello')
    return tmp_path
