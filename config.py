from pathlib import Path

PROJECT_DIR = Path(r"C:\Working\Others\Python\Cloud App Projects")
TEMPLATE_PATH = PROJECT_DIR / "templates" / "FrontNestLoading_Template.xlsx"
OUTPUT_FILE = PROJECT_DIR / "494-ESD-06XF.xlsx"
CUSTOMER_FILE = PROJECT_DIR / "3291-36930B-J032-020 RevC_ESD.xls"
UPLOAD_FOLDER = PROJECT_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
LOGS_FOLDER = PROJECT_DIR / "logs"
LOGS_FOLDER.mkdir(exist_ok=True)
