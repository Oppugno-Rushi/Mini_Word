"""
Evaluation script for text inference results using F1 score method.

This script:
1. Loads predictions from inference results JSON
2. Loads ground truth from evaluation JSON
3. Extracts numbered steps from both predicted and ground truth answers
4. Matches each predicted step with the most similar ground truth step
5. Calculates F1 score based on alignment
"""

import json
import re
from typing import List, Tuple, Dict
from difflib import SequenceMatcher
from collections import defaultdict


def extract_steps(answer: str) -> List[str]:
    """
    Extract numbered steps from an answer string.
    
    Args:
        answer: Answer string (may contain reasoning blocks)
        
    Returns:
        List of step strings, each starting with a number
    """
    # Remove reasoning blocks if present
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
    answer = answer.strip()
    
    # Pattern to match numbered steps: "1. ", "2. ", etc. or "1.", "2.", etc.
    # Also handle cases like "1. Click..." or "1. Click..."
    pattern = r'(\d+[\.\)]\s+[^\n]+(?:\n(?!\d+[\.\)])[^\n]+)*)'
    
    steps = []
    matches = re.findall(pattern, answer, re.MULTILINE)
    
    for match in matches:
        # Clean up the step
        step = match.strip()
        # Remove any trailing newlines within the step and normalize
        step = re.sub(r'\n+', ' ', step)
        step = step.strip()
        if step:
            steps.append(step)
    
    # If no numbered steps found, try splitting by newlines and finding numbered lines
    if not steps:
        lines = answer.split('\n')
        current_step = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if line starts with a number followed by period/parenthesis
            if re.match(r'^\d+[\.\)]', line):
                if current_step:
                    steps.append(current_step)
                current_step = line
            elif current_step:
                # Continue the current step
                current_step += ' ' + line
        if current_step:
            steps.append(current_step)
    
    return steps


def normalize_step(step: str) -> str:
    """Normalize a step string for comparison"""
    # Remove extra whitespace
    step = re.sub(r'\s+', ' ', step)
    # Remove step number prefix
    step = re.sub(r'^\d+[\.\)]\s*', '', step)
    # Lowercase for comparison
    step = step.lower().strip()
    return step


def calculate_similarity(step1: str, step2: str) -> float:
    """
    Calculate similarity between two steps using SequenceMatcher.
    
    Similarity is calculated using Python's SequenceMatcher (from difflib), which:
    - Compares the character sequences of two strings after normalization
    - Returns a ratio between 0.0 and 1.0:
      * 1.0 = strings are identical
      * 0.0 = strings are completely different
      * 0.95 = approximately 95% of characters match in sequence
    
    The similarity threshold (default 0.95) means:
    - A predicted step must have at least 95% character-level similarity 
      with a ground truth step to be considered "aligned"
    - This accounts for minor wording differences, typos, or phrasing variations
    
    Example:
    - "click the file section" vs "click the 'file' section" → ~0.95 similarity
    - "click the file section" vs "select document type" → ~0.2 similarity
    
    Args:
        step1: First step string
        step2: Second step string
        
    Returns:
        Similarity score between 0 and 1
    """
    normalized1 = normalize_step(step1)
    normalized2 = normalize_step(step2)
    return SequenceMatcher(None, normalized1, normalized2).ratio()


