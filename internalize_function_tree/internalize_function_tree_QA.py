import json
import os

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def find_all_paths(node, current_path=None, paths=None):
    """
    Recursively find all paths from root to leaves.
    Returns list of paths, where each path is a list of node data.
    """
    if paths is None:
        paths = []
    if current_path is None:
        current_path = []
    
    current_path.append(node)
    
    # If this node has an 'action' field with content, traverse it
    if 'action' in node and isinstance(node['action'], dict) and node['action']:
        for key, child_node in node['action'].items():
            find_all_paths(child_node, current_path.copy(), paths)
    else:
        # This is a leaf node, save the path
        paths.append(current_path)
    
    return paths

def extract_section_name(path_item):
    """Extract section name from path (e.g., 'file', 'edit', 'view')."""
    if 'begin' in path_item:
        begin_path = path_item['begin']
        # Extract section from path like "function_tree_10/file/begin.png"
        parts = begin_path.split('/')
        if len(parts) >= 3 and parts[0] == 'function_tree_10':
            return parts[1]
    return None

def get_section_lookup(ground_data):
    """Build a lookup dictionary for section switch questions from ground_data."""
    section_lookup = {}
    
    for item in ground_data:
        human_value = item['conversations'][0]['value']
        if '<image>' in human_value:
            question_part = human_value.split('<image>')[1]
            if question_part.startswith('Where shall I click if I want to '):
                desc = question_part.replace('Where shall I click if I want to ', '').split('?')[0]
                
                # Check if this is a section switch question
                if 'switch to' in desc and 'toolbar section' in desc:
                    # Extract section name from description like "switch to FILE toolbar section"
                    section_name = desc.replace('switch to ', '').replace(' toolbar section', '').strip()
                    section_lookup[section_name] = desc
    
    return section_lookup

def get_button_name_mapping():
    """Load button name mappings from explainations_for_botton.json."""
    button_mapping = {}
    
    try:
        with open('/shared/nas/data/m1/jiateng5/Mini_Word/explainations_for_botton.json', 'r') as f:
            data = json.load(f)
            
        for section_name, section_data in data['MiniWord_Button_Documentation']['sections'].items():
            for button in section_data['buttons']:
                button_id = button['id']
                button_name = button['name']
                button_mapping[button_id] = button_name
                
    except Exception as e:
        print(f"Warning: Could not load button mapping: {e}")
    
    return button_mapping

def get_button_id_from_path(begin_path):
    """Extract button ID from begin path."""
    if not begin_path:
        return None
    parts = begin_path.split('/')
    if len(parts) >= 4:
        return parts[2]  # e.g., 'function_tree_10/file/file_new/begin.png' -> 'file_new'
    return None

def clean_description(desc):
    """Clean up description text."""
    if desc.startswith('Execute action: '):
        return desc.replace('Execute action: ', '')
    return desc

def build_ground_data_lookup(ground_data):
    """Build a lookup dictionary mapping image paths to questions and descriptions from ground_data."""
    # This maps image paths to the question and button/field descriptions
    ground_lookup = {}
    
    for item in ground_data:
        if 'images' in item and len(item['images']) > 0:
            image_path = item['images'][0]
            # Extract just the filename with path (e.g., "function_tree_10/file/file_new/blank/begin.png")
            if '/shared/nas/data/m1/jiateng5/Mini_Word/' in image_path:
                rel_path = image_path.replace('/shared/nas/data/m1/jiateng5/Mini_Word/', '')
            else:
                rel_path = image_path
            
            human_value = item['conversations'][0]['value']
            if '<image>' in human_value:
                question_part = human_value.split('<image>')[1]
                if question_part.startswith('Where shall I click if I want to '):
                    # Extract the full description
                    full_desc = question_part.replace('Where shall I click if I want to ', '').split('?')[0]
                    # Store the clean question without coordinate instruction
                    clean_question = question_part.replace('? Please output the x,y value and the height and width of the bounding box for the click area or button.', '?')
                    ground_lookup[rel_path] = {
                        'question': clean_question,
                        'description': full_desc
                    }
    
    return ground_lookup

