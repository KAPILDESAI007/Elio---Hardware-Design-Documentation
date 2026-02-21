SPARE_PERCENT_DEFAULT = 10
MAX_NODES_PER_CONTROLLER = 32
SLOTS_PER_NODE = 16

# ============================================================================
# EXCEL COLUMN MAPPING - Design Input Review Module
# ============================================================================
# Map excel column names to Signal model attributes
# Customize this dictionary for different excel file formats
# Add alternative column names in the list for each attribute

EXCEL_COLUMN_MAPPING = {
    # Primary identifier columns (alter for different excel formats)
    "tag": ["Tag", "PID_TAG", "pid_tag", "TagName", "tag_name"],
    "signal_type": ["Type", "signal_type", "Signal Type", "signal type"],
    
    # Design Input Review columns - Add alternative names as needed
    "pid_tag": ["PID_TAG", "PID Tag", "PID", "pid_tag"],
    "signal_origin": ["signal_origin", "Signal Origin", "Origin", "IO Source"],
    "io_redundancy": ["IO_REDUNDANCY", "IO Redundancy", "Redundancy", "io_redundancy"],
    "is_non_is": ["IS_Non_IS", "IS/Non-IS", "IS_NonIS", "Safety"],
    "jb_cable_name": ["JB_Cable_Name", "JB Cable Name", "Cable Name", "jb_cable_name"],
    "spare_channel_requirement": ["Spare Channel Requirement", "Spare Channels", "spare_channel_requirement"],
}