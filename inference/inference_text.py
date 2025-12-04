"""
MiniWord Text Inference Pipeline

This script:
1. Loads a fine-tuned model (Qwen3-4B)
2. Reads questions from JSON evaluation files
3. Generates answers using the model
4. Saves results to output files

Usage (with defaults):
    python inference_text.py
    
Usage (custom paths):
    python inference_text.py --model_path /path/to/model --output_dir /path/to/output

Requirements:
    - Fine-tuned model at the specified path
    - Dependencies: torch, transformers, tqdm
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Optional
from tqdm import tqdm

# Set default GPU devices before importing torch
os.environ["CUDA_VISIBLE_DEVICES"] = "1,3"

# Add LLaMA-Factory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../LLaMA-Factory/src'))

from llamafactory.chat import ChatModel


class TextInferenceModel:
    """Text generation model for question answering"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        
    def initialize(self):
        """Initialize the model"""
        print(f"Loading model from {self.model_path}...")
        args = {
            "model_name_or_path": self.model_path,
            "adapter_name_or_path": None,
            "template": "qwen3",
            "infer_backend": "huggingface",
        }
        self.model = ChatModel(args)
        print("Model loaded successfully!")
        
    def generate_answer(self, question: str) -> str:
        """
        Generate an answer for a given question
        
        Args:
            question: Input question
            
        Returns:
            Generated answer
        """
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        # Create a message in the chat format
        messages = [{"role": "user", "content": question}]
        
        # Generate response
        response = self.model.chat(messages)[0].response_text
        
        return response.strip()


def load_questions_from_json(json_file_path: str) -> List[Dict]:
    """
    Load questions from a JSON file
    
    Args:
        json_file_path: Path to the JSON file
        
    Returns:
        List of dictionaries containing question data
    """
    print(f"Loading questions from {json_file_path}...")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = []
    for item in data:
        # Extract question from the evaluation field
        if "evaluation" in item and item["evaluation"].get("question"):
            question = item["evaluation"]["question"]
            if question:  # Filter out null questions
                questions.append({
                    "id": item.get("id"),
                    "section": item.get("section"),
                    "combination": item.get("combination"),
                    "function_count": item.get("function_count"),
                    "question": question,
                    "gold_answer": item["evaluation"].get("answer"),
                    "evaluation": item["evaluation"]
                })
    
    print(f"Loaded {len(questions)} questions from {json_file_path}")
    return questions


def save_results(results: List[Dict], output_file_path: str):
    """
    Save inference results to a JSON file
    
    Args:
        results: List of results containing predictions
        output_file_path: Path to save the output file
    """
    print(f"Saving results to {output_file_path}...")
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results saved successfully!")


def main():
    parser = argparse.ArgumentParser(description="Run text inference on evaluation questions")
    parser.add_argument(
        "--model_path",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/LLaMA-Factory/saves/qwen3-4b/full/sft_update",
        help="Path to the fine-tuned model"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference/results",
        help="Directory to save output files"
    )
    parser.add_argument(
        "--eval_file",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data/evaluate_data_combination2,3,4.json",
        help="Path to the combined evaluation JSON file"
    )
    args = parser.parse_args()
    
    # Confirm GPU usage
    print(f"Using GPU devices: {os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set')}")
    print()
    
    # Input JSON file (combined evaluation set)
    json_file = args.eval_file
    
    # Initialize the model
    print("=" * 80)
    print("Initializing Text Inference Model")
    print("=" * 80)
    model = TextInferenceModel(args.model_path)
    model.initialize()
    print()
    
    # Process the single JSON file
    print("=" * 80)
    print(f"Processing: {json_file}")
    print("=" * 80)

    # Load questions
    questions = load_questions_from_json(json_file)

    if not questions:
        print(f"No valid questions found in {json_file}, exiting...")
        return

    # Generate answers
    results = []
    for question_data in tqdm(questions, desc="Generating answers"):
        try:
            question = question_data["question"]
            generated_answer = model.generate_answer(question)

            # Store result (simple format: question and answer only)
            results.append({
                "question": question,
                "answer": generated_answer
            })
        except Exception as e:
            print(f"Error processing question: {str(e)}")
            results.append({
                "question": question_data["question"],
                "answer": None,
                "error": str(e)
            })

    # Save results
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Create output filename based on input filename
    base_name = os.path.basename(json_file)
    output_filename = base_name.replace(".json", "_inference_results.json")
    output_path = os.path.join(output_dir, output_filename)

    save_results(results, output_path)
    print()
    
    print("=" * 80)
    print("All inference tasks completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()

