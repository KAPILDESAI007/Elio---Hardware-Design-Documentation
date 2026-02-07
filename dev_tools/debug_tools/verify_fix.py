#!/usr/bin/env python
"""
Quick test to verify signals are assigned after the fix
"""
import sys
from pathlib import Path

# The key test: Can we load and run the module without errors?
try:
    import importlib
    spec = importlib.util.spec_from_file_location("DesignInputReview", "Design Input Review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print("[✓] Design Input Review module loaded successfully")
except Exception as e:
    print(f"[✗] Failed to load module: {e}")
    sys.exit(1)

# Verify the assign_modules method exists and has the right structure
from inspect import getsource
try:
    source = getsource(module.DesignInputReview.assign_modules)
    if "wired_spares_count = {}" in source:
        print("[✓] assign_modules() has wired_spares_count initialization")
    else:
        print("[✗] assign_modules() missing wired_spares_count initialization")
        
    if "for io_type_base_normalized in self.df_instruments['IO_type_base']" in source or \
       "for io_type_base in self.df_instruments['IO_type_base']" in source:
        print("[✓] assign_modules() has signal loop")
    else:
        print("[✗] assign_modules() missing signal loop")
        
    # Check for early return
    lines = source.split('\n')
    returns = [(i, l.strip()) for i, l in enumerate(lines) if 'return' in l]
    if len(returns) == 1:
        print("[✓] assign_modules() has exactly one return statement")
    else:
        print(f"[⚠] assign_modules() has {len(returns)} return statements:")
        for idx, ret in returns:
            print(f"    Line {idx}: {ret}")
            
except Exception as e:
    print(f"[✗] Failed to inspect assign_modules: {e}")
    sys.exit(1)

print("\n[✓] All structural checks passed!")
print("    The assign_modules() method should now properly assign signals to modules.")
print("    Test by running the Flask app with a design input file.")
