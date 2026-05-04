"""pytest configuration for running from project root."""
import os
import sys

# Ensure we can import from src/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Change to project root for data file access
os.chdir(PROJECT_ROOT)