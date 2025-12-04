#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update the bbox coordinates in ground_data1.json based on function_tree_11/trajectory.json.

This script:
1. Reads ground_data1.json 
2. For each item, finds the corresponding node in function_tree_10/trajectory.json by image path
3. Finds the same node in function_tree_11/trajectory.json
4. Converts the new bbox format (x_topleft, y_topleft, x_bottomright, y_bottomright) 
   to the old format (x, y, width, height)
5. Updates only the "value" part in ground_data1.json while preserving all other fields
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple


def make_abs(path: str, repo_root: str) -> str:
    """Convert relative path to absolute path."""
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.abspath(os.path.join(repo_root, path))


def normalize_path(path: str) -> str:
    """Normalize path for comparison (handle function_tree_X differences).
    
    Extracts the relative path after function_tree_X/ for matching across different trees.
    Works for both absolute (..../function_tree_X/...) and relative (function_tree_X/...) paths.
    """
    marker = "function_tree_"
    idx = path.find(marker)
    if idx == -1:
        return path
    # Position after "function_tree_" prefix
    rest = path[idx + len(marker):]
    # Drop the version number and following slash
    # rest looks like "10/dir1/dir2/file.png" → want "dir1/dir2/file.png"
    slash_pos = rest.find("/")
    if slash_pos == -1:
        return rest
    return rest[slash_pos + 1:]


def parse_bbox_from_value(value_str: str) -> Optional[Dict[str, int]]:
    """Legacy helper (kept for compatibility). Not required for update.

    Returns None always to avoid relying on old-format parsing.
    """
    return None


def find_node_by_image(traj: Dict[str, Any], target_image: str) -> Optional[Dict[str, Any]]:
    """Recursively find a node in trajectory by matching the begin image path.
    
    Args:
        traj: The trajectory tree to search (can be top-level dict or a node)
        target_image: The image path from ground_data1.json (can be absolute or relative)
    
    Returns:
        The matching node or None
    """
    if not isinstance(traj, dict):
        return None
    
    # Handle top-level dict structure like {"initial page": {...}}
    # If this dict has keys that look like descriptions but has no "begin" field,
    # treat it as containing child nodes
    if "begin" not in traj and traj:
        # Check if this is the top-level structure - iterate over values
        for child in traj.values():
            found = find_node_by_image(child, target_image)
            if found is not None:
                return found
        return None
    
    # Check current node
    begin_path = traj.get("begin", "")
    if begin_path:
        # Normalize both paths for comparison (extract part after function_tree_X/)
        normalized_target = normalize_path(target_image)
        normalized_begin = normalize_path(begin_path)
        
        # Match by the normalized path (without function_tree_X prefix)
        if normalized_target == normalized_begin:
            return traj
    
    # Check children
    actions = traj.get("action", {})
    if isinstance(actions, dict):
        for child in actions.values():
            found = find_node_by_image(child, target_image)
            if found is not None:
                return found
    
    return None


def convert_bbox_format(bbox_new: Dict[str, Any]) -> Dict[str, int]:
    """Convert from new format (x_topleft, y_topleft, x_bottomright, y_bottomright) 
    to old format (x, y, width, height)."""
    if "x_topleft" in bbox_new:
        x = bbox_new["x_topleft"]
        y = bbox_new["y_topleft"]
        x_br = bbox_new["x_bottomright"]
        y_br = bbox_new["y_bottomright"]
        width = x_br - x
        height = y_br - y
        return {"x": x, "y": y, "width": width, "height": height}
    elif "x" in bbox_new:
        # Already in old format; approximate conversion back to corners
        x = int(bbox_new.get("x", 0))
        y = int(bbox_new.get("y", 0))
        w = int(bbox_new.get("width", 0))
        h = int(bbox_new.get("height", 0))
        return {"x": x, "y": y, "width": w, "height": h}
    else:
        raise ValueError(f"Unknown bbox format: {bbox_new}")


