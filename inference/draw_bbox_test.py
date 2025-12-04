#!/usr/bin/env python3
"""
Draw bounding boxes on images based on model predictions.

This script reads ground data JSON file, uses a vision model to predict
bounding boxes for each image-question pair, and draws the bboxes on the images.
"""

import json
import os
import re
import argparse
import gc
from typing import Optional, Tuple, List, Dict
from pathlib import Path

# Set GPU before importing PyTorch
os.environ["CUDA_VISIBLE_DEVICES"] = "0,3"

from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm
import torch

# Import ChatModel from LLaMA-Factory
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'LLaMA-Factory', 'src'))
from llamafactory.chat import ChatModel

# ---------------------------------------------------------------------------
# Torch compatibility shim: some transformers pipelines reference
# torch.compiler.is_compiling(), which may not exist in older torch versions.
# This defines a no-op fallback to avoid AttributeError at runtime.
# ---------------------------------------------------------------------------
try:
    if not hasattr(torch, "compiler") or not hasattr(torch.compiler, "is_compiling"):
        class _TorchCompilerShim:
            @staticmethod
            def is_compiling():
                return False
        if not hasattr(torch, "compiler"):
            torch.compiler = _TorchCompilerShim()  # type: ignore
        else:
            torch.compiler.is_compiling = _TorchCompilerShim.is_compiling  # type: ignore
except Exception:
    pass


class BboxDetector:
    """Detect bounding boxes in images using Qwen2.5-VL-7B."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model: Optional[ChatModel] = None

    def initialize(self):
        """Initialize the model."""
        args = {
            "model_name_or_path": self.model_path,
            "adapter_name_or_path": None,
            "template": "qwen2_vl",
            "infer_backend": "huggingface",
        }
        self.model = ChatModel(args)

    @staticmethod
    def parse_bbox(text: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Parse bbox coordinates from model text output.
        Expected format: JSON with x_topleft, y_topleft, x_bottomright, y_bottomright
        Returns: (x_topleft, y_topleft, x_bottomright, y_bottomright)
        """
        # Try to parse as JSON first
        try:
            # Look for JSON-like structure in the response
            json_match = re.search(r'\{[^}]*"x_topleft"[^}]*\}', text, re.IGNORECASE)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                x_tl = int(data.get('x_topleft', 0))
                y_tl = int(data.get('y_topleft', 0))
                x_br = int(data.get('x_bottomright', 0))
                y_br = int(data.get('y_bottomright', 0))
                if x_tl < x_br and y_tl < y_br:
                    return (x_tl, y_tl, x_br, y_br)
        except:
            pass
        
        # Try to find individual values
        x_tl_match = re.search(r'"x_topleft"\s*:\s*(\d+)', text, re.IGNORECASE)
        y_tl_match = re.search(r'"y_topleft"\s*:\s*(\d+)', text, re.IGNORECASE)
        x_br_match = re.search(r'"x_bottomright"\s*:\s*(\d+)', text, re.IGNORECASE)
        y_br_match = re.search(r'"y_bottomright"\s*:\s*(\d+)', text, re.IGNORECASE)
        
        if x_tl_match and y_tl_match and x_br_match and y_br_match:
            try:
                x_tl = int(x_tl_match.group(1))
                y_tl = int(y_tl_match.group(1))
                x_br = int(x_br_match.group(1))
                y_br = int(y_br_match.group(1))
                if x_tl < x_br and y_tl < y_br:
                    return (x_tl, y_tl, x_br, y_br)
            except ValueError:
                pass
        
        # Fallback: try to parse 4 numbers
        numbers = re.findall(r"\d+", text)
        if len(numbers) >= 4:
            try:
                x_tl, y_tl, x_br, y_br = [int(n) for n in numbers[:4]]
                if x_tl < x_br and y_tl < y_br:
                    return (x_tl, y_tl, x_br, y_br)
            except ValueError:
                pass
        
        return None

    def detect_bbox(self, image_path: str, question: str) -> Optional[Tuple[int, int, int, int]]:
        """Detect bounding box for a given image and question."""
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        image = Image.open(image_path)
        
        # Question already contains <image> tag, use it directly
        # LLaMA-Factory's qwen2_vl template expects string content with <image> tag
        messages = [{"role": "user", "content": question}]
        
        try:
            # Pass image as separate parameter - this is the correct format for qwen2_vl
            response = self.model.chat(messages, images=[image])[0].response_text
        except Exception as e:
            print(f"Error calling model: {e}")
            # Clean up GPU memory before raising
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise
        
        bbox = self.parse_bbox(response)
        if bbox is None:
            print(f"Warning: Could not parse bbox from response: {response[:200]}")
        
        # Clean up image from memory
        image.close()
        
        return bbox


