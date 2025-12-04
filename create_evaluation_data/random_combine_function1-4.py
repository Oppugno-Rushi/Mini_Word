#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Random Function Combination Generator for MiniWord
Generates random combinations of functions from 2 to 4 functions in sequence.
Only specific functions can be the first function in each combination.
"""

import json
import random
import itertools
from typing import List, Tuple

class MiniWordFunctionCombiner:
    def __init__(self, json_file_path: str = "explainations_for_botton.json"):
        self.json_file_path = json_file_path
        self.all_functions = []
        self.first_functions = [
            "New Document",
            "Open Document", 
            "Template Library"
        ]
        # Functions to exclude from all combinations
        self.excluded_functions = [
            "Print Document",
            "Refresh Page", 
            "Close Page",
            "Open New Tab",
            "Toggle Pagination",
            "Print Preview",
            "Toggle Sidebar",
            "Focus Mode",
            "Find Text"
        ]
        # Functions that can only appear once and must be last
        self.last_only_functions = ["Save Document"]
        # Functions that can only appear once in each combination
        self.single_use_functions = ["New Document", "Open Document", "Template Library"]
        # Mutually exclusive function groups
        self.mutually_exclusive_groups = [
            ["Bulleted List", "Numbered List"],
            ["Left Align", "Center Align", "Right Align", "Justify Align"]
        ]
        self.load_functions()
    
    def is_valid_combination(self, combination: List[str]) -> bool:
        """Check if a combination follows all the constraints"""
        if not combination:
            return False
        
        # Check if first function is valid
        if combination[0] not in self.first_functions:
            return False
        
        # Check for single-use functions (can only appear once)
        for func in self.single_use_functions:
            if combination.count(func) > 1:
                return False
        
        # Check for last-only functions (must be last if present)
        for func in self.last_only_functions:
            if func in combination and combination[-1] != func:
                return False
        
        # Check for mutually exclusive groups
        for group in self.mutually_exclusive_groups:
            group_functions_in_combo = [func for func in group if func in combination]
            if len(group_functions_in_combo) > 1:
                return False
        
        # Check for "Paste Content" constraint
        if "Paste Content" in combination:
            paste_index = combination.index("Paste Content")
            # Check if any of the required functions come before "Paste Content"
            required_before_paste = ["Cut Content", "Direct Copy", "Formatted Copy"]
            has_required_before = any(func in combination[:paste_index] for func in required_before_paste)
            if not has_required_before:
                return False
        
        # Check for "Format Painter" constraint
        if "Format Painter" in combination and "Clear All Formatting" in combination:
            format_painter_index = combination.index("Format Painter")
            clear_format_index = combination.index("Clear All Formatting")
            if format_painter_index > clear_format_index:
                return False
        
        # Check for "Insert Chart" constraint (must come after "Insert Table")
        if "Insert Chart" in combination:
            if "Insert Table" not in combination:
                return False
            chart_index = combination.index("Insert Chart")
            table_index = combination.index("Insert Table")
            if chart_index <= table_index:
                return False
        
        # Check for "Share Document" constraint (must be last)
        if "Share Document" in combination:
            if combination[-1] != "Share Document":
                return False
        
        return True
    
    def load_functions(self):
        """Load all function names from the JSON file"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract all function names from all sections
            for section_name, section_data in data['MiniWord_Button_Documentation']['sections'].items():
                if 'buttons' in section_data:
                    for button in section_data['buttons']:
                        if 'name' in button:
                            function_name = button['name']
                            # Only add if not in excluded functions
                            if function_name not in self.excluded_functions:
                                self.all_functions.append(function_name)
            
            print(f"✓ Loaded {len(self.all_functions)} functions from JSON (after filtering)")
            print(f"✓ Excluded {len(self.excluded_functions)} functions: {', '.join(self.excluded_functions)}")
            print(f"✓ Available first functions: {len(self.first_functions)}")
            
        except Exception as e:
            print(f"✗ Error loading functions: {e}")
            self.all_functions = []
    
    def generate_two_function_combinations(self, num_combinations: int = 100) -> List[List[str]]:
        """Generate random combinations with 2 functions each"""
        combinations = []
        attempts = 0
        max_attempts = num_combinations * 10  # Prevent infinite loops
        
        while len(combinations) < num_combinations and attempts < max_attempts:
            attempts += 1
            # Randomly select first function from first_functions
            first_func = random.choice(self.first_functions)
            # Randomly select second function from all_functions (excluding first)
            remaining_functions = [f for f in self.all_functions if f != first_func]
            if remaining_functions:
                second_func = random.choice(remaining_functions)
                combination = [first_func, second_func]
                if self.is_valid_combination(combination) and combination not in combinations:
                    combinations.append(combination)
        
        return combinations
    
    def generate_three_function_combinations(self, num_combinations: int = 800) -> List[List[str]]:
        """Generate random combinations with 3 functions each"""
        combinations = []
        attempts = 0
        max_attempts = num_combinations * 10  # Prevent infinite loops
        
        while len(combinations) < num_combinations and attempts < max_attempts:
            attempts += 1
            # Randomly select first function from first_functions
            first_func = random.choice(self.first_functions)
            # Randomly select second function from all_functions (excluding first)
            remaining_after_first = [f for f in self.all_functions if f != first_func]
            if remaining_after_first:
                second_func = random.choice(remaining_after_first)
                # Randomly select third function from all_functions (excluding first two)
                remaining_after_second = [f for f in self.all_functions if f not in [first_func, second_func]]
                if remaining_after_second:
                    third_func = random.choice(remaining_after_second)
                    combination = [first_func, second_func, third_func]
                    if self.is_valid_combination(combination) and combination not in combinations:
                        combinations.append(combination)
        
        return combinations
    
    def generate_four_function_combinations(self, num_combinations: int = 1200) -> List[List[str]]:
        """Generate random combinations with 4 functions each"""
        combinations = []
        attempts = 0
        max_attempts = num_combinations * 10  # Prevent infinite loops
        
        while len(combinations) < num_combinations and attempts < max_attempts:
            attempts += 1
            # Randomly select first function from first_functions
            first_func = random.choice(self.first_functions)
            # Randomly select second function from all_functions (excluding first)
            remaining_after_first = [f for f in self.all_functions if f != first_func]
            if remaining_after_first:
                second_func = random.choice(remaining_after_first)
                # Randomly select third function from all_functions (excluding first two)
                remaining_after_second = [f for f in self.all_functions if f not in [first_func, second_func]]
                if remaining_after_second:
                    third_func = random.choice(remaining_after_second)
                    # Randomly select fourth function from all_functions (excluding first three)
                    remaining_after_third = [f for f in self.all_functions if f not in [first_func, second_func, third_func]]
                    if remaining_after_third:
                        fourth_func = random.choice(remaining_after_third)
                        combination = [first_func, second_func, third_func, fourth_func]
                        if self.is_valid_combination(combination) and combination not in combinations:
                            combinations.append(combination)
        
        return combinations
    
    def generate_all_combinations(self) -> dict:
        """Generate ALL possible combinations with constraints"""
        print("🎯 Generating 2100 random function combinations with constraints...")
        print("=" * 70)
        print("📋 Target distribution:")
        print("   • Two Functions: 100 combinations")
        print("   • Three Functions: 800 combinations")
        print("   • Four Functions: 1200 combinations")
        print("   • Total: 2100 combinations")
        print("=" * 70)
        print("📋 Constraints applied:")
        print("   • No duplicate functions within each combination")
        print("   • First functions: New Document, Open Document, Template Library")
        print("   • Single-use functions (once per combination): New Document, Open Document, Template Library")
        print("   • Last-only functions: Save Document (can only be last step)")
        print("   • Mutually exclusive groups:")
        print("     - Bulleted List OR Numbered List (not both)")
        print("     - Left Align OR Center Align OR Right Align OR Justify Align (only one)")
        print("   • Paste Content requires: Cut Content, Direct Copy, or Formatted Copy before it")
        print("   • Format Painter cannot come after Clear All Formatting")
        print("   • Insert Chart must come after Insert Table")
        print("   • Share Document can only be last")
        print("   • Excluded functions: Print Document, Refresh Page, Close Page, Open New Tab,")
        print("     Toggle Pagination, Print Preview, Toggle Sidebar, Focus Mode, Find Text")
        print("=" * 70)
        
        all_combinations = {
            "two_functions": self.generate_two_function_combinations(100),
            "three_functions": self.generate_three_function_combinations(800),
            "four_functions": self.generate_four_function_combinations(1200)
        }
        
        return all_combinations
    
    def print_combinations(self, combinations: dict):
        """Print all combinations in a formatted way"""
        print("\n🎉 Generated Function Combinations:")
        print("=" * 60)
        
        for combo_type, combo_list in combinations.items():
            print(f"\n📋 {combo_type.replace('_', ' ').title()} ({len(combo_list)} combinations):")
            print("-" * 50)
            
            for i, combo in enumerate(combo_list, 1):
                combo_str = " → ".join(combo)
                print(f"{i:2d}. {combo_str}")
    
    def save_combinations_to_file(self, combinations: dict, output_file: str = "function_combinations.txt"):
        """Save combinations to a text file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("MiniWord Function Combinations\n")
                f.write("=" * 50 + "\n\n")
                
                for combo_type, combo_list in combinations.items():
                    f.write(f"{combo_type.replace('_', ' ').title()} ({len(combo_list)} combinations):\n")
                    f.write("-" * 50 + "\n")
                    
                    for i, combo in enumerate(combo_list, 1):
                        combo_str = " → ".join(combo)
                        f.write(f"{i:2d}. {combo_str}\n")
                    f.write("\n")
            
            print(f"✓ Combinations saved to: {output_file}")
            
        except Exception as e:
            print(f"✗ Error saving combinations: {e}")
    
    def get_statistics(self, combinations: dict):
        """Get statistics about the generated combinations"""
        total_combinations = sum(len(combo_list) for combo_list in combinations.values())
        unique_first_functions = set()
        
        for combo_list in combinations.values():
            for combo in combo_list:
                if combo:  # Check if combo is not empty
                    unique_first_functions.add(combo[0])
        
        print(f"\n📊 Statistics:")
        print(f"   Total combinations: {total_combinations}")
        print(f"   Unique first functions used: {len(unique_first_functions)}")
        print(f"   Available first functions: {len(self.first_functions)}")
        print(f"   All available functions: {len(self.all_functions)}")


def main():
    """Main function to run the combination generator"""
    print("🎯 MiniWord Function Combination Generator - 2100 RANDOM COMBINATIONS WITH CONSTRAINTS")
    print("=" * 70)
    
    # Initialize the combiner
    combiner = MiniWordFunctionCombiner()
    
    if not combiner.all_functions:
        print("✗ No functions loaded. Exiting.")
        return
    
    # Generate ALL possible combinations
    combinations = combiner.generate_all_combinations()
    
    # Print combinations
    combiner.print_combinations(combinations)
    
    # Save to file
    combiner.save_combinations_to_file(combinations)
    
    # Show statistics
    combiner.get_statistics(combinations)
    
    print(f"\n🎉 Generation completed!")
    print(f"📁 Results saved to: function_combinations.txt")


if __name__ == "__main__":
    main()
