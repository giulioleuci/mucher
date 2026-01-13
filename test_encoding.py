#!/usr/bin/env python3
"""Test script to identify encoding issues in Excel files."""

import sys
import pandas as pd

def analyze_excel_encoding(filepath):
    """Analyze an Excel file for potential encoding issues."""
    print(f"Analyzing: {filepath}\n")

    try:
        # Try to read the Excel file
        excel_file = pd.ExcelFile(filepath)
        sheets = excel_file.sheet_names
        print(f"Found {len(sheets)} sheets: {sheets}\n")

        for sheet in sheets:
            print(f"=== Sheet: {sheet} ===")
            df = excel_file.parse(sheet, header=None)

            # Check each cell for potential encoding issues
            for row_idx, row in df.iterrows():
                for col_idx, cell in enumerate(row):
                    if pd.notna(cell):
                        cell_str = str(cell)
                        try:
                            # Try to encode to UTF-8
                            cell_str.encode('utf-8')
                        except UnicodeEncodeError as e:
                            print(f"  ❌ Encoding error at row {row_idx}, col {col_idx}")
                            print(f"     Content: {repr(cell_str[:100])}")
                            print(f"     Error: {e}\n")

                        # Check for suspicious characters
                        for i, char in enumerate(cell_str):
                            if ord(char) > 127 and ord(char) not in range(0x00A0, 0x0180):
                                # Non-ASCII, non-Latin-1 extended character
                                if i == 0 or i % 100 == 0:  # Report only first or every 100th
                                    print(f"  ⚠️  Non-standard char at row {row_idx}, col {col_idx}, pos {i}")
                                    print(f"     Char: {repr(char)} (U+{ord(char):04X})")
                                    print(f"     Context: {repr(cell_str[max(0,i-10):i+10])}\n")

            print()

        print("✅ Analysis complete - file can be read")
        return True

    except UnicodeDecodeError as e:
        print(f"❌ UTF-8 Decode Error: {e}")
        print(f"   This suggests the Excel file contains invalid UTF-8 bytes")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_encoding.py <excel_file.xlsx>")
        sys.exit(1)

    filepath = sys.argv[1]
    success = analyze_excel_encoding(filepath)
    sys.exit(0 if success else 1)
