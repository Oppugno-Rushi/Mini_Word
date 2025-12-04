import json
import os

def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def convert_to_llama_format(data):
    """Convert the QA data to LLaMA-Factory format."""
    
    system_prompt = "You are a helpful assistant. Your task is to answer the users' question about how to use the MiniWord application. You should answer it step by step, where each step contains one action and has a sequence number."
    
    converted_data = []
    
    for item in data:
        question = item['question']
        answer = item['answer']
        
        # Create the messages array
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question
            },
            {
                "role": "assistant",
                "content": answer
            }
        ]
        
        converted_item = {
            "messages": messages
        }
        
        converted_data.append(converted_item)
    
    return converted_data

def main():
    # Paths
    input_path = '/shared/nas/data/m1/jiateng5/Mini_Word/internalize_function_tree/internalized_combine2.json'
    output_dir = '/shared/nas/data/m1/jiateng5/Mini_Word/LLaMA-Factory/data'
    output_filename = 'internalized_qa_openai_update.json'
    output_path = os.path.join(output_dir, output_filename)
    
    # Load data
    print("Loading data from internalized_combine.json...")
    data = load_json(input_path)
    print(f"Loaded {len(data)} QA pairs")
    
    # Convert to LLaMA-Factory format
    print("\nConverting to LLaMA-Factory format...")
    converted_data = convert_to_llama_format(data)
    print(f"Converted {len(converted_data)} items")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the converted data
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, indent=2, ensure_ascii=False)
    
    print("Done!")
    
    # Show example of converted format
    print("\n" + "="*80)
    print("Example of converted format:")
    print("="*80)
    
    example = converted_data[0]
    print(json.dumps(example, indent=2, ensure_ascii=False)[:500])
    print("...")

if __name__ == '__main__':
    main()