def match_steps(predicted_steps: List[str], ground_truth_steps: List[str], 
                similarity_threshold: float = 0.95) -> Tuple[Dict[int, int], float]:
    """
    Match predicted steps with ground truth steps based on similarity.
    
    评估流程 (Evaluation Process):
    1. 对每个预测步骤 (predicted step)，遍历所有ground truth步骤
    2. 计算与每个ground truth步骤的相似度
    3. 找到相似度最高的ground truth步骤
    4. 如果最高相似度 >= threshold (0.95)，则判定为"正确"匹配
    5. 使用一对一匹配（one-to-one）：每个ground truth步骤只能被匹配一次
    
    Args:
        predicted_steps: List of predicted step strings
        ground_truth_steps: List of ground truth step strings
        similarity_threshold: Minimum similarity to consider a match (default: 0.95)
        
    Returns:
        Tuple of (mapping from predicted index to ground truth index, average similarity)
    """
    matches = {}  # 存储匹配关系：{预测步骤索引: ground truth步骤索引}
    total_similarity = 0.0
    matched_count = 0
    used_gt_indices = set()  # 记录已经匹配过的ground truth步骤（保证一对一匹配）
    
    # 对每个预测步骤进行处理
    for pred_idx, pred_step in enumerate(predicted_steps):
        best_match_idx = -1
        best_similarity = 0.0
        
        # 遍历所有ground truth步骤，找到相似度最高的
        for gt_idx, gt_step in enumerate(ground_truth_steps):
            # 跳过已经被匹配的ground truth步骤（一对一匹配）
            if gt_idx in used_gt_indices:
                continue
                
            # 计算相似度
            similarity = calculate_similarity(pred_step, gt_step)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = gt_idx
        
        # 只有当最高相似度 >= 阈值 (0.95) 时，才判定为正确匹配
        if best_similarity >= similarity_threshold:
            matches[pred_idx] = best_match_idx
            used_gt_indices.add(best_match_idx)  # 标记该ground truth步骤已被使用
            total_similarity += best_similarity
            matched_count += 1
    
    avg_similarity = total_similarity / matched_count if matched_count > 0 else 0.0
    return matches, avg_similarity


def calculate_f1_score(predicted_steps: List[str], ground_truth_steps: List[str],
                       matches: Dict[int, int]) -> Tuple[float, float, float]:
    """
    Calculate precision, recall, and F1 score.
    
    Args:
        predicted_steps: List of predicted steps
        ground_truth_steps: List of ground truth steps
        matches: Mapping from predicted index to ground truth index
        
    Returns:
        Tuple of (precision, recall, f1_score)
    """
    num_matched = len(matches)
    num_predicted = len(predicted_steps)
    num_ground_truth = len(ground_truth_steps)
    
    if num_predicted == 0:
        precision = 0.0
    else:
        precision = num_matched / num_predicted
    
    if num_ground_truth == 0:
        recall = 0.0
    else:
        recall = num_matched / num_ground_truth
    
    if precision + recall == 0:
        f1_score = 0.0
    else:
        f1_score = 2 * (precision * recall) / (precision + recall)
    
    return precision, recall, f1_score


def normalize_answer(answer) -> str:
    """Convert answer to string format (handle both string and list)"""
    if isinstance(answer, list):
        return '\n'.join(str(item) for item in answer)
    elif answer is None:
        return ""
    else:
        return str(answer)


