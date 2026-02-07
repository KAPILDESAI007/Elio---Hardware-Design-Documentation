import pandas as pd

# Test the regex patterns for wired spare detection
test_tags = [
    'AI_SPARE_1',
    'DI_SPARE_2', 
    'DO_SPARE_3',
    'AO_SPARE_4',
    'SPARE_5',
    'spare1',
    'SPARE1',
    '0122-EAI-040109',
    'SCS0101_N1S1CH1',
]

df = pd.DataFrame({'PID_TAG': test_tags})

print("Testing regex patterns for spare detection:")
print("=" * 70)

# NEW pattern (using .contains())
mask_new = df['PID_TAG'].str.contains(r'^SPARE_|_SPARE_\d+$', regex=True, na=False)
print(f"NEW PATTERN: r'^SPARE_|_SPARE_\\d+$'")
print(f"  Matches: {df[mask_new]['PID_TAG'].tolist()}")
print()

# Test wired spare pattern
mask_wired = df['PID_TAG'].str.match(r'^(AI|DI|DO|AO)_SPARE_\d+$', na=False)
print(f"Wired spare pattern: r'^(AI|DI|DO|AO)_SPARE_\\d+$'")
print(f"  Matches: {df[mask_wired]['PID_TAG'].tolist()}")
print()

print("Summary of AI_SPARE_1:")
print(f"  Matched by new pattern? {mask_new[0]}")
print(f"  Matched by wired pattern? {mask_wired[0]}")
print(f"  Will be REGENERATED? {mask_new[0]} (will get new SCS name)")
