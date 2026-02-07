#!/usr/bin/env python
"""Check the unassigned DO signal details"""

import pandas as pd
from pathlib import Path

output_file = Path('Design Input Review_2026-01-25.xlsx')

if output_file.exists():
    df_unassigned = pd.read_excel(output_file, sheet_name='Unassigned')
    
    # Get DO signals
    do_signals = df_unassigned[df_unassigned['IO_type'] == 'DO']
    
    print("\n" + "="*100)
    print(f"Unassigned DO signals: {len(do_signals)}")
    print("="*100)
    print(do_signals[['PID_TAG', 'IO_type', 'IO_REDUNDANCY', 'IS_Non_IS']].head(20).to_string() if len(do_signals) > 0 else "No DO signals")
    
    # Check if there's something in DO's columns that might help
    print("\n" + "="*100)
    print("All columns in unassigned sheet:")
    print("="*100)
    print(do_signals.columns.tolist()[:20] if len(do_signals) > 0 else "N/A")

else:
    print(f"File not found: {output_file}")
