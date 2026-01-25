from abc import ABC, abstractmethod
from pathlib import Path
import logging

logger = logging.getLogger("CloudAppLogger")

class SheetProcessor(ABC):
    def __init__(self, workbook_path: Path, sheet_name: str, df_points):
        self.workbook_path = Path(workbook_path)
        self.sheet_name = sheet_name
        self.df_points = df_points

    @abstractmethod
    def process(self):
        pass

    def _save_workbook(self, wb):
        try:
            wb.save(self.workbook_path)
            logger.debug(f"Workbook saved: {self.workbook_path}")
        except Exception as e:
            logger.error(f"Failed to save workbook: {e}")
            raise
        finally:
            try:
                wb.close()
            except Exception:
                pass
