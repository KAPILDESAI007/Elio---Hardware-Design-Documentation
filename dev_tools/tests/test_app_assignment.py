"""
Test the full Flask app workflow to verify signals are assigned properly
"""
import os
import sys
from flask import Flask
from pathlib import Path

# Import the app module
sys.path.insert(0, str(Path(__file__).parent))

# Set Flask env var for testing
os.environ['FLASK_ENV'] = 'testing'

# Create temp directories if needed
uploads_dir = Path("uploads")
logs_dir = Path("logs")
uploads_dir.mkdir(exist_ok=True)
logs_dir.mkdir(exist_ok=True)

# Import Flask app
from app import app, process_design_review
from werkzeug.datastructures import FileStorage
from io import BytesIO

# Check if test input file exists
test_file = Path("inputs/SCS0101_SCS0103_20241120.xlsx")
if not test_file.exists():
    print(f"[ERROR] Test file not found: {test_file}")
    print(f"Available files in inputs/:")
    inputs_dir = Path("inputs")
    if inputs_dir.exists():
        for f in inputs_dir.iterdir():
            print(f"  - {f.name}")
    sys.exit(1)

print(f"[INFO] Found test input file: {test_file}")

# Test with manual parameters instead of Flask form
print(f"\n[INFO] Testing assignment with 20% wired spares...")

# Read the test file
with open(test_file, 'rb') as f:
    file_content = f.read()

# Call the process function directly
try:
    result = process_design_review(
        design_input_file=file_content,
        system_type="ESD",
        controller_model="SCADA-SIEMENS",
        explosion_protection="No",
        temperature_rating="Standard",
        redundancy_types="",
        is_types="",
        wired_spares_percentage=20
    )
    
    print(f"\n[SUCCESS] Processing completed")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else type(result)}")
    
except Exception as e:
    print(f"\n[ERROR] Processing failed: {e}")
    import traceback
    traceback.print_exc()
