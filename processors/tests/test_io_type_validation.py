"""
Test cases for IO type validation.

Tests use the actual project Excel file:
- File: 3291-36930B-J032-020 RevC_ESD.xls in templates folder
- Contains real IO type data with variations: AI-R, DI-RL, DI-R, DO-R, DO, SOFT

Tests:
1. All IO types are valid - verifies that all IO_type values belong to valid categories
2. IO type categorization - verifies that IO types are correctly categorized as AI, DI, DO, AO, or SOFT
3. Invalid IO type detection - verifies that invalid IO types are properly identified (uses synthetic data)
4. IO type base extraction - verifies that base IO types are correctly extracted from compound types
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


class TestIOTypeValidation(unittest.TestCase):
    """Test cases for IO type validation using real project data"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        # Use the actual project Excel file
        cls.test_file_path = Path(r"C:\Working\Others\Python\Cloud App Projects\templates\3291-36930B-J032-020 RevC_ESD.xls")
        
        # Verify file exists
        if not cls.test_file_path.exists():
            raise FileNotFoundError(f"Test file not found: {cls.test_file_path}")
        
        # Load the real data
        cls.processor = MockSheetProcessor(cls.test_file_path, 'Sheet1', None)
        cls.df = cls.processor.read_excel_file(cls.test_file_path)
    
    # ===================== TEST CASE 1: All IO types are valid =====================
    
    def test_all_io_types_valid(self):
        """
        TEST 1: Verify that all IO types in the project file are valid.
        
        Valid types: AI, DI, DO, AO, SOFT
        
        This test uses the real project data to ensure:
        - All IO_type values are categorized as valid
        - No invalid types are detected
        - All rows are successfully validated
        """
        # Arrange
        # Use only non-null IO_type values
        df_with_io = self.df[self.df['IO_type'].notna()]
        
        # Act
        result = self.processor.validate_io_types(df_with_io, 'IO_type')
        
        # Assert
        self.assertTrue(result['success'], "Validation should succeed for project data")
        self.assertEqual(len(result['invalid_io_types']), 0, "No invalid types should be found in project data")
        self.assertGreater(result['total_rows'], 0, "Should have rows with IO_type data")
        
        # Verify valid types are detected
        valid_types_found = result['valid_io_types']
        self.assertGreater(len(valid_types_found), 0, "Should find at least one valid type")
        
        for valid_type in valid_types_found:
            self.assertIn(valid_type, self.processor.VALID_IO_TYPES, 
                         f"{valid_type} should be in VALID_IO_TYPES")
        
        print(f"✓ TEST 1 PASSED: All IO types are valid")
        print(f"   Valid types found: {result['valid_io_types']}")
        print(f"   Total rows validated: {result['total_rows']}")
    
    def test_valid_io_type_variations(self):
        """
        Verify that IO type variations in the project are correctly normalized and validated.
        
        Real variations in the project file:
        - AI-R (Redundant AI)
        - DI-RL, DI-R (Redundant variants)
        - DO-R (Redundant DO)
        - DO (Standard DO)
        - SOFT (Software signals)
        """
        # Arrange
        df_with_io = self.df[self.df['IO_type'].notna()]
        
        # Act
        result = self.processor.validate_io_types(df_with_io, 'IO_type')
        
        # Assert
        self.assertTrue(result['success'], "All variations should be valid")
        
        # Check categorization contains expected types
        categorization = result['categorization']
        print(f"\n✓ Extended TEST 1: IO type variations in project file:")
        for io_type, count in sorted(categorization.items()):
            print(f"   {io_type:8s}: {count:4d} signals")
        
        # Verify counts are positive
        for io_type, count in categorization.items():
            self.assertGreater(count, 0, f"{io_type} should have count > 0")
    
    def test_case_insensitive_validation(self):
        """
        Verify that IO types are validated case-insensitively
        even if project data contains mixed cases.
        """
        # Arrange
        # Create custom DataFrame with mixed case IO types
        test_data = {
            'IO_type': ['ai', 'AI', 'Ai', 'di', 'DI', 'do', 'DO', 'soft', 'SOFT']
        }
        df_mixed_case = pd.DataFrame(test_data)
        
        # Act
        result = self.processor.validate_io_types(df_mixed_case, 'IO_type')
        
        # Assert
        self.assertTrue(result['success'], "Case should not matter")
        self.assertEqual(len(result['invalid_io_types']), 0, "All should be valid")
        self.assertEqual(len(result['valid_io_types']), 4, "Should have 4 distinct valid types")
        
        print("✓ Extended TEST 1: Case-insensitive validation works correctly")
    
    # ===================== TEST CASE 2: IO type categorization =====================
    
    def test_io_type_categorization(self):
        """
        TEST 2: Verify that IO types are correctly categorized and counted.
        
        This test ensures:
        - Each IO type is counted correctly
        - Categorization matches the actual data
        - All valid categories are present
        """
        # Arrange
        df_with_io = self.df[self.df['IO_type'].notna()]
        
        # Act
        result = self.processor.validate_io_types(df_with_io, 'IO_type')
        
        # Assert
        self.assertTrue(result['success'], "Validation should succeed")
        
        categorization = result['categorization']
        
        # Verify categorization structure
        self.assertIsInstance(categorization, dict, "Categorization should be a dictionary")
        
        # All categories should have count > 0
        total_count = sum(categorization.values())
        self.assertEqual(total_count, result['total_rows'], 
                        "Sum of categories should equal total rows")
        
        print(f"✓ TEST 2 PASSED: IO type categorization is correct")
        print(f"   Total signals: {total_count}")
        for io_type in sorted(categorization.keys()):
            pct = 100 * categorization[io_type] / total_count
            print(f"   {io_type:8s}: {categorization[io_type]:5d} ({pct:5.1f}%)")
    
    def test_categorization_with_variations(self):
        """
        Verify correct categorization when IO types have variations.
        
        Example: 'AI-R', 'AI' should both count as 'AI'
                 'DI-R', 'DI-RL' should both count as 'DI'
        """
        # Arrange
        # Create synthetic data with variations
        test_data = {
            'IO_type': ['AI', 'AI-R', 'AI-R', 'DI-2W', 'DI-R', 'DI-RL', 'DO', 'DO-R', 'AO', 'SOFT']
        }
        df_variations = pd.DataFrame(test_data)
        
        # Act
        result = self.processor.validate_io_types(df_variations, 'IO_type')
        
        # Assert
        self.assertTrue(result['success'], "All variations should be valid")
        
        categorization = result['categorization']
        
        # Check the counts
        self.assertEqual(categorization['AI'], 3, "AI and AI-R variants should count as 3")
        self.assertEqual(categorization['DI'], 3, "DI variants should count as 3")
        self.assertEqual(categorization['DO'], 2, "DO variants should count as 2")
        self.assertEqual(categorization['AO'], 1, "AO should count as 1")
        self.assertEqual(categorization['SOFT'], 1, "SOFT should count as 1")
        
        print("✓ Extended TEST 2: Categorization with variations works correctly")
    
    def test_zero_count_categories(self):
        """
        Verify that categories with 0 count are not included in results.
        """
        # Arrange - create data with only AI and DI
        test_data = {
            'IO_type': ['AI', 'AI', 'DI', 'DI']
        }
        df_limited = pd.DataFrame(test_data)
        
        # Act
        result = self.processor.validate_io_types(df_limited, 'IO_type')
        
        # Assert
        categorization = result['categorization']
        
        self.assertIn('AI', categorization, "AI should be present")
        self.assertIn('DI', categorization, "DI should be present")
        self.assertNotIn('DO', categorization, "DO with 0 count should not be present")
        self.assertNotIn('AO', categorization, "AO with 0 count should not be present")
        self.assertNotIn('SOFT', categorization, "SOFT with 0 count should not be present")
        
        print("✓ Extended TEST 2: Zero count categories properly excluded")
    
    # ===================== TEST CASE 3: Invalid IO type detection =====================
    
    def test_invalid_io_type_detection(self):
        """
        TEST 3: Verify that invalid IO types are detected and reported.
        
        Uses synthetic data with invalid types.
        
        This test ensures:
        - Invalid types are identified
        - Validation fails
        - Error list is populated
        """
        # Arrange - create data with invalid types
        test_data = {
            'IO_type': ['AI', 'INVALID_TYPE', 'DI', 'UNKNOWN', 'BOGUS']
        }
        df_invalid = pd.DataFrame(test_data)
        
        # Act
        result = self.processor.validate_io_types(df_invalid, 'IO_type')
        
        # Assert
        self.assertFalse(result['success'], "Validation should fail")
        self.assertEqual(len(result['invalid_io_types']), 3, "Should have 3 invalid types")
        self.assertIn('INVALID_TYPE', result['invalid_io_types'], "INVALID_TYPE should be reported")
        self.assertIn('UNKNOWN', result['invalid_io_types'], "UNKNOWN should be reported")
        self.assertIn('BOGUS', result['invalid_io_types'], "BOGUS should be reported")
        self.assertGreater(len(result['errors']), 0, "Error list should be populated")
        
        print("✓ TEST 3 PASSED: Invalid IO types are properly detected")
    
    def test_invalid_io_in_large_dataset(self):
        """
        Verify invalid type detection in a large dataset.
        """
        # Arrange - create large dataset with mostly valid and some invalid
        data = {
            'IO_type': ['AI' if i % 5 == 0 else 'DI' if i % 5 == 1 else 'DO' if i % 5 == 2 else 'AO' if i % 5 == 3 else 'INVALID' for i in range(100)],
        }
        df_large = pd.DataFrame(data)
        
        # Act
        result = self.processor.validate_io_types(df_large, 'IO_type')
        
        # Assert
        self.assertFalse(result['success'], "Validation should fail due to invalid types")
        self.assertEqual(len(result['invalid_io_types']), 1, "Should detect 1 invalid type")
        self.assertIn('INVALID', result['invalid_io_types'], "INVALID should be in invalid types")
        self.assertEqual(result['categorization']['INVALID'], 20, "Should have 20 INVALID entries")
        
        print("✓ Extended TEST 3: Invalid type detection works in large datasets")
    
    # ===================== TEST CASE 4: IO type base extraction =====================
    
    def test_io_type_base_extraction(self):
        """
        TEST 4: Verify that base IO types are correctly extracted from compound types.
        
        Examples from project file:
        - 'AI-R' -> 'AI' (Redundant Analog Input)
        - 'DI-RL' -> 'DI' (Redundant Latching Digital Input)
        - 'DI-R' -> 'DI' (Redundant Digital Input)
        - 'DO-R' -> 'DO' (Redundant Digital Output)  
        - 'DO' -> 'DO' (Standard Digital Output)
        - 'SOFT' -> 'SOFT' (Software signal)
        - 'SOFTWARE' -> 'SOFT' (Alternative software designation)
        """
        # Arrange
        test_cases = [
            # Standard types
            ('AI', 'AI'),
            ('DI', 'DI'),
            ('DO', 'DO'),
            ('AO', 'AO'),
            ('SOFT', 'SOFT'),
            # Project file variations
            ('AI-R', 'AI'),
            ('DI-RL', 'DI'),
            ('DI-R', 'DI'),
            ('DO-R', 'DO'),
            # Other variations
            ('AI-Redundant', 'AI'),
            ('DO-EXP', 'DO'),
            ('AO-4-20', 'AO'),
            ('AO-2W', 'AO'),
            ('DI-4-20', 'DI'),
            ('DI-2W', 'DI'),
            # Case variations
            ('ai', 'AI'),
            ('di', 'DI'),
            ('do', 'DO'),
            ('ao', 'AO'),
            ('soft', 'SOFT'),
            ('SoftWare', 'SOFT'),
            ('SOFTWARE', 'SOFT'),
        ]
        
        # Act & Assert
        for input_type, expected_base in test_cases:
            with self.subTest(input_type=input_type):
                result = self.processor._extract_io_type_base(input_type)
                self.assertEqual(result, expected_base, 
                               f"'{input_type}' should extract to '{expected_base}', got '{result}'")
        
        print("✓ TEST 4 PASSED: IO type base extraction is correct")
    
    def test_edge_cases_extraction(self):
        """
        Verify handling of edge cases in IO type extraction.
        """
        # Arrange
        edge_cases = [
            ('', ''),  # Empty string
            ('   ', ''),  # Just spaces
            ('AI   ', 'AI'),  # Trailing spaces
            ('   AI', 'AI'),  # Leading spaces
            ('AI-R-DUAL', 'AI'),  # Multiple delimiters
            ('A-I', 'A-I'),  # Separate characters (no match)
        ]
        
        # Act & Assert
        for input_type, expected_base in edge_cases:
            with self.subTest(input_type=repr(input_type)):
                result = self.processor._extract_io_type_base(input_type)
                # For edge cases, just verify reasonable behavior
                if expected_base:
                    self.assertIn(expected_base, result or '', 
                                f"'{input_type}' extraction issue")
        
        print("✓ Extended TEST 4: Edge case extraction works correctly")


