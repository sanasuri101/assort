import sys
import os
print(f"Executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")
try:
    import pipecat
    print("pipecat found")
except ImportError as e:
    print(f"pipecat not found: {e}")
