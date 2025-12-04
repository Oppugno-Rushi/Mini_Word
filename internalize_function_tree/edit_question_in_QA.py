import json
import re

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_icon_name(answer):
    """Extract the icon name from the second step in the answer.
    
    Example:
        Input: '1. Switch to FILE toolbar section.\n2. Click the "New Document" icon.\n3. Click the "Close..." button.'
        Output: 'New Document'
    """
    # Look for the second step (index 1) in the split answer
    lines = answer.split('\n')
    if len(lines) >= 2:
        # Extract content after "2. Click the " and before " icon"
        match = re.search(r'2\.\s*Click the\s+"([^"]+)"\s+icon\.', lines[1])
        if match:
            return match.group(1)
    return None

def modify_question(question, icon_name):
    """Modify the question to include the function context."""
    if icon_name:
        return f'{question.rstrip("?")} under the "{icon_name}" function?'
    return question

def process_questions(data):
    """Process the questions and add function context where needed."""
    
    # Target question patterns
    target_questions = [
        "Where shall I click if I want to close the current dialog or sidebar?",
        "Where shall I click if I want to cancel the current operation?"
    ]
    
    modified_count = 0
    
    for item in data:
        question = item['question']
        answer = item['answer']
        
        # Check if the question matches one of our target patterns
        if any(target in question for target in target_questions):
            # Extract the icon name from the answer
            icon_name = extract_icon_name(answer)
            
            if icon_name:
                # Modify the question
                new_question = modify_question(question, icon_name)
                
                # Update the item
                item['question'] = new_question
                modified_count += 1
                
                # Debug output for first few examples
                if modified_count <= 5:
                    print(f"\nModified question #{modified_count}:")
                    print(f"  Original: {question}")
                    print(f"  Updated:  {new_question}")
                    print(f"  Icon:     {icon_name}")
    
    return modified_count

def main():
    # Paths
    input_path = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_qa.json'
    output_path = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_qa1.json'
    
    # Load data
    print("Loading internalized QA data...")
    data = load_json(input_path)
    
    print(f"Loaded {len(data)} QA pairs")
    
    # Process questions
    print("\nProcessing questions to add function context...")
    modified_count = process_questions(data)
    
    print(f"\nModified {modified_count} questions")
    
    # Save results (overwrite original file)
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Done!")
    
    # Show summary
    print(f"\nSummary:")
    print(f"  - Total QA pairs: {len(data)}")
    print(f"  - Modified questions: {modified_count}")

if __name__ == '__main__':
    main()

