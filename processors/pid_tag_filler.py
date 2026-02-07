import pandas as pd
import re
from pathlib import Path
import logging
from excel.excel_manager import ExcelManager

logger = logging.getLogger("CloudAppLogger")

class PIDTagFiller:
    def __init__(self, workbook_path: Path, sheet_name: str, df_points):
        self.workbook_path = Path(workbook_path)
        self.sheet_name = sheet_name
        self.df_points = df_points

    def process(self):
        logger.info(f"Processing PID tags for sheet: {self.sheet_name}")
        try:
            wb = ExcelManager.load_workbook(self.workbook_path)
            if self.sheet_name not in wb.sheetnames:
                logger.error(f"Sheet {self.sheet_name} not found")
                wb.close()
                return
            
            ws = wb[self.sheet_name]
            self._update_header_cells(ws)
            
            header_row, slot_data_cols = self._detect_header_row(ws)
            if header_row is None or not slot_data_cols:
                logger.error(f"Header row not found in {self.sheet_name}")
                wb.close()
                return
            
            node_headers = self._find_node_headers(ws)
            if not node_headers:
                logger.error(f"No node headers found in {self.sheet_name}")
                wb.close()
                return
            
            df_lookup = self._prepare_lookup_data()
            pid_tags_written = self._fill_pid_tags(ws, node_headers, slot_data_cols, df_lookup)
            
            logger.info(f"Filled {pid_tags_written} PID tags in {self.sheet_name}")
            ExcelManager.save_workbook(wb, self.workbook_path)
            
        except Exception as e:
            logger.error(f"Error processing PID tags: {e}")
            raise

    def _update_header_cells(self, ws):
        cabinet_name = self.df_points['SYSTEM_CABINET'].iloc[0] if 'SYSTEM_CABINET' in self.df_points.columns else ""
        station_val = self.df_points['STATION NAME'].iloc[0] if 'STATION NAME' in self.df_points.columns else ""
        
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                val = ws.cell(row=r, column=c).value
                if isinstance(val, str):
                    if 'Cabinet No :' in val:
                        ExcelManager.write_cell_safe(ws, r, c, f"Cabinet No : {cabinet_name}")
                    elif 'Station Name :' in val:
                        ExcelManager.write_cell_safe(ws, r, c, f"Station Name : {station_val}")

    def _detect_header_row(self, ws):
        for r in range(1, ws.max_row + 1):
            row_texts = [str(ws.cell(row=r, column=c).value).strip().upper() 
                        if ws.cell(row=r, column=c).value is not None else "" 
                        for c in range(1, ws.max_column+1)]
            
            if any('CH' == t or 'CHANNEL' in t or re.search(r'\bCH\b', t) for t in row_texts) and \
               any(re.search(r'\bS\d+\b', t) for t in row_texts):
                
                slot_header_cols = {}
                for c_idx, t in enumerate(row_texts, start=1):
                    m = re.search(r'\bS(\d+)\b', t)
                    if m:
                        try:
                            slot_no = int(m.group(1))
                            slot_header_cols[slot_no] = c_idx
                        except Exception:
                            continue
                
                slot_data_cols = {slot_no: header_col + 1 for slot_no, header_col in slot_header_cols.items()}
                return r, slot_data_cols
        
        return None, {}

    def _find_node_headers(self, ws):
        node_headers = []
        node_re = re.compile(r'NODE\s*[:\-]?\s*(\d+)', re.IGNORECASE)
        
        for r in range(1, ws.max_row+1):
            for c in range(1, ws.max_column+1):
                val = ws.cell(row=r, column=c).value
                if isinstance(val, str):
                    m = node_re.search(val)
                    if m:
                        try:
                            node_headers.append((int(m.group(1)), r))
                            break
                        except Exception:
                            continue
        
        return sorted(node_headers, key=lambda x: x[1])

    def _prepare_lookup_data(self):
        df_lookup = self.df_points.copy()
        df_lookup.columns = [c.strip().upper() for c in df_lookup.columns]
        for col in ['NODE', 'SLOT_P', 'CHANNEL']:
            if col in df_lookup.columns:
                df_lookup[col] = pd.to_numeric(df_lookup[col], errors='coerce').astype('Int64')
        return df_lookup

    def _fill_pid_tags(self, ws, node_headers, slot_data_cols, df_lookup):
        pid_tags_written = 0
        
        for node_num, node_row in node_headers:
            next_rows = [r for nnum, r in node_headers if r > node_row]
            zone_end = (min(next_rows) - 1) if next_rows else ws.max_row
            
            channel_row_map = self._find_channel_rows(ws, node_row, zone_end)
            if not channel_row_map:
                continue
            
            node_data = df_lookup[df_lookup['NODE'] == node_num]
            if node_data.empty:
                continue
            
            for _, row_data in node_data.iterrows():
                slot_p = row_data.get('SLOT_P')
                channel = row_data.get('CHANNEL')
                pid_tag = row_data.get('PID_TAG')
                redundancy_flag = row_data.get('REDUNDANCY_FLAG', 'No')
                
                if pd.isna(slot_p) or pd.isna(channel) or pd.isna(pid_tag):
                    continue
                
                try:
                    slot_p = int(slot_p)
                    channel = int(channel)
                except Exception:
                    continue
                
                if slot_p not in slot_data_cols or channel not in channel_row_map:
                    continue
                
                col_idx = slot_data_cols[slot_p]
                row_idx = channel_row_map[channel]
                
                # Check if cell already has a tag assigned
                existing_value = ws.cell(row=row_idx, column=col_idx).value
                if existing_value and str(existing_value).strip() != '':
                    logger.debug(f"Cell ({row_idx},{col_idx}) already has tag '{existing_value}', skipping {pid_tag}")
                    continue
                
                # Check for redundancy: if Redundancy_Flag=Yes, even slots are reserved
                if str(redundancy_flag).strip().upper() == 'YES' and slot_p % 2 == 0:
                    logger.debug(f"Slot {slot_p} is EVEN and reserved for redundancy, skipping {pid_tag}")
                    continue
                
                ExcelManager.write_cell_safe(ws, row_idx, col_idx, str(pid_tag))
                pid_tags_written += 1
        
        return pid_tags_written

    def _find_channel_rows(self, ws, node_row, zone_end):
        channel_row_map = {}
        
        for r in range(node_row + 1, zone_end + 1):
            v = ws.cell(row=r, column=1).value
            try:
                iv = int(v)
                if 1 <= iv <= 16 and iv not in channel_row_map:
                    channel_row_map[iv] = r
            except Exception:
                continue
        
        if 1 not in channel_row_map and 2 in channel_row_map:
            channel_row_map[1] = channel_row_map[2] - 1
        
        return channel_row_map
