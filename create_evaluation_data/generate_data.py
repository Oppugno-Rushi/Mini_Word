#!/usr/bin/env python3
"""
Generate evaluation data for MiniWord function combinations
"""

import json
import os
import time
import requests
from typing import Dict, List, Optional
import re

class MiniWordDataGenerator:
    def __init__(self, api_key: str, api_url: str = "https://api.openai.com/v1/chat/completions"):
        """
        Initialize the data generator
        
        Args:
            api_key: Your OpenAI API key
            api_url: API endpoint URL
        """
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    def load_combinations(self, file_path: str) -> List[Dict]:
        """
        Load function combinations from the text file
        
        Args:
            file_path: Path to function_combinations.txt
            
        Returns:
            List of dictionaries containing combination info
        """
        combinations = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the file content
        current_section = None
        combination_id = 0
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Detect section headers
            if line.startswith('Two Functions') or line.startswith('Three Functions') or line.startswith('Four Functions'):
                current_section = line.split('(')[0].strip()
                continue
            
            # Parse combination lines
            if line and line[0].isdigit() and '→' in line:
                # Extract combination from line like "1. New Document → Subscript"
                parts = line.split('.', 1)
                if len(parts) > 1:
                    combination = parts[1].strip()
                    combination_id += 1
                    
                    # Determine function count
                    function_count = len(combination.split('→'))
                    
                    combinations.append({
                        'id': combination_id,
                        'section': current_section,
                        'combination': combination,
                        'function_count': function_count
                    })
        
        return combinations
    
    def load_prompt(self, prompt_path: str) -> str:
        """
        Load the evaluation prompt
        
        Args:
            prompt_path: Path to judge_combinations_prompt.txt
            
        Returns:
            The prompt text
        """
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def load_documentation(self, documentation_path: str) -> Dict:
        """
        Load the function documentation
        
        Args:
            documentation_path: Path to explainations_for_botton.json
            
        Returns:
            The documentation as a dictionary
        """
        with open(documentation_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_function_usage(self, function_name: str, documentation: Dict) -> List[str]:
        """
        Get usage steps for a specific function from documentation
        
        Args:
            function_name: Name of the function to look up
            documentation: The loaded documentation dictionary
            
        Returns:
            List of usage steps or empty list if not found
        """
        # Search through all sections and buttons
        for section_name, section_data in documentation.get("MiniWord_Button_Documentation", {}).get("sections", {}).items():
            for button in section_data.get("buttons", []):
                if button.get("name") == function_name:
                    return button.get("usage", [])
        return []
    
    def get_function_details(self, function_name: str, documentation: Dict) -> Optional[Dict]:
        """
        Get complete function details for a specific function from documentation
        
        Args:
            function_name: Name of the function to look up
            documentation: The loaded documentation dictionary
            
        Returns:
            Dictionary with function details or None if not found
        """
        # Search through all sections and buttons
        for section_name, section_data in documentation.get("MiniWord_Button_Documentation", {}).get("sections", {}).items():
            for button in section_data.get("buttons", []):
                if button.get("name") == function_name:
                    # Return the complete button information
                    return {
                        "id": button.get("id", ""),
                        "name": button.get("name", ""),
                        "icon": button.get("icon", ""),
                        "usage": button.get("usage", [])
                    }
        return None
    
    def create_enhanced_prompt(self, base_prompt: str, combination: str, documentation: Dict) -> str:
        """
        Create an enhanced prompt with specific function documentation for a combination
        
        Args:
            base_prompt: The original prompt from judge_combinations_prompt.txt
            combination: The function combination (e.g., "New Document → Text Color")
            documentation: The loaded documentation dictionary
            
        Returns:
            Enhanced prompt with specific function usage
        """
        # Parse the combination to get individual function names
        functions = [func.strip() for func in combination.split('→')]
        
        # Get function details for each function
        function_details = {}
        for func in functions:
            details = self.get_function_details(func, documentation)
            if details:
                function_details[func] = details
        
        # Create the complete prompt matching the exact format from judge_combinations_prompt.txt
        enhanced_prompt = f"{base_prompt}\n\n"
        enhanced_prompt += f"Input:\n\n"
        enhanced_prompt += f"{combination}\n"
        enhanced_prompt += f"References:\n"
        
        # Add function references in JSON format (using array format as shown in prompt)
        for func, details in function_details.items():
            enhanced_prompt += "```json\n"
            enhanced_prompt += "[\n"
            enhanced_prompt += f'  "id": "{details["id"]}",\n'
            enhanced_prompt += f'  "name": "{details["name"]}",\n'
            enhanced_prompt += f'  "icon": "{details["icon"]}",\n'
            enhanced_prompt += '  "usage": [\n'
            for i, step in enumerate(details["usage"]):
                if i == len(details["usage"]) - 1:
                    enhanced_prompt += f'    "{step}"\n'
                else:
                    enhanced_prompt += f'    "{step}",\n'
            enhanced_prompt += '  ]\n'
            enhanced_prompt += "]\n"
            enhanced_prompt += "```\n"
        
        return enhanced_prompt
    
    def call_api(self, prompt: str, combination: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Call the API to evaluate a single combination
        
        Args:
            prompt: The evaluation prompt
            combination: The function combination to evaluate
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response or None if failed
        """
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result
                else:
                    print(f"API Error (attempt {attempt + 1}): {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Request Error (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def parse_response(self, response_text: str, combination: str) -> Optional[Dict]:
        """
        Parse the API response to extract JSON
        
        Args:
            response_text: Raw response text from API
            combination: The original combination being evaluated
            
        Returns:
            Parsed JSON or None if parsing failed
        """
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                # Ensure all required fields are present
                if "judgment" in result:
                    # Add combination if not present
                    if "combination" not in result:
                        result["combination"] = combination
                    return result
        except json.JSONDecodeError:
            pass
        
        # If no JSON found, try to parse as plain text
        if "unreasonable" in response_text.lower():
            return {
                "combination": combination,
                "judgment": "unreasonable",
                "question": None,
                "answer": None
            }
        elif "reasonable" in response_text.lower():
            # Try to extract question and answer from text
            lines = response_text.split('\n')
            question = None
            answer = None
            
            for i, line in enumerate(lines):
                if "question" in line.lower() and ":" in line:
                    # Extract question content
                    question_start = line.find(":") + 1
                    question = line[question_start:].strip().strip('"[]')
                elif "answer" in line.lower() and ":" in line:
                    # Extract answer content
                    answer_start = line.find(":") + 1
                    answer = line[answer_start:].strip().strip('"[]')
                    # If answer continues on next lines, collect them
                    j = i + 1
                    while j < len(lines) and not lines[j].strip().startswith(('"judgment"', '"question"', '}')):
                        answer += " " + lines[j].strip().strip('"[]')
                        j += 1
            
            return {
                "combination": combination,
                "judgment": "reasonable",
                "question": question,
                "answer": answer
            }
        
        # Handle the case where response contains "null" (unreasonable)
        if "null" in response_text.lower() and "unreasonable" in response_text.lower():
            return {
                "combination": combination,
                "judgment": "unreasonable",
                "question": None,
                "answer": None
            }
        
        return None
    
    def process_combinations(self, combinations: List[Dict], base_prompt: str, documentation: Dict, 
                           output_files: Dict[str, str]) -> None:
        """
        Process all combinations and save results to separate files by function count
        
        Args:
            combinations: List of combinations to process
            base_prompt: The original prompt from judge_combinations_prompt.txt
            documentation: The loaded documentation dictionary
            output_files: Dictionary mapping function counts to output file paths
        """
        # Load existing results if files exist
        results_by_count = {
            2: self.load_existing_results(output_files[2]) if os.path.exists(output_files[2]) else [],
            3: self.load_existing_results(output_files[3]) if os.path.exists(output_files[3]) else [],
            4: self.load_existing_results(output_files[4]) if os.path.exists(output_files[4]) else []
        }
        
        total = len(combinations)
        print(f"Processing {total} combinations...")
        
        for i, combo in enumerate(combinations):
            print(f"Processing {i+1}/{total}: {combo['combination']}")
            
            # Check if this combination has already been processed
            function_count = combo['function_count']
            if function_count in results_by_count:
                existing_ids = [result['id'] for result in results_by_count[function_count]]
                if combo['id'] in existing_ids:
                    print(f"⏭ Skipping already processed combination: {combo['combination']}")
                    continue
            
            # Create enhanced prompt with specific function documentation
            enhanced_prompt = self.create_enhanced_prompt(base_prompt, combo['combination'], documentation)
            
            # Call API
            response = self.call_api(enhanced_prompt, combo['combination'])
            
            # Debug: Stop after first API call
            #import ipdb
            #ipdb.set_trace()
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                parsed_result = self.parse_response(content, combo['combination'])
                
                if parsed_result:
                    result = {
                        'id': combo['id'],
                        'section': combo['section'],
                        'combination': combo['combination'],
                        'function_count': combo['function_count'],
                        'evaluation': parsed_result
                    }
                    
                    # Add to appropriate results list based on function count
                    function_count = combo['function_count']
                    if function_count in results_by_count:
                        results_by_count[function_count].append(result)
                        
                        # Save immediately after each successful result
                        self.save_results(results_by_count[function_count], output_files[function_count])
                        print(f"✓ Processed and saved: {parsed_result.get('judgment', 'unknown')}")
                    else:
                        print(f"✓ Processed: {parsed_result.get('judgment', 'unknown')} (no output file for {function_count} functions)")
                else:
                    print(f"✗ Failed to parse response for: {combo['combination']}")
            else:
                print(f"✗ API call failed for: {combo['combination']}")
            
            # Rate limiting - increased delay for better API stability
            time.sleep(2)
        
        total_processed = sum(len(results) for results in results_by_count.values())
        print(f"Completed! Processed {total_processed} combinations total")
    
    def load_existing_results(self, output_file: str) -> List[Dict]:
        """
        Load existing results from JSON file
        
        Args:
            output_file: Path to output file
            
        Returns:
            List of existing results or empty list if file doesn't exist
        """
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def save_results(self, results: List[Dict], output_file: str) -> None:
        """
        Save results to JSON file
        
        Args:
            results: List of results to save
            output_file: Path to output file
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    def generate_summary(self, results_file: str) -> None:
        """
        Generate a summary of the results
        
        Args:
            results_file: Path to results JSON file
        """
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Count by judgment
        judgment_counts = {}
        section_counts = {}
        
        for result in results:
            judgment = result['evaluation'].get('judgment', 'unknown')
            section = result['section']
            
            judgment_counts[judgment] = judgment_counts.get(judgment, 0) + 1
            section_counts[section] = section_counts.get(section, 0) + 1
        
        print("\n" + "="*50)
        print("EVALUATION SUMMARY")
        print("="*50)
        print(f"Total combinations processed: {len(results)}")
        print("\nJudgment distribution:")
        for judgment, count in judgment_counts.items():
            print(f"  {judgment}: {count}")
        
        print("\nSection distribution:")
        for section, count in section_counts.items():
            print(f"  {section}: {count}")
        
        # Save summary
        summary_file = results_file.replace('.json', '_summary.json')
        summary = {
            'total_processed': len(results),
            'judgment_distribution': judgment_counts,
            'section_distribution': section_counts,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nSummary saved to: {summary_file}")
    
    def test_api_connection(self) -> bool:
        """
        Test API connection with a simple request
        
        Returns:
            True if connection successful, False otherwise
        """
        test_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Respond with 'API connection successful'."
            },
            {
                "role": "user", 
                "content": "Test connection"
            }
        ]
        
        payload = {
            "model": "gpt-4o",
            "messages": test_messages,
            "temperature": 0.1,
            "max_tokens": 50
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✓ API connection successful")
                return True
            else:
                print(f"✗ API connection failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ API connection error: {e}")
            return False


def main():
    """
    Main function to run the data generation
    """
    print("MiniWord Function Combination Evaluator")
    print("="*50)
    
    # Change to the correct directory
    script_dir = "/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data"
    os.chdir(script_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Configuration
    # Get API key from environment variable or user input
    API_KEY = os.environ.get("OPENAI_API_KEY")
    
    # If not in environment, prompt user for input
    if not API_KEY:
        API_KEY = input("Enter your OpenAI API key: ").strip()
        if not API_KEY:
            print("Error: API key is required")
            return
    
    if not API_KEY or API_KEY == "your-api-key-here":
        print("Error: Please set a valid OpenAI API key")
        return
    
    # File paths - use absolute paths
    base_dir = "/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data"
    combinations_file = os.path.join(base_dir, "function_combinations.txt")
    prompt_file = os.path.join(base_dir, "judge_combinations_prompt.txt")
    documentation_file = os.path.join("/shared/nas/data/m1/jiateng5/Mini_Word", "explainations_for_botton.json")
    
    # Separate output files for each function count
    output_files = {
        2: os.path.join(base_dir, "generate_data_combination2.json"),
        3: os.path.join(base_dir, "generate_data_combination3.json"),
        4: os.path.join(base_dir, "generate_data_combination4.json")
    }
    
    # Check if files exist
    if not os.path.exists(combinations_file):
        print(f"Error: {combinations_file} not found")
        return
    
    if not os.path.exists(prompt_file):
        print(f"Error: {prompt_file} not found")
        return
    
    if not os.path.exists(documentation_file):
        print(f"Error: {documentation_file} not found")
        return
    
    # Initialize generator
    generator = MiniWordDataGenerator(API_KEY)
    
    # Test API connection first
    print("Testing API connection...")
    if not generator.test_api_connection():
        print("Failed to connect to API. Please check your API key and internet connection.")
        return
    
    # Load data
    print("\nLoading combinations...")
    combinations = generator.load_combinations(combinations_file)
    print(f"Loaded {len(combinations)} combinations")
    
    print("Loading prompt...")
    base_prompt = generator.load_prompt(prompt_file)
    
    print("Loading documentation...")
    documentation = generator.load_documentation(documentation_file)
    
    # Process combinations
    print("\nStarting evaluation...")
    generator.process_combinations(combinations, base_prompt, documentation, output_files)
    
    # Generate summary for each file
    print("\nGenerating summaries...")
    for count, file_path in output_files.items():
        if os.path.exists(file_path):
            print(f"\nSummary for {count}-function combinations:")
            generator.generate_summary(file_path)
    
    print(f"\nResults saved to separate files:")
    for count, file_path in output_files.items():
        print(f"  {count}-function combinations: {file_path}")
    print("Evaluation complete!")


if __name__ == "__main__":
    main()
