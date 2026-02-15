import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
import re
from pathlib import Path
import sys

# Get the current directory
current_dir = Path(__file__).parent
project_dir = current_dir.parent

# Add project dir to path
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Import all classes from processors.py in the same directory
import importlib.util

processors_file = current_dir / "processors.py"
spec = importlib.util.spec_from_file_location("processors_module", processors_file)
processors_module = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(processors_module)
    
    # Export classes
    PIDTagFiller = processors_module.PIDTagFiller
    ModuleNameAdder = processors_module.ModuleNameAdder
    StationWriter = processors_module.StationWriter
    ModuleDetailsFiller = processors_module.ModuleDetailsFiller
    AssignmentBuilder = processors_module.AssignmentBuilder
    ModuleMapper = processors_module.ModuleMapper
    
except Exception as e:
    raise ImportError(f"Failed to import processors module: {e}")

# Import ExcelOutputGenerator from excel_output module
from .excel_output import ExcelOutputGenerator

__all__ = [
    'PIDTagFiller',
    'ModuleNameAdder',
    'StationWriter',
    'ModuleDetailsFiller',
    'AssignmentBuilder',
    'ModuleMapper',
    'ExcelOutputGenerator'
]
