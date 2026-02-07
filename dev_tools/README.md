# Development Tools - Index

This folder contains all development, testing, and documentation files that are not part of the core production application.

## Directory Structure

### 📋 tests/ (33 unit and integration tests)
Test files for validating system functionality:
- `test_app_assignment.py` - Flask app route tests
- `test_channel_assignment_manager.py` - Channel assignment logic tests
- `test_wired_spares*.py` - Wired spares calculation tests
- `test_blank_channels_fix.py` - Blank channel handling tests
- `test_channel_redundancy.py` - Redundancy logic tests
- `test_extraction.py` - Data extraction validation
- `test_requirement_*.py` - Requirement validation tests
- Plus 20+ other specific functionality tests

**To run tests:**
```bash
python -m pytest tests/
# or individual test:
python tests/test_channel_assignment_manager.py
```

### 🔧 debug_tools/ (15 debug and analysis scripts)
Debug utilities and validation tools:
- `check_*.py` - Check specific system aspects (capacity, assignments, spares, etc.)
- `debug_*.py` - Debug specific features (redundancy, IO assignment, wired spares)
- `diagnostic_*.py` - Diagnostic analysis scripts
- `verify_*.py` - Verification utilities
- `validate_*.py` - Validation tools

**Usage:** These are utility scripts for troubleshooting and inspection during development.

### 📊 analysis_scripts/ (7 analysis tools)
Analysis and reporting utilities:
- `analyze_unassigned.py` - Analyze unassigned IO channels
- `capacity_analysis.py` - Analyze system capacity
- `quick_check_modules.py` - Quick module verification
- `quick_test.py` - Quick functionality test
- `run_review.py` - Run design review process
- `simple_test_spares.py` - Test spare calculations
- `WIRED_SPARES_COMPARISON.py` - Compare wired spare implementations

### 📚 documentation/ (54 documentation files)
Comprehensive project documentation, implementation guides, and design decisions:

**Reference Guides:**
- `00_START_HERE.md` - Project overview and quick start
- `README.md` - Full project documentation
- `QUICK_REFERENCE.md` - Quick reference guide
- `QUICK_START_GUIDE.md` - Getting started guide
- `INDEX.md` - Documentation index

**Technical Documentation:**
- `TECHNICAL_IMPLEMENTATION_REFERENCE.md` - Implementation details
- `SIGNAL_TYPES_EXPLANATION.md` - Signal type documentation
- `CONSTRAINT_IMPLEMENTATION_VERIFICATION.md` - Constraint details
- `CHANNEL_ASSIGNMENT_MANAGER_GUIDE.md` - Channel manager guide
- `CHANNEL_REDUNDANCY_IMPLEMENTATION.md` - Redundancy implementation

**Implementation Records:**
- `CODE_CHANGES_SUMMARY.md` - Summary of code changes
- `IMPLEMENTATION_CHECKLIST.md` - Implementation checklist
- `DEPLOYMENT_CHECKLIST.md` - Deployment verification
- `CONSTRAINT_**` files - Constraint implementation tracking

**Fix Documentation:**
- `FIX_DOCUMENTATION.md` - Documentation of fixes applied
- `FIXES_SUMMARY.md` - Summary of fixes
- `WIRED_SPARES_**` files - Wired spares fix documentation
- `ROOT_CAUSE_ANALYSIS.md` - Root cause analysis
- Various `FINAL_**` and `RESOLUTION_**` files

**Design & Analysis:**
- `VISUAL_*.md` - Visual diagrams and comparisons
- `REFACTORING_*.md` - Refactoring discussions and plans
- `ON_PAGE_SUMMARY.md` - One-page summary
- Plus project completion and status reports

**Generated Output Files:**
- `Design Input Review_*.xlsx` - Generated sample output files

## Cleanup Notes

✅ **What was moved:**
- 33 test files (test_*.py)
- 7 analysis scripts (quick_*.py, analyze_*.py, capacity_*.py, etc.)
- 15 debug/check utilities (debug_*.py, check_*.py, verify_*.py, validate_*.py)
- 54 documentation files (*.md files)
- Generated output files and text logs

✅ **What remains in root (production code):**
- `app.py` - Flask web application
- `main.py` - Command-line entry point
- `config.py` - Configuration
- `logger_config.py` - Logging setup
- `Design Input Review.py` - Core business logic
- `processors/` - Processing modules
- `excel/` - Excel utilities
- `templates/` - Web templates (HTML)
- `static/` - Web assets (CSS, JS)

## Quick Start for Development

If you need to:

1. **Run the web application:**
   ```bash
   python app.py
   ```

2. **Run tests:**
   ```bash
   # Navigate to dev_tools/tests
   cd dev_tools/tests
   python test_channel_assignment_manager.py
   ```

3. **Check system capacity:**
   ```bash
   python dev_tools/debug_tools/check_capacity.py
   ```

4. **Read documentation:**
   - Start with `documentation/00_START_HERE.md`
   - Reference `documentation/QUICK_REFERENCE.md` for specific topics

## Important
These development files are kept for reference and testing but are **not imported** by the production code. The clean root directory ensures the main application is focused and maintainable.
