import json

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # Paths
    qa_path = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_qa1.json'
    explanations_path = '/shared/nas/data/m1/jiateng5/Mini_Word/explainations_for_botton.json'
    output_path = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_qa2.json'
    
    # Load existing QA data
    print("Loading existing QA data...")
    qa_data = load_json(qa_path)
    print(f"Loaded {len(qa_data)} existing QA pairs")
    
    # Load button explanations
    print("\nLoading button explanations...")
    explanations_data = load_json(explanations_path)
    
    # Extract all buttons and their usage
    new_qa_pairs = []
    
    sections = explanations_data['MiniWord_Button_Documentation']['sections']
    
    for section_name, section_data in sections.items():
        print(f"\nProcessing section: {section_name}")
        
        for button in section_data['buttons']:
            button_name = button['name']
            usage_steps = button['usage']
            
            # Create question
            question = f"How to use the {button_name} function?"
            
            # Create answer by joining usage steps with \n
            answer = "\n".join(usage_steps)
            
            # Create QA pair
            qa_pair = {
                "question": question,
                "answer": answer
            }
            
            new_qa_pairs.append(qa_pair)
            print(f"  Created QA for: {button_name}")
    
    print(f"\nCreated {len(new_qa_pairs)} new QA pairs from button explanations")
    
    # Combine the datasets (existing + new)
    combined_data = qa_data + new_qa_pairs
    
    print(f"\nTotal QA pairs: {len(combined_data)} (original: {len(qa_data)}, added: {len(new_qa_pairs)})")
    
    # Save the combined data
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    print("Done!")
    
    # Show some examples
    print("\n" + "="*80)
    print("Examples of new QA pairs:")
    print("="*80)
    
    # Show first 3 new examples
    for i, qa_pair in enumerate(new_qa_pairs[:3]):
        print(f"\nExample {i+1}:")
        print(f"Q: {qa_pair['question']}")
        print(f"A: {qa_pair['answer'][:150]}...")

if __name__ == '__main__':
    main()