def evaluate_results(predictions_file: str, ground_truth_file: str, 
                    similarity_threshold: float = 0.95) -> Dict:
    """
    Evaluate predictions against ground truth.
    
    Args:
        predictions_file: Path to inference results JSON file
        ground_truth_file: Path to ground truth JSON file
        similarity_threshold: Minimum similarity to consider a step matched
        
    Returns:
        Dictionary containing evaluation metrics
    """
    # Load predictions
    print(f"Loading predictions from {predictions_file}...")
    with open(predictions_file, 'r', encoding='utf-8') as f:
        predictions = json.load(f)
    
    # Load ground truth
    print(f"Loading ground truth from {ground_truth_file}...")
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth_list = json.load(f)
    
    # Create a mapping from question to ground truth for easier lookup
    gt_by_question = {}
    for item in ground_truth_list:
        evaluation = item.get('evaluation', {})
        question = evaluation.get('question')
        answer = evaluation.get('answer')
        if question and answer:
            gt_by_question[question] = normalize_answer(answer)
    
    print(f"Loaded {len(predictions)} predictions and {len(gt_by_question)} ground truth entries")
    
    # Evaluate each prediction
    results = []
    total_precision = 0.0
    total_recall = 0.0
    total_f1 = 0.0
    total_avg_similarity = 0.0
    
    matched_count = 0
    
    for pred in predictions:
        question = pred.get('question')
        predicted_answer = pred.get('answer', '')
        
        if not question or question not in gt_by_question:
            print(f"Warning: Question not found in ground truth: {question[:50]}...")
            continue
        
        ground_truth_answer = gt_by_question[question]
        
        # Extract steps
        predicted_steps = extract_steps(predicted_answer)
        ground_truth_steps = extract_steps(ground_truth_answer)
        
        if not ground_truth_steps:
            print(f"Warning: No steps extracted from ground truth for question: {question[:50]}...")
            continue
        
        # Match steps
        matches, avg_similarity = match_steps(predicted_steps, ground_truth_steps, similarity_threshold)
        
        # Calculate metrics
        precision, recall, f1_score = calculate_f1_score(predicted_steps, ground_truth_steps, matches)
        
        result = {
            'question': question,
            'num_predicted_steps': len(predicted_steps),
            'num_ground_truth_steps': len(ground_truth_steps),
            'num_matched_steps': len(matches),
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'average_similarity': avg_similarity,
            'matches': {str(k): v for k, v in matches.items()}
        }
        
        results.append(result)
        total_precision += precision
        total_recall += recall
        total_f1 += f1_score
        total_avg_similarity += avg_similarity
        matched_count += 1
    
    # Calculate averages
    avg_precision = total_precision / matched_count if matched_count > 0 else 0.0
    avg_recall = total_recall / matched_count if matched_count > 0 else 0.0
    avg_f1 = total_f1 / matched_count if matched_count > 0 else 0.0
    avg_similarity = total_avg_similarity / matched_count if matched_count > 0 else 0.0
    
    evaluation_summary = {
        'total_evaluated': matched_count,
        'average_precision': avg_precision,
        'average_recall': avg_recall,
        'average_f1_score': avg_f1,
        'average_similarity': avg_similarity,
        'similarity_threshold': similarity_threshold,
        'detailed_results': results
    }
    
    return evaluation_summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate text inference results")
    parser.add_argument(
        '--predictions',
        type=str,
        default='/shared/nas/data/m1/jiateng5/Mini_Word/inference/results_text/evaluate_data_combination2,3,4_inference_results.json',
        help='Path to predictions JSON file'
    )
    parser.add_argument(
        '--ground_truth',
        type=str,
        default='/shared/nas/data/m1/jiateng5/Mini_Word/create_evaluation_data/evaluate_data_combination2,3,4.json',
        help='Path to ground truth JSON file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='/shared/nas/data/m1/jiateng5/Mini_Word/inference/results_text/evaluation_score_f1.json',
        help='Path to save evaluation results'
    )
    parser.add_argument(
        '--similarity_threshold',
        type=float,
        default=0.95,
        help='Minimum similarity threshold for step matching (default: 0.95)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Text Inference Evaluation")
    print("=" * 80)
    print(f"Predictions: {args.predictions}")
    print(f"Ground Truth: {args.ground_truth}")
    print(f"Similarity Threshold: {args.similarity_threshold}")
    print("=" * 80)
    print()
    
    # Run evaluation
    results = evaluate_results(args.predictions, args.ground_truth, args.similarity_threshold)
    
    # Save summary scores (F1 and other metrics) to output file
    score_summary = {
        'total_evaluated': results['total_evaluated'],
        'average_precision': results['average_precision'],
        'average_recall': results['average_recall'],
        'average_f1_score': results['average_f1_score'],
        'average_similarity': results['average_similarity'],
        'similarity_threshold': results['similarity_threshold']
    }
    print(f"\nSaving score summary to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(score_summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 80)
    print("Evaluation Summary")
    print("=" * 80)
    print(f"Total Evaluated: {results['total_evaluated']}")
    print(f"Average Precision: {results['average_precision']:.4f}")
    print(f"Average Recall: {results['average_recall']:.4f}")
    print(f"Average F1 Score: {results['average_f1_score']:.4f}")
    print(f"Average Similarity: {results['average_similarity']:.4f}")
    print("=" * 80)


if __name__ == '__main__':
    main()

