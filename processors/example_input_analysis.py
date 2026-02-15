"""
Example usage of InputDataAnalyzer with real project data
"""

import pandas as pd
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from input_data_analysis import InputDataAnalyzer


def example_with_real_project_data():
    """Example: Analyze real project instrument data"""
    
    # Load real project file
    file_path = Path(r"C:\Working\Others\Python\Cloud App Projects\templates\3291-36930B-J032-020 RevC_ESD.xls")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    print("\n" + "="*70)
    print("EXAMPLE: Analyzing Real Project Data")
    print("="*70)
    print(f"File: {file_path.name}\n")
    
    # Read data
    df = pd.read_excel(file_path)
    
    # Ensure IO_type_base column exists
    if 'IO_type_base' not in df.columns and 'IO_type' in df.columns:
        # Extract base IO type if needed
        def extract_base_type(io_type):
            if pd.isna(io_type):
                return None
            io_str = str(io_type).upper().strip()
            for base in ['AI', 'DI', 'DO', 'AO']:
                if base in io_str:
                    return base
            if 'SOFT' in io_str or 'SOFTWARE' in io_str:
                return 'SOFT'
            return io_str
        
        df['IO_type_base'] = df['IO_type'].apply(extract_base_type)
    
    # ===================== SCENARIO 1: Without wired spares =====================
    print("\nSCENARIO 1: Without Wired Spares")
    print("-" * 70)
    
    analyzer1 = InputDataAnalyzer(df)
    table1 = analyzer1.generate_analysis_table()
    
    print("\nSignal Distribution by IO Type:")
    print(table1.to_string(index=False))
    
    summary1 = analyzer1.get_analysis_summary()
    print(f"\nTotal Signals: {summary1['total_signals']}")
    
    # ===================== SCENARIO 2: With 20% wired spares =====================
    print("\n" + "="*70)
    print("SCENARIO 2: With 20% Wired Spares")
    print("-" * 70)
    
    analyzer2 = InputDataAnalyzer(df, wired_spares_percentage=20)
    table2 = analyzer2.generate_analysis_table()
    
    print("\nSignal Distribution with Wired Spares:")
    print(table2.to_string(index=False))
    
    summary2 = analyzer2.get_analysis_summary()
    print(f"\nTotal Signals: {summary2['total_signals']}")
    print(f"Wired Spares (20%): {summary2['total_wired_spares']}")
    print(f"Total with Spares: {summary2['total_all']}")
    
    # ===================== SCENARIO 3: With 30% wired spares =====================
    print("\n" + "="*70)
    print("SCENARIO 3: With 30% Wired Spares")
    print("-" * 70)
    
    analyzer3 = InputDataAnalyzer(df, wired_spares_percentage=30)
    table3 = analyzer3.generate_analysis_table()
    
    print("\nSignal Distribution with Wired Spares:")
    print(table3.to_string(index=False))
    
    summary3 = analyzer3.get_analysis_summary()
    print(f"\nTotal Signals: {summary3['total_signals']}")
    print(f"Wired Spares (30%): {summary3['total_wired_spares']}")
    print(f"Total with Spares: {summary3['total_all']}")
    
    # ===================== Query specific IO types =====================
    print("\n" + "="*70)
    print("QUERY: Specific IO Type Information (30% spares)")
    print("-" * 70)
    
    for io_type in ['AI', 'DI', 'DO', 'AO', 'SOFT']:
        signal_count = analyzer3.get_signal_count_by_io_type(io_type)
        spare_count = analyzer3.get_wired_spare_count_by_io_type(io_type)
        total_count = analyzer3.get_total_count_by_io_type(io_type)
        
        print(f"\n{io_type}:")
        print(f"  Signals:   {signal_count:4d}")
        print(f"  Spares:    {spare_count:4d}")
        print(f"  Total:     {total_count:4d}")


if __name__ == '__main__':
    example_with_real_project_data()
