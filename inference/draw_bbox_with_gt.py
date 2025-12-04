#!/usr/bin/env python3
"""
Draw ground truth bounding boxes on images.

This script reads the ground data JSON file, extracts bbox coordinates
from GPT responses, and draws them on the corresponding images.
"""

import json
import os
import argparse
from typing import Optional, Tuple, List, Dict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm


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
        image.close()
        return output_path


def load_ground_data(json_path: str) -> List[Dict]:
    """Load ground data from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def parse_bbox_from_gpt_value(value: str) -> Optional[Tuple[int, int, int, int]]:
    """Parse bbox coordinates from GPT response value.
    
    Expected format: JSON string like '{"x_topleft": 4, "y_topleft": 34, "x_bottomright": 26, "y_bottomright": 57}'
    Returns: (x_topleft, y_topleft, x_bottomright, y_bottomright) or None
    """
    try:
        bbox_data = json.loads(value)
        x_tl = int(bbox_data.get('x_topleft', 0))
        y_tl = int(bbox_data.get('y_topleft', 0))
        x_br = int(bbox_data.get('x_bottomright', 0))
        y_br = int(bbox_data.get('y_bottomright', 0))
        
        # Validate bbox
        if x_tl >= x_br or y_tl >= y_br:
            return None
            
        return (x_tl, y_tl, x_br, y_br)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        return None


def process_entry(entry: Dict, annotator: ImageAnnotator, 
                 output_dir: str, entry_idx: int) -> Dict:
    """Process a single entry from the JSON file."""
    # Extract bbox from GPT response
    bbox = None
    action = None
    
    if not entry.get("conversations"):
        return {"status": "error", "message": "No conversations found", "entry_idx": entry_idx}
    
    for conv in entry["conversations"]:
        if conv.get("from") == "gpt":
            bbox_value = conv.get("value", "")
            if bbox_value:
                bbox = parse_bbox_from_gpt_value(bbox_value)
        elif conv.get("from") == "human":
            action = conv.get("value", "")
    
    if bbox is None:
        return {
            "status": "error", 
            "message": "Failed to parse bbox from GPT response",
            "entry_idx": entry_idx
        }
    
    # Extract image path
    if not entry.get("images") or len(entry["images"]) == 0:
        return {"status": "error", "message": "No image path found", "entry_idx": entry_idx}
    
    image_path = entry["images"][0]
    
    if not os.path.exists(image_path):
        return {
            "status": "error", 
            "message": f"Image not found: {image_path}",
            "entry_idx": entry_idx
        }
    
    # Create output path
    image_name = Path(image_path).stem
    output_path = os.path.join(output_dir, f"{entry_idx:05d}_{image_name}_gt_bbox.png")
    
    # Create label from action (shorten if too long)
    label = "GT Bbox"
    if action:
        # Remove <image> tag and shorten
        action_clean = action.replace("<image>", "").strip()
        if len(action_clean) > 50:
            action_clean = action_clean[:47] + "..."
        label = f"GT: {action_clean}"
    
    # Draw and save annotated image
    try:
        annotator.save_annotated_image(image_path, bbox, label, output_path)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to draw bbox: {str(e)}",
            "entry_idx": entry_idx
        }
    
    result = {
        "status": "success",
        "image_path": image_path,
        "bbox": bbox,
        "output_path": output_path,
        "entry_idx": entry_idx
    }
    
    if action:
        result["action"] = action
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Draw ground truth bounding boxes on images"
    )
    parser.add_argument(
        "--input_json",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/ground_data_image_to_bbox/ground_data1_update.json",
        help="Path to input JSON file with ground data"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference/bbox_output_gt",
        help="Output directory for annotated images"
    )
    parser.add_argument(
        "--max_items",
        type=int,
        default=None,
        help="Maximum number of items to process (for testing)"
    )
    parser.add_argument(
        "--bbox_color",
        type=str,
        default="red",
        help="Color for bounding box (default: red)"
    )
    parser.add_argument(
        "--bbox_thickness",
        type=int,
        default=3,
        help="Thickness of bounding box lines (default: 3)"
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("Ground Truth Bounding Box Visualization")
    print("=" * 80)
    print(f"Input JSON: {args.input_json}")
    print(f"Output directory: {args.output_dir}")
    print(f"Bbox color: {args.bbox_color}")
    print(f"Bbox thickness: {args.bbox_thickness}")
    print()
    
    # Check if input file exists
    if not os.path.exists(args.input_json):
        print(f"❌ Error: Input JSON file does not exist: {args.input_json}")
        return
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load ground data
    print("Loading ground data...")
    try:
        ground_data = load_ground_data(args.input_json)
        print(f"✓ Loaded {len(ground_data)} entries")
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        return
    
    # Limit items if specified
    if args.max_items:
        ground_data = ground_data[:args.max_items]
        print(f"Limited to {len(ground_data)} items for testing")
    
    # Initialize annotator
    annotator = ImageAnnotator(
        bbox_color=args.bbox_color,
        bbox_thickness=args.bbox_thickness
    )
    
    # Process each entry
    print(f"\nProcessing {len(ground_data)} entries...")
    results = []
    
    for idx, entry in enumerate(tqdm(ground_data, desc="Processing")):
        result = process_entry(entry, annotator, args.output_dir, idx)
        results.append(result)
        
        if result["status"] == "error":
            print(f"\n⚠️ Entry {idx}: {result.get('message', 'Unknown error')}")
    
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
    print()


if __name__ == "__main__":
    main()

