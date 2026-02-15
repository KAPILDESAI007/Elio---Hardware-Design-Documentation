"""
Input Data Analysis Module

Analyzes user input data (instrument DataFrame) to:
1. Count total signals for each IO type
2. Calculate wired spare counts for each IO type
3. Generate summary analysis table
"""

import pandas as pd
import logging
from typing import Dict, Tuple, Optional
from pathlib import Path
import sys

logger = logging.getLogger("CloudAppLogger")


class InputDataAnalyzer:
    """Analyzes instrument data and wired spare requirements"""
    
    VALID_IO_TYPES = ['AI', 'DI', 'DO', 'AO', 'SOFT']
    SKIP_IO_TYPES = ['SOFT']  # SOFT signals don't require hardware
    
    def __init__(self, df_instruments: pd.DataFrame, wired_spares_percentage: Optional[float] = None):
        """
        Initialize analyzer with instrument data.
        
        Args:
            df_instruments: DataFrame with instrument data (must have IO_type_base column)
            wired_spares_percentage: Percentage of wired spares to calculate (0-100)
        """
        self.df_instruments = df_instruments
        self.wired_spares_percentage = wired_spares_percentage
        
        self.signal_counts = {}
        self.wired_spares_counts = {}
        self.total_signal_counts = {}
        self.analysis_table = pd.DataFrame()
        
        logger.info(f"InputDataAnalyzer initialized with {len(df_instruments)} instrument records")
        if wired_spares_percentage:
            logger.info(f"Wired spares percentage: {wired_spares_percentage}%")
    
    def count_signals_by_io_type(self) -> Dict[str, int]:
        """
        Count total signals for each IO type.
        
        Returns:
            Dictionary mapping IO_type_base to signal count
        """
        self.signal_counts = {}
        
        if self.df_instruments is None or self.df_instruments.empty:
            logger.warning("DataFrame is empty")
            return self.signal_counts
        
        if 'IO_type_base' not in self.df_instruments.columns:
            logger.error("IO_type_base column not found")
            return self.signal_counts
        
        for io_type_base in self.df_instruments['IO_type_base'].unique():
            if pd.isna(io_type_base):
                continue
            
            io_type_str = str(io_type_base).upper().strip()
            count = len(self.df_instruments[self.df_instruments['IO_type_base'] == io_type_base])
            self.signal_counts[io_type_str] = count
            logger.info(f"Signal count - {io_type_str}: {count}")
        
        return self.signal_counts
    
    def calculate_wired_spares(self) -> Dict[str, int]:
        """
        Calculate wired spare count for each IO type.
        
        Wired spares are calculated as percentage of signals, excluding SOFT signals.
        Rounding is done using standard rounding (2.5+ rounds up).
        
        Returns:
            Dictionary mapping IO_type_base to wired spare count
        """
        self.wired_spares_counts = {}
        
        if not self.signal_counts:
            self.count_signals_by_io_type()
        
        if self.wired_spares_percentage is None or self.wired_spares_percentage <= 0:
            logger.info("No wired spares percentage provided")
            return self.wired_spares_counts
        
        logger.info(f"Calculating wired spares at {self.wired_spares_percentage}%")
        
        for io_type, signal_count in self.signal_counts.items():
            # Skip SOFT signals - no hardware required
            if io_type in self.SKIP_IO_TYPES:
                logger.info(f"Skipping {io_type} (no hardware required)")
                continue
            
            # Calculate spare count with proper rounding
            spare_count_float = signal_count * (self.wired_spares_percentage / 100)
            spare_count = round(spare_count_float)
            
            self.wired_spares_counts[io_type] = spare_count
            logger.info(f"Wired spares - {io_type}: {signal_count} signals × {self.wired_spares_percentage}% = {spare_count_float:.2f} → {spare_count}")
        
        return self.wired_spares_counts
    
    def generate_analysis_table(self) -> pd.DataFrame:
        """
        Generate analysis table with signal counts and totals.
        
        Returns:
            DataFrame with columns: IO_Type, Signal_Count, Wired_Spares, Total_Count
        """
        if not self.signal_counts:
            self.count_signals_by_io_type()
        
        if self.wired_spares_percentage and self.wired_spares_percentage > 0:
            if not self.wired_spares_counts:
                self.calculate_wired_spares()
        
        # Build analysis table
        rows = []
        total_signals = 0
        total_spares = 0
        total_all = 0
        
        for io_type in sorted(self.signal_counts.keys()):
            signal_count = self.signal_counts[io_type]
            spare_count = self.wired_spares_counts.get(io_type, 0)
            total_count = signal_count + spare_count
            
            rows.append({
                'IO_Type': io_type,
                'Signal_Count': signal_count,
                'Wired_Spares': spare_count,
                'Total_Count': total_count
            })
            
            total_signals += signal_count
            total_spares += spare_count
            total_all += total_count
        
        # Add totals row
        rows.append({
            'IO_Type': 'TOTAL',
            'Signal_Count': total_signals,
            'Wired_Spares': total_spares,
            'Total_Count': total_all
        })
        
        self.analysis_table = pd.DataFrame(rows)
        
        logger.info("Analysis table generated:")
        logger.info(f"\n{self.analysis_table.to_string(index=False)}")
        
        return self.analysis_table
    
    def get_signal_count_by_io_type(self, io_type: str) -> int:
        """
        Get signal count for a specific IO type.
        
        Args:
            io_type: IO type (e.g., 'AI', 'DI', 'DO')
        
        Returns:
            Signal count or 0 if not found
        """
        if not self.signal_counts:
            self.count_signals_by_io_type()
        
        return self.signal_counts.get(io_type.upper(), 0)
    
    def get_wired_spare_count_by_io_type(self, io_type: str) -> int:
        """
        Get wired spare count for a specific IO type.
        
        Args:
            io_type: IO type (e.g., 'AI', 'DI', 'DO')
        
        Returns:
            Wired spare count or 0 if not found
        """
        if not self.wired_spares_counts:
            self.calculate_wired_spares()
        
        return self.wired_spares_counts.get(io_type.upper(), 0)
    
    def get_total_count_by_io_type(self, io_type: str) -> int:
        """
        Get total count (signals + spares) for a specific IO type.
        
        Args:
            io_type: IO type (e.g., 'AI', 'DI', 'DO')
        
        Returns:
            Total count (signals + spares)
        """
        io_type_upper = io_type.upper()
        signal_count = self.get_signal_count_by_io_type(io_type_upper)
        spare_count = self.get_wired_spare_count_by_io_type(io_type_upper)
        return signal_count + spare_count
    
    def get_analysis_summary(self) -> Dict:
        """
        Get summary of analysis.
        
        Returns:
            Dictionary with summary statistics
        """
        if self.analysis_table.empty:
            self.generate_analysis_table()
        
        totals_row = self.analysis_table[self.analysis_table['IO_Type'] == 'TOTAL'].iloc[0]
        
        return {
            'total_signals': int(totals_row['Signal_Count']),
            'total_wired_spares': int(totals_row['Wired_Spares']),
            'total_all': int(totals_row['Total_Count']),
            'wired_spares_percentage': self.wired_spares_percentage or 0,
            'analysis_table': self.analysis_table
        }


