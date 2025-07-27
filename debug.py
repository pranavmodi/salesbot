#!/usr/bin/env python3

import sys
import os

print("🔍 DEBUG: Python Import Investigation")
print("=" * 50)

print(f"Current working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

print("\nPython path:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print(f"\nPYTHONPATH environment: {os.environ.get('PYTHONPATH', 'Not set')}")

print("\nDirectory contents of /app:")
try:
    for item in os.listdir("/app"):
        item_path = os.path.join("/app", item)
        if os.path.isdir(item_path):
            print(f"  📁 {item}/")
        else:
            print(f"  📄 {item}")
except Exception as e:
    print(f"  Error listing /app: {e}")

print("\nDirectory contents of /app/app:")
try:
    for item in os.listdir("/app/app"):
        item_path = os.path.join("/app/app", item)
        if os.path.isdir(item_path):
            print(f"  📁 {item}/")
        else:
            print(f"  📄 {item}")
except Exception as e:
    print(f"  Error listing /app/app: {e}")

print("\nTrying to import app module...")
try:
    import app
    print(f"✅ SUCCESS: app module imported from {app.__file__}")
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\nTrying to import app.config...")
try:
    import app.config
    print(f"✅ SUCCESS: app.config imported from {app.config.__file__}")
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\nTrying manual sys.path manipulation...")
sys.path.insert(0, '/app')
try:
    import app.config
    print(f"✅ SUCCESS after sys.path.insert: app.config imported")
except Exception as e:
    print(f"❌ STILL FAILED after sys.path.insert: {e}")