class ImageAnnotator:
    """Annotate images with bounding boxes."""
    
    def __init__(self, font_size: int = 20, bbox_color: str = "red", 
                 text_color: str = "white", bbox_thickness: int = 3):
        self.font_size = font_size
        self.bbox_color = bbox_color
        self.text_color = text_color
        self.bbox_thickness = bbox_thickness
        self.font = None
        self._load_font()

    def _load_font(self):
        """Load font for text labels."""
        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.font_size)
        except Exception:
            try:
                self.font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", self.font_size)
            except Exception:
                self.font = ImageFont.load_default()

    def draw_bbox(self, image: Image.Image, bbox: Tuple[int, int, int, int], 
                  label: Optional[str] = None) -> Image.Image:
        """Draw bounding box on image."""
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        
        # bbox format: (x_topleft, y_topleft, x_bottomright, y_bottomright)
        x_tl, y_tl, x_br, y_br = bbox
        
        # Draw rectangle
        draw.rectangle([x_tl, y_tl, x_br, y_br], 
                      outline=self.bbox_color, 
                      width=self.bbox_thickness)
        
        # Draw label if provided
        if label:
            text_bbox = draw.textbbox((x_tl, max(0, y_tl - self.font_size - 8)), 
                                     label, font=self.font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            padding = 6
            bg_rect = [x_tl - padding, 
                      max(0, y_tl - text_height - padding * 2), 
                      x_tl + text_width + padding, 
                      max(0, y_tl - padding)]
            draw.rectangle(bg_rect, fill=self.bbox_color)
            draw.text((x_tl, max(0, y_tl - text_height - padding)), 
                     label, fill=self.text_color, font=self.font)
        
        return annotated

    def save_annotated_image(self, image_path: str, bbox: Tuple[int, int, int, int], 
                            label: str, output_path: str) -> str:
        """Load image, annotate it, and save to output path."""
        image = Image.open(image_path)
        annotated = self.draw_bbox(image, bbox, label)
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        annotated.save(output_path)
        return output_path


def load_ground_data(json_path: str) -> List[Dict]:
    """Load ground data from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def process_entry(entry: Dict, detector: BboxDetector, annotator: ImageAnnotator, 
                 output_dir: str, entry_idx: int) -> Dict:
    """Process a single entry from the JSON file."""
    # Extract question and image path
    if not entry.get("conversations") or len(entry["conversations"]) == 0:
        return {"status": "error", "message": "No conversations found"}
    
    question = entry["conversations"][0].get("value", "")
    if not question:
        return {"status": "error", "message": "No question found"}
    
    # Question already contains <image> tag, use it directly
    
    if not entry.get("images") or len(entry["images"]) == 0:
        return {"status": "error", "message": "No image path found"}
    
    image_path = entry["images"][0]
    
    if not os.path.exists(image_path):
        return {"status": "error", "message": f"Image not found: {image_path}"}
    
    # Get ground truth bbox for comparison (if available)
    gt_bbox = None
    if len(entry["conversations"]) > 1:
        gt_value = entry["conversations"][1].get("value", "")
        if gt_value:
            try:
                gt_data = json.loads(gt_value)
                gt_bbox = (
                    gt_data.get("x_topleft", 0),
                    gt_data.get("y_topleft", 0),
                    gt_data.get("x_bottomright", 0),
                    gt_data.get("y_bottomright", 0)
                )
            except:
                pass
    
    # Detect bbox using model
    predicted_bbox = detector.detect_bbox(image_path, question)
    
    if predicted_bbox is None:
        return {
            "status": "error",
            "message": "Failed to detect bbox",
            "image_path": image_path,
            "question": question
        }
    
    # Create output path
    image_name = Path(image_path).stem
    output_path = os.path.join(output_dir, f"{entry_idx:05d}_{image_name}_bbox.png")
    
    # Draw and save annotated image
    label = f"Predicted: {predicted_bbox}"
    annotator.save_annotated_image(image_path, predicted_bbox, label, output_path)
    
    result = {
        "status": "success",
        "image_path": image_path,
        "question": question,
        "predicted_bbox": predicted_bbox,
        "output_path": output_path
    }
    
    if gt_bbox:
        result["ground_truth_bbox"] = gt_bbox
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Draw bounding boxes on images using vision model predictions"
    )
    parser.add_argument(
        "--input_json",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/ground_data_image_to_bbox/ground_data1_update.json",
        help="Path to input JSON file with ground data"
    )
    parser.add_argument(
        "--single_image",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference/text_to_image_output/evaluate_data_combination2,3,4_inference_results/item_0001/screenshots/screenshot_0009.png",
        help="Optional: path to a single image to process instead of JSON"
    )
    parser.add_argument(
        "--question",
        type=str,
        default="Where shall I click if I want to Click the 'Tools' section? Please output the bounding box coordinates in JSON format with: \"x_topleft\", \"y_topleft\", \"x_bottomright\", \"y_bottomright\" for the click area or button.",
        help="Optional: action/question string to ask for bbox with single_image"
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/LLaMA-Factory/saves/qwen2_5vl-7b/full/sft_update",
        help="Path to the vision model"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference",
        help="Output directory for annotated images"
    )
    parser.add_argument(
        "--output_name",
        type=str,
        default="tools_begin_bbox.png",
        help="Optional: explicit output filename for single_image mode"
    )
    parser.add_argument(
        "--max_items",
        type=int,
        default=None,
        help="Maximum number of items to process (for testing)"
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("Bounding Box Detection and Visualization")
    print("=" * 80)
    print(f"Using GPUs: {os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set')}")
    print(f"Input JSON: {args.input_json}")
    print(f"Model path: {args.model_path}")
    print(f"Output directory: {args.output_dir}")
    print()
    
    # Check if model path exists
    if not os.path.exists(args.model_path):
        print(f"❌ Error: Model path does not exist: {args.model_path}")
        return
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Single-image mode
    if args.single_image and args.question:
        print("\nInitializing vision model (single image mode)...")
        detector = BboxDetector(args.model_path)
        detector.initialize()
        print("✓ Model initialized")

        annotator = ImageAnnotator()

        image_path = args.single_image
        question = args.question

        if not os.path.exists(image_path):
            print(f"❌ Error: Image does not exist: {image_path}")
            return

        print("\nRunning inference for single image...")
        predicted_bbox = detector.detect_bbox(image_path, question)
        if predicted_bbox is None:
            print("❌ Error: Failed to detect bbox for the provided image/question")
            return

        from pathlib import Path
        image_name = Path(image_path).stem
        out_name = args.output_name if args.output_name else f"{image_name}_bbox.png"
        output_path = os.path.join(args.output_dir, out_name)

        label = f"Predicted: {predicted_bbox}"
        annotator.save_annotated_image(image_path, predicted_bbox, label, output_path)
        print(f"\n✓ Saved annotated image: {output_path}")
        return

    # JSON-driven batch mode
    print("Loading ground data...")
    ground_data = load_ground_data(args.input_json)
    print(f"✓ Loaded {len(ground_data)} entries")
    
    # Limit items if specified
    if args.max_items:
        ground_data = ground_data[:args.max_items]
        print(f"Limited to {len(ground_data)} items for testing")
    
    # Initialize model
    print("\nInitializing vision model...")
    detector = BboxDetector(args.model_path)
    detector.initialize()
    print("✓ Model initialized")
    
    # Initialize annotator
    annotator = ImageAnnotator()
    
    # Process each entry
    print(f"\nProcessing {len(ground_data)} entries...")
    results = []
    
    for idx, entry in enumerate(tqdm(ground_data, desc="Processing")):
        try:
            result = process_entry(entry, detector, annotator, args.output_dir, idx)
            results.append(result)
            
            if result["status"] == "error":
                print(f"\n⚠️ Entry {idx}: {result.get('message', 'Unknown error')}")
            
            # Clean up GPU cache after each inference to prevent memory buildup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        except RuntimeError as e:
            if "CUDA out of memory" in str(e):
                print(f"\n❌ Entry {idx}: CUDA out of memory - skipping")
                results.append({
                    "status": "error",
                    "message": "CUDA out of memory",
                    "entry_idx": idx
                })
                # Clear cache and continue
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    # Try to free up more memory
                    gc.collect()
            else:
                print(f"\n❌ Entry {idx}: {str(e)}")
                results.append({
                    "status": "error",
                    "message": str(e),
                    "entry_idx": idx
                })
        except Exception as e:
            print(f"\n❌ Entry {idx}: Unexpected error - {str(e)}")
            results.append({
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "entry_idx": idx
            })
    
    # Save results summary
    results_json = os.path.join(args.output_dir, "results_summary.json")
    with open(results_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total entries: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Results saved to: {results_json}")
    print(f"Annotated images saved to: {args.output_dir}")


if __name__ == "__main__":
    main()

