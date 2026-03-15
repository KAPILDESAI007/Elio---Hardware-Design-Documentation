import streamlit as st
import pandas as pd
from datetime import datetime
from infrastructure.excel_reader import ExcelReader
from services.design_input_review_service import DesignInputReviewService
from services.nest_loading_service import NestLoadingService

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
            # Store results in session state for other modules
            st.session_state.design_input_results = results
            st.session_state.uploaded_filename = uploaded_file.name
            
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
            if results["signal_data"]:
                if isinstance(results["available_modules"], pd.DataFrame) and not results["available_modules"].empty:
                    st.subheader("🔧 Available Modules for Allocation")
                    df_modules = results["available_modules"][ ["IO_Type", "Module", "Usable_Channels"] ].copy()
                    st.dataframe(df_modules, width='stretch')
                    st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
                else:
                    st.subheader("🔧 Available Modules for Allocation")
                    st.info("Available modules data format not recognized or is empty")
                    st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            else:
                st.info("⏳ No signal data available")
            
            # ====================================================================
            # MODULE ALLOCATION REQUIRED
            # ====================================================================
            if isinstance(results["module_allocation_with_redundancy"], pd.DataFrame) and not results["module_allocation_with_redundancy"].empty:
                st.subheader("📦 Module Allocation Required per IO Type")
                st.dataframe(results["module_allocation_with_redundancy"], width='stretch')
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            
            # ====================================================================
            # MODULE SUMMARY
            # ====================================================================
            if isinstance(results["module_summary"], pd.DataFrame) and not results["module_summary"].empty:
                st.subheader("📈 Module Summary")
                df_summary_mods = results["module_summary"]
                st.dataframe(df_summary_mods, width='stretch')
                
                total_single_mods = df_summary_mods["Single_Modules"].sum()
                total_dual_red = df_summary_mods["Dual_Red_Modules"].sum()
                total_fio_mods = df_summary_mods["Total_FIO_Modules"].sum()
                
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
            # SLOT ALLOCATION DETAILS (Available for Nest Loading)
            # ====================================================================
            slot_details_df = results.get("slot_allocation_details_df", None)
            
            # Debug: Show why table might be empty
            with st.expander("🔧 Debug: Slot Allocation Details Status"):
                st.write(f"**Key exists in results:** {'slot_allocation_details_df' in results}")
                st.write(f"**DataFrame is None:** {slot_details_df is None}")
                if slot_details_df is not None:
                    st.write(f"**DataFrame is empty:** {slot_details_df.empty}")
                    st.write(f"**DataFrame shape:** {slot_details_df.shape}")
                    st.write(f"**DataFrame columns:** {list(slot_details_df.columns)}")
                    if not slot_details_df.empty:
                        st.write("**First few rows:**")
                        st.dataframe(slot_details_df.head(10))
            
            if slot_details_df is not None and not slot_details_df.empty:
                st.subheader("🔍 Slot Allocation Details (Available for Channel Assignment)")
                st.caption("This table shows which slots can be used for which signal types and redundancy types in Nest Loading")
                
                # Display the detailed DataFrame
                st.dataframe(
                    slot_details_df,
                    width='stretch',
                    hide_index=True,
                    height=400
                )
                
                # Show summary using analysis results
                slot_analysis = results.get("slot_allocation_analysis", {})
                col_slot1, col_slot2, col_slot3 = st.columns(3)
                with col_slot1:
                    red_count = slot_analysis.get("redundancy_yes_count", 0)
                    st.metric("Redundant Slots", red_count)
                with col_slot2:
                    nonred_count = slot_analysis.get("redundancy_no_count", 0)
                    st.metric("Non-Redundant Slots", nonred_count)
                with col_slot3:
                    total_slots = slot_analysis.get("total_slots", 0)
                    st.metric("Total Slots", total_slots)
                
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ Slot Allocation Details not available - check debug section above")
            
            # ====================================================================
            # EXPORT OPTIONS & PROCEED
            # ====================================================================
            st.subheader("⬇️ Next Steps")
            col_export1, col_export2, col_export3 = st.columns(3)
            
            with col_export1:
                if st.button("📤 Export Signals to Excel"):
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

            with col_export2:
                if st.button("📋 Generate Report"):
                    add_log("Processing report generated")
                    st.success("✓ Report generated!")
                    st.write(f"Total signals: {len(results['signals'])}")
                    st.write(f"Signal types: {len(results['summary_table'])}")

            with col_export3:
                if st.button("➡️ Go to Nest Loading", type="primary"):
                    add_log("✓ Design Input complete - ready for Nest Loading")
                    st.success("✅ Design Input processing complete!")
                    st.info("👉 **Next:** Click **'Nest Loading & IO Assignment'** tab at the top left to assign channels to signals")
            
            # ====================================================================
            # LOGS (Even when file is uploaded)
            # ====================================================================
            with st.expander("📝 Processing Logs"):
                if st.session_state.logs:
                    st.text_area(
                        "Activity Logs",
                        value="\n".join(st.session_state.logs),
                        height=300,
                        disabled=True
                    )
                else:
                    st.info("No logs yet")
        
        else:
            error_msg = results.get("error", "Unknown error occurred")
            st.error(error_msg)
            st.info("Please ensure your Excel file has the required columns: Tag, Type")

    # ====================================================================
    # LOGS SECTION (AT THE BOTTOM) - Only shown if no file is uploaded
    # ====================================================================
    if not uploaded_file:
        st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
        st.subheader("📝 Activity Logs")
        
        logs_container = st.container()
        with logs_container:
            if st.session_state.logs:
                logs_text = "\n".join(st.session_state.logs[-20:])  # Show last 20 logs
                st.text_area(
                    "Logs",
                    value=logs_text,
                    height=150,
                    disabled=True,
                    key="logs_display"
                )
            else:
                st.info("No logs yet. Upload a file to see activity logs.")

