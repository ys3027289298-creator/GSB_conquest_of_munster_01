"""pyquest test suite (stdlib unittest; also runnable under pytest).

Run from the pyquest directory:
    python3 -m unittest discover -s tests -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
