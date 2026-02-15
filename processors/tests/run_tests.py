"""
Test runner for all processor tests.

Run different test suites or all tests together.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest

def run_all_tests():
    """Run all test suites"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Discover and add all tests
    tests = loader.discover('.', pattern='test_*.py')
    suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_excel_tests():
    """Run only Excel file read tests"""
    from test_excel_read import TestExcelFileRead, TestExcelFileIntegration
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestExcelFileRead))
    suite.addTests(loader.loadTestsFromTestCase(TestExcelFileIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_io_type_tests():
    """Run only IO type validation tests"""
    from test_io_type_validation import TestIOTypeValidation, TestIOTypeErrorHandling
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestIOTypeValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestIOTypeErrorHandling))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run processor tests')
    parser.add_argument('--suite', choices=['all', 'excel', 'io_type'], 
                       default='all', help='Which test suite to run')
    args = parser.parse_args()
    
    if args.suite == 'excel':
        success = run_excel_tests()
    elif args.suite == 'io_type':
        success = run_io_type_tests()
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)
