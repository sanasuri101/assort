import sys
import os

# Ensure backend dir is in path
sys.path.insert(0, os.getcwd())

try:
    from app.main import app
    print("Success: app imported")
except Exception as e:
    import traceback
    traceback.print_exc()
