import sys
sys.path.insert(0, 'backend')
try:
    from main import app
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