def find_matching_node_in_tree11(
    node_tree10: Dict[str, Any], 
    traj_tree11: Dict[str, Any],
    repo_root: str
) -> Optional[Dict[str, Any]]:
    """Find the corresponding node in tree11 by matching image path structure.
    
    Uses the same normalize_path logic to match nodes across different function_tree_X directories.
    """
    if not isinstance(node_tree10, dict):
        return None
    
    description = node_tree10.get("description", "")
    begin_path = node_tree10.get("begin", "")
    
    if not begin_path:
        return None
    
    # Normalize the path to match (extract part after function_tree_X/)
    normalized_path = normalize_path(begin_path)
    
    # Search in tree11 recursively
    def search_recursive(traj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(traj, dict):
            return None
        
        # Handle top-level dict structure like {"initial page": {...}}
        if "begin" not in traj and traj:
            # Iterate over top-level values
            for child in traj.values():
                found = search_recursive(child)
                if found is not None:
                    return found
            return None
        
        # Check if this node matches
        curr_begin = traj.get("begin", "")
        curr_desc = traj.get("description", "")
        
        if curr_begin:
            normalized_curr = normalize_path(curr_begin)
            # Match by normalized path (path after function_tree_X/)
            if normalized_path == normalized_curr:
                # Also verify description matches if both have it (for safety)
                if description and curr_desc:
                    if description == curr_desc:
                        return traj
                else:
                    # If descriptions don't both exist, still match by path
                    return traj
        
        # Check children
        actions = traj.get("action", {})
        if isinstance(actions, dict):
            for child in actions.values():
                found = search_recursive(child)
                if found is not None:
                    return found
        
        return None
    
    return search_recursive(traj_tree11)


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # File paths
    ground_data_path = os.path.join(repo_root, "ground_data_image_to_bbox", "ground_data1.json")
    tree10_traj_path = os.path.join(repo_root, "function_tree_10", "trajectory.json")
    tree11_traj_path = os.path.join(repo_root, "function_tree_11", "trajectory.json")
    
    # Load files
    print(f"Loading {ground_data_path}...")
    with open(ground_data_path, "r", encoding="utf-8") as f:
        ground_data = json.load(f)
    
    print(f"Loading {tree10_traj_path}...")
    with open(tree10_traj_path, "r", encoding="utf-8") as f:
        traj_tree10 = json.load(f)
    
    print(f"Loading {tree11_traj_path}...")
    with open(tree11_traj_path, "r", encoding="utf-8") as f:
        traj_tree11 = json.load(f)
    
    updated_count = 0
    not_found_count = 0
    error_count = 0
    
    # Process each item in ground_data
    for idx, item in enumerate(ground_data):
        try:
            # Get the image path and current value
            if "images" not in item or not item["images"]:
                continue
            
            image_path = item["images"][0]
            
            # Get current bbox value from conversations
            conversations = item.get("conversations", [])
            if len(conversations) < 2:
                continue
            
            gpt_response = conversations[1]
            if gpt_response.get("from") != "gpt":
                continue
            
            current_value = gpt_response.get("value", "")
            # We no longer require parsing current value; we'll overwrite it from tree11
            
            # Find corresponding node in tree10
            node_tree10 = find_node_by_image(traj_tree10, image_path)
            if node_tree10 is None:
                print(f"Warning: Item {idx}: Node not found in tree10 for image: {image_path}")
                not_found_count += 1
                continue
            
            # Find matching node in tree11
            node_tree11 = find_matching_node_in_tree11(node_tree10, traj_tree11, repo_root)
            if node_tree11 is None:
                print(f"Warning: Item {idx}: Corresponding node not found in tree11 for image: {image_path}")
                not_found_count += 1
                continue
            
            # Get new bbox from tree11
            new_bbox_raw = node_tree11.get("coordinates_bbox")
            if not new_bbox_raw:
                print(f"Warning: Item {idx}: No bbox found in tree11 node for image: {image_path}")
                not_found_count += 1
                continue
            
            # Directly copy the coordinates_bbox JSON from tree11 into the value string
            try:
                new_value = json.dumps(new_bbox_raw, ensure_ascii=False)
            except Exception as e:
                print(f"Warning: Item {idx}: Error serializing coordinates_bbox: {e}")
                error_count += 1
                continue
            gpt_response["value"] = new_value
            updated_count += 1
            
            if (idx + 1) % 100 == 0:
                print(f"Processed {idx + 1} items...")
        
        except Exception as e:
            print(f"Error processing item {idx}: {e}")
            error_count += 1
            continue
    
    # Save updated ground_data
    output_path = os.path.join(repo_root, "ground_data_image_to_bbox", "ground_data1_update.json")
    print(f"\nSaving updated data to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ground_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Update complete!")
    print(f"  Updated: {updated_count} items")
    print(f"  Not found: {not_found_count} items")
    print(f"  Errors: {error_count} items")
    print(f"  Total: {len(ground_data)} items")


if __name__ == "__main__":
    main()

