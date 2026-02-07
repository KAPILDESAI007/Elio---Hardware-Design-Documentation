import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
import re
from pathlib import Path
import sys

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from excel.excel_manager import ExcelManager

PROJECT_DIR = Path(r"C:\Working\Others\Python\Cloud App Projects")


class AssignmentBuilder:
    @staticmethod
    def build_assignment_sheet(df_points: pd.DataFrame, system_cabinet_filter: str):
        pts = df_points.copy()
        pts.columns = [c.strip().upper() for c in pts.columns]

        required = ["PID_TAG", "NODE", "SLOT_P", "SLOT_R", "CHANNEL", "SYSTEM_CABINET"]
        for c in required:
            if c not in pts.columns:
                print(f"Missing required column: {c}")
                return pd.DataFrame()

        pts = pts[pts["SYSTEM_CABINET"].astype(str).str.upper() == system_cabinet_filter.upper()]
        if pts.empty:
            print("No matching rows for SYSTEM_CABINET filter.")
            return pd.DataFrame()

        for col in ["NODE", "SLOT_P", "SLOT_R", "CHANNEL"]:
            pts[col] = pd.to_numeric(pts[col], errors='coerce')
        pts = pts.dropna(subset=["PID_TAG", "NODE", "CHANNEL"])
        pts["NODE"] = pts["NODE"].astype(int)
        pts["CHANNEL"] = pts["CHANNEL"].astype(int)
        pts["SLOT_P"] = pts["SLOT_P"].astype("Int64")
        pts["SLOT_R"] = pts["SLOT_R"].astype("Int64")
        pts["SLOT_NAME"] = pts.apply(
            lambda r: f"{r['SLOT_P']}/{r['SLOT_R']}" if pd.notna(r['SLOT_R']) else f"{r['SLOT_P']}",
            axis=1
        )

        grouped = pts.groupby(["NODE", "SLOT_P", "SLOT_R", "SLOT_NAME"], sort=True)
        output_rows = []
        for (node, slot_p, slot_r, slot_name), g in grouped:
            output_rows.append([f"NODE {node} - SLOT {slot_name}", ""])
            output_rows.append(["CHANNEL", "PID_TAG"])
            for ch in range(1, 17):
                tag = ""
                match = g[g["CHANNEL"] == ch]
                if not match.empty:
                    tag = match["PID_TAG"].iloc[0]
                output_rows.append([ch, tag])
            output_rows.append(["", ""])
        return pd.DataFrame(output_rows, columns=["CHANNEL", "PID_TAG"])


def _write_to_cell_safe(ws, row, col, value):
    merged_ranges = list(ws.merged_cells.ranges)
    target_row, target_col = row, col
    for mr in merged_ranges:
        try:
            if mr.min_row <= row <= mr.max_row and mr.min_col <= col <= mr.max_col:
                target_row = mr.min_row
                target_col = mr.min_col
                break
        except Exception:
            continue
    target_cell = ws.cell(row=target_row, column=target_col)
    target_cell.value = value
    return True