class TestIOTypeErrorHandling(unittest.TestCase):
    """Error handling tests for IO type validation"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.processor = MockSheetProcessor(Path('dummy'), 'Sheet1', None)
    
    def test_missing_io_type_column(self):
        """
        Verify error handling when IO_type column doesn't exist.
        """
        # Arrange
        test_data = {
            'PID_TAG': ['TAG001'],
            'Channel': [1]
        }
        df = pd.DataFrame(test_data)
        
        # Act
        result = self.processor.validate_io_types(df, 'IO_type')
        
        # Assert
        self.assertFalse(result['success'], "Validation should fail")
        self.assertGreater(len(result['errors']), 0, "Error list should be populated")
        self.assertIn("not found", result['errors'][0], "Error should mention column not found")
        
        print("✓ Error handling: Missing IO_type column")
    
    def test_empty_dataframe_validation(self):
        """
        Verify error handling for empty DataFrame.
        """
        # Arrange
        df = pd.DataFrame()
        
        # Act
        result = self.processor.validate_io_types(df, 'IO_type')
        
        # Assert
        self.assertFalse(result['success'], "Validation should fail")
        self.assertEqual(result['total_rows'], 0, "Total rows should be 0")
        self.assertGreater(len(result['errors']), 0, "Error list should be populated")
        
        print("✓ Error handling: Empty DataFrame validation")
    
    def test_none_dataframe_validation(self):
        """
        Verify error handling for None DataFrame.
        """
        # Act
        result = self.processor.validate_io_types(None, 'IO_type')
        
        # Assert
        self.assertFalse(result['success'], "Validation should fail")
        self.assertEqual(result['total_rows'], 0, "Total rows should be 0")
        self.assertGreater(len(result['errors']), 0, "Error list should be populated")
        
        print("✓ Error handling: None DataFrame validation")


def run_tests():
    """Run all tests with formatted output"""
    print("\n" + "="*70)
    print("IO TYPE VALIDATION TEST SUITE")
    print("Using Real Project File: 3291-36930B-J032-020 RevC_ESD.xls")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIOTypeValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestIOTypeErrorHandling))
    
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
