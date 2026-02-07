#!/usr/bin/env python3
"""Check spare signals in source data"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import pandas as pd

# Load raw source data
test_file = 'Design Input Review_2026-01-31.xlsx'
print(f"Loading {test_file}...")
df_raw = pd.read_excel(test_file)

print(f"\nTotal rows in source file: {len(df_raw)}")
print(f"Columns: {df_raw.columns.tolist()}\n")

# Look for spare signals
spare_rows = df_raw[df_raw['PID_TAG'].str.contains('SPARE', case=False, na=False)]
print(f"Found {len(spare_rows)} spare signals in source file")
print("\nFirst 20 spares:")
for idx, row in spare_rows.head(20).iterrows():
    print(f"  {row['PID_TAG']:20s} | signal_origin: {row.get('signal_origin', 'UNKNOWN'):15s} | IO_type: {row.get('IO_type', 'UNKNOWN'):10s}")

print(f"\n=== SPECIFIC SPARES MENTIONED ===")
specific_spares = ['SPARE74', 'SPARE75', 'SPARE84', 'SPARE85']
for spare in specific_spares:
    match = df_raw[df_raw['PID_TAG'] == spare]
    if len(match) > 0:
        row = match.iloc[0]
        print(f"\n{spare}:")
        print(f"  signal_origin: {row.get('signal_origin', 'UNKNOWN')}")
        print(f"  IO_type: {row.get('IO_type', 'UNKNOWN')}")
        print(f"  IO_REDUNDANCY: {row.get('IO_REDUNDANCY', 'UNKNOWN')}")
        print(f"  IS_Non_IS: {row.get('IS_Non_IS', 'UNKNOWN')}")
    else:
        print(f"\n{spare}: NOT FOUND")

# Check IO_type variations
print(f"\n=== ALL UNIQUE IO_TYPES ===")
io_types = df_raw['IO_type'].value_counts()
for io_type, count in io_types.items():
    print(f"  {io_type}: {count}")