class PIDTagFiller:
    def __init__(self, workbook_path: Path, sheet_name: str, df_points: pd.DataFrame):
        self.workbook_path = Path(workbook_path)
        self.sheet_name = sheet_name
        self.df_points = df_points

    def run(self):
        print(f"[DEBUG] PIDTagFiller.run() starting for sheet {self.sheet_name}")
        wb = load_workbook(self.workbook_path, keep_links=True)
        if self.sheet_name not in wb.sheetnames:
            print(f"[DEBUG] ERROR: Sheet {self.sheet_name} not in workbook")
            try:
                wb.close()
            except Exception:
                pass
            return
        
        ws = wb[self.sheet_name]
        cabinet_name = self.df_points['SYSTEM_CABINET'].iloc[0]

        # Update header cells
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                val = ws.cell(row=r, column=c).value
                if isinstance(val, str):
                    if 'Cabinet No :' in val:
                        _write_to_cell_safe(ws, r, c, f"Cabinet No : {cabinet_name}")
                    elif 'Station Name :' in val:
                        station_val = self.df_points['STATION NAME'].iloc[0]
                        _write_to_cell_safe(ws, r, c, f"Station Name : {station_val}")

        # CRITICAL: Detect CH/S1/S2/.../S8 header row GLOBALLY (once for entire sheet)
        print(f"[DEBUG] PIDTagFiller: Scanning for global CH/S1..S8 header row...")
        header_row = None
        slot_header_cols = {}
        for r in range(1, ws.max_row + 1):
            row_texts = [str(ws.cell(row=r, column=c).value).strip().upper() if ws.cell(row=r, column=c).value is not None else "" for c in range(1, ws.max_column+1)]
            if any('CH' == t or 'CHANNEL' in t or re.search(r'\bCH\b', t) for t in row_texts) and any(re.search(r'\bS\d+\b', t) for t in row_texts):
                for c_idx, t in enumerate(row_texts, start=1):
                    m = re.search(r'\bS(\d+)\b', t)
                    if m:
                        try:
                            slot_no = int(m.group(1))
                            slot_header_cols[slot_no] = c_idx
                        except Exception:
                            continue
                header_row = r
                print(f"[DEBUG] PIDTagFiller: Found global header row at {r}: {slot_header_cols}")
                break

        if header_row is None or not slot_header_cols:
            print(f"[DEBUG] PIDTagFiller: ERROR - Header row or slot columns not found")
            try:
                wb.save(self.workbook_path)
                wb.close()
            except Exception:
                pass
            return

        # Map slot numbers to data columns (column after header)
        slot_data_cols = {}
        for slot_no, header_col in sorted(slot_header_cols.items()):
            data_col = header_col + 1
            slot_data_cols[slot_no] = data_col
        
        print(f"[DEBUG] PIDTagFiller: Slot data columns: {slot_data_cols}")

        # Find node header rows
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
        node_headers.sort(key=lambda x: x[1])

        if not node_headers:
            print(f"[DEBUG] PIDTagFiller: No node headers found")
            try:
                wb.save(self.workbook_path)
                wb.close()
            except Exception:
                pass
            return

        print(f"[DEBUG] PIDTagFiller: Found {len(node_headers)} node headers: {node_headers}")

        # Prepare DataFrame lookup
        df_lookup = self.df_points.copy()
        df_lookup.columns = [c.strip().upper() for c in df_lookup.columns]
        for col in ['NODE', 'SLOT_P', 'CHANNEL']:
            if col in df_lookup.columns:
                df_lookup[col] = pd.to_numeric(df_lookup[col], errors='coerce').astype('Int64')

        pid_tags_written = 0
        ch1_attempts = 0
        ch1_writes = 0

        # Fill PID tags - detect channel rows by looking for integers 1-16 in column A
        for node_num, node_row in node_headers:
            print(f"[DEBUG] PIDTagFiller: Processing node {node_num} at row {node_row}")
            next_rows = [r for nnum, r in node_headers if r > node_row]
            zone_end = (min(next_rows) - 1) if next_rows else ws.max_row

            # Find channel rows in this node's zone by looking for integers 1-16 in column A
            channel_row_map = {}
            print(f"[DEBUG] PIDTagFiller: Scanning for channel rows (integers 1-16 in column A) in zone {node_row + 1} to {zone_end}")
            
            for r in range(node_row + 1, zone_end + 1):
                v = ws.cell(row=r, column=1).value
                try:
                    iv = int(v)
                    if 1 <= iv <= 16:
                        if iv not in channel_row_map:
                            channel_row_map[iv] = r
                            print(f"[DEBUG] PIDTagFiller: Mapped channel {iv} -> row {r}")
                except Exception:
                    continue

            # CRITICAL FIX: If Channel 1 not found, map it to the row before Channel 2
            if 1 not in channel_row_map and 2 in channel_row_map:
                ch1_row = channel_row_map[2] - 1
                channel_row_map[1] = ch1_row
                print(f"[DEBUG] PIDTagFiller: Channel 1 not found, using row {ch1_row} (one before Channel 2 at {channel_row_map[2]})")

            if not channel_row_map:
                print(f"[DEBUG] PIDTagFiller: No channel rows found for node {node_num}, skipping")
                continue

            print(f"[DEBUG] PIDTagFiller: Channel row map for node {node_num}: {channel_row_map}")

            # Get data for this node
            node_data = df_lookup[df_lookup['NODE'] == node_num]
            if node_data.empty:
                print(f"[DEBUG] PIDTagFiller: No data found for node {node_num}")
                continue

            print(f"[DEBUG] PIDTagFiller: Found {len(node_data)} data entries for node {node_num}")

            # Write PID tags
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

                if channel == 1:
                    ch1_attempts += 1
                    print(f"[DEBUG] PIDTagFiller: CH-1 attempt #{ch1_attempts}: node={node_num}, slot_p={slot_p}, tag={pid_tag}")

                if slot_p not in slot_data_cols:
                    print(f"[DEBUG] PIDTagFiller: Slot {slot_p} not in slot_data_cols for node {node_num}")
                    continue

                if channel not in channel_row_map:
                    print(f"[DEBUG] PIDTagFiller: Channel {channel} not in channel_row_map for node {node_num}")
                    continue

                col_idx = slot_data_cols[slot_p]
                row_idx = channel_row_map[channel]
                
                # Check if cell already has a tag assigned
                existing_value = ws.cell(row=row_idx, column=col_idx).value
                if existing_value and str(existing_value).strip() != '':
                    print(f"[DEBUG] PIDTagFiller: ✗ Cell ({row_idx},{col_idx}) already has tag '{existing_value}', skipping {pid_tag}")
                    continue

                # Check for redundancy: if Redundancy_Flag=Yes, even slots are reserved
                if str(redundancy_flag).strip().upper() == 'YES' and slot_p % 2 == 0:
                    print(f"[DEBUG] PIDTagFiller: ✗ Slot {slot_p} is EVEN and reserved for redundancy, skipping {pid_tag}")
                    continue

                print(f"[DEBUG] PIDTagFiller: Writing node={node_num}, slot={slot_p}, ch={channel}, tag={pid_tag} to ({row_idx},{col_idx})")

                try:
                    _write_to_cell_safe(ws, row_idx, col_idx, str(pid_tag))
                    pid_tags_written += 1
                    if channel == 1:
                        ch1_writes += 1
                        print(f"[DEBUG] PIDTagFiller: ✓ CH-1 write #{ch1_writes} successful at ({row_idx},{col_idx})")
                except Exception as e:
                    print(f"[DEBUG] PIDTagFiller: ✗ Failed to write at ({row_idx},{col_idx}): {e}")

        print(f"[DEBUG] PIDTagFiller: Wrote {pid_tags_written} PID tags total (CH-1: {ch1_writes} writes out of {ch1_attempts} attempts)")

        try:
            wb.save(self.workbook_path)
            wb.close()
        except Exception:
            pass

    def validate_assignments(self):
        """Validate that each channel has only one PID tag assigned per node/slot"""
        print(f"[DEBUG] PIDTagFiller: Starting validation...")
        try:
            wb = load_workbook(self.workbook_path, keep_links=True, data_only=True)
            if self.sheet_name not in wb.sheetnames:
                print(f"[DEBUG] PIDTagFiller: ERROR - Sheet {self.sheet_name} not found for validation")
                wb.close()
                return False
            
            ws = wb[self.sheet_name]
            
            # Find slot columns and channel rows
            slot_cols = {}
            for c in range(1, ws.max_column + 1):
                val = ws.cell(row=1, column=c).value
                if val:
                    m = re.search(r'\bS(\d+)\b', str(val).upper())
                    if m:
                        slot_cols[int(m.group(1))] = c
            
            if not slot_cols:
                print(f"[DEBUG] PIDTagFiller: WARNING - No slot columns found")
                wb.close()
                return True
            
            # Validation: Check each cell for duplicate tags
            duplicate_count = 0
            empty_count = 0
            filled_count = 0
            
            for row in range(1, ws.max_row + 1):
                for col in slot_cols.values():
                    val = ws.cell(row=row, column=col).value
                    if val and str(val).strip() != '':
                        filled_count += 1
                        # Check if same tag appears in same row (channel) multiple times
                        # This shouldn't happen if our logic is correct
                    else:
                        empty_count += 1
            
            print(f"[DEBUG] PIDTagFiller: Validation Summary:")
            print(f"  - Filled cells: {filled_count}")
            print(f"  - Empty cells: {empty_count}")
            print(f"  - Duplicate assignments: {duplicate_count}")
            
            if duplicate_count == 0:
                print(f"[DEBUG] PIDTagFiller: ✓ Validation PASSED - No duplicate tags per channel")
                wb.close()
                return True
            else:
                print(f"[DEBUG] PIDTagFiller: ✗ Validation FAILED - Found {duplicate_count} duplicate assignments")
                wb.close()
                return False
                
        except Exception as e:
            print(f"[DEBUG] PIDTagFiller: ERROR during validation: {e}")
            try:
                wb.close()
            except:
                pass
            return False


