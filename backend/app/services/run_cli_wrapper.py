"""Wrapper to run the original pipeline.py from the new backend/app layout.

This script forwards CLI args to the pipeline.py located in the SHIELD3 root.
Use it when you want the original interactive prompts but prefer the new folder layout.
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
# Point to the renamed service in the same folder
PIPELINE = os.path.join(HERE, 'pii_detector.py')

if not os.path.exists(PIPELINE):
    print(f"Error: pii_detector.py not found at expected location: {PIPELINE}")
    sys.exit(1)

# Forward all command-line args to the original pipeline.py
cmd = [sys.executable, PIPELINE] + sys.argv[1:]
print('Running:', ' '.join(cmd))
res = subprocess.run(cmd)
sys.exit(res.returncode)
