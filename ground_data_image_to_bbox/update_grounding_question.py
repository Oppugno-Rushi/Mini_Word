#!/usr/bin/env python3
"""
Update grounding questions in ground_data_new.json by matching with ground_data1.json
based on the relative path after function_tree_XX/
"""

import json
import re
from typing import Dict, List, Any

def extract_relative_path(full_path: str) -> str:
    """
    Extract the relative path after function_tree_XX/
    Example: "/shared/.../function_tree_10/file/begin.png" -> "/file/begin.png"
    """
    # Match pattern: function_tree_XX/...rest of path
    match = re.search(r'function_tree_\d+/(.+)', full_path)
    if match:
        return '/' + match.group(1)
    return None

def extract_question_from_value(value: str) -> str:
    """
    Extract the question part between <image> and "Please output"
    Example: "<image>Where shall I click if I want to execute action: blank? Please output..."
    -> "Where shall I click if I want to execute action: blank?"
    """
    # Pattern: <image>...Please output
    match = re.search(r'<image>(.+?)\s+Please output', value)
    if match:
        return match.group(1).strip()
    return None

def replace_question_in_value(original_value: str, new_question: str) -> str:
    """
    Replace the question part in the value while keeping <image> and "Please output" parts
    """
    # Find the pattern and replace the question part
    pattern = r'(<image>)(.+?)(\s+Please output)'
    replacement = r'\1' + new_question + r'\3'
    new_value = re.sub(pattern, replacement, original_value)
    return new_value

def main():
    old_file = "/shared/nas/data/m1/jiateng5/Mini_Word/ground_data_image_to_bbox/ground_data1.json"
    new_file = "/shared/nas/data/m1/jiateng5/Mini_Word/ground_data_image_to_bbox/ground_data_new.json"
    output_file = "/shared/nas/data/m1/jiateng5/Mini_Word/ground_data_image_to_bbox/ground_data_new.json"
    
    print("Loading old ground data (ground_data1.json)...")
    with open(old_file, 'r', encoding='utf-8') as f:
        old_data: List[Dict[str, Any]] = json.load(f)
    
    print("Loading new ground data (ground_data_new.json)...")
    with open(new_file, 'r', encoding='utf-8') as f:
        new_data: List[Dict[str, Any]] = json.load(f)
    
    # Build a mapping from relative path to question in old_data
    print("Building mapping from old data...")
    path_to_question: Dict[str, str] = {}
    
    for item in old_data:
        if "images" in item and len(item["images"]) > 0:
            image_path = item["images"][0]
            relative_path = extract_relative_path(image_path)
            
            if relative_path and "conversations" in item and len(item["conversations"]) > 0:
                human_message = item["conversations"][0]
                if human_message.get("from") == "human" and "value" in human_message:
                    question = extract_question_from_value(human_message["value"])
                    if question:
                        path_to_question[relative_path] = question
    
    print(f"Found {len(path_to_question)} entries in old data")
    
    # Update new_data based on matching relative paths
    print("Updating new data...")
    updated_count = 0
    
    for item in new_data:
        if "images" in item and len(item["images"]) > 0:
            image_path = item["images"][0]
            relative_path = extract_relative_path(image_path)
            
            # Check if we have a matching question in old data
            if relative_path in path_to_question:
                if "conversations" in item and len(item["conversations"]) > 0:
                    human_message = item["conversations"][0]
                    if human_message.get("from") == "human" and "value" in human_message:
                        old_question = path_to_question[relative_path]
                        new_value = replace_question_in_value(human_message["value"], old_question)
                        human_message["value"] = new_value
                        updated_count += 1
                        print(f"  Updated: {relative_path}")
    
    print(f"\nUpdated {updated_count} entries")
    
    # Save the updated new_data
    print(f"\nSaving updated data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    
    print("Done!")

if __name__ == "__main__":
    main()

