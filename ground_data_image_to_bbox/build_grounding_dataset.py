#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build an image grounding dataset from function_tree_8/trajectory.json.

For each node that contains both a begin image and coordinates_bbox,
emit a dataset item in the format:

[
  {
    "conversations": [
      {"from": "human", "value": "<image>Where shall I click if I want to {action}?"},
      {"from": "gpt",   "value": "x_topleft={x_topleft}, y_topleft={y_topleft}, x_bottomright={x_bottomright}, y_bottomright={y_bottomright}"}
    ],
    "images": ["/abs/path/to/begin.png"]
  },
  ...
]

Outputs to: ground_data.json (project root)
"""

import json
import os
from typing import Any, Dict, List


def to_sentence_fragment(text: str) -> str:
    """Make description read naturally inside the question template."""
    if not text:
        return "perform this action"
    text = text.strip()
    if not text:
        return "perform this action"
    return text[0].lower() + text[1:]


def make_abs(path: str, repo_root: str) -> str:
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.abspath(os.path.join(repo_root, path))


def has_valid_bbox(node: Dict[str, Any]) -> bool:
    bbox = node.get("coordinates_bbox") or {}
    return all(k in bbox for k in ("x_topleft", "y_topleft", "x_bottomright", "y_bottomright"))


def collect_items_from_node(node: Dict[str, Any], repo_root: str, out: List[Dict[str, Any]]) -> None:
    if not isinstance(node, dict):
        return

    begin_path = node.get("begin")
    if begin_path and has_valid_bbox(node):
        abs_begin = make_abs(begin_path, repo_root)
        if os.path.exists(abs_begin):
            desc = to_sentence_fragment(node.get("description", ""))
            bbox = node.get("coordinates_bbox", {})
            x_topleft = bbox.get("x_topleft")
            y_topleft = bbox.get("y_topleft")
            x_bottomright = bbox.get("x_bottomright")
            y_bottomright = bbox.get("y_bottomright")
            item = {
                "conversations": [
                    {
                        "from": "human",
                        "value": f"<image>Where shall I click if I want to {desc}? Please output the bounding box coordinates in the format: x_topleft, y_topleft, x_bottomright, y_bottomright.",
                    },
                    {
                        "from": "gpt",
                        "value": f"x_topleft={x_topleft}, y_topleft={y_topleft}, x_bottomright={x_bottomright}, y_bottomright={y_bottomright}",
                    },
                ],
                "images": [abs_begin],
            }
            out.append(item)

    children = node.get("action")
    if isinstance(children, dict):
        for child in children.values():
            collect_items_from_node(child, repo_root, out)


def main() -> None:
    traj_path = "/shared/nas/data/m1/jiateng5/Mini_Word/function_tree_12/trajectory.json"
    out_path = "/shared/nas/data/m1/jiateng5/Mini_Word/ground_data_image_to_bbox/ground_data_new.json"
    repo_root = "/shared/nas/data/m1/jiateng5/Mini_Word"  # Base directory for resolving relative image paths

    with open(traj_path, "r", encoding="utf-8") as f:
        traj = json.load(f)

    items: List[Dict[str, Any]] = []

    if isinstance(traj, dict):
        for node in traj.values():
            collect_items_from_node(node, repo_root, items)
    else:
        collect_items_from_node(traj, repo_root, items)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"✓ Wrote {len(items)} items to {out_path}")


if __name__ == "__main__":
    main()


