import streamlit as st
import pandas as pd
from datetime import datetime
from infrastructure.excel_reader import ExcelReader
from services.design_input_review_service import DesignInputReviewService

st.set_page_config(page_title="ELIO Enterprise", layout="wide")

# Initialize session state for logs
if "logs" not in st.session_state:
    st.session_state.logs = []

# Initialize session state for form widgets
widget_keys = {
    "system_type_select": "Select...",
    "io_types_select": [],
    "controller_model": "Select...",
    "explosion_protection": "Select...",
    "temperature_rating": "Select...",
    "wired_spares_input": 0
}

for key, default_value in widget_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

def add_log(message, level="INFO"):
    """Add a log entry to session state"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    st.session_state.logs.append(log_entry)

st.title("ELIO Enterprise - Hardware Design & Documentation")

# Add custom CSS to reduce margins and spacing
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        h1 {
            margin-top: 0 !important;
            margin-bottom: 0.2rem !important;
        }
        h2 {
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        h3 {
            margin-top: 0.2rem !important;
            margin-bottom: 0.1rem !important;
        }
        .element-container {
            margin-bottom: 0.2rem !important;
        }
        /* Center align all dataframe content */
        .stDataFrame {
            text-align: center !important;
        }
        [data-testid="stDataFrame"] {
            text-align: center !important;
        }
        tbody {
            text-align: center !important;
        }
        thead {
            text-align: center !important;
        }
        td {
            text-align: center !important;
        }
        th {
            text-align: center !important;
        }
        tr {
            text-align: center !important;
        }
        .glide-data-grid {
            text-align: center !important;
        }
        .glide-data-grid-cell {
            text-align: center !important;
            justify-content: center !important;
            display: flex !important;
            align-items: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("Modules")
page = st.sidebar.radio(
    "Select Module",
    ["Design Input Review", "Nest Loading & IO Assignment", "Bill of Materials"]
)

# ============================================================================
# DESIGN INPUT REVIEW MODULE
# ============================================================================
if page == "Design Input Review":
    st.header("📊 Design Input Review")
    st.markdown("Review and validate design input signals from your I/O files")

    # ====================================================================
    # FILE UPLOAD (AT THE TOP)
    # ====================================================================
    st.subheader("📁 Input File (Required*)")
    
    uploaded_file = st.file_uploader(
        "Select Excel file to upload",
        type=["xlsx", "xls"],
        key="design_input_file"
    )

    if uploaded_file:
        add_log(f"File uploaded: {uploaded_file.name}")
        
        # Get column mapping first
        col_mapping = ExcelReader.get_available_columns(uploaded_file)

        # ====================================================================
        # USER CONFIGURATION OPTIONS (BELOW FILE UPLOAD)
        # ====================================================================
        st.subheader("⚙️ Configuration Options")
        
        # Quick Test Defaults Button
        col_test_btn, col_spacer = st.columns([1, 4])
        with col_test_btn:
            if st.button("🧪 Load Test Defaults", help="Quickly load test values: FIO, S2SC70D, No, Standard, 20%"):
                st.session_state['system_type_select'] = "ESD"
                st.session_state['io_types_select'] = ["FIO"]
                st.session_state['controller_model'] = "S2SC70D"
                st.session_state['explosion_protection'] = "No"
                st.session_state['temperature_rating'] = "Standard"
                st.session_state['wired_spares_input'] = 20
                add_log("✓ Test defaults loaded: FIO, S2SC70D, No, Standard, 20%")
                st.toast("✓ Test defaults loaded!", icon="✅")

        # Create columns for user input
        col1, col2, col3 = st.columns(3)

        with col1:
            system_type_label = "System Type"
            if col_mapping.get("signal_origin"):
                system_type_label += " 🟢"
                st.caption(f"System Type 🟢 (used from column: `{col_mapping['signal_origin']}`)")
            system_type = st.selectbox(
                system_type_label,
                ["Select...", "ESD", "FGS", "DCS"],
                help="Used when signal_origin column is not available",
                key="system_type_select",
                label_visibility="collapsed" if col_mapping.get("signal_origin") else "visible"
            )

        with col2:
            io_types = st.multiselect(
                "IO Types",
                ["FIO", "NIO"],
                help="Select Field I/O or Normal I/O types for this project",
                key="io_types_select"
            )

        with col3:
            controller_model = st.selectbox(
                "Controller Model",
                ["Select...", "S2SC70S", "S2SC70D", "SCS60S", "SCS60D", "SCS50S"],
                help="Select the controller model for allocation",
                key="controller_model"
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            explosion_protection = st.selectbox(
                "Explosion Protection",
                ["Select...", "Yes", "No"],
                help="Explosion protection requirement",
                key="explosion_protection"
            )

        with col5:
            temperature_rating = st.selectbox(
                "Temperature Rating",
                ["Select...", "Standard", "Wide"],
                help="Temperature rating requirement",
                key="temperature_rating"
            )

        with col6:
            wired_spares = st.number_input(
                "Wired Spares %",
                min_value=0,
                max_value=100,
                step=5,
                help="Percentage of wired spare channels (0-100)",
                key="wired_spares_input"
            )

        col7, col8 = st.columns(2)

        with col7:
            redundancy_label = "IO Redundancy"
            if col_mapping.get("io_redundancy"):
                redundancy_label += " 🟢"
                st.caption(f"IO Redundancy 🟢 (used from column: `{col_mapping['io_redundancy']}`)")
            redundancy_types = st.multiselect(
                redundancy_label,
                ["AI", "DI", "AO", "DO"],
                help="Signal types to mark as redundant",
                key="redundancy_select",
                label_visibility="collapsed" if col_mapping.get("io_redundancy") else "visible"
            )

        with col8:
            is_label = "IS/Non-IS Type"
            if col_mapping.get("is_non_is"):
                is_label += " 🟢"
                st.caption(f"IS/Non-IS Type 🟢 (used from column: `{col_mapping['is_non_is']}`)")
            is_types = st.multiselect(
                is_label,
                ["AI", "DI", "AO", "DO"],
                help="Signal types to mark as IS (Intrinsically Safe)",
                key="is_select",
                label_visibility="collapsed" if col_mapping.get("is_non_is") else "visible"
            )

        # Prepare user config dictionary
        user_config = {
            "system_type": system_type if col_mapping.get("signal_origin") is None and system_type != "Select..." else None,
            "io_types": io_types,
            "controller_model": controller_model if controller_model != "Select..." else None,
            "explosion_protection": explosion_protection if explosion_protection != "Select..." else None,
            "temperature_rating": temperature_rating if temperature_rating != "Select..." else None,
            "wired_spares": wired_spares,
            "redundancy_types": redundancy_types,
            "is_types": is_types,
        }

        st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)

        # ====================================================================
        # PROCESS DESIGN INPUT
        # ====================================================================
        with st.spinner("Processing design input..."):
            results = DesignInputReviewService.process_design_input(
                uploaded_file=uploaded_file,
                user_config=user_config,
                col_mapping=col_mapping,
                logger_callback=add_log
            )
        
        if results.get("success"):
            # Display all results
            
            # ====================================================================
            # SIGNAL SUMMARY TABLE
            # ====================================================================
            st.subheader("📊 Signals Summary")
            df_summary = pd.DataFrame(results["summary_table"]).T
            df_summary.index.name = "Signal Type"
            st.dataframe(df_summary, width='stretch')
            st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # DETAILED SIGNAL DATA
            # ====================================================================
            st.subheader("📑 Consolidated Signal Data")
            if results["signal_data"]:
                df_signals = pd.DataFrame(results["signal_data"])
                st.dataframe(df_signals, width='stretch', height=300)
            st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # SIGNAL COUNTS WITH WIRED SPARES
            # ====================================================================
            if results["signal_spares_table"]:
                st.subheader("📊 Signal Counts with Wired Spares")
                df_signal_spares = pd.DataFrame(results["signal_spares_table"]).T
                df_signal_spares.index.name = "Signal Type"
                st.dataframe(df_signal_spares, width='stretch')
                
                grand_total = sum([row["Total"] for row in results["signal_spares_table"].values()])
                total_spares_added = sum([row["IS-Red Spares"] + row["IS-NonRed Spares"] + row["NIS-Red Spares"] + row["NIS-NonRed Spares"] for row in results["signal_spares_table"].values()])
                st.info(f"✓ Total Signals with Spares: **{grand_total}** signals (Spares added: {total_spares_added})")
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            else:
                if user_config.get("wired_spares", 0) > 0:
                    st.info("⏳ No signal data available")
                else:
                    st.info("⏳ Enter Wired Spares % to see signal counts with spares breakdown")
            
            # ====================================================================
            # AVAILABLE MODULES
            # ====================================================================
            if results["available_modules"]:
                st.subheader("🔧 Available Modules for Allocation")
                modules_data = []
                for module in results["available_modules"]:
                    modules_data.append({
                        "IO_Type": module.get("IO_Type", "-"),
                        "Module": module.get("Module", "-"),
                        "Usable_Channels": module.get("Usable_Channels", 0)
                    })
                df_modules = pd.DataFrame(modules_data)
                st.dataframe(df_modules, width='stretch')
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # MODULE ALLOCATION REQUIRED
            # ====================================================================
            if results["module_allocation_with_redundancy"]:
                st.subheader("📦 Module Allocation Required per IO Type")
                df_allocation = pd.DataFrame(results["module_allocation_with_redundancy"]).T
                df_allocation.index.name = "IO Type"
                st.dataframe(df_allocation, width='stretch')
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # MODULE SUMMARY
            # ====================================================================
            if results["module_summary"]:
                st.subheader("📈 Module Summary")
                df_summary_mods = pd.DataFrame(results["module_summary"]).T
                df_summary_mods.index.name = "IO Type"
                st.dataframe(df_summary_mods, width='stretch')
                
                total_single_mods = sum([row["Single_Modules"] for row in results["module_summary"].values() if isinstance(row.get("Single_Modules"), int)])
                total_dual_red = sum([row["Dual_Red_Modules"] for row in results["module_summary"].values() if isinstance(row.get("Dual_Red_Modules"), int)])
                total_fio_mods = sum([row["Total_FIO_Modules"] for row in results["module_summary"].values() if isinstance(row.get("Total_FIO_Modules"), int)])
                
                st.info(f"✓ **Single Modules:** {total_single_mods} | **Dual Red (before doubling):** {total_dual_red} | **Total FIO Modules:** {total_fio_mods}")
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # MODULE ALLOCATION (RACK PLACEMENT)
            # ====================================================================
            if results["rack_allocation"] and "Error" not in results["rack_allocation"]:
                st.subheader("🏗️ Module Allocation")
                
                allocation_data = []
                for node_key in sorted(results["rack_allocation"].keys()):
                    row = {"Node": node_key}
                    slots = results["rack_allocation"][node_key]
                    
                    for slot_num in range(1, 13):
                        slot_key = f"Slot-{slot_num}"
                        row[slot_key] = slots.get(slot_key, "")
                    
                    allocation_data.append(row)
                
                df_rack = pd.DataFrame(allocation_data)
                st.dataframe(df_rack, width='stretch', hide_index=True)
                
                st.success(f"✓ Modules successfully allocated to {len(results['rack_allocation'])} node(s)")
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # EXPORT OPTIONS
            # ====================================================================
            st.subheader("⬇️ Export Results")
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("Generate Processing Report"):
                    add_log("Processing report generated")
                    st.success("✓ Processing report generated successfully!")
                    st.write(f"Total signals processed: {len(results['signals'])}")
                    st.write(f"Signal types: {len(results['summary_table'])}")
            
            with col_export2:
                if st.button("Export Signals to Excel") and results["signal_data"]:
                    df_signals = pd.DataFrame(results["signal_data"])
                    output_file = "design_input_review.xlsx"
                    df_signals.to_excel(output_file, index=False)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="Download Signals Data",
                            data=f.read(),
                            file_name=output_file
                        )
                    add_log(f"Export complete: {output_file}")
        
        else:
            error_msg = results.get("error", "Unknown error occurred")
            st.error(error_msg)
            st.info("Please ensure your Excel file has the required columns: Tag, Type")

    # ====================================================================
    # LOGS SECTION (AT THE BOTTOM)
    # ====================================================================
    st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
    st.subheader("📝 Activity Logs")
    
    logs_container = st.container()
    with logs_container:
        if st.session_state.logs:
            logs_text = "\n".join(st.session_state.logs)
            st.text_area(
                "Logs",
                value=logs_text,
                height=150,
                disabled=True,
                key="logs_display"
            )
        else:
            st.info("No logs yet. Upload a file to see activity logs.")
    
    if st.button("🗑️ Clear Logs"):
        st.session_state.logs = []
        st.rerun()

# ============================================================================
# NEST LOADING & IO ASSIGNMENT MODULE
# ============================================================================
elif page == "Nest Loading & IO Assignment":
    st.header("⚙️ Nest Loading & IO Assignment")
    st.markdown("Allocate I/O signals to hardware modules and controllers")
    st.info("Coming Soon - Channel allocation logic will be implemented here")

# ============================================================================
# BILL OF MATERIALS MODULE
# ============================================================================
elif page == "Bill of Materials":
    st.header("📦 Hardware Bill of Materials")
    st.info("Coming Soon...")


# ============================================================================
# DESIGN INPUT REVIEW MODULE
# ============================================================================
if page == "Design Input Review":
    st.header("📊 Design Input Review")
    st.markdown("Review and validate design input signals from your I/O files")

    # ====================================================================
    # FILE UPLOAD (AT THE TOP)
    # ====================================================================
    st.subheader("📁 Input File (Required*)")
    
    uploaded_file = st.file_uploader(
        "Select Excel file to upload",
        type=["xlsx", "xls"],
        key="design_input_file"
    )

    if uploaded_file:
        add_log(f"File uploaded: {uploaded_file.name}")
        
        # Get column mapping first
        col_mapping = ExcelReader.get_available_columns(uploaded_file)

        # ====================================================================
        # USER CONFIGURATION OPTIONS (BELOW FILE UPLOAD)
        # ====================================================================
        st.subheader("⚙️ Configuration Options")
        
        # Quick Test Defaults Button
        col_test_btn, col_spacer = st.columns([1, 4])
        with col_test_btn:
            if st.button("🧪 Load Test Defaults", help="Quickly load test values: FIO, S2SC70D, No, Standard, 20%"):
                st.session_state['system_type_select'] = "ESD"
                st.session_state['io_types_select'] = ["FIO"]
                st.session_state['controller_model'] = "S2SC70D"
                st.session_state['explosion_protection'] = "No"
                st.session_state['temperature_rating'] = "Standard"
                st.session_state['wired_spares_input'] = 20
                add_log("✓ Test defaults loaded: FIO, S2SC70D, No, Standard, 20%")
                st.toast("✓ Test defaults loaded!", icon="✅")

        # Create columns for user input
        col1, col2, col3 = st.columns(3)

        with col1:
            system_type_label = "System Type"
            if col_mapping.get("signal_origin"):
                system_type_label += " 🟢"
                st.caption(f"System Type 🟢 (used from column: `{col_mapping['signal_origin']}`)")
            system_type = st.selectbox(
                system_type_label,
                ["Select...", "ESD", "FGS", "DCS"],
                help="Used when signal_origin column is not available",
                key="system_type_select",
                label_visibility="collapsed" if col_mapping.get("signal_origin") else "visible"
            )

        with col2:
            io_types = st.multiselect(
                "IO Types",
                ["FIO", "NIO"],
                help="Select Field I/O or Normal I/O types for this project",
                key="io_types_select"
            )

        with col3:
            controller_model = st.selectbox(
                "Controller Model",
                ["Select...", "S2SC70S", "S2SC70D", "SCS60S", "SCS60D", "SCS50S"],
                help="Select the controller model for allocation",
                key="controller_model"
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            explosion_protection = st.selectbox(
                "Explosion Protection",
                ["Select...", "Yes", "No"],
                help="Explosion protection requirement",
                key="explosion_protection"
            )

        with col5:
            temperature_rating = st.selectbox(
                "Temperature Rating",
                ["Select...", "Standard", "Wide"],
                help="Temperature rating requirement",
                key="temperature_rating"
            )

        with col6:
            wired_spares = st.number_input(
                "Wired Spares %",
                min_value=0,
                max_value=100,
                step=5,
                help="Percentage of wired spare channels (0-100)",
                key="wired_spares_input"
            )

        col7, col8 = st.columns(2)

        with col7:
            redundancy_label = "IO Redundancy"
            if col_mapping.get("io_redundancy"):
                redundancy_label += " 🟢"
                st.caption(f"IO Redundancy 🟢 (used from column: `{col_mapping['io_redundancy']}`)")
            redundancy_types = st.multiselect(
                redundancy_label,
                ["AI", "DI", "AO", "DO"],
                help="Signal types to mark as redundant",
                key="redundancy_select",
                label_visibility="collapsed" if col_mapping.get("io_redundancy") else "visible"
            )

        with col8:
            is_label = "IS/Non-IS Type"
            if col_mapping.get("is_non_is"):
                is_label += " 🟢"
                st.caption(f"IS/Non-IS Type 🟢 (used from column: `{col_mapping['is_non_is']}`)")
            is_types = st.multiselect(
                is_label,
                ["AI", "DI", "AO", "DO"],
                help="Signal types to mark as IS (Intrinsically Safe)",
                key="is_select",
                label_visibility="collapsed" if col_mapping.get("is_non_is") else "visible"
            )

        # Prepare user config dictionary
        user_config = {
            "system_type": system_type if col_mapping.get("signal_origin") is None and system_type != "Select..." else None,
            "io_types": io_types,
            "controller_model": controller_model if controller_model != "Select..." else None,
            "explosion_protection": explosion_protection if explosion_protection != "Select..." else None,
            "temperature_rating": temperature_rating if temperature_rating != "Select..." else None,
            "wired_spares": wired_spares,
            "redundancy_types": redundancy_types,
            "is_types": is_types,
        }

        st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)

        try:
            # Read the excel file
            with st.spinner("Reading file..."):
                add_log("Reading Excel file...")
                signals = ExcelReader.read(uploaded_file)
            
            add_log(f"Successfully read {len(signals)} signals")
            # ====================================================================
            # SIGNAL SUMMARY TABLE
            # ====================================================================
            st.subheader("📊 Signals Summary")
            
            # Calculate detailed signal distribution
            summary_breakdown = {}
            unclassified_count = 0
            
            for signal in signals:
                signal_type = signal.signal_type if signal.signal_type else "Unclassified"
                
                if signal.signal_type is None:
                    unclassified_count += 1
                    continue
                
                # Determine IS/Non-IS status
                is_status = "IS"
                if col_mapping.get("is_non_is") and signal.is_non_is:
                    # Use data from file
                    is_status = signal.is_non_is if signal.is_non_is.upper().startswith("IS") else "Non-IS"
                else:
                    # Use user selection
                    is_status = "IS" if signal.signal_type in user_config.get("is_types", []) else "Non-IS"
                
                # Determine Redundancy status
                redundancy_status = "Non-Redundant"
                if col_mapping.get("io_redundancy") and signal.io_redundancy:
                    # Already classified by RedundancyClassifier in excel_reader
                    redundancy_status = signal.io_redundancy
                else:
                    # Use user selection
                    redundancy_status = "Redundant" if signal.signal_type in user_config.get("redundancy_types", []) else "Non-Redundant"
                
                # Create composite key
                key = f"{signal_type}|{is_status}|{redundancy_status}"
                summary_breakdown[key] = summary_breakdown.get(key, 0) + 1

            # Build summary table with signal types as rows
            summary_table = {}
            
            for signal_type in ["AI", "DI", "DO", "AO", "SOFT"]:
                is_count = 0
                non_is_count = 0
                redundant_count = 0
                non_redundant_count = 0
                
                for key, count in summary_breakdown.items():
                    parts = key.split("|")
                    if parts[0] == signal_type:
                        if parts[1] == "IS":
                            is_count += count
                        else:
                            non_is_count += count
                        
                        if parts[2] == "Redundant":
                            redundant_count += count
                        else:
                            non_redundant_count += count
                
                total_for_type = is_count + non_is_count
                if total_for_type > 0:  # Only show signal types with at least one signal
                    summary_table[signal_type] = {
                        "IS": is_count,
                        "Non-IS": non_is_count,
                        "Redundant": redundant_count,
                        "Non-Redundant": non_redundant_count,
                        "Total": total_for_type
                    }
            
            # Add unclassified
            if unclassified_count > 0:
                summary_table["⚠ Unclassified"] = {
                    "IS": "-",
                    "Non-IS": "-",
                    "Redundant": "-",
                    "Non-Redundant": "-",
                    "Total": unclassified_count
                }
                add_log(f"WARNING: {unclassified_count} signals have unknown/unclassified type", level="WARNING")
            
            # Create dataframe
            df_summary = pd.DataFrame(summary_table).T
            df_summary.index.name = "Signal Type"
            
            # Display table
            st.dataframe(df_summary, width='stretch')
            
            total_signals = len(signals)
            add_log(f"Summary: {len(summary_table)} signal types, {total_signals} total signals")

            st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)

            # ====================================================================
            # DETAILED SIGNAL DATA WITH USER SELECTIONS APPLIED
            # ====================================================================
            st.subheader("📑 Consolidated Signal Data")
            
            # Prepare dataframe for display with user selections
            signal_data = []
            for signal in signals:
                row = {
                    "Tag": signal.tag or "-",
                    "Type": signal.signal_type if signal.signal_type else "⚠ Unclassified",
                    "PID_TAG": signal.pid_tag or "-",
                }

                # Apply user config to signals
                if col_mapping.get("signal_origin") and signal.signal_origin:
                    row["Signal Origin"] = signal.signal_origin
                else:
                    row["Signal Origin"] = user_config.get("system_type", "-")

                if col_mapping.get("io_redundancy") and signal.io_redundancy:
                    row["IO Redundancy"] = signal.io_redundancy
                else:
                    # Check if signal type is in redundancy list (only if classified)
                    redundancy_mark = signal.signal_type in user_config.get("redundancy_types", []) if signal.signal_type else False
                    row["IO Redundancy"] = "Yes" if redundancy_mark else "No"

                if col_mapping.get("is_non_is") and signal.is_non_is:
                    row["IS/Non-IS"] = signal.is_non_is
                else:
                    # Check if signal type is in IS types list (only if classified)
                    is_mark = signal.signal_type in user_config.get("is_types", []) if signal.signal_type else False
                    row["IS/Non-IS"] = "IS" if is_mark else "Non-IS"

                row["JB Cable Name"] = signal.jb_cable_name or "-"

                signal_data.append(row)
            
            df_signals = pd.DataFrame(signal_data)
            st.dataframe(df_signals, width='stretch', height=300)

            add_log(f"Displayed {len(signal_data)} signals in data table")

            st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)

            # ====================================================================
            # SIGNAL COUNTS WITH WIRED SPARES
            # ====================================================================
            wired_spares_percent = user_config.get("wired_spares", 0)
            
            if wired_spares_percent > 0:
                # Build signal counts table with spares using SignalClassifier
                signal_spares_table = SignalClassifier.build_signal_counts_table_with_spares(
                    summary_breakdown=summary_breakdown,
                    spare_percentage=wired_spares_percent
                )
            else:
                signal_spares_table = {}
            
            if signal_spares_table:
                st.subheader("📊 Signal Counts with Wired Spares")
                # Log each signal type breakdown
                for signal_type, table_row in signal_spares_table.items():
                    add_log(f"{signal_type}: IS-Red({table_row['IS-Red']})+Spares({table_row['IS-Red Spares']}) | IS-NonRed({table_row['IS-NonRed']})+Spares({table_row['IS-NonRed Spares']}) | NIS-Red({table_row['NIS-Red']})+Spares({table_row['NIS-Red Spares']}) | NIS-NonRed({table_row['NIS-NonRed']})+Spares({table_row['NIS-NonRed Spares']}) = {table_row['Total']} total")
                
                # Display table
                df_signal_spares = pd.DataFrame(signal_spares_table).T
                df_signal_spares.index.name = "Signal Type"
                st.dataframe(df_signal_spares, width='stretch')
                
                # Display summary
                grand_total = sum([row["Total"] for row in signal_spares_table.values()])
                total_spares_added = sum([row["IS-Red Spares"] + row["IS-NonRed Spares"] + row["NIS-Red Spares"] + row["NIS-NonRed Spares"] for row in signal_spares_table.values()])
                st.info(f"✓ Total Signals with Spares: **{grand_total}** signals (Spares added: {total_spares_added} @ {wired_spares_percent}%)")
                
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            elif wired_spares_percent > 0:
                st.info("⏳ No signal data available")
            else:
                st.info("⏳ Enter Wired Spares % to see signal counts with spares breakdown")

            # ====================================================================
            # AVAILABLE MODULES FOR ALLOCATION
            # ====================================================================
            selected_io_types = user_config.get("io_types", [])
            temperature_rating = user_config.get("temperature_rating")
            
            if selected_io_types and wired_spares_percent > 0:
                st.subheader("🔧 Available Modules for Allocation")
                
                try:
                    from domain.services.module_selector import ModuleSelector
                    from pathlib import Path
                    
                    # Construct path to Yokogawa constraints file
                    base_path = Path(__file__).parent.parent
                    excel_path = base_path / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
                    
                    if excel_path.exists():
                        # Get available modules
                        available_modules = ModuleSelector.get_available_modules(
                            excel_path=str(excel_path),
                            selected_io_types=selected_io_types,
                            temperature_rating=temperature_rating
                        )
                        
                        if available_modules:
                            # Create DataFrame from available modules
                            modules_data = []
                            for module in available_modules:
                                modules_data.append({
                                    "IO_Type": module.get("IO_Type", "-"),
                                    "Module": module.get("Module", "-"),
                                    "Usable_Channels": module.get("Usable_Channels", 0)
                                })
                            
                            df_modules = pd.DataFrame(modules_data)
                            st.dataframe(df_modules, width='stretch')
                            
                            add_log(f"Available modules loaded: {len(available_modules)} modules found for IO types {selected_io_types}")
                            
                            st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
                            
                            # Calculate module allocation based on signal counts + spares
                            st.subheader("📦 Module Allocation Required per IO Type")
                            
                            from domain.services.module_calculator import ModuleCalculator
                            
                            module_allocation = ModuleCalculator.calculate_module_allocation(
                                signal_spares_table=signal_spares_table,
                                available_modules=available_modules
                            )
                            
                            # Apply redundancy doubling to Red modules
                            module_allocation_with_redundancy = ModuleCalculator.apply_redundancy_doubling(
                                allocation=module_allocation
                            )
                            
                            if module_allocation_with_redundancy:
                                # Log allocation details (with redundancy applied)
                                for io_type, allocation_data in module_allocation_with_redundancy.items():
                                    if "Error" not in allocation_data:
                                        is_red = allocation_data.get("IS-Red_Modules", 0)
                                        is_nonred = allocation_data.get("IS-NonRed_Modules", 0)
                                        nis_red = allocation_data.get("NIS-Red_Modules", 0)
                                        nis_nonred = allocation_data.get("NIS-NonRed_Modules", 0)
                                        total = allocation_data.get("Modules_Required", 0)
                                        add_log(f"{io_type} (with redundancy): IS-Red({is_red}) + IS-NonRed({is_nonred}) + NIS-Red({nis_red}) + NIS-NonRed({nis_nonred}) = {total} total modules ({allocation_data['Module']})")
                                
                                # Display allocation table (with redundancy applied)
                                df_allocation = pd.DataFrame(module_allocation_with_redundancy).T
                                df_allocation.index.name = "IO Type"
                                st.dataframe(df_allocation, width='stretch')
                                
                                # Calculate module summary
                                module_summary = ModuleCalculator.calculate_module_summary(
                                    allocation_before_redundancy=module_allocation,
                                    allocation_after_redundancy=module_allocation_with_redundancy
                                )
                                
                                if module_summary:
                                    st.subheader("📈 Module Summary")
                                    
                                    # Log summary details
                                    for io_type, summary_data in module_summary.items():
                                        if "Error" not in summary_data:
                                            single_mods = summary_data.get("Single_Modules", 0)
                                            dual_red_mods = summary_data.get("Dual_Red_Modules", 0)
                                            total_fio = summary_data.get("Total_FIO_Modules", 0)
                                            add_log(f"{io_type} summary: Single({single_mods}) + Dual_Red({dual_red_mods}) = Total({total_fio}) modules")
                                    
                                    # Display summary table
                                    df_summary = pd.DataFrame(module_summary).T
                                    df_summary.index.name = "IO Type"
                                    st.dataframe(df_summary, width='stretch')
                                    
                                    # Display final summary
                                    total_single_mods = sum([row["Single_Modules"] for row in module_summary.values() if isinstance(row.get("Single_Modules"), int)])
                                    total_dual_red = sum([row["Dual_Red_Modules"] for row in module_summary.values() if isinstance(row.get("Dual_Red_Modules"), int)])
                                    total_fio_mods = sum([row["Total_FIO_Modules"] for row in module_summary.values() if isinstance(row.get("Total_FIO_Modules"), int)])
                                    
                                    st.info(f"✓ **Single Modules:** {total_single_mods} | **Dual Red (before doubling):** {total_dual_red} | **Total FIO Modules:** {total_fio_mods}")
                                    
                                    # ====================================================================
                                    # MODULE ALLOCATION (RACK PLACEMENT)
                                    # ====================================================================
                                    st.subheader("🏗️ Module Allocation")
                                    
                                    try:
                                        from domain.services.rack_allocator import RackAllocator
                                        from pathlib import Path
                                        
                                        # Get Excel path
                                        base_path = Path(__file__).parent.parent
                                        excel_path = base_path / "templates" / "Yokogawa_SIS_Constraints_Model_v3.xlsx"
                                        
                                        if excel_path.exists():
                                            # Allocate modules to rack
                                            rack_allocation = RackAllocator.allocate_modules_to_rack(
                                                excel_path=str(excel_path),
                                                module_summary=module_summary,
                                                available_modules=available_modules
                                            )
                                            
                                            if rack_allocation and "Error" not in rack_allocation:
                                                # Build allocation table
                                                allocation_data = []
                                                for node_key in sorted(rack_allocation.keys()):
                                                    row = {"Node": node_key}
                                                    slots = rack_allocation[node_key]
                                                    
                                                    # Add slots 1-12
                                                    for slot_num in range(1, 13):
                                                        slot_key = f"Slot-{slot_num}"
                                                        row[slot_key] = slots.get(slot_key, "")
                                                    
                                                    allocation_data.append(row)
                                                
                                                # Display allocation table
                                                df_rack = pd.DataFrame(allocation_data)
                                                st.dataframe(df_rack, width='stretch', hide_index=True)
                                                
                                                # Log allocation summary
                                                total_allocated = sum(1 for node in rack_allocation.values() for slot in node.values() if slot and slot != "")
                                                add_log(f"Module allocation complete: {total_allocated} slots filled across {len(rack_allocation)} nodes")
                                                
                                                st.success(f"✓ Modules successfully allocated to {len(rack_allocation)} node(s)")
                                            elif "Error" in rack_allocation:
                                                st.error(f"⚠️ {rack_allocation['Error']}")
                                                add_log(f"Rack allocation error: {rack_allocation['Error']}", level="ERROR")
                                            else:
                                                st.info("ℹ️ No allocation data generated")
                                        else:
                                            st.info("⏳ Yokogawa constraints file not found. Module allocation requires configured file.")
                                    
                                    except Exception as e:
                                        st.error(f"Error allocating modules to rack: {str(e)}")
                                        add_log(f"Error allocating modules to rack: {str(e)}", level="ERROR")
                                
                                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ No modules found matching the selected criteria")
                            add_log("No modules found for the selected IO types and temperature rating", level="WARNING")
                    else:
                        st.info("⏳ Yokogawa constraints file not found. Module selection will be available when configured.")
                        add_log(f"Module catalog not found at {excel_path}", level="WARNING")
                
                except Exception as e:
                    st.error(f"Error loading modules: {str(e)}")
                    add_log(f"Error loading modules: {str(e)}", level="ERROR")
            elif selected_io_types and wired_spares_percent == 0:
                st.info("⏳ Enter Wired Spares % to see available modules")
            elif not selected_io_types:
                st.info("⏳ Select IO Types to see available modules")

            # Export options
            st.subheader("⬇️ Export Results")
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("Generate Processing Report"):
                    add_log("Processing report generated")
                    st.success("✓ Processing report generated successfully!")
                    st.write(f"Total signals processed: {len(signals)}")
                    st.write(f"Signal types: {len(summary_table)}")

            with col_export2:
                if st.button("Export Signals to Excel"):
                    # Convert to Excel
                    add_log("Exporting signals to Excel")
                    output_file = "design_input_review.xlsx"
                    df_signals.to_excel(output_file, index=False)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="Download Signals Data",
                            data=f.read(),
                            file_name=output_file
                        )
                    add_log(f"Export complete: {output_file}")

        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            add_log(error_msg, level="ERROR")
            st.error(error_msg)
            st.info("Please ensure your Excel file has the required columns: Tag, Type")

    # ====================================================================
    # LOGS SECTION (AT THE BOTTOM)
    # ====================================================================
    st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
    st.subheader("📝 Activity Logs")
    
    # Create a scrollable logs container
    logs_container = st.container()
    with logs_container:
        if st.session_state.logs:
            logs_text = "\n".join(st.session_state.logs)
            st.text_area(
                "Logs",
                value=logs_text,
                height=150,
                disabled=True,
                key="logs_display"
            )
        else:
            st.info("No logs yet. Upload a file to see activity logs.")
    
    # Clear logs button
    if st.button("🗑️ Clear Logs"):
        st.session_state.logs = []
        st.rerun()

# ============================================================================
# NEST LOADING & IO ASSIGNMENT MODULE
# ============================================================================
elif page == "Nest Loading & IO Assignment":
    st.header("⚙️ Nest Loading & IO Assignment")
    st.markdown("Allocate I/O signals to hardware modules and controllers")

    add_log("Opened Nest Loading & IO Assignment module")

    uploaded_file = st.file_uploader(
        "Upload I/O Excel File",
        type=["xlsx", "xls"],
        key="nest_loading_file"
    )

    if uploaded_file:
        try:
            # User inputs
            col1, col2, col3 = st.columns(3)
            
            with col1:
                spare_percent = st.slider("Spare %", 0, 30, 10)
            
            with col2:
                st.write("")  # Spacing
            
            with col3:
                st.write("")  # Spacing

            if st.button("Process Allocation"):
                add_log("Starting allocation processing")
                with st.spinner("Processing..."):
                    signals = ExcelReader.read(uploaded_file)
                    add_log(f"Read {len(signals)} signals for allocation")
                    orchestrator = Orchestrator()
                    nodes = orchestrator.run(signals, spare_percent)
                    add_log(f"Allocation complete: {len(nodes)} nodes created")
                
                st.success("✓ Allocation Complete")
                
                # Show results
                st.subheader("📊 Allocation Results")
                st.metric("Total Nodes Created", len(nodes))
                
                # Download results
                if st.button("Download Allocation Results"):
                    ExcelWriter.write(nodes, "output.xlsx")
                    with open("output.xlsx", "rb") as f:
                        st.download_button(
                            label="Download Output File",
                            data=f.read(),
                            file_name="elio_allocation.xlsx"
                        )
        
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            add_log(error_msg, level="ERROR")
            st.error(error_msg)

# ============================================================================
# BILL OF MATERIALS MODULE
# ============================================================================
elif page == "Bill of Materials":
    st.header("📦 Hardware Bill of Materials")
    st.info("Coming Soon...")
    add_log("Opened Bill of Materials module")


# ============================================================================
# NEST LOADING & IO ASSIGNMENT MODULE
# ============================================================================
elif page == "Nest Loading & IO Assignment":
    st.header("⚙️ Nest Loading & IO Assignment")
    st.markdown("Allocate I/O signals to hardware modules and controllers")

    uploaded_file = st.file_uploader(
        "Upload I/O Excel File",
        type=["xlsx", "xls"],
        key="nest_loading_file"
    )

    if uploaded_file:
        try:
            # User inputs
            col1, col2, col3 = st.columns(3)
            
            with col1:
                spare_percent = st.slider("Spare %", 0, 30, 10)
            
            with col2:
                st.write("")  # Spacing
            
            with col3:
                st.write("")  # Spacing

            if st.button("Process Allocation"):
                with st.spinner("Processing..."):
                    signals = ExcelReader.read(uploaded_file)
                    orchestrator = Orchestrator()
                    nodes = orchestrator.run(signals, spare_percent)
                
                st.success("✓ Allocation Complete")
                
                # Show results
                st.subheader("📊 Allocation Results")
                st.metric("Total Nodes Created", len(nodes))
                
                # Download results
                if st.button("Download Allocation Results"):
                    ExcelWriter.write(nodes, "output.xlsx")
                    with open("output.xlsx", "rb") as f:
                        st.download_button(
                            label="Download Output File",
                            data=f.read(),
                            file_name="elio_allocation.xlsx"
                        )
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")


# ============================================================================
# BILL OF MATERIALS MODULE
# ============================================================================
elif page == "Bill of Materials":
    st.header("📦 Hardware Bill of Materials")
    st.info("Coming Soon...")