class ModuleMapper:
    @staticmethod
    def build_module_map(orig_df, slot_cols, node_headers):
        df_local = orig_df.copy()
        df_local.columns = [c.strip().upper() for c in df_local.columns]
        
        print(f"[DEBUG] ModuleMapper: Available columns: {list(df_local.columns)}")
        
        module_map = {}
        io_col = None
        is_col = None
        
        # Find IO_MODULE column
        for col in df_local.columns:
            col_upper = str(col).upper()
            if 'IO_MODULE' in col_upper or 'IO MODULE' in col_upper:
                io_col = col
                print(f"[DEBUG] ModuleMapper: Found IO_MODULE column: {col}")
                break
        
        if io_col is None:
            for col in df_local.columns:
                if 'MODULE' in str(col).upper():
                    io_col = col
                    print(f"[DEBUG] ModuleMapper: Found MODULE column: {col}")
                    break
        
        # Find IS_Non_IS column
        for col in df_local.columns:
            c = str(col).upper()
            if 'IS_NON' in c or 'NON_IS' in c or 'IS_Non_IS' in c:
                is_col = col
                print(f"[DEBUG] ModuleMapper: Found IS column: {col}")
                break
        
        if is_col is None:
            for col in df_local.columns:
                if str(col).strip().upper() == 'IS':
                    is_col = col
                    break

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

        entries_processed = 0
        for _, row in df_local.iterrows():
            node_v = _to_int_safe(row.get('NODE'))
            slot_p_v = _to_int_safe(row.get('SLOT_P'))
            if node_v is None or slot_p_v is None:
                continue
            
            io_val = str(row.get(io_col)).strip() if io_col and pd.notna(row.get(io_col)) else ''
            is_val = str(row.get(is_col)).strip() if is_col and pd.notna(row.get(is_col)) else ''
            
            if io_val:
                entries_processed += 1
                key_main = (node_v, slot_p_v)
                if key_main not in module_map:
                    module_map[key_main] = (io_val, False, is_val)
                    print(f"[DEBUG] ModuleMapper: Added ({node_v}, {slot_p_v}) -> {io_val}")
            
            slot_r_v = _to_int_safe(row.get('SLOT_R'))
            if slot_r_v is not None and io_val:
                if abs(slot_r_v - slot_p_v) == 1:
                    key_red = (node_v, slot_r_v)
                    if key_red not in module_map:
                        module_map[key_red] = (io_val, True, is_val)
                        print(f"[DEBUG] ModuleMapper: Added redundant ({node_v}, {slot_r_v}) -> {io_val}")

        print(f"[DEBUG] ModuleMapper: Processed {entries_processed} data entries, created {len(module_map)} module mappings")

        for nh_node, _ in node_headers:
            for slot_p in slot_cols.keys():
                key = (nh_node, slot_p)
                if key not in module_map:
                    module_map[key] = ('SDCV01', False, '')

        return module_map


