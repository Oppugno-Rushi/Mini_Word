import json
import random
from typing import List, Dict, Any

def load_json_file(filepath: str) -> List[Dict[str, Any]]:
    """Load JSON data from file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(data: Any, filepath: str):
    """Save data to JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_answer(answer: Any) -> str:
    """Convert answer to string format (handle both string and list)"""
    if isinstance(answer, list):
        return '\n'.join(str(item) for item in answer)
    elif answer is None:
        return ""
    else:
        return str(answer)

def main():
    # File paths
    input_files = [
        '/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data/generate_data_combination2.json',
        '/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data/generate_data_combination3.json',
        '/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data/generate_data_combination4.json'
    ]
    
    existing_file = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_combine.json'
    eval_output = '/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data/evaluate_data_combination2,3,4.json'
    final_output = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_combine2.json'
    
    # Step 1: Load all three JSON files and filter for reasonable entries
    print("Loading and filtering data...")
    all_reasonable_data = []
    
    for input_file in input_files:
        print(f"Processing {input_file}...")
        data = load_json_file(input_file)
        
        for item in data:
            evaluation = item.get('evaluation', {})
            if evaluation.get('judgment') == 'reasonable':
                all_reasonable_data.append(item)
    
    print(f"Total reasonable entries: {len(all_reasonable_data)}")
    
    # Step 2: Randomly shuffle and split: 30% for evaluation, 70% for training
    random.seed(42)  # For reproducibility
    random.shuffle(all_reasonable_data)
    
    total = len(all_reasonable_data)
    eval_count = int(total * 0.3)
    
    eval_data = all_reasonable_data[:eval_count]
    training_data = all_reasonable_data[eval_count:]
    
    print(f"Evaluation data (30%): {len(eval_data)} entries")
    print(f"Training data (70%): {len(training_data)} entries")
    
    # Step 3: Save evaluation data (keep original format)
    print(f"Saving evaluation data to {eval_output}...")
    save_json_file(eval_data, eval_output)
    
    # Step 4: Transform training data format and load existing data
    print("Transforming training data format...")
    formatted_training_data = []
    
    for item in training_data:
        evaluation = item.get('evaluation', {})
        question = evaluation.get('question')
        answer = evaluation.get('answer')
        
        if question and answer:
            formatted_training_data.append({
                "question": question,
                "answer": normalize_answer(answer)
            })
    
    print(f"Formatted {len(formatted_training_data)} training entries")
    
    # Step 5: Load existing internalized_combine.json
    print(f"Loading existing data from {existing_file}...")
    existing_data = load_json_file(existing_file)
    print(f"Existing data entries: {len(existing_data)}")
    
    # Step 6: Append training data to existing data
    combined_data = existing_data + formatted_training_data
    print(f"Total entries after combining: {len(combined_data)}")
    
    # Step 7: Save final combined data
    print(f"Saving final combined data to {final_output}...")
    save_json_file(combined_data, final_output)
    
    print("\nComplete!")
    print(f"Evaluation data: {len(eval_data)} entries saved to {eval_output}")
    print(f"Training data: {len(formatted_training_data)} entries appended to existing data")
    print(f"Final combined data: {len(combined_data)} entries saved to {final_output}")

if __name__ == '__main__':
    main()

