import sys
import importlib
spec = importlib.util.spec_from_file_location("DesignInputReview", "Design Input Review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DesignInputReview = module.DesignInputReview

c = DesignInputReview()
c.read_instrument_file()
c.read_hardware_config()
c.wired_spares_percentage = 20
c.read_controller_limits()
c.assign_modules()

assigned = len(c.df_assigned[c.df_assigned['Module_Name'] != ''])
unassigned = len(c.df_assigned[c.df_assigned['Module_Name'] == ''])

print(f"\n[RESULTS] Assigned: {assigned}, Unassigned: {unassigned}")
print(f"\nFirst 20 assigned signals:")
print(c.df_assigned[c.df_assigned['Module_Name'] != ''][['PID_TAG', 'IO_type_base', 'Module_Name', 'Module_Instance', 'Channel']].head(20))

if unassigned > 0:
    print(f"\nFirst unassigned signals:")
    print(c.df_assigned[c.df_assigned['Module_Name'] == ''][['PID_TAG', 'IO_type_base']].head(10))