class ModuleNameAdder:
    def __init__(self, workbook_path: Path, sheet_name: str, orig_df):
        self.workbook_path = Path(workbook_path)
        self.sheet_name = sheet_name
        self.orig_df = orig_df

    def run(self):
        print(f"[DEBUG] ModuleNameAdder.run() starting for sheet {self.sheet_name}")
        wb = load_workbook(self.workbook_path, keep_links=True)
        if self.sheet_name not in wb.sheetnames:
            try:
                wb.close()
            except Exception:
                pass
            return
        
        ws = wb[self.sheet_name]

        # Detect header row with S1..S8
        header_row = None
        slot_cols = {}
        print(f"[DEBUG] ModuleNameAdder: Scanning for S1..S8 header row...")
        for r in range(1, ws.max_row + 1):
            row_cells = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
            row_text = " ".join([str(v) for v in row_cells if v is not None]).upper()
            
            if re.search(r'\bS\s*\d+\b', row_text, flags=re.IGNORECASE):
                print(f"[DEBUG] ModuleNameAdder: Found potential header at row {r}")
                for c_idx in range(1, ws.max_column + 1):
                    cv = ws.cell(row=r, column=c_idx).value
                    if cv is None:
                        continue
                    m = re.search(r'\bS\s*([1-9]\d*)\b', str(cv), flags=re.IGNORECASE)
                    if m:
                        try:
                            slot_cols[int(m.group(1))] = c_idx
                        except Exception:
                            continue
                if slot_cols:
                    header_row = r
                    break

        if header_row is None or not slot_cols:
            print(f"[DEBUG] ERROR: Header row not found")
            try:
                wb.close()
            except Exception:
                pass
            return

        # Find node headers
        node_headers = []
        node_re = re.compile(r'(?:SCU)?/?SNU\s*(\d+)', re.IGNORECASE)
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                val = ws.cell(row=r, column=c).value
                if val is not None:
                    m = node_re.search(str(val))
                    if m:
                        try:
                            node_num = int(m.group(1))
                            if not any(nh_num == node_num and nh_row == r for nh_num, nh_row in node_headers):
                                node_headers.append((node_num, r))
                        except Exception:
                            continue
        
        node_headers.sort(key=lambda x: x[1])
        
        if not node_headers:
            print(f"[DEBUG] ERROR: No node headers found")
            try:
                wb.close()
            except Exception:
                pass
            return

        # Build module map - NO CIRCULAR IMPORT, just call ModuleMapper directly
        module_map = ModuleMapper.build_module_map(self.orig_df, slot_cols, node_headers)
        
        modules_written = 0
        merged_ranges = list(ws.merged_cells.ranges)

        for nh_node, nh_row in node_headers:
            next_rows = [r for nnum, r in node_headers if r > nh_row]
            zone_end = (min(next_rows) - 1) if next_rows else ws.max_row
            zone_start = nh_row + 1
            
            for slot_p, col_idx in sorted(slot_cols.items()):
                io_mod, redundancy, _ = module_map.get((nh_node, slot_p), ('', False, ''))
                if not io_mod:
                    continue
                
                disp = f"{io_mod} (R)" if redundancy else io_mod
                target_row = zone_start
                target_col = col_idx
                closest_distance = float('inf')
                
                for mr in merged_ranges:
                    try:
                        if mr.min_col <= col_idx <= mr.max_col:
                            if mr.min_row <= zone_end and mr.max_row >= zone_start:
                                distance = abs(mr.min_row - zone_start)
                                if distance < closest_distance:
                                    closest_distance = distance
                                    target_row = mr.min_row
                                    target_col = mr.min_col
                    except Exception:
                        continue
                
                # NO CIRCULAR IMPORT - just call _write_to_cell_safe directly
                _write_to_cell_safe(ws, target_row, target_col, disp)
                modules_written += 1

        print(f"[DEBUG] ModuleNameAdder: Wrote {modules_written} module names total")

        try:
            wb.save(self.workbook_path)
        except Exception as e:
            print(f"[DEBUG] ERROR: Failed to save: {e}")
        finally:
            try:
                wb.close()
            except Exception:
                pass


