import pandas as pd
df = pd.read_excel('templates/Yokogawa_SIS_Constraints_Model_v3.xlsx', sheet_name='IO_Module_Catalog')
df = df[df['Family'] == 'FIO']
modules = df[['Module', 'IO_Type']].drop_duplicates()
print('FIO Modules:')
print(modules)
