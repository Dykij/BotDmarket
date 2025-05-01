"""
Configuration module for running pytest.
"""

import os
import sys

# Add src directory to path so that imports in tests work correctly
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