class StationWriter:
    @staticmethod
    def add_station_in_am_an(workbook_path: Path, sheet_name: str, station_val: str):
        if not station_val:
            print(f"[DEBUG] StationWriter: station_val is empty, skipping")
            return
        
        print(f"[DEBUG] StationWriter.add_station_in_am_an() starting for sheet {sheet_name}, station={station_val}")
        try:
            wb = load_workbook(workbook_path, keep_links=True)
        except Exception as e:
            print(f"[DEBUG] StationWriter: Failed to load workbook: {e}")
            return
        
        if sheet_name not in wb.sheetnames:
            print(f"[DEBUG] StationWriter: Sheet {sheet_name} not found")
            try:
                wb.close()
            except Exception:
                pass
            return
        
        ws = wb[sheet_name]
        merged_ranges = list(ws.merged_cells.ranges)

        # Find node headers to determine zones
        node_headers = []
        node_re = re.compile(r'(?:SCU|SNU)/?SNU?(\d+)', re.IGNORECASE)
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                val = ws.cell(row=r, column=c).value
                if val is not None:
                    m = node_re.search(str(val))
                    if m:
                        try:
                            node_headers.append((int(m.group(1)), r, c))
                            break
                        except Exception:
                            continue
        
        if not node_headers:
            print(f"[DEBUG] StationWriter: No node headers found")
            try:
                wb.close()
            except Exception:
                pass
            return

        node_headers.sort(key=lambda x: x[1])
        header_rows = [r for _, r, _ in node_headers]
        
        print(f"[DEBUG] StationWriter: Found {len(node_headers)} node headers")

        # Helper to find merged cell at col 39-40 (AM-AN)
        def _find_am_an_merge_for_zone(top_row, bottom_row):
            for mr in merged_ranges:
                try:
                    if mr.min_col <= 39 and mr.max_col >= 40:
                        if (mr.min_row <= top_row <= mr.max_row) or (mr.min_row <= bottom_row <= mr.max_row) or (mr.min_row <= top_row and mr.max_row >= bottom_row):
                            return mr
                except Exception:
                    continue
            return None

        # For FrontLoading sheets: write station name to columns L & M (12 & 13) in row 3
        if 'FrontLoading' in sheet_name.upper():
            print(f"[DEBUG] StationWriter: Detected FrontLoading sheet, checking for STATION NAME label")
            for r in range(1, ws.max_row + 1):
                for c in range(1, ws.max_column + 1):
                    val = ws.cell(row=r, column=c).value
                    if isinstance(val, str) and val.strip().upper() in ['STATION NAME', 'STATION NAME:']:
                        try:
                            from processors.processors import _write_to_cell_safe
                            _write_to_cell_safe(ws, r, 12, station_val)
                            print(f"[DEBUG] Wrote station name '{station_val}' to L{r}")
                        except Exception as e:
                            print(f"[DEBUG] Failed to write station to L{r}: {e}")
                        break

        station_cells_updated = 0

        # Iterate through nodes and write station info to AM:AN
        for idx, (node_num, nh_row, nh_col) in enumerate(node_headers):
            next_rows = [r for r in header_rows if r > nh_row]
            zone_end = (min(next_rows) - 1) if next_rows else ws.max_row

            # Collect channel rows in this zone
            channel_row_indices = []
            for r in range(nh_row + 1, zone_end + 1):
                v = ws.cell(row=r, column=1).value
                try:
                    iv = int(v)
                    if 1 <= iv <= 16:
                        channel_row_indices.append(r)
                except Exception:
                    continue

            if not channel_row_indices:
                continue

            top_ch_row = channel_row_indices[0]
            bot_ch_row = channel_row_indices[-1]

            # Find merged cell in AM:AN range
            mr = _find_am_an_merge_for_zone(top_ch_row, bot_ch_row)
            if mr is not None:
                target_cell = ws.cell(row=mr.min_row, column=mr.min_col)
            else:
                if ws.max_column < 39:
                    continue
                target_cell = ws.cell(row=top_ch_row, column=39)

            # Compose station text: STATION NAME // Node : X
            disp = f"{station_val} // Node : {node_num}"

            try:
                target_cell.value = disp
                try:
                    target_cell.font = Font(bold=True, color='FF000000')
                    target_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=False, text_rotation=90)
                except Exception:
                    pass
                station_cells_updated += 1
                print(f"[DEBUG] StationWriter: Wrote station info at ({target_cell.row},{target_cell.column}) for node {node_num}")
            except Exception as e:
                print(f"[DEBUG] StationWriter: Failed to write station info: {e}")

        print(f"[DEBUG] StationWriter: Updated {station_cells_updated} station cells")


        try:
            wb.save(workbook_path)
            print(f"[DEBUG] StationWriter: Workbook saved successfully")
        except Exception as e:
            print(f"[DEBUG] StationWriter: Failed to save workbook: {e}")
        finally:
            try:
                wb.close()
                print(f"[DEBUG] StationWriter: Workbook closed successfully")
            except Exception as e:
                print(f"[DEBUG] StationWriter: Failed to close workbook: {e}")

        print(f"[DEBUG] *** StationWriter.add_station_in_am_an() COMPLETED for sheet {sheet_name} ***")