# ===================== TEST CASES =====================

import unittest


class TestInputDataAnalyzer(unittest.TestCase):
    """Test cases for InputDataAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create sample instrument data
        self.test_data = {
            'PID_TAG': ['TAG001', 'TAG002', 'TAG003', 'TAG004', 'TAG005', 
                       'TAG006', 'TAG007', 'TAG008', 'TAG009', 'TAG010'],
            'IO_type': ['AI', 'AI', 'DI', 'DI', 'DI', 'DO', 'AO', 'SOFT', 'SOFT', 'SOFT'],
            'IO_type_base': ['AI', 'AI', 'DI', 'DI', 'DI', 'DO', 'AO', 'SOFT', 'SOFT', 'SOFT']
        }
        self.df = pd.DataFrame(self.test_data)
    
    # ===================== TEST 1: Count signals by IO type =====================
    
    def test_count_signals_basic(self):
        """TEST 1: Count total signals for each IO type"""
        analyzer = InputDataAnalyzer(self.df)
        signal_counts = analyzer.count_signals_by_io_type()
        
        # Verify counts
        self.assertEqual(signal_counts['AI'], 2)
        self.assertEqual(signal_counts['DI'], 3)
        self.assertEqual(signal_counts['DO'], 1)
        self.assertEqual(signal_counts['AO'], 1)
        self.assertEqual(signal_counts['SOFT'], 3)
        
        print("✓ TEST 1 PASSED: Signal counts are correct")
    
    def test_count_signals_excludes_null(self):
        """TEST 1 Extended: Null IO types are excluded"""
        test_data_with_null = {
            'PID_TAG': self.test_data['PID_TAG'] + ['TAG011'],
            'IO_type': self.test_data['IO_type'] + ['AI'],
            'IO_type_base': self.test_data['IO_type_base'] + [None]
        }
        
        df_with_null = pd.DataFrame(test_data_with_null)
        analyzer = InputDataAnalyzer(df_with_null)
        signal_counts = analyzer.count_signals_by_io_type()
        
        # Should not include None in counts
        self.assertNotIn(None, signal_counts)
        self.assertEqual(sum(signal_counts.values()), 10)  # Still 10 valid signals
        
        print("✓ Extended TEST 1: Null values properly excluded")
    
    def test_count_signals_empty_dataframe(self):
        """TEST 1 Error handling: Empty DataFrame"""
        empty_df = pd.DataFrame()
        analyzer = InputDataAnalyzer(empty_df)
        signal_counts = analyzer.count_signals_by_io_type()
        
        self.assertEqual(len(signal_counts), 0)
        print("✓ Error handling: Empty DataFrame returns empty dict")
    
    # ===================== TEST 2: Calculate wired spares =====================
    
    def test_calculate_wired_spares_20_percent(self):
        """TEST 2: Calculate wired spares at 20% (standard case)"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        analyzer.count_signals_by_io_type()
        spares = analyzer.calculate_wired_spares()
        
        # Expected: AI(2)*20% = 0.4 → 0, DI(3)*20% = 0.6 → 1, DO(1)*20% = 0.2 → 0, AO(1)*20% = 0.2 → 0
        # Note: SOFT should be skipped
        self.assertEqual(spares['AI'], 0)
        self.assertEqual(spares['DI'], 1)
        self.assertEqual(spares['DO'], 0)
        self.assertEqual(spares['AO'], 0)
        self.assertNotIn('SOFT', spares)  # SOFT not in wired spares
        
        print("✓ TEST 2 PASSED: Wired spares calculated at 20%")
    
    def test_calculate_wired_spares_rounding_2_6(self):
        """TEST 2: Proper rounding - 2.6 rounds to 3"""
        # Create data where 10 signals * 26% = 2.6 → 3
        test_data = {
            'PID_TAG': [f'TAG{i:03d}' for i in range(10)],
            'IO_type_base': ['AI'] * 10
        }
        df_test = pd.DataFrame(test_data)
        
        analyzer = InputDataAnalyzer(df_test, wired_spares_percentage=26)
        analyzer.count_signals_by_io_type()
        spares = analyzer.calculate_wired_spares()
        
        # 10 * 26% = 2.6 → 3
        self.assertEqual(spares['AI'], 3)
        print("✓ Extended TEST 2: 2.6 correctly rounds to 3")
    
    def test_calculate_wired_spares_rounding_2_4(self):
        """TEST 2: Proper rounding - 2.4 rounds to 2"""
        # Create data where 10 signals * 24% = 2.4 → 2
        test_data = {
            'PID_TAG': [f'TAG{i:03d}' for i in range(10)],
            'IO_type_base': ['DI'] * 10
        }
        df_test = pd.DataFrame(test_data)
        
        analyzer = InputDataAnalyzer(df_test, wired_spares_percentage=24)
        analyzer.count_signals_by_io_type()
        spares = analyzer.calculate_wired_spares()
        
        # 10 * 24% = 2.4 → 2
        self.assertEqual(spares['DI'], 2)
        print("✓ Extended TEST 2: 2.4 correctly rounds to 2")
    
    def test_calculate_wired_spares_2_5_rounds_to_2(self):
        """TEST 2: Proper rounding - 2.5 rounds to 2 (banker's rounding)"""
        # Create data where 10 signals * 25% = 2.5
        test_data = {
            'PID_TAG': [f'TAG{i:03d}' for i in range(10)],
            'IO_type_base': ['DO'] * 10
        }
        df_test = pd.DataFrame(test_data)
        
        analyzer = InputDataAnalyzer(df_test, wired_spares_percentage=25)
        analyzer.count_signals_by_io_type()
        spares = analyzer.calculate_wired_spares()
        
        # 10 * 25% = 2.5 → 2 (banker's rounding)
        self.assertEqual(spares['DO'], 2)
        print("✓ Extended TEST 2: 2.5 correctly rounds to 2 (banker's rounding)")
    
    def test_calculate_wired_spares_skips_soft(self):
        """TEST 2: SOFT signals are excluded from wired spares"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        analyzer.count_signals_by_io_type()
        spares = analyzer.calculate_wired_spares()
        
        # SOFT should not appear in wired spares
        self.assertNotIn('SOFT', spares)
        self.assertIn('AI', spares)  # But other types should be present
        
        print("✓ Extended TEST 2: SOFT signals correctly excluded")
    
    def test_calculate_wired_spares_no_percentage(self):
        """TEST 2: No wired spares when percentage is None"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=None)
        analyzer.count_signals_by_io_type()
        spares = analyzer.calculate_wired_spares()
        
        self.assertEqual(len(spares), 0)
        print("✓ Extended TEST 2: No spares when percentage is None")
    
    # ===================== TEST 3: Generate analysis table =====================
    
    def test_analysis_table_structure(self):
        """TEST 3: Analysis table has correct structure and values"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        table = analyzer.generate_analysis_table()
        
        # Check columns
        expected_cols = ['IO_Type', 'Signal_Count', 'Wired_Spares', 'Total_Count']
        self.assertEqual(list(table.columns), expected_cols)
        
        # Check last row is TOTAL
        last_row = table.iloc[-1]
        self.assertEqual(last_row['IO_Type'], 'TOTAL')
        
        # Check totals
        self.assertEqual(last_row['Signal_Count'], 10)
        self.assertEqual(last_row['Wired_Spares'], 1)
        self.assertEqual(last_row['Total_Count'], 11)
        
        print("✓ TEST 3 PASSED: Analysis table structure and values correct")
    
    def test_analysis_table_totals_row(self):
        """TEST 3 Extended: Totals row sums are correct"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=30)
        table = analyzer.generate_analysis_table()
        
        totals = table[table['IO_Type'] == 'TOTAL'].iloc[0]
        
        # Sum of Signal_Count column (excluding TOTAL row)
        signal_sum = table[table['IO_Type'] != 'TOTAL']['Signal_Count'].sum()
        self.assertEqual(totals['Signal_Count'], signal_sum)
        
        # Sum of Total_Count (excluding TOTAL row)
        total_sum = table[table['IO_Type'] != 'TOTAL']['Total_Count'].sum()
        self.assertEqual(totals['Total_Count'], total_sum)
        
        print("✓ Extended TEST 3: Totals row correctly sums all rows")
    
    def test_analysis_table_no_spares(self):
        """TEST 3 Extended: Table correct when no wired spares"""
        analyzer = InputDataAnalyzer(self.df)
        table = analyzer.generate_analysis_table()
        
        # All Wired_Spares should be 0
        non_total_rows = table[table['IO_Type'] != 'TOTAL']
        self.assertTrue((non_total_rows['Wired_Spares'] == 0).all())
        
        # Total and Signal count should be the same for each row
        for _, row in non_total_rows.iterrows():
            self.assertEqual(row['Signal_Count'], row['Total_Count'])
        
        print("✓ Extended TEST 3: No spares case handled correctly")
    
    # ===================== TEST 4: Query methods =====================
    
    def test_get_signal_count_by_io_type(self):
        """TEST 4: Get signal count for specific IO type"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        
        self.assertEqual(analyzer.get_signal_count_by_io_type('AI'), 2)
        self.assertEqual(analyzer.get_signal_count_by_io_type('DI'), 3)
        self.assertEqual(analyzer.get_signal_count_by_io_type('SOFT'), 3)
        self.assertEqual(analyzer.get_signal_count_by_io_type('DO'), 1)
        
        print("✓ TEST 4.1 PASSED: Get signal count by IO type")
    
    def test_get_wired_spare_count_by_io_type(self):
        """TEST 4: Get wired spare count for specific IO type"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        
        self.assertEqual(analyzer.get_wired_spare_count_by_io_type('AI'), 0)
        self.assertEqual(analyzer.get_wired_spare_count_by_io_type('DI'), 1)
        self.assertEqual(analyzer.get_wired_spare_count_by_io_type('SOFT'), 0)  # Excluded
        
        print("✓ TEST 4.2 PASSED: Get wired spare count by IO type")
    
    def test_get_total_count_by_io_type(self):
        """TEST 4: Get total count (signals + spares) for specific IO type"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        
        self.assertEqual(analyzer.get_total_count_by_io_type('AI'), 2)  # 2 + 0
        self.assertEqual(analyzer.get_total_count_by_io_type('DI'), 4)  # 3 + 1
        self.assertEqual(analyzer.get_total_count_by_io_type('SOFT'), 3)  # 3 + 0
        
        print("✓ TEST 4.3 PASSED: Get total count by IO type")
    
    def test_get_analysis_summary(self):
        """TEST 4: Get analysis summary"""
        analyzer = InputDataAnalyzer(self.df, wired_spares_percentage=20)
        summary = analyzer.get_analysis_summary()
        
        self.assertEqual(summary['total_signals'], 10)
        self.assertEqual(summary['total_wired_spares'], 1)
        self.assertEqual(summary['total_all'], 11)
        self.assertEqual(summary['wired_spares_percentage'], 20)
        self.assertIsInstance(summary['analysis_table'], pd.DataFrame)
        
        print("✓ TEST 4.4 PASSED: Get analysis summary")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*70)
    print("INPUT DATA ANALYZER TEST SUITE")
    print("="*70 + "\n")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInputDataAnalyzer)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
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
    success = run_all_tests()
    exit(0 if success else 1)
