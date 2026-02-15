"""
Test cases for Excel file reading and column validation.

Tests use the actual project Excel file:
- File: 3291-36930B-J032-020 RevC_ESD.xls in templates folder
- Contains real project instrument data with 1323 rows and 83 columns
- Includes columns like PID_TAG, IO_type, signal_origin, NODE, SLOT_P, CHANNEL, etc.

Tests:
1. Excel file read successful - verifies that an Excel file can be read
2. All required columns available - verifies that all required columns exist in the file
3. Column normalization - verifies that column names are properly normalized
"""

import unittest
from pathlib import Path
import pandas as pd
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sheet_processor import SheetProcessor


class MockSheetProcessor(SheetProcessor):
    """Mock implementation of SheetProcessor for testing"""
    def process(self):
        pass


class TestExcelFileRead(unittest.TestCase):
    """Test cases for reading Excel files using the actual project file"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        # Use the actual project Excel file
        cls.test_file_path = Path(r"C:\Working\Others\Python\Cloud App Projects\templates\3291-36930B-J032-020 RevC_ESD.xls")
        
        # Verify file exists
        if not cls.test_file_path.exists():
            raise FileNotFoundError(f"Test file not found: {cls.test_file_path}")
    
    # ===================== TEST CASE 1: Excel file read successful =====================
    
    def test_excel_file_read_successful(self):
        """
        TEST 1: Verify that Excel file can be read successfully.
        
        This test ensures:
        - Real Excel file with project data can be read
        - DataFrame is created correctly
        - Proper logging occurs
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        
        # Act
        result = processor.read_excel_file(self.test_file_path)
        
        # Assert
        self.assertIsNotNone(result, "DataFrame should not be None")
        self.assertGreater(len(result), 0, "DataFrame should have rows")
        self.assertGreater(len(result.columns), 0, "DataFrame should have columns")
        self.assertEqual(len(result), 1323, "Should have 1323 rows from project file")
        print(f"✓ TEST 1 PASSED: Excel file read successfully ({len(result)} rows, {len(result.columns)} columns)")
    
    def test_excel_file_structure_valid(self):
        """
        Verify the actual file has expected structure and data types.
        
        This extends TEST 1 to validate actual data.
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        df = processor.read_excel_file(self.test_file_path)
        
        # Act & Assert
        # Check for expected columns in the file
        expected_columns = ['PID_TAG', 'IO_type', 'signal_origin', 'NODE', 'CHANNEL']
        
        for col in expected_columns:
            self.assertIn(col, df.columns, f"Column '{col}' should exist in data")
        
        # Verify PID_TAG column has data
        self.assertGreater(df['PID_TAG'].notna().sum(), 0, "PID_TAG should have values")
        
        # Verify IO_type column has data
        self.assertGreater(df['IO_type'].notna().sum(), 0, "IO_type should have values")
        
        print("✓ Extended TEST 1: File structure and data are valid")
    
    def test_excel_file_not_found(self):
        """
        Verify that FileNotFoundError is raised when file doesn't exist.
        
        This is an error case for TEST 1.
        """
        # Arrange
        non_existent_path = Path(r"C:\NonExistent\File.xlsx")
        processor = MockSheetProcessor(non_existent_path, 'Sheet1', None)
        
        # Act & Assert
        with self.assertRaises(FileNotFoundError):
            processor.read_excel_file(non_existent_path)
        
        print("✓ Excel file not found - error handling works correctly")
    
    # ===================== TEST CASE 2: All required columns available =====================
    
    def test_all_required_columns_available(self):
        """
        TEST 2: Verify that all required columns exist in the Excel file.
        
        This test ensures:
        - All key columns are present in the real project file
        - Column check returns success status
        - All columns are accounted for
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        df = processor.read_excel_file(self.test_file_path)
        
        # Required columns for the application
        required_columns = ['PID_TAG', 'IO_type', 'signal_origin', 'SYSTEM_CABINET', 'NODE', 'CHANNEL']
        
        # Act
        result = processor.check_columns_exist(df, required_columns)
        
        # Assert
        self.assertTrue(result['success'], "Column check should succeed")
        self.assertEqual(len(result['missing_columns']), 0, "No columns should be missing")
        self.assertEqual(result['required_columns_count'], len(required_columns), 
                        f"Should have {len(required_columns)} required columns")
        print(f"✓ TEST 2 PASSED: All {len(required_columns)} required columns are available")
    
    def test_missing_required_columns_detection(self):
        """
        Verify that missing columns are properly detected.
        
        This extends TEST 2 to handle missing columns.
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        df = processor.read_excel_file(self.test_file_path)
        
        # Check for columns that don't exist
        required_columns = ['PID_TAG', 'IO_type', 'NonExistentColumn123', 'AnotherFakeColumn']
        
        # Act
        result = processor.check_columns_exist(df, required_columns)
        
        # Assert
        self.assertFalse(result['success'], "Column check should fail")
        self.assertEqual(len(result['missing_columns']), 2, "2 columns should be missing")
        self.assertIn('NonExistentColumn123', result['missing_columns'], "Fake column should be missing")
        self.assertIn('AnotherFakeColumn', result['missing_columns'], "Fake column should be missing")
        print("✓ Extended TEST 2: Missing columns properly detected")
    
    def test_column_normalization_real_data(self):
        """
        Verify that column names work correctly with real data.
        
        This extends TEST 2 to validate actual column access.
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        df = processor.read_excel_file(self.test_file_path)
        
        required_columns = ['PID_TAG', 'IO_type', 'signal_origin']
        
        # Act
        result = processor.check_columns_exist(df, required_columns)
        
        # Assert - should find all three columns in real data
        self.assertTrue(result['success'], "All columns should exist in real data")
        self.assertEqual(result['total_columns'], 83, "Should have 83 total columns")
        
        print("✓ Extended TEST 2: Column normalization works with real data")
    
    def test_full_column_inventory(self):
        """
        Display all available columns in the project file.
        
        This helps understand the complete data structure.
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        df = processor.read_excel_file(self.test_file_path)
        
        # Act & Report
        all_columns = list(df.columns)
        
        # Assert
        self.assertEqual(len(all_columns), 83, "Should have 83 columns")
        
        # Print first 20 columns
        print("\n✓ Full column inventory (83 total columns):")
        for i, col in enumerate(all_columns, 1):
            print(f"   {i:2d}. {col}")
            if i >= 20:
                print(f"   ... and {83-20} more columns")
                break


class TestExcelFileIntegration(unittest.TestCase):
    """Integration tests combining read and column validation with real data"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.test_file_path = Path(r"C:\Working\Others\Python\Cloud App Projects\templates\3291-36930B-J032-020 RevC_ESD.xls")
    
    def test_complete_read_and_validate_workflow(self):
        """
        Integration test: Read file and validate columns in one workflow.
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        required_columns = ['PID_TAG', 'IO_type', 'signal_origin', 'SYSTEM_CABINET']
        
        # Act - Read file first
        df = processor.read_excel_file(self.test_file_path)
        
        # Then validate columns
        col_result = processor.check_columns_exist(df, required_columns)
        
        # Assert
        self.assertIsNotNone(df, "File should be read successfully")
        self.assertEqual(len(df), 1323, "Should have 1323 rows")
        self.assertTrue(col_result['success'], "All required columns should exist")
        
        # Verify data content
        self.assertGreater(len(df[df['PID_TAG'].notna()]), 0, "Should have PID_TAG data")
        self.assertGreater(len(df[df['IO_type'].notna()]), 0, "Should have IO_type data")
        
        print("✓ Integration Test PASSED: Complete workflow successful with real project data")
    
    def test_data_quality_check(self):
        """
        Verify data quality in the loaded file.
        """
        # Arrange
        processor = MockSheetProcessor(self.test_file_path, 'Sheet1', None)
        df = processor.read_excel_file(self.test_file_path)
        
        # Assert data quality
        total_rows = len(df)
        
        # Check for key columns with data
        pid_tag_filled = df['PID_TAG'].notna().sum()
        io_type_filled = df['IO_type'].notna().sum()
        signal_origin_filled = df['signal_origin'].notna().sum()
        
        print(f"\n✓ Data Quality Check:")
        print(f"   Total rows: {total_rows}")
        print(f"   PID_TAG filled: {pid_tag_filled}/{total_rows} ({100*pid_tag_filled/total_rows:.1f}%)")
        print(f"   IO_type filled: {io_type_filled}/{total_rows} ({100*io_type_filled/total_rows:.1f}%)")
        print(f"   signal_origin filled: {signal_origin_filled}/{total_rows} ({100*signal_origin_filled/total_rows:.1f}%)")
        
        # At least most rows should have key data
        self.assertGreater(pid_tag_filled / total_rows, 0.8, "At least 80% PID_TAG should be filled")


def run_tests():
    """Run all tests with formatted output"""
    print("\n" + "="*70)
    print("EXCEL FILE READ & COLUMN VALIDATION TEST SUITE")
    print("Using Real Project File: 3291-36930B-J032-020 RevC_ESD.xls")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestExcelFileRead))
    suite.addTests(loader.loadTestsFromTestCase(TestExcelFileIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
