import pandas as pd
import openpyxl

file_path = 'Design Input Review_2025-12-25.xlsx'

# Check with pandas
df = pd.read_excel(file_path, sheet_name='Assigned')
print(f'Total rows in Assigned sheet: {len(df)}')
print(f'Columns: {list(df.columns)}')

# Count rows by PID_TAG patterns
scs_rows = df[df['PID_TAG'].str.contains('SCS0101_N', na=False)]
print(f'\nRows with SCS0101_N in PID_TAG: {len(scs_rows)}')

spare_in_pid = df[df['PID_TAG'].str.contains('spare', case=False, na=False)]
print(f'Rows with "spare" in PID_TAG: {len(spare_in_pid)}')

spare_in_io = df[df['IO_type'].str.contains('spare', case=False, na=False)]
print(f'Rows with "spare" in IO_type: {len(spare_in_io)}')

# Get wired spares (SCS0101_N but no spare in PID_TAG)
wired = scs_rows[~scs_rows['PID_TAG'].str.contains('spare', case=False, na=False)]
print(f'\nWired spares (SCS0101_N in PID_TAG, no spare in PID_TAG): {len(wired)}')

if len(wired) > 0:
    print('\nSample wired spares:')
    print(wired[['PID_TAG', 'IO_type', 'Module_Name', 'Node', 'Slot', 'Channel']].head(10))
else:
    print('\nNo wired spares found')
    if len(scs_rows) > 0:
        print('\nFirst few SCS0101_N rows:')
        print(scs_rows[['PID_TAG', 'IO_type', 'Module_Name']].head(10))

# Check for spare in IO_type
print(f'\n\nRows with Spare in IO_type:')
spare_io = df[df['IO_type'].str.contains('spare', case=False, na=False)]
print(f'Count: {len(spare_io)}')
if len(spare_io) > 0:
    print(spare_io[['PID_TAG', 'IO_type', 'Module_Name']].head(10))
