# Cloud App Projects - Design Input Review & IO Assignment System

## Overview
This project is a Flask-based web application for managing Nest Loading, IO Assignment, and Design Input Review for ESD (Electrical Safety Development) systems.

## Core Application Structure

### Root Level Files
- **app.py** - Flask web application with REST API endpoints
- **main.py** - Command-line entry point for batch processing
- **config.py** - Configuration and path management
- **logger_config.py** - Logging setup

### Core Business Logic
- **Design Input Review.py** - Main intelligence for design review, module assignment, and IO configuration

### Processing Modules (`processors/`)
- **__init__.py** - Main processor classes (PIDTagFiller, ModuleNameAdder, StationWriter, ModuleDetailsFiller)
- **pid_tag_filler.py** - Fills PID tags into worksheets
- **module_name_adder.py** - Adds module names to front loading sheets
- **station_writer.py** - Writes station information to worksheets
- **sheet_processor.py** - Base class for sheet processing
- **channel_assignment_manager.py** - Manages IO channel assignments and redundancy
- **module_mapper.py** - Maps modules to system configuration

### Excel Utilities (`excel/`)
- **excel_manager.py** - Excel file manipulation and formatting

### Web Interface
- **templates/** - HTML templates for the Flask web interface
- **static/** - CSS, JavaScript, and static assets
- **uploads/** - Temporary upload folder (generated at runtime)
- **logs/** - Application logs (generated at runtime)

## Running the Application

### Web Interface
```bash
python app.py
```
Launches Flask server at http://localhost:5000

### Command Line Processing
```bash
python main.py
```
Processes input files based on configuration in `config.py`

## Development & Testing

All test scripts, debug utilities, and development documentation have been organized in the **`dev_tools/`** folder:

- **tests/** - Unit and integration tests (test_*.py files)
- **debug_tools/** - Debugging scripts and validation utilities
- **analysis_scripts/** - Analysis and reporting scripts
- **documentation/** - Detailed documentation and design decisions (*.md files)

## Key Dependencies
- Flask - Web framework
- pandas - Data processing
- openpyxl - Excel file handling
- pathlib - Path management
- logging - Application logging

## File Organization Philosophy
- **Root directory**: Only essential production code
- **dev_tools/**: All development, testing, and documentation files
- **processors/**: Modular processing logic
- **excel/**: External system integrations

---
*Last updated: February 2026 - Project cleaned and optimized for production readiness*
