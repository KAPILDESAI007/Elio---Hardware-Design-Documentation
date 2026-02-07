import pandas as pd
import importlib.util

spec = importlib.util.spec_from_file_location('design_input_review', 'Design Input Review.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

review = DesignInputReview(wired_spares=20)

# Run all steps
if (review.read_instrument_file() and 
    review.extract_required_columns() and 
    review.apply_user_inputs() and 
    review.sort_by_pid_tag() and 
    review.read_hardware_config() and 
    review.assign_modules() and 
    review.read_fio_config() and 
    review.assign_nodes_and_controllers() and 
    review.identify_unassigned()):
    
    print('[OK] Initial steps done')
    spares = review.generate_wired_spares()
    print(f'[OK] Generated {len(spares)} wired spares')
    
    if not spares.empty:
        # Check what tags the spares have
        print(f'\nWired spare tags before adding to assigned:')
        print(spares['PID_TAG'].value_counts().head(20))
        
        # Add to assigned
        review.df_assigned = pd.concat([review.df_assigned, spares], ignore_index=True)
        print(f'\n[OK] df_assigned now has {len(review.df_assigned)} rows')
        
        # Reassign nodes
        if review.assign_nodes_and_controllers():
            print('[OK] Reassigned nodes/slots')
            
            # Check tags after reassignment
            assigned = review.df_assigned[review.df_assigned['Module_Name'] != ""].copy()
            n0s0_tags = assigned[assigned['PID_TAG'].str.contains('N0S0', na=False)]
            print(f'\nTags with N0S0 after reassignment: {len(n0s0_tags)}')
            
            # Check what would be filtered
            before_filter = len(assigned)
            filtered = assigned[~assigned['PID_TAG'].str.lower().str.contains('spare', na=False)]
            after_filter = len(filtered)
            print(f'\nBefore filter: {before_filter} rows')
            print(f'After filter: {after_filter} rows')
            print(f'Filtered out: {before_filter - after_filter} rows')
            
            # Show what gets filtered
            removed = assigned[assigned['PID_TAG'].str.lower().str.contains('spare', na=False)]
            if len(removed) > 0:
                print(f'\nRows that would be filtered (contain "spare"):')
                print(removed[['PID_TAG', 'IO_type', 'Module_Name']].head(20))
