import pandas as pd
import importlib.util

spec = importlib.util.spec_from_file_location('design_input_review', 'Design Input Review.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

print("Running complete review with wired_spares=20...")
review = DesignInputReview(wired_spares=20)
if review.run_complete_review():
    df = pd.read_excel('Design Input Review_2025-12-25.xlsx', sheet_name='Assigned')
    
    print(f"\nTotal rows in output: {len(df)}")
    
    # Count different categories
    with_scs = df['PID_TAG'].str.contains('SCS0101_N', na=False)
    with_n0s0 = df['PID_TAG'].str.contains('N0S0', na=False)
    with_spare = df['PID_TAG'].str.contains('spare', case=False, na=False)
    
    print(f"Rows with SCS0101_N: {len(df[with_scs])}")
    print(f"Rows with N0S0: {len(df[with_n0s0])}")
    print(f"Rows with 'spare' in name: {len(df[with_spare])}")
    
    # Get actual wired spares (SCS0101_N but not N0S0)
    wired_spares = df[with_scs & ~with_n0s0]
    print(f"\nActual wired spares (SCS0101_N* without N0S0): {len(wired_spares)}")
    
    if len(wired_spares) > 0:
        print("\nFirst 10 wired spares:")
        print(wired_spares[['PID_TAG', 'Module_Name', 'Node', 'Slot', 'Channel']].head(10).to_string())
        
        # Check distribution by node
        print("\nDistribution by Node:")
        print(wired_spares['Node'].value_counts().sort_index())
        
        # Check distribution by module type
        print("\nDistribution by Module Type:")
        print(wired_spares['Module_Name'].value_counts())
else:
    print("Error running complete review")
