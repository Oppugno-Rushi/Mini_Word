#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate image-to-bbox training data from a MiniWord trajectory file.

Output format (array of samples):
[
  {
    "conversations": [
      {"from": "human", "value": "<image>user instruction"},
      {"from": "gpt",   "value": "x: 28, y: 440, width: 293, height: 114, right: 321, bottom: 554"}
    ],
    "images": [
      "image path (required)"
    ]
  }
]

By default, this script reads:
- trajectory:   function_tree_7/trajectory.json
- explanations: explainations_for_botton.json
and writes:
- dataset:      training_data_image/dataset.json
"""

import os
import json
import argparse
import textwrap
from typing import Any, Dict, List, Optional, Tuple


def read_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def normalize_text(text: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() or ch.isspace() else ' ' for ch in text).strip()


def tokens(text: str) -> List[str]:
    return [t for t in normalize_text(text).split() if t]


def label_from_action_button_path(action_button_path: str) -> str:
    # Example: function_tree_7/file/file_open/Paste_document_content.../action_button.png
    # We want the directory name before the file (e.g., "Paste_document_content...")
    parts = action_button_path.replace('\\', '/').split('/')
    if len(parts) >= 2:
        parent_dir = parts[-2]
        return parent_dir.replace('_', ' ')
    return os.path.splitext(os.path.basename(action_button_path))[0].replace('_', ' ')


def humanize_name(raw: str) -> str:
    name = raw or ''
    name = name.replace('mw2_', '')
    name = name.replace('_', ' ')
    name = name.replace('-', ' ')
    return ' '.join(w.capitalize() for w in name.split())


class Config:
    USE_LLM: bool = False
    PROMPT_PATH: Optional[str] = None
    LLM_MODEL: str = os.environ.get('MW_LLM_MODEL', 'gpt-4o-mini')
    API_BASE: str = os.environ.get('MW_LLM_API_BASE', 'https://api.openai.com/v1/chat/completions')


def generate_instruction_with_llm(section: str,
                                  function_id: str,
                                  action_key: str,
                                  description: str,
                                  function_description: str,
                                  action_button_path: Optional[str]) -> Optional[str]:
    if not Config.USE_LLM or not Config.PROMPT_PATH:
        return None
    try:
        with open(Config.PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_template = f.read().strip()
    except Exception:
        return None

    # Build a single input block as the prompt instructs
    input_block = textwrap.dedent(f"""
    Input: section={section}, function_id={function_id}, action_key={action_key}, description={description or ''}, function_description={function_description or ''}, action_button_path={action_button_path or ''}
    """)

    prompt = f"{prompt_template}\n\n{input_block}\nOutput:"

    # Call OpenAI-compatible API via requests (optional)
    try:
        import requests
        api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('MW_LLM_API_KEY')
        if not api_key:
            return None
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'model': Config.LLM_MODEL,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.2,
        }
        resp = requests.post(Config.API_BASE, headers=headers, json=data, timeout=30)
        if resp.status_code != 200:
            return None
        j = resp.json()
        # OpenAI format
        content = j.get('choices', [{}])[0].get('message', {}).get('content', '')
        content = (content or '').strip()
        if content:
            # Ensure single-line instruction
            return ' '.join(content.splitlines()).strip()
        return None
    except Exception:
        return None


def build_user_instruction(section: str,
                           function_id: str,
                           action_key: str,
                           action_desc: str,
                           function_desc: str,
                           action_button_path: Optional[str],
                           explain_index: Dict[str, Dict[str, List[str]]]) -> str:
    # 1) Try LLM-based instruction if enabled
    llm_sentence = generate_instruction_with_llm(
        section=section,
        function_id=function_id,
        action_key=action_key,
        description=action_desc,
        function_description=function_desc,
        action_button_path=action_button_path,
    )
    if llm_sentence:
        return llm_sentence

    # Try to map via explanations usage lines; build a UI-visible label first
    usage_lines = explain_index.get(section.lower(), {}).get(function_id, [])

    # Prefer real UI strings in this order: Execute action text -> action_button folder name -> action_key prettified
    ui_label = ''
    if action_desc and action_desc.lower().startswith('execute action:'):
        ui_label = action_desc.split(':', 1)[1].strip()
    elif action_button_path:
        ui_label = label_from_action_button_path(action_button_path)
    else:
        ui_label = action_key.replace('_', ' ')
    label = ui_label.strip()

    # Attempt fuzzy match to usage lines
    label_tokens = set(tokens(label))
    best_line: Optional[Tuple[int, str]] = None
    for line in usage_lines:
        lt = set(tokens(line))
        score = len(label_tokens & lt)
        if score > 0 and (best_line is None or score > best_line[0]):
            best_line = (score, line)

    if best_line:
        return f"In {humanize_name(section)} > {humanize_name(function_id)}, {best_line[1]}"

    # Fallbacks using action description
    desc = action_desc or ''
    # Special case: color selection under Format -> text_color, produce concrete color wording when possible
    if section.lower() == 'format' and function_id == 'text_color':
        rgba_text = ''
        if 'rgba' in desc.lower():
            rgba_text = desc
        elif action_button_path and 'rgba' in action_button_path:
            rgba_text = action_button_path
        if rgba_text:
            lower = rgba_text.lower()
            import re
            m = re.search(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', lower)
            if m:
                r, g, b = map(int, m.groups())
                color_name = None
                mapping = {
                    (0, 0, 0): 'black',
                    (255, 0, 0): 'red',
                    (0, 255, 0): 'green',
                    (0, 0, 255): 'blue',
                    (255, 255, 0): 'yellow',
                    (255, 0, 255): 'magenta',
                    (0, 255, 255): 'cyan',
                }
                color_name = mapping.get((r, g, b))
                # Treat grays
                if color_name is None and abs(r-g) < 3 and abs(g-b) < 3:
                    color_name = 'grey'
                if color_name:
                    return f"In {humanize_name(section)} > {humanize_name(function_id)}, choose {color_name} color from the color square"
                return f"In {humanize_name(section)} > {humanize_name(function_id)}, choose a color from the color square"
    if 'input field' in desc.lower():
        return f"In {humanize_name(section)} > {humanize_name(function_id)}, enter the content in the '{label}' box"
    if desc.lower().startswith('execute action:'):
        act = desc.split(':', 1)[1].strip()
        return f"In {humanize_name(section)} > {humanize_name(function_id)}, click '{act}'"
    if any(k in desc.lower() for k in ['apply', 'toggle', 'insert', 'save', 'open', 'create', 'print', 'choose', 'select', 'click']):
        return f"In {humanize_name(section)} > {humanize_name(function_id)}, {desc.strip()}"

    # If function description is informative, use it as instruction fallback
    if function_desc and function_desc.strip():
        return f"In {humanize_name(section)} > {humanize_name(function_id)}, {function_desc.strip()}"

    # Generic fallback
    return f"In {humanize_name(section)} > {humanize_name(function_id)}, click '{label}'"


def build_gpt_bbox_response(bbox: Dict[str, Any]) -> str:
    x = bbox.get('x')
    y = bbox.get('y')
    w = bbox.get('width')
    h = bbox.get('height')
    r = bbox.get('right')
    b = bbox.get('bottom')
    return f"x: {x}, y: {y}, width: {w}, height: {h}, right: {r}, bottom: {b}"


def index_explanations(explain_json: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    # section(lower) -> function_id -> usage lines
    result: Dict[str, Dict[str, List[str]]] = {}
    root = explain_json.get('MiniWord_Button_Documentation', {})
    sections = root.get('sections', {})
    for section_name, section_obj in sections.items():
        lower_sec = section_name.lower()
        if lower_sec not in result:
            result[lower_sec] = {}
        for btn in section_obj.get('buttons', []):
            fid = btn.get('id')
            usage = btn.get('usage', []) or []
            if fid:
                result[lower_sec][fid] = usage
    return result


def traverse_actions(node: Dict[str, Any],
                     parent_status_img: Optional[str],
                     section: str,
                     function_id: Optional[str],
                     function_desc: str,
                     explain_index: Dict[str, Dict[str, List[str]]],
                     out_samples: List[Dict[str, Any]]) -> None:
    # Use the nearest ancestor (or self) status image that represents the UI before applying this action
    current_img = node.get('status') or parent_status_img

    actions = node.get('action', {}) or {}
    for action_key, action_node in actions.items():
        bbox = action_node.get('coordinates_bbox')
        action_button_path = action_node.get('action_button')
        desc = action_node.get('description', '')

        # If bbox present and we have an image (status), create a sample
        if bbox and current_img:
            user_instruction = build_user_instruction(
                section=section,
                function_id=function_id or '',
                action_key=action_key,
                action_desc=desc,
                function_desc=function_desc,
                action_button_path=action_button_path,
                explain_index=explain_index,
            )
            gpt_value = build_gpt_bbox_response(bbox)
            sample = {
                "conversations": [
                    {"from": "human", "value": f"<image>{user_instruction}"},
                    {"from": "gpt", "value": gpt_value},
                ],
                "images": [current_img],
            }
            out_samples.append(sample)

        # Recurse into deeper actions
        traverse_actions(
            node=action_node,
            parent_status_img=current_img,
            section=section,
            function_id=function_id,
            function_desc=function_desc,
            explain_index=explain_index,
            out_samples=out_samples,
        )


def build_dataset(trajectory: Dict[str, Any], explain_index: Dict[str, Dict[str, List[str]]]) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []

    root = trajectory.get('initial page', {})
    sections = root.get('action', {}) or {}

    for section_key, section_node in sections.items():
        functions = section_node.get('action', {}) or {}
        for function_id, function_node in functions.items():
            # The function node's status image will be used for its child actions
            traverse_actions(
                node=function_node,
                parent_status_img=function_node.get('status'),
                section=section_key,
                function_id=function_id,
                function_desc=function_node.get('description', ''),
                explain_index=explain_index,
                out_samples=samples,
            )

    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate image-to-bbox training data from trajectory.json")
    parser.add_argument('--trajectory', type=str, default='/shared/nas/data/m1/jiateng5/Mini_Word/function_tree_7/trajectory.json', help='Path to trajectory.json')
    parser.add_argument('--explanations', type=str, default='/shared/nas/data/m1/jiateng5/Mini_Word/explainations_for_botton.json', help='Path to explainations_for_botton.json')
    parser.add_argument('--output', type=str, default='/shared/nas/data/m1/jiateng5/Mini_Word/training_data_image/dataset.json', help='Output dataset path (JSON array)')
    parser.add_argument('--use_llm', action='store_true', help='Use action_map_prompt.txt with an LLM to generate user instruction')
    parser.add_argument('--prompt', type=str, default='/shared/nas/data/m1/jiateng5/Mini_Word/training_data_image/action_map_prompt.txt', help='Prompt file for instruction generation')
    parser.add_argument('--llm_model', type=str, default=None, help='LLM model name (OpenAI-compatible)')
    parser.add_argument('--api_base', type=str, default=None, help='OpenAI-compatible chat completions endpoint')
    args = parser.parse_args()

    # Configure optional LLM usage
    Config.USE_LLM = bool(args.use_llm)
    Config.PROMPT_PATH = args.prompt
    if args.llm_model:
        Config.LLM_MODEL = args.llm_model
    if args.api_base:
        Config.API_BASE = args.api_base

    trajectory = read_json(args.trajectory)
    explain_json = read_json(args.explanations)
    explain_index = index_explanations(explain_json)

    dataset = build_dataset(trajectory, explain_index)

    ensure_dir(args.output)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"✓ Wrote {len(dataset)} samples to: {args.output}")


if __name__ == '__main__':
    main()


