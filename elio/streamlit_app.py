import streamlit as st
import pandas as pd
from infrastructure.excel_reader import ExcelReader
from infrastructure.excel_writer import ExcelWriter
from core.orchestrator import Orchestrator

st.set_page_config(page_title="ELIO Enterprise", layout="wide")

st.title("ELIO Enterprise - Hardware Design & Documentation")

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

    # File upload
    uploaded_file = st.file_uploader(
        "Upload I/O Excel File",
        type=["xlsx", "xls"],
        key="design_input_file"
    )

    if uploaded_file:
        try:
            # Read the excel file
            with st.spinner("Reading file..."):
                signals = ExcelReader.read(uploaded_file)
            
            st.success(f"✓ Successfully read {len(signals)} signals")

            # Display Column Detection Info
            st.subheader("📋 Column Detection")
            col_mapping = ExcelReader.get_available_columns(uploaded_file)
            
            with st.expander("View detected columns", expanded=False):
                st.write("**Column Mapping Results:**")
                for attr, column in col_mapping.items():
                    status = "✓" if column else "✗"
                    st.write(f"{status} **{attr}**: {column if column else 'Not found'}")

            # Display Signals Summary
            st.subheader("📊 Signals Summary")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Signals", len(signals))
            with col2:
                signal_types = list(set(s.signal_type for s in signals))
                st.metric("Signal Types", len(signal_types))
            with col3:
                with_pidtag = sum(1 for s in signals if s.pid_tag)
                st.metric("With PID Tags", with_pidtag)

            # Display detailed signal data
            st.subheader("📑 Signal Details")
            
            # Prepare dataframe for display
            signal_data = []
            for signal in signals:
                signal_data.append({
                    "Tag": signal.tag,
                    "Type": signal.signal_type,
                    "PID_TAG": signal.pid_tag or "-",
                    "Signal Origin": signal.signal_origin or "-",
                    "IO Redundancy": signal.io_redundancy or "-",
                    "IS/Non-IS": signal.is_non_is or "-",
                    "JB Cable Name": signal.jb_cable_name or "-",
                    "Spare Requirement": signal.spare_channel_requirement or "-",
                })
            
            df_signals = pd.DataFrame(signal_data)
            st.dataframe(df_signals, use_container_width=True)

            # Download processed signals
            st.subheader("⬇️ Export Results")
            if st.button("Generate Processing Report"):
                # You can add more processing here
                st.write("Processing report generated successfully!")

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            st.info("Please ensure your Excel file has the required columns: Tag, Type")


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