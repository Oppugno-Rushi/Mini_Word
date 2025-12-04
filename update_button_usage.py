#!/usr/bin/env python3
"""
Update usage steps to add section click as first step and increment all subsequent steps
"""

import json
import re

def update_usage_steps():
    # Load the JSON file
    with open('/shared/nas/data/m1/jiateng5/Mini_Word/explainations_for_botton.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Define section mappings
    section_mappings = {
        "File": "File",
        "Edit": "Edit", 
        "View": "View",
        "Insert": "Insert",
        "Format": "Format",
        "Tools": "Tools",
        "Help": "Help"
    }
    
    # Process each section
    for section_name, section_data in data["MiniWord_Button_Documentation"]["sections"].items():
        print(f"Processing section: {section_name}")
        
        # Process each button in the section
        for button in section_data["buttons"]:
            if "usage" in button:
                # Add the section click as the first step
                new_usage = [f"1. Click the '{section_name}' section"]
                
                # Update existing steps by incrementing their numbers
                for step in button["usage"]:
                    # Extract the number and content
                    match = re.match(r'^(\d+)\.\s*(.*)$', step)
                    if match:
                        old_number = int(match.group(1))
                        content = match.group(2)
                        new_number = old_number + 1
                        new_usage.append(f"{new_number}. {content}")
                    else:
                        # If no number found, just add as is with incremented number
                        new_usage.append(f"{len(new_usage) + 1}. {step}")
                
                button["usage"] = new_usage
                print(f"  Updated {button['name']}: {len(new_usage)} steps")
    
    # Save the updated JSON to the new file
    with open('/shared/nas/data/m1/jiateng5/Mini_Word/explainations_for_botton1.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("✅ Successfully updated all usage steps and saved to explainations_for_botton1.json!")

if __name__ == "__main__":
    update_usage_steps()
