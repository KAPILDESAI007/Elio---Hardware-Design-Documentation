#!/usr/bin/env python
"""Test IO_type_base extraction for DI-RL and similar"""

import re

def _extract_io_type_base(io_type_str):
    """
    Extract base IO type (AI, DI, DO, AO) from IO_type string.
    Examples: 'AI-R' -> 'AI', 'DI' -> 'DI', 'AO-2W' -> 'AO'
    """
    io_type_upper = str(io_type_str).upper().strip()
    
    # Look for AI, DI, DO, AO at the start of the string
    base_types = ['AI', 'DI', 'DO', 'AO']
    for base_type in base_types:
        if base_type in io_type_upper:
            # Check if it's at the start or after a delimiter
            match = re.search(r'(AI|DI|DO|AO)', io_type_upper)
            if match:
                return match.group(1)
    
    # If no match found, return the original string
    return io_type_upper

# Test cases
test_types = ['DO', 'DO-R', 'DI', 'DI-RL', 'DI-R', 'AI', 'AI-R', 'AO']

print("Testing IO_type_base extraction:")
print("-" * 60)
for io_type in test_types:
    base = _extract_io_type_base(io_type)
    normalized = base.split('-')[0]
    print(f"{io_type:8} → base={base:3} → normalized={normalized:3}")