# ============================================================================
# NEST LOADING & IO ASSIGNMENT MODULE
# ============================================================================
elif page == "Nest Loading & IO Assignment":
    st.header("⚙️ Nest Loading & IO Assignment")
    st.markdown("Allocate I/O signals to specific hardware channels")

    # Check if design input review results are available
    if "design_input_results" not in st.session_state or st.session_state.design_input_results is None:
        st.warning("⚠️ Please complete Design Input Review first")
        st.info("👉 **First:** Click **'Design Input Review'** tab at the top left to upload a file and process signals")
        st.info("""
        **Steps:**
        1. Go to 'Design Input Review' tab
        2. Upload your input file and configure options
        3. Click 'Process Design Input'
        4. Click 'Go to Nest Loading' to proceed here
        """)
    else:
        design_results = st.session_state.design_input_results
        add_log("Nest Loading & IO Assignment module opened")

        # Display design input summary
        st.subheader("📊 Design Input Summary (from Design Input Review)")
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        
        with col_sum1:
            st.metric("Total Signals", len(design_results.get("signal_data", [])))
        with col_sum2:
            total_spares = sum([row.get("Total", 0) for row in design_results.get("signal_spares_table", {}).values()])
            st.metric("Signals + Spares", total_spares)
        with col_sum3:
            module_summary = design_results.get("module_summary")
            total_mods = module_summary["Total_FIO_Modules"].sum() if isinstance(module_summary, pd.DataFrame) and not module_summary.empty else 0
            st.metric("Total FIO Modules", total_mods)

        st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)

        # Process Nest Loading
        if st.button("🔄 Process Nest Loading & Channel Assignment", type="primary"):
            with st.spinner("Processing channel allocation..."):
                try:
                    nest_results = NestLoadingService.process_nest_loading(
                        input_file=st.session_state.get("uploaded_filename", ""),
                        design_input_results=design_results,
                        logger_callback=add_log
                    )

                    if nest_results.get("status") == "success":
                        st.session_state.nest_loading_results = nest_results
                        add_log("✓ Channel allocation complete")
                        st.success("✓ Channel allocation completed successfully!")
                    else:
                        error_msg = nest_results.get("message", "Unknown error")
                        add_log(f"ERROR: {error_msg}", level="ERROR")
                        st.error(f"Error: {error_msg}")

                except Exception as e:
                    error_msg = str(e)
                    add_log(f"EXCEPTION: {error_msg}", level="ERROR")
                    st.error(f"Exception: {error_msg}")

        # Display results if available
        if "nest_loading_results" in st.session_state and st.session_state.nest_loading_results.get("status") == "success":
            results = st.session_state.nest_loading_results
            
            # Display allocation summary
            st.subheader("📊 Allocation Results")
            summary = results.get("allocation_summary", {})
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Allocated", summary.get("allocated_signals", 0))
            with col2:
                st.metric("Unallocated", summary.get("unallocated_signals", 0))
            with col3:
                st.metric("Nodes Used", summary.get("nodes_used", 0))
            with col4:
                st.metric("Allocation %", f"{summary.get('allocation_percentage', 0):.1f}%")
            with col5:
                st.metric("Total Signals", summary.get("total_signals", 0))

            # Display signals with allocation
            st.subheader("📋 Signals with Node, Slot & Channel Assignment")
            signals_df = results.get("signals_with_allocation", pd.DataFrame())
            
            if not signals_df.empty:
                # Select columns to display - remove old duplicate columns (IO Redundancy, IS/Non-IS)
                # Keep only: metadata (PID_TAG, Tag, Type), derived columns (IS, Redundancy), allocation (Node, Slot, Channel, Module)
                display_columns = ['PID_TAG', 'Tag', 'Type', 'IS', 'Redundancy', 'Node', 'Slot', 'Channel', 'Module']
                available_cols = [col for col in display_columns if col in signals_df.columns]
                
                st.dataframe(
                    signals_df[available_cols],
                    width='stretch',
                    hide_index=True,
                    height=400
                )

                # Option to download
                st.markdown("<hr style='margin: 0.1rem 0;'>", unsafe_allow_html=True)
                col_down1, col_down2 = st.columns([1, 4])
                with col_down1:
                    csv = signals_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Allocation",
                        data=csv,
                        file_name="nest_loading_allocation.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("No signal allocation data available")

            # Display unallocated signals if any
            unallocated = results.get("unallocated_signals", [])
            if unallocated:
                st.warning(f"⚠️ {len(unallocated)} signals could not be allocated:")
                st.write(", ".join(unallocated[:10]))  # Show first 10
                if len(unallocated) > 10:
                    st.write(f"... and {len(unallocated) - 10} more")


# ============================================================================
# BILL OF MATERIALS MODULE
# ============================================================================
elif page == "Bill of Materials":
    st.header("📦 Hardware Bill of Materials")
    st.info("Coming Soon...")