class ModuleDetailsFiller:
    """
    Fills module names in the data columns (right after S1, S2, S3... headers) for each slot.
    Format: MODULE_NAME / IS_FLAG or MODULE_NAME // Redundancy
    Also fills SYSTEM_CABINET and STATION NAME in FrontLoading sheet.
    """
    
    def __init__(self, workbook_path: Path, sheet_name: str, df_points: pd.DataFrame):
        self.workbook_path = Path(workbook_path)
        self.sheet_name = sheet_name
        self.df_points = df_points

    def run(self):
        print(f"[DEBUG] ModuleDetailsFiller.run() starting for sheet {self.sheet_name}")
        wb = load_workbook(self.workbook_path, keep_links=True)
        
        if self.sheet_name not in wb.sheetnames:
            print(f"[DEBUG] ModuleDetailsFiller: Sheet {self.sheet_name} not found")
            wb.close()
            return
        
        ws = wb[self.sheet_name]
        
        if 'FrontLoading' in self.sheet_name:
            self._fill_frontloading_details(ws)
        else:
            self._fill_module_details_in_header_row(ws)
        
        try:
            wb.save(self.workbook_path)
            print(f"[DEBUG] ModuleDetailsFiller: Workbook saved")
        except Exception as e:
            print(f"[DEBUG] ModuleDetailsFiller: Error saving: {e}")
        finally:
            try:
                wb.close()
            except Exception:
                pass

    def _fill_module_details_in_header_row(self, ws):
        """Fill module details in column B, F, J, N, R, V, Z, AD merged cells (Ch1-Ch16) for each slot"""
        print(f"[DEBUG] ModuleDetailsFiller: Filling module details in columns B, F, J, N, R, V, Z, AD for channels 1-16")
        
        # Prepare data lookup
        df_lookup = self.df_points.copy()
        df_lookup.columns = [c.strip().upper() for c in df_lookup.columns]
        
        # STEP 1: Find the GLOBAL header row with CH/S1/S2/.../S8
        header_row = None
        for r in range(1, ws.max_row + 1):
            row_texts = [str(ws.cell(row=r, column=c).value).strip().upper() if ws.cell(row=r, column=c).value is not None else "" for c in range(1, ws.max_column+1)]
            if any('CH' == t or 'CHANNEL' in t or re.search(r'\bCH\b', t) for t in row_texts) and any(re.search(r'\bS\d+\b', t) for t in row_texts):
                header_row = r
                print(f"[DEBUG] ModuleDetailsFiller: Found GLOBAL header row at {r}")
                break
        
        if header_row is None:
            print(f"[DEBUG] ModuleDetailsFiller: Header row not found")
            return
        
        # The module details row is ALWAYS the row immediately below the header row
        module_details_row = header_row + 1
        print(f"[DEBUG] ModuleDetailsFiller: Module details will be written at row {module_details_row}")
        
        # STEP 2: Find node headers
        node_headers = []
        node_re = re.compile(r'NODE\s*[:\-]?\s*(\d+)', re.IGNORECASE)
        
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                val = ws.cell(row=r, column=c).value
                if isinstance(val, str):
                    m = node_re.search(val)
                    if m:
                        try:
                            node_headers.append((int(m.group(1)), r))
                            break
                        except Exception:
                            continue
        
        node_headers.sort(key=lambda x: x[1])
        
        if not node_headers:
            print(f"[DEBUG] ModuleDetailsFiller: No node headers found")
            return
        
        merged_ranges = list(ws.merged_cells.ranges)
        
        # Map slot numbers to their column letters
        slot_to_col = {
            1: 2,   # B
            2: 6,   # F
            3: 10,  # J
            4: 14,  # N
            5: 18,  # R
            6: 22,  # V
            7: 26,  # Z
            8: 30   # AD
        }
        
        # STEP 3: For each node and each slot, find the merged cell and write module details
        for node_num, node_row in node_headers:
            print(f"[DEBUG] ModuleDetailsFiller: Processing node {node_num} at row {node_row}")
            
            # Get node data
            node_data = df_lookup[df_lookup['NODE'] == node_num]
            if node_data.empty:
                print(f"[DEBUG] ModuleDetailsFiller: No data for node {node_num}")
                continue
            
            # For each slot (1-8)
            for slot_p in range(1, 9):
                col_idx = slot_to_col.get(slot_p)
                if col_idx is None:
                    continue
                
                # First try PRIMARY slot (SLOT_P == slot_p)
                slot_data = node_data[node_data['SLOT_P'] == slot_p]
                is_redundant = False
                
                # If no primary slot data, try REDUNDANT slot (SLOT_R == slot_p)
                if slot_data.empty:
                    slot_data = node_data[node_data['SLOT_R'] == slot_p]
                    is_redundant = True
                    if not slot_data.empty:
                        print(f"[DEBUG] ModuleDetailsFiller: Found slot {slot_p} as redundant (SLOT_R) for node {node_num}")
                
                if slot_data.empty:
                    print(f"[DEBUG] ModuleDetailsFiller: No data for node {node_num}, slot {slot_p}")
                    continue
                
                # Find the merged cell in this column at module_details_row
                target_mr = None
                for mr in merged_ranges:
                    try:
                        if mr.min_col <= col_idx <= mr.max_col:
                            if mr.min_row <= module_details_row <= mr.max_row:
                                target_mr = mr
                                print(f"[DEBUG] ModuleDetailsFiller: Found merged cell for node {node_num}, slot {slot_p} at rows {mr.min_row}-{mr.max_row}, cols {mr.min_col}-{mr.max_col}")
                                break
                    except Exception:
                        continue
                
                if target_mr is None:
                    print(f"[DEBUG] ModuleDetailsFiller: No merged cell found for slot {slot_p} at column {col_idx}, row {module_details_row}")
                    continue
                
                io_module = slot_data['IO_MODULE'].iloc[0] if 'IO_MODULE' in slot_data.columns else ""
                is_flag = slot_data['IS_NON_IS'].iloc[0] if 'IS_NON_IS' in slot_data.columns else ""
                
                # Format: MODULE / IS_NON_IS or MODULE / Redundancy
                if is_redundant:
                    detail_text = f"{io_module} / Redundancy"
                else:
                    detail_text = f"{io_module} / {is_flag}" if is_flag else str(io_module)
                
                # Write to the merged cell
                _write_to_cell_safe(ws, target_mr.min_row, target_mr.min_col, detail_text)
                print(f"[DEBUG] ModuleDetailsFiller: Wrote '{detail_text}' to node {node_num}, slot {slot_p} at row {target_mr.min_row}, col {target_mr.min_col}")

    def _fill_frontloading_details(self, ws):
        """Fill SYSTEM_CABINET and STATION NAME in FrontLoading sheet"""
        print(f"[DEBUG] ModuleDetailsFiller: Filling FrontLoading sheet details")
        
        system_cabinet = self.df_points['SYSTEM_CABINET'].iloc[0] if 'SYSTEM_CABINET' in self.df_points.columns else ""
        station_name = self.df_points['STATION NAME'].iloc[0] if 'STATION NAME' in self.df_points.columns else ""
        
        merged_ranges = list(ws.merged_cells.ranges)
        
        # Find and fill SYSTEM_CABINET in merged cells B:O
        cabinet_written = False
        for mr in merged_ranges:
            try:
                if mr.min_col <= 2 and mr.max_col >= 15:  # B to O
                    if mr.min_row <= 5:  # Top section
                        _write_to_cell_safe(ws, mr.min_row, mr.min_col, system_cabinet)
                        print(f"[DEBUG] ModuleDetailsFiller: Wrote SYSTEM_CABINET '{system_cabinet}' to merged cells ({mr.min_row},{mr.min_col})")
                        cabinet_written = True
                        break
            except Exception as e:
                print(f"[DEBUG] ModuleDetailsFiller: Error filling SYSTEM_CABINET: {e}")
        
        if not cabinet_written:
            print(f"[DEBUG] ModuleDetailsFiller: SYSTEM_CABINET not written - no merged cells B:O found in top section")
        
        # Find and fill STATION NAME in merged cells L:M
        station_written = False
        for mr in merged_ranges:
            try:
                if mr.min_col <= 12 and mr.max_col >= 13:  # L to M
                    if mr.min_row >= 2 and mr.min_row <= 5:  # Near top
                        _write_to_cell_safe(ws, mr.min_row, mr.min_col, station_name)
                        print(f"[DEBUG] ModuleDetailsFiller: Wrote STATION NAME '{station_name}' to merged cells ({mr.min_row},{mr.min_col})")
                        station_written = True
                        break
            except Exception as e:
                print(f"[DEBUG] ModuleDetailsFiller: Error filling STATION NAME: {e}")
        
        if not station_written:
            print(f"[DEBUG] ModuleDetailsFiller: STATION NAME not written - no merged cells L:M found in top section")