def process_trajectory(trajectory_data, ground_data):
    """Process trajectory to generate combined QA pairs."""
    results = []
    
    # Build section lookup, button mapping, and ground data lookup
    section_lookup = get_section_lookup(ground_data)
    button_mapping = get_button_name_mapping()
    ground_lookup = build_ground_data_lookup(ground_data)
    
    # Get the initial page node
    initial_page = trajectory_data.get('initial page')
    if not initial_page:
        return results
    
    # Find all paths from root to leaves
    all_paths = find_all_paths(initial_page)
    
    # Process each path
    for path in all_paths:
        # Skip if path is too short (must have at least 3 levels: initial, section, leaf)
        if len(path) < 3:
            continue
        
        # Get the leaf node (last in path)
        leaf = path[-1]
        if 'description' not in leaf:
            continue
        
        leaf_desc = leaf['description']
        
        # Build the steps
        steps = []
        step_num = 1
        
        # First step: switch to the section toolbar
        section_item = path[1]  # Second item should be the section
        section_name = extract_section_name(section_item)
        # Convert to uppercase for lookup (trajectory has lowercase like "file", lookup has "FILE")
        if section_name:
            section_name = section_name.upper()
        if section_name and section_name in section_lookup:
            section_desc = section_lookup[section_name]
            # Capitalize first letter
            section_desc = section_desc[0].upper() + section_desc[1:] if section_desc else section_desc
            steps.append(f"{step_num}. {section_desc}.")
            step_num += 1
        
        # Second step and onwards: intermediate actions and final action
        # Start from index 2 (after section) to len-1 (before leaf)
        for i in range(2, len(path)):
            item = path[i]
            if 'description' in item and item['description']:
                begin_path = item.get('begin', '')
                
                # Try to get the real description from ground_data
                if begin_path in ground_lookup:
                    real_desc = ground_lookup[begin_path]['description']
                else:
                    real_desc = clean_description(item['description'])
                
                # Determine if it's an icon click or button click
                if i < len(path) - 1:
                    # Intermediate step - icon click in toolbar
                    # Try to get the actual button name from the mapping
                    button_id = get_button_id_from_path(begin_path)
                    if button_id and button_id in button_mapping:
                        display_name = button_mapping[button_id]
                    else:
                        display_name = real_desc
                    steps.append(f"{step_num}. Click the \"{display_name}\" icon.")
                else:
                    # Final step - button click in dialog (use real description from ground_data)
                    # Capitalize the first letter of the button description
                    display_name = real_desc[0].upper() + real_desc[1:] if real_desc else real_desc
                    steps.append(f"{step_num}. Click the \"{display_name}\" button.")
                step_num += 1
        
        # Create the question from leaf's begin path using ground_data lookup
        leaf_begin = leaf.get('begin', '')
        if leaf_begin in ground_lookup:
            question = ground_lookup[leaf_begin]['question']
        else:
            # Fallback to simple question
            question = f"Where shall I click if I want to {leaf_desc.lower()}?"
        
        # Create the conversation item - just question and answer
        conversation_item = {
            "question": question,
            "answer": "\n".join(steps)
        }
        
        results.append(conversation_item)
    
    return results

def main():
    """Main function."""
    # Paths
    trajectory_path = '/shared/nas/data/m1/jiateng5/Mini_Word/function_tree_10/trajectory.json'
    ground_data_path = '/shared/nas/data/m1/jiateng5/Mini_Word/ground_data1.json'
    output_path = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_qa.json'
    
    # Load data
    print("Loading trajectory data...")
    trajectory_data = load_json(trajectory_path)
    
    print("Loading ground data...")
    ground_data = load_json(ground_data_path)
    
    # Process
    print("Processing trajectory to generate combined QA pairs...")
    results = process_trajectory(trajectory_data, ground_data)
    
    # Save results
    print(f"Generated {len(results)} QA pairs")
    print(f"Saving to {output_path}...")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("Done!")

if __name__ == '__main__':
    main()
