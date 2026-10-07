import os
import sys

# Make the textadv package importable no matter where the test runner
# is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
