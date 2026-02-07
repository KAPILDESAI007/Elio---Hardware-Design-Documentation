#!/usr/bin/env python
"""Direct test of summary sheet generation"""

import sys
sys.path.insert(0, r'c:\Working\Others\Python\Cloud App Projects')

# Import the class directly
import importlib.util
spec = importlib.util.spec_from_file_location("design_input", 
    r"c:\Working\Others\Python\Cloud App Projects\Design Input Review.py")
design_input = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design_input)

# Create instance
dir_obj = design_input.DesignInputReview(r'c:\Working\Others\Python\Cloud App Projects')

# Load test data
print("Loading test data...")
if dir_obj.load_design_input_file('uploads/sample_design_input.xls'):
    print("Data loaded, running complete review...")
    dir_obj.run_complete_review()
    print("\nReview complete!")
else:
    print("Failed to load data")
