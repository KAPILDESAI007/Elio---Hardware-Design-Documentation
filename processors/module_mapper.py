import pandas as pd
import logging

logger = logging.getLogger("CloudAppLogger")

class ModuleMapper:
    @staticmethod
    def build_module_map(orig_df, slot_cols, node_headers):
        df_local = orig_df.copy()
        df_local.columns = [c.strip().upper() for c in df_local.columns]
        
        module_map = {}
        io_col = ModuleMapper._find_io_module_column(df_local)
        is_col = ModuleMapper._find_is_column(df_local)
        
        for _, row in df_local.iterrows():
            node_v = ModuleMapper._to_int_safe(row.get('NODE'))
            slot_p_v = ModuleMapper._to_int_safe(row.get('SLOT_P'))
            
            if node_v is None or slot_p_v is None:
                continue
            
            io_val = str(row.get(io_col)).strip() if io_col and pd.notna(row.get(io_col)) else ''
            is_val = str(row.get(is_col)).strip() if is_col and pd.notna(row.get(is_col)) else ''
            
            if io_val:
                key_main = (node_v, slot_p_v)
                if key_main not in module_map:
                    module_map[key_main] = (io_val, False, is_val)
            
            slot_r_v = ModuleMapper._to_int_safe(row.get('SLOT_R'))
            if slot_r_v is not None and io_val and abs(slot_r_v - slot_p_v) == 1:
                key_red = (node_v, slot_r_v)
                if key_red not in module_map:
                    module_map[key_red] = (io_val, True, is_val)
        
        for nh_node, _ in node_headers:
            for slot_p in slot_cols.keys():
                key = (nh_node, slot_p)
                if key not in module_map:
                    module_map[key] = ('SDCV01', False, '')
        
        return module_map

    @staticmethod
    def _find_io_module_column(df_local):
        for col in df_local.columns:
            if 'IO_MODULE' in str(col).upper() or 'IO MODULE' in str(col).upper():
                return col
        for col in df_local.columns:
            if 'MODULE' in str(col).upper():
                return col
        return None

    @staticmethod
    def _find_is_column(df_local):
        for col in df_local.columns:
            c = str(col).upper()
            if 'IS_NON' in c or 'NON_IS' in c or 'IS_Non_IS' in c:
                return col
        for col in df_local.columns:
            if str(col).strip().upper() == 'IS':
                return col
        return None

    @staticmethod
    def _to_int_safe(val):
        try:
            if pd.isna(val):
                return None
            return int(float(val))
        except Exception:
            try:
                return int(str(val).strip())
            except Exception:
                return None
