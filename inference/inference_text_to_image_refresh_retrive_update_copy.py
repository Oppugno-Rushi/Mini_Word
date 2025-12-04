"""
MiniWord Text-to-Image Inference Pipeline

This script takes the user's generated answers (steps) and:
1) Splits the answer into step-by-step actions
2) Formats each step into a bbox-detection question
3) Captures the initial UI screenshot
4) Uses Qwen2.5-VL to predict a bbox for each step given the screenshot
5) Draws the bbox and overlays the original step text next to it
6) Executes the action by clicking the bbox center, then captures the next screenshot
7) Repeats for all steps

Input JSON files (same schema):
- /shared/nas/data/m1/jiateng5/Mini_Word/inference/results/generate_data_combination2_inference_results.json
- /shared/nas/data/m1/jiateng5/Mini_Word/inference/results/generate_data_combination3_inference_results.json
- /shared/nas/data/m1/jiateng5/Mini_Word/inference/results/generate_data_combination4_inference_results.json

Each JSON contains a list of dicts: {"question": str, "answer": str}

Usage:
    python inference_text_to_image.py

Args:
    --vision_model: path to Qwen2.5-VL-7B model (fine-tuned)
    --inputs: list of input result json files
    --output_dir: directory for screenshots and annotations

Notes:
- Requires: Pillow, selenium, tqdm
- MiniWord must be running at http://localhost:8001
"""

import os
import re
import sys
import json
import time
import argparse
import shutil
import tempfile
import numpy as np
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Use GPU 1, 3, and 4
os.environ["CUDA_VISIBLE_DEVICES"] = "4,5"

# Add LLaMA-Factory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../LLaMA-Factory/src'))
from llamafactory.chat import ChatModel


import tempfile, shutil, atexit, os, uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# In your _setup_driver():
#self.driver = webdriver.Chrome(options=make_chrome_options())

# ===============================
# Utilities
# ===============================

def strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> blocks, if present."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)


def extract_steps(answer: str) -> List[str]:
    """
    Split the answer into one-sentence/one-action steps.
    - Remove <think> blocks
    - Split by newlines
    - Clean numbering like '1. ', '2) ', etc.
    - Drop empty lines
    """
    cleaned = strip_think_blocks(answer)
    lines = [ln.strip() for ln in cleaned.split('\n')]
    steps: List[str] = []
    for ln in lines:
        if not ln:
            continue
        # Remove leading numbering patterns: '1. ', '1) ', '1 - ', etc.
        ln = re.sub(r"^\s*\d+\s*[\.)-]\s*", "", ln)
        # Some lines might still be bullets
        ln = re.sub(r"^[-•]\s*", "", ln)
        # Filter out lines that are just section headers like "Click the 'File' section" is still valid
        if ln:
            steps.append(ln)
    return steps


def detect_file_upload(step_text: str) -> Optional[str]:
    """
    Detect if a step involves file upload and extract the filename.
    
    Examples:
        - "Select the file named 'sustainability_report.txt' from your computer"
        - "Select the image file 'story.png' from your computer"
        - "Choose File 'power.png'"
        - "Select a file from your computer"
    
    Returns:
        Filename if detected, None otherwise
    """
    step_lower = step_text.lower()
    
    # Keywords that indicate file upload operations
    upload_keywords = [
        'select the file', 'select file', 'select a file', 'select the image file',
        'choose file', 'choose the file', 'upload', 'select document',
        'file named', 'image file', 'document file', 'select'
    ]
    
    # Check if step contains upload-related keywords
    has_upload_keyword = any(keyword in step_lower for keyword in upload_keywords)
    
    if not has_upload_keyword:
        return None
    
    # Extract potential filename (with extension)
    # Priority patterns - more specific first
    
    # Pattern 1: 'filename.ext' or "filename.ext" (with quotes)
    # Matches: "Select the file named 'sustainability_report.txt'"
    quoted_pattern = r"['\"]([\w\-_]+\.(txt|html|htm|md|png|jpg|jpeg|gif|pdf|doc|docx))['\"]"
    match = re.search(quoted_pattern, step_text, re.IGNORECASE)
    if match:
        filename = match.group(1)
        return filename
    
    # Pattern 2: "named 'filename.ext'" or "named \"filename.ext\""
    named_pattern = r"named\s+['\"]([\w\-_]+\.(txt|html|htm|md|png|jpg|jpeg|gif|pdf|doc|docx))['\"]"
    match = re.search(named_pattern, step_text, re.IGNORECASE)
    if match:
        filename = match.group(1)
        return filename
    
    # Pattern 3: filename.ext without quotes (but must have file extension)
    # Matches: "Select the file sustainability_report.txt from your computer"
    unquoted_pattern = r"\b([\w\-_]+\.(txt|html|htm|md|png|jpg|jpeg|gif|pdf|doc|docx))\b"
    match = re.search(unquoted_pattern, step_text, re.IGNORECASE)
    if match:
        filename = match.group(1)
        return filename
    
    # Pattern 4: Known file patterns (backup)
    known_files = [
        r'(sustainability_report\.txt)',
        r'(short_story\.txt)',
        r'(power\.png)',
        r'(story\.png)',
        r'(logol\.png)',
        r'(pig\.jpg)',
    ]
    for pattern in known_files:
        match = re.search(pattern, step_text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def format_action_for_bbox(action: str) -> str:
    """Wrap an action into the bbox-detection question template."""
    return (
        f"Where shall I click if I want to {action}? "
        "Please output the bounding box coordinates in JSON format with: "
        '"x_topleft", "y_topleft", "x_bottomright", "y_bottomright" for the click area or button.'
    )


# ===============================
# Vision model wrapper (Qwen2.5-VL-7B)
# ===============================

class BboxDetector:
    """Detect bounding boxes in screenshots using Qwen2.5-VL-7B."""

    def __init__(self, model_path: str, trajectory_path: str = "/shared/nas/data/m1/jiateng5/Mini_Word/function_tree_12/trajectory.json"):
        self.model_path = model_path
        self.model: Optional[ChatModel] = None
        self.trajectory_path = trajectory_path
        self.trajectory_data: Optional[Dict] = None
        self.load_trajectory()
        # First-layer menu whitelist (normalized keys)
        self.MENU_SECTION_KEYS = {"file", "edit", "view", "insert", "format", "tools", "help"}
        # Keep last retrieval info for logging
        self.last_match_info: Optional[Dict] = None
        self.last_failure_info: Optional[str] = None
        # Sentence-BERT availability (lazy loaded model)
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._sbert_available = True
        except Exception:
            self._sbert_available = False
        self._sbert_model = None

    def load_trajectory(self):
        """Load trajectory.json file."""
        try:
            if os.path.exists(self.trajectory_path):
                with open(self.trajectory_path, 'r', encoding='utf-8') as f:
                    self.trajectory_data = json.load(f)
                print(f"    ✓ Loaded trajectory data from {self.trajectory_path}")
            else:
                print(f"    Warning: Trajectory file not found: {self.trajectory_path}")
        except Exception as e:
            print(f"    Warning: Failed to load trajectory: {e}")

    def _normalize_name_to_key(self, name: str) -> str:
        """Convert action name to trajectory key format."""
        # Convert to lowercase, replace spaces with underscores
        key = name.lower().replace(' ', '_')
        return key

    def _get_sections(self) -> Dict:
        if not self.trajectory_data:
            return {}
        initial_page = self.trajectory_data.get('initial page', {})
        return initial_page.get('action', {}) if isinstance(initial_page, dict) else {}

    def resolve_section_key(self, section_name: str) -> Optional[str]:
        """Resolve a human section name to a top-level section key in trajectory."""
        sections = self._get_sections()
        if not sections:
            return None
        key = self._normalize_name_to_key(section_name)
        if key in sections and key in self.MENU_SECTION_KEYS:
            return key
        candidate = self._fuzzy_find_in_actions(sections, section_name)
        if candidate and candidate in self.MENU_SECTION_KEYS:
            return candidate
        return None

    def resolve_icon_key(self, section_key: Optional[str], icon_name: str) -> Optional[str]:
        """Resolve an icon/button name to a second-level key under the section."""
        if not section_key:
            return None
        sections = self._get_sections()
        section_node = sections.get(section_key, {}) if isinstance(sections, dict) else {}
        if not isinstance(section_node, dict):
            return None
        actions = section_node.get('action', {})
        if not isinstance(actions, dict):
            return None
        key = self._normalize_name_to_key(icon_name)
        if key in actions:
            return key
        return self._fuzzy_find_in_actions(actions, icon_name)

    def _iter_bbox_nodes_recursive(self, node: Dict):
        """Yield nodes (dicts) that contain coordinates_bbox recursively under node.action tree."""
        if not isinstance(node, dict):
            return
        if node.get('coordinates_bbox'):
            yield node
        child_actions = node.get('action')
        if isinstance(child_actions, dict):
            for child in child_actions.values():
                if isinstance(child, dict):
                    yield from self._iter_bbox_nodes_recursive(child)

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        return [t for t in text.split() if len(t) > 1]

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple token Jaccard similarity for description matching."""
        ta = set(self._tokenize(a))
        tb = set(self._tokenize(b))
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union else 0.0

    def _semantic_similarity(self, a: str, b: str) -> float:
        """Semantic similarity using Sentence-BERT cosine (fallback to Jaccard if unavailable)."""
        a = (a or "").strip()
        b = (b or "").strip()
        #import ipdb; ipdb.set_trace()
        if not a or not b:
            return 0.0
        if self._sbert_available:
            model = self._get_sbert_model()
            if model is not None:
                try:
                    emb = model.encode([a, b], normalize_embeddings=True)
                    # cosine similarity for normalized vectors is dot product
                    sim = float((emb[0] * emb[1]).sum())
                    # Clamp to [0,1] for safety if slight numeric drift
                    if sim < 0.0:
                        sim = 0.0
                    elif sim > 1.0:
                        sim = 1.0
                    return sim
                except Exception:
                    return self._text_similarity(a, b)
        return self._text_similarity(a, b)

    def _get_sbert_model(self):
        if self._sbert_model is not None:
            return self._sbert_model
        if not self._sbert_available:
            return None
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            # A lightweight, general-purpose English model
            self._sbert_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        except Exception:
            self._sbert_model = None
        return self._sbert_model

    def _fuzzy_find_in_actions(self, actions: Dict, name: str) -> Optional[str]:
        """Find a key in actions dict that best matches name (using key and description)."""
        if not isinstance(actions, dict):
            return None
        name_words = [w for w in name.split() if len(w) > 2 and w not in ['the', 'new', 'add', 'create', 'click']]
        if not name_words:
            name_words = name.split()
        best_key = None
        best_score = -1
        for candidate_key, candidate_node in actions.items():
            score = 0
            key_lower = str(candidate_key).lower()
            for w in name_words:
                if w.lower() in key_lower:
                    score += 2
            desc = (candidate_node.get('description', '') if isinstance(candidate_node, dict) else '').lower()
            for w in name_words:
                if w.lower() in desc:
                    score += 1
            if score > best_score:
                best_score = score
                best_key = candidate_key
        return best_key

    def _find_deep_bbox(self, action_sentence: str, previous_section: Optional[str], previous_icon: Optional[str]) -> Optional[Tuple[int, int, int, int]]:
        """Use previous section and icon context to locate deeper-level actions via description matching."""
        try:
            sections = self._get_sections()
            # Resolve section node (use given key directly; do not refuzzy here to avoid scope drift)
            section_key = previous_section if previous_section in sections else None
            if not section_key:
                return None
            section_node = sections.get(section_key, {})
            # Resolve icon node under section
            icon_actions = section_node.get('action', {}) if isinstance(section_node, dict) else {}
            icon_key = previous_icon if previous_icon in icon_actions else None
            icon_node = icon_actions.get(icon_key, {}) if icon_key else {}
            # If we don't have a valid icon node, do not expand to whole section to avoid drift
            if not icon_node or not isinstance(icon_node, dict):
                return None
            # Recursively search only inside icon subtree
            best = None
            best_sim = 0.0
            for node in self._iter_bbox_nodes_recursive(icon_node):
                desc = node.get('description', '')
                sim = self._semantic_similarity(action_sentence, desc)
                if sim > best_sim:
                    best_sim = sim
                    best = node
            if best and best.get('coordinates_bbox'):
                bbox_data = best['coordinates_bbox']
                x_tl = int(bbox_data.get('x_topleft', 0))
                y_tl = int(bbox_data.get('y_topleft', 0))
                x_br = int(bbox_data.get('x_bottomright', 0))
                y_br = int(bbox_data.get('y_bottomright', 0))
                if x_tl < x_br and y_tl < y_br:
                    self.last_match_info = {
                        'source': 'deep',
                        'path': f"{section_key} -> {icon_key}",
                        'description': best.get('description', ''),
                    }
                    return (x_tl, y_tl, x_br, y_br)
        except Exception:
            return None
        return None

    def _find_bbox_from_trajectory(self, action_sentence: str, previous_section: Optional[str] = None, previous_icon: Optional[str] = None, prev_section_valid: Optional[bool] = None) -> Optional[Tuple[int, int, int, int]]:
        """Find bbox from trajectory.json based on action sentence pattern, with deep-level matching."""
        
        if not self.trajectory_data:
            return None
        
        action_lower = action_sentence.lower()
        
        # Pattern 1: "Click the 'X' section" or "Click the X section" (first level) - support Unicode quotes
        section_pattern = r"click\s+(?:the\s+)?[\"'“”‘’]?\s*([a-z0-9][a-z0-9\s_\-]*?)\s*[\"'“”‘’]?\s+section"
        section_match = re.search(section_pattern, action_lower)
        if section_match:
            
            section_name = section_match.group(1).strip()
            section_key = self._normalize_name_to_key(section_name)
            
            # Look in trajectory: initial page -> action -> section_key
            try:
                actions = self._get_sections()
                section_node = actions.get(section_key)
                if section_node and 'coordinates_bbox' in section_node:
                    bbox_data = section_node['coordinates_bbox']
                    x_tl = int(bbox_data.get('x_topleft', 0))
                    y_tl = int(bbox_data.get('y_topleft', 0))
                    x_br = int(bbox_data.get('x_bottomright', 0))
                    y_br = int(bbox_data.get('y_bottomright', 0))
                    if x_tl < x_br and y_tl < y_br:
                        self.last_match_info = {
                            'source': 'section',
                            'path': f"{section_key}",
                            'description': section_node.get('description', ''),
                        }
                        print(f"    Found bbox from trajectory (section): {section_key}")
                        return (x_tl, y_tl, x_br, y_br)
                # Fuzzy across first layer if exact not found (key/description similarity)
                best_key = None
                best_score = 0.0
                for cand_key, cand_node in actions.items():
                    if not isinstance(cand_node, dict):
                        continue
                    key_text = str(cand_key).replace('_', ' ')
                    score_key = self._semantic_similarity(section_name, key_text)
                    score_desc = self._semantic_similarity(action_sentence, cand_node.get('description', '') or '')
                    score = 2.0 * score_key + 1.0 * score_desc
                    if cand_node.get('coordinates_bbox') and score > best_score:
                        best_score = score
                        best_key = cand_key
                if best_key is not None and best_score > 0.15:
                    node = actions[best_key]
                    bbox_data = node['coordinates_bbox']
                    x_tl = int(bbox_data.get('x_topleft', 0))
                    y_tl = int(bbox_data.get('y_topleft', 0))
                    x_br = int(bbox_data.get('x_bottomright', 0))
                    y_br = int(bbox_data.get('y_bottomright', 0))
                    if x_tl < x_br and y_tl < y_br:
                        self.last_match_info = {
                            'source': 'section_fuzzy',
                            'path': f"{best_key}",
                            'description': node.get('description', ''),
                        }
                        print(f"    Found bbox from trajectory (section, fuzzy): {best_key}")
                        return (x_tl, y_tl, x_br, y_br)
                # record failure for section
                self.last_failure_info = (
                    f"section_not_found: name='{section_name}', key='{section_key}', "
                    f"fuzzy_best='{best_key}', score={best_score:.2f}"
                )
            except Exception as e:
                self.last_failure_info = f"section_exception: {e}"
        
        # Pattern 2: "Click the X icon|button" (second level, requires previous section) - support Unicode quotes
        icon_pattern = r"click\s+(?:the\s+)?[\"'“”‘’]?\s*([a-z0-9][a-z0-9\s_\-]*?)\s*[\"'“”‘’]?\s+(?:icon|button)"
        icon_match = re.search(icon_pattern, action_lower)
        # Only honor icon-level retrieval when the previous action is a valid section click
        if icon_match and previous_section and (prev_section_valid is True):
            icon_name = icon_match.group(1).strip()
            icon_key = self._normalize_name_to_key(icon_name)
            
            # Look in trajectory: initial page -> action -> previous_section -> action -> icon_key
            try:
                actions = self._get_sections()
                section_node = actions.get(previous_section)
                
                if section_node:
                    section_actions = section_node.get('action', {})
                    icon_node = section_actions.get(icon_key)
                    # If exact key not found, try resolving under this section
                    if not icon_node:
                        alt_key = self.resolve_icon_key(previous_section, icon_name)
                        if alt_key:
                            icon_node = section_actions.get(alt_key)
                            icon_key = alt_key
                    
                    # Try exact match first
                    if icon_node and 'coordinates_bbox' in icon_node:
                        bbox_data = icon_node['coordinates_bbox']
                        x_tl = int(bbox_data.get('x_topleft', 0))
                        y_tl = int(bbox_data.get('y_topleft', 0))
                        x_br = int(bbox_data.get('x_bottomright', 0))
                        y_br = int(bbox_data.get('y_bottomright', 0))
                        if x_tl < x_br and y_tl < y_br:
                            self.last_match_info = {
                                'source': 'icon',
                                'path': f"{previous_section} -> {icon_key}",
                                'description': icon_node.get('description', ''),
                            }
                            print(f"    Found bbox from trajectory (icon): {previous_section} -> {icon_key}")
                            return (x_tl, y_tl, x_br, y_br)
                    
                    # Fuzzy match using key/description similarity within current section only
                    best_match_key = None
                    best_match_score = 0.0
                    for candidate_key, candidate_node in section_actions.items():
                        if not isinstance(candidate_node, dict):
                            continue
                        key_text = str(candidate_key).replace('_', ' ')
                        score_key = self._semantic_similarity(icon_name, key_text)
                        score_desc = self._semantic_similarity(action_sentence, candidate_node.get('description', '') or '')
                        score = 2.0 * score_key + 1.5 * score_desc
                        if candidate_node.get('coordinates_bbox') and score > best_match_score:
                            best_match_score = score
                            best_match_key = candidate_key
                    if best_match_key and best_match_score > 0:
                        matched_node = section_actions[best_match_key]
                        bbox_data = matched_node.get('coordinates_bbox')
                        if bbox_data:
                            x_tl = int(bbox_data.get('x_topleft', 0))
                            y_tl = int(bbox_data.get('y_topleft', 0))
                            x_br = int(bbox_data.get('x_bottomright', 0))
                            y_br = int(bbox_data.get('y_bottomright', 0))
                            if x_tl < x_br and y_tl < y_br:
                                self.last_match_info = {
                                    'source': 'icon_fuzzy',
                                    'path': f"{previous_section} -> {best_match_key}",
                                    'description': matched_node.get('description', ''),
                                }
                                print(f"    Found bbox from trajectory (icon, fuzzy match): {previous_section} -> {best_match_key} (matched '{icon_name}')")
                                return (x_tl, y_tl, x_br, y_br)
                    # record failure for icon under section
                    self.last_failure_info = (
                        f"icon_not_found: section='{previous_section}', icon_name='{icon_name}', "
                        f"key='{icon_key}', fuzzy_best='{best_match_key}', score={best_match_score:.2f}"
                    )
            except Exception as e:
                self.last_failure_info = f"icon_exception: {e}"
        
        # Deep-level: when not section/icon format, try to resolve using prior section+icon context
        #import ipdb; ipdb.set_trace()
        if previous_section:
            deep_bbox = self._find_deep_bbox(action_sentence, previous_section, previous_icon)
            if deep_bbox:
                # last_match_info is set inside _find_deep_bbox-like process below; ensure it's set if not
                if not self.last_match_info:
                    self.last_match_info = {
                        'source': 'deep',
                        'path': f"{previous_section} -> {previous_icon or '?'}",
                        'description': '',
                    }
                return deep_bbox
            else:
                if previous_icon is None:
                    self.last_failure_info = f"deep_skipped_no_icon: section='{previous_section}'"
                else:
                    self.last_failure_info = f"deep_no_match: section='{previous_section}', icon='{previous_icon}'"
        return None

    def initialize(self):
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
        
        # Fallback: try to parse 4 numbers (assuming topleft, topleft, bottomright, bottomright)
        numbers = re.findall(r"\d+", text)
        if len(numbers) >= 4:
            try:
                x_tl, y_tl, x_br, y_br = [int(n) for n in numbers[:4]]
                # Validate that it's a valid bbox
                if x_tl < x_br and y_tl < y_br:
                    return (x_tl, y_tl, x_br, y_br)
            except ValueError:
                pass
        
        # Legacy format support (x, y, w, h) - convert to topleft/bottomright
        patterns = [
            (r"\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))),
            (r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]", lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))),
            (r"x:\s*(\d+),\s*y:\s*(\d+),\s*w:\s*(\d+),\s*h:\s*(\d+)", lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))),
        ]
        for pattern, converter in patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    x, y, val3, val4 = converter(m)
                    # Check if it's (x, y, w, h) format
                    if val3 > 100 or val4 > 100:  # width/height are usually larger than coordinates
                        # Assume (x, y, w, h) format
                        return (x, y, x + val3, y + val4)
                    else:
                        # Assume (x_tl, y_tl, x_br, y_br) format
                        return (x, y, val3, val4)
                except (ValueError, IndexError):
                    continue
        return None

    def detect_bbox(self, image_path: str, formatted_action: str, original_action: str = "", previous_section: Optional[str] = None, previous_icon: Optional[str] = None, prev_section_valid: Optional[bool] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect bbox using trajectory.json first, then fall back to vision model.
        
        Args:
            image_path: Path to screenshot image
            formatted_action: Formatted action for vision model (e.g., "Where shall I click if I want to...")
            original_action: Original action sentence (for pattern matching)
            previous_section: Previous section name (for second-level icon lookup)
        """
        # If action mentions cursor, skip trajectory and use model to infer click/selection area
        # Reset last infos
        self.last_match_info = None
        self.last_failure_info = None

        if original_action and ('cursor' in original_action.lower()):
            # For cursor/editor operations, do not detect any bbox; handle via editor actions only
            self.last_match_info = {
                'source': 'cursor_editor',
                'path': '',
                'description': 'editor operation (no bbox)'
            }
            return None
        else:
            # Try trajectory.json first if we have original_action
            if original_action:
                bbox_from_traj = self._find_bbox_from_trajectory(original_action, previous_section, previous_icon, prev_section_valid)
                if bbox_from_traj:
                    return bbox_from_traj
        
        # Fall back to vision model
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        image = Image.open(image_path)
        
        # Use the correct format for vision models
        messages = [{"role": "user", "content": formatted_action}]
        
        try:
            # Pass image as separate parameter
            response = self.model.chat(messages, images=[image])[0].response_text
        except Exception as e:
            print(f"Error calling model: {e}")
            # Try alternative format
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": formatted_action},
                ]
            }]
            response = self.model.chat(messages)[0].response_text
        
        bbox = self.parse_bbox(response)
        if bbox is None:
            print(f"Warning: Could not parse bbox from response: {response}")
        else:
            # Record that bbox came from model
            self.last_match_info = self.last_match_info or {
                'source': 'model',
                'path': '',
                'description': '',
            }
        return bbox


# ===============================
# Image annotation and UI interaction
# ===============================

class ImageAnnotator:
    def __init__(self, font_size: int = 20, bbox_color: str = "red", text_color: str = "white", bbox_thickness: int = 3):
        self.font_size = font_size
        self.bbox_color = bbox_color
        self.text_color = text_color
        self.bbox_thickness = bbox_thickness
        self.font = None
        self._load_font()

    def _load_font(self):
        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.font_size)
        except Exception:
            try:
                self.font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", self.font_size)
            except Exception:
                self.font = ImageFont.load_default()

    def draw_bbox_with_label(self, image: Image.Image, bbox: Tuple[int, int, int, int], label: Optional[str]) -> Image.Image:
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        # bbox format: (x_topleft, y_topleft, x_bottomright, y_bottomright)
        x_tl, y_tl, x_br, y_br = bbox
        draw.rectangle([x_tl, y_tl, x_br, y_br], outline=self.bbox_color, width=self.bbox_thickness)
        if label:
            text_bbox = draw.textbbox((x_tl, max(0, y_tl - self.font_size - 8)), label, font=self.font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            padding = 6
            bg_rect = [x_tl - padding, max(0, y_tl - text_height - padding * 2), x_tl + text_width + padding, max(0, y_tl - padding)]
            draw.rectangle(bg_rect, fill=self.bbox_color)
            draw.text((x_tl, max(0, y_tl - text_height - padding)), label, fill=self.text_color, font=self.font)
        return annotated

    def annotate_and_save(self, image_path: str, bbox: Tuple[int, int, int, int], label: str, output_path: str) -> str:
        image = Image.open(image_path)
        annotated = self.draw_bbox_with_label(image, bbox, label)
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        annotated.save(output_path)
        return output_path

    def annotate_center_text(self, image_path: str, text: str, output_path: str) -> str:
        image = Image.open(image_path).convert("RGB")
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        # measure text size
        text_bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        W, H = annotated.size
        x = max(0, (W - text_width) // 2)
        y = max(0, (H - text_height) // 2)
        padding = 10
        bg_rect = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]
        draw.rectangle(bg_rect, fill=self.bbox_color)
        draw.text((x, y), text, fill=self.text_color, font=self.font)
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        annotated.save(output_path)
        return output_path


class ScreenshotCapture:
    def __init__(self, base_url: str = "http://localhost:8001", user_data_dir: Optional[str] = None):
        self.base_url = base_url
        self.counter = 0
        self.driver = None
        self.temp_dir = None
        # Use custom user data directory to avoid /tmp space issues
        if user_data_dir is None:
            # Use project directory instead of /tmp, but make it unique per instance
            # to avoid conflicts when multiple instances run simultaneously
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            # Keep all chrome profiles under a dedicated folder
            base_profiles_dir = os.path.join(project_dir, "chrome_profiles")
            os.makedirs(base_profiles_dir, exist_ok=True)
            # Create unique directory using process ID, timestamp, and random suffix
            unique_id = f"chrome_user_data_{os.getpid()}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
            user_data_dir = os.path.join(base_profiles_dir, unique_id)
        self.user_data_dir = user_data_dir
        self._setup_driver()
        
    def _setup_driver(self):
        """Setup Selenium WebDriver for MiniWord"""
        # We will attempt multiple times with fresh unique user-data-dirs to avoid lock conflicts
        base_dir_abs = os.path.abspath(os.path.dirname(self.user_data_dir))
        # Preserve original temp env so we can restore on retries/fallback
        original_tmpdir = os.environ.get("TMPDIR")
        original_tmp = os.environ.get("TMP")
        original_temp = os.environ.get("TEMP")
        last_error = None
        for attempt in range(1, 5):  # 1-3 with unique dirs, 4th without user-data-dir
            use_custom_profile = attempt < 4
            if use_custom_profile:
                # Generate a fresh unique user data directory for this attempt
                unique_id = f"chrome_user_data_{os.getpid()}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
                current_user_data_dir = os.path.join(base_dir_abs, unique_id)
                abs_user_data_dir = os.path.abspath(current_user_data_dir)
                
                # If directory exists, try to clean and remove it for a fresh start
                if os.path.exists(abs_user_data_dir):
                    try:
                        self._cleanup_chrome_locks(abs_user_data_dir)
                        if "chrome_user_data_" in os.path.basename(abs_user_data_dir):
                            shutil.rmtree(abs_user_data_dir)
                            print(f"    Cleaned up existing directory: {abs_user_data_dir}")
                    except Exception as e:
                        print(f"    Warning during cleanup: {e}")
                os.makedirs(abs_user_data_dir, exist_ok=True)
            else:
                abs_user_data_dir = None  # No custom dir on final attempt
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            
            if use_custom_profile and abs_user_data_dir is not None:
                chrome_options.add_argument(f"--user-data-dir={abs_user_data_dir}")
            
            # Additional flags to prevent conflicts
            chrome_options.add_argument("--remote-debugging-port=0")  # Random port
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            
            # Set custom temp directory for Chrome to avoid /tmp
            temp_env_set = False
            if use_custom_profile and abs_user_data_dir is not None:
                chrome_temp_dir = os.path.join(abs_user_data_dir, "temp")
                os.makedirs(chrome_temp_dir, exist_ok=True)
                os.environ["TMPDIR"] = chrome_temp_dir
                os.environ["TMP"] = chrome_temp_dir
                os.environ["TEMP"] = chrome_temp_dir
                temp_env_set = True
            
            try:
                if use_custom_profile and abs_user_data_dir is not None:
                    print(f"    Initializing Chrome with user-data-dir: {abs_user_data_dir} (attempt {attempt})")
                else:
                    print(f"    Initializing Chrome without custom user-data-dir (attempt {attempt})")
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.get(f"{self.base_url}/index.html")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "editor"))
                )
                time.sleep(1)
                print(f"    ✓ Connected to MiniWord at {self.base_url}")
                # Update the chosen user data dir only on success
                if use_custom_profile and abs_user_data_dir is not None:
                    self.user_data_dir = abs_user_data_dir
                else:
                    # When no custom dir is used, keep previous value for cleanup logic to no-op
                    pass
                return
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                print(f"ERROR: Failed to setup WebDriver (attempt {attempt}): {e}")
                # Clean up locks for the directory we just tried
                try:
                    if use_custom_profile and abs_user_data_dir is not None:
                        self._cleanup_chrome_locks(abs_user_data_dir)
                        # Attempt to remove the failed profile directory to avoid reuse
                        if os.path.exists(abs_user_data_dir):
                            shutil.rmtree(abs_user_data_dir, ignore_errors=True)
                except Exception:
                    pass
                finally:
                    # Restore temp env vars if we set them for this attempt
                    if temp_env_set:
                        if original_tmpdir is None:
                            os.environ.pop("TMPDIR", None)
                        else:
                            os.environ["TMPDIR"] = original_tmpdir
                        if original_tmp is None:
                            os.environ.pop("TMP", None)
                        else:
                            os.environ["TMP"] = original_tmp
                        if original_temp is None:
                            os.environ.pop("TEMP", None)
                        else:
                            os.environ["TEMP"] = original_temp
                
                # If not a user-data-dir conflict or this was the last attempt, break
                if "user data directory is already in use" not in msg and "session not created" not in msg:
                    break
                # Otherwise, loop to try again with a fresh profile or without profile on final attempt
                continue
        
        # If we get here, all attempts failed
        raise last_error if last_error else RuntimeError("Failed to initialize Chrome WebDriver")
    
    def _cleanup_chrome_locks(self, directory: Optional[str] = None):
        """Remove Chrome lock files that might prevent new sessions"""
        target_dir = directory if directory is not None else self.user_data_dir
        if not os.path.exists(target_dir):
            return
        
        # Common Chrome lock file patterns
        lock_patterns = [
            "SingletonLock",
            "SingletonSocket",
            "SingletonCookie",
            "lockfile",
            ".lock",
        ]
        
        # Check for lock files in user data dir and Default subdirectory
        dirs_to_check = [target_dir]
        default_dir = os.path.join(target_dir, "Default")
        if os.path.exists(default_dir):
            dirs_to_check.append(default_dir)
        
        for check_dir in dirs_to_check:
            try:
                if not os.path.isdir(check_dir):
                    continue
                items = os.listdir(check_dir)
                for item in items:
                    item_path = os.path.join(check_dir, item)
                    # Remove lock files
                    if any(pattern in item for pattern in lock_patterns):
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                                print(f"    Removed lock file: {item_path}")
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                                print(f"    Removed lock directory: {item_path}")
                        except Exception as e:
                            print(f"    Warning: Could not remove {item_path}: {e}")
            except Exception as e:
                # Ignore errors when listing directory (might be locked)
                pass

    def capture_initial(self, output_dir: str) -> str:
        # Backwards-compatible no-op for initial naming; prefer capture_named in pipeline
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix="minword_screenshots_")
        temp_path = os.path.join(self.temp_dir, "screenshot_initial.png")
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            time.sleep(0.3)
            self.driver.save_screenshot(temp_path)
        except Exception as e:
            Image.new("RGB", (1920, 1080), (40, 40, 40)).save(temp_path)
        return temp_path

    def capture_next(self, output_dir: str) -> str:
        # Backwards-compatible counter capture; prefer capture_named in pipeline
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix="minword_screenshots_")
        temp_path = os.path.join(self.temp_dir, f"screenshot_{self.counter:04d}.png")
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            time.sleep(0.3)
            self.driver.save_screenshot(temp_path)
        except Exception as e:
            Image.new("RGB", (1920, 1080), (40, 40, 40)).save(temp_path)
        self.counter += 1
        return temp_path

    def capture_named(self, output_dir: str, filename: str) -> str:
        # Create temp directory for this capture session if not exists
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix="minword_screenshots_")
        # Save to temp for bbox detection
        temp_path = os.path.join(self.temp_dir, filename)
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            time.sleep(0.3)
            self.driver.save_screenshot(temp_path)
        except Exception as e:
            Image.new("RGB", (1920, 1080), (40, 40, 40)).save(temp_path)
        # Save to screenshots directory with provided name
        if output_dir:
            screenshots_dir = os.path.join(output_dir, "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshots_dir, filename)
            try:
                shutil.copy2(temp_path, screenshot_path)
            except Exception:
                pass
        return temp_path
    
    def close(self):
        if self.driver:
            self.driver.quit()
        # Clean up the unique user data directory if it was auto-generated
        # This prevents accumulation of directories from multiple runs
        if self.user_data_dir and "chrome_user_data_" in os.path.basename(self.user_data_dir):
            try:
                if os.path.exists(self.user_data_dir):
                    shutil.rmtree(self.user_data_dir)
                    print(f"    ✓ Cleaned up user data directory: {self.user_data_dir}")
            except Exception as e:
                print(f"    Warning: Could not clean up user data directory: {e}")
        # Clean up temporary screenshot directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"    Warning: Could not clean up temp screenshot directory: {e}")


class ActionExecutor:
    def __init__(self, driver, files_dir: str = "/shared/nas/data/m1/jiateng5/Mini_Word/file_and_images"):
        self.driver = driver
        self.files_dir = files_dir
    
    # -------------------------------
    # Text-driven action execution
    # -------------------------------
    def _focus_editor(self) -> bool:
        try:
            # Try by id
            try:
                editor = self.driver.find_element(By.ID, "editor")
            except Exception:
                editor = None
            # Try common selectors if not found
            if editor is None:
                candidates = self.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true'], textarea, input[type='text']")
                editor = candidates[0] if candidates else None
            if editor is None:
                return False
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", editor)
            try:
                editor.click()
            except Exception:
                # Fallback focus via JS
                self.driver.execute_script("arguments[0].focus();", editor)
            time.sleep(0.1)
            return True
        except Exception:
            return False

    def _send_keys(self, text: str) -> bool:
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(text).perform()
            return True
        except Exception:
            return False

    def _find_form_field(self, field_name: str):
        """Find form field (input, textarea, select) by label or ID."""
        field_lower = field_name.lower()
        
        # Common field mappings
        field_mappings = {
            'comment content': ['comment-text', 'comment-content', 'commentcontent'],
            'comment author': ['comment-author', 'commentauthor'],
            'comment priority': ['comment-priority', 'commentpriority'],
        }
        
        # Check mappings first
        for key, ids in field_mappings.items():
            if key in field_lower:
                for field_id in ids:
                    try:
                        el = self.driver.find_element(By.ID, field_id)
                        if el:
                            return el
                    except:
                        continue
        
        # Try to find by label text (look for label containing field name, then find associated input/textarea/select)
        try:
            # Find all labels
            labels = self.driver.find_elements(By.TAG_NAME, "label")
            for label in labels:
                label_text = (label.text or '').lower()
                if field_lower in label_text:
                    # Try to find associated input/textarea/select
                    label_for = label.get_attribute('for')
                    if label_for:
                        try:
                            el = self.driver.find_element(By.ID, label_for)
                            if el:
                                return el
                        except:
                            pass
                    # Try to find following sibling input/textarea/select
                    try:
                        el = label.find_element(By.XPATH, "following-sibling::input | following-sibling::textarea | following-sibling::select")
                        if el:
                            return el
                    except:
                        pass
                    # Try to find in parent form-group
                    try:
                        parent = label.find_element(By.XPATH, "ancestor::div[contains(@class, 'form-group')]")
                        el = parent.find_element(By.CSS_SELECTOR, "input, textarea, select")
                        if el:
                            return el
                    except:
                        pass
        except:
            pass
        
        # Try direct ID/name search
        try:
            # Clean field name for ID matching
            clean_id = field_lower.replace(' ', '-').replace('_', '-')
            try:
                el = self.driver.find_element(By.ID, clean_id)
                if el:
                    return el
            except:
                pass
            try:
                el = self.driver.find_element(By.NAME, clean_id)
                if el:
                    return el
            except:
                pass
        except:
            pass
        
        return None

    def _select_text_in_editor(self, text_to_select: str) -> bool:
        """Select text in the contenteditable editor."""
        try:
            editor = self.driver.find_element(By.ID, "editor")
            if not editor:
                return False
            
            # Escape the text for JavaScript (handle quotes, special chars)
            import json
            text_escaped = json.dumps(text_to_select)
            
            # Use JavaScript to find and select text
            script = f"""
            var editor = arguments[0];
            var textToFind = {text_escaped};
            
            // First check if text exists in editor
            var editorText = editor.innerText || editor.textContent || '';
            if (editorText.indexOf(textToFind) === -1) {{
                // Try to find partial matches (for cases where formatting might break text)
                var words = textToFind.split(/\\s+/);
                if (words.length > 0) {{
                    // Try to find first few words
                    var partialText = words.slice(0, Math.min(3, words.length)).join(' ');
                    if (editorText.indexOf(partialText) === -1) {{
                        return false;
                    }}
                    textToFind = partialText;
                }} else {{
                    return false;
                }}
            }}
            
            // Clear any existing selection
            var selection = window.getSelection();
            selection.removeAllRanges();
            
            var range = document.createRange();
            var found = false;
            
            // Find the text node containing the text
            var treeWalker = document.createTreeWalker(
                editor,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            var node;
            var allText = '';
            var nodeList = [];
            
            // Collect all text nodes
            while (node = treeWalker.nextNode()) {{
                nodeList.push(node);
                allText += node.textContent;
            }}
            
            // Find the starting position in concatenated text
            var globalIndex = allText.indexOf(textToFind);
            if (globalIndex === -1) {{
                // Try partial match with first few words
                var words = textToFind.split(/\\s+/);
                if (words.length > 1) {{
                    var partialMatch = words.slice(0, Math.min(3, words.length)).join(' ');
                    globalIndex = allText.indexOf(partialMatch);
                    if (globalIndex !== -1) {{
                        textToFind = partialMatch;
                    }}
                }}
            }}
            
            if (globalIndex === -1) {{
                return false;
            }}
            
            // Find which text node contains the start position
            var charCount = 0;
            var startNode = null;
            var startOffset = 0;
            var endNode = null;
            var endOffset = 0;
            
            for (var i = 0; i < nodeList.length; i++) {{
                var n = nodeList[i];
                var nodeText = n.textContent;
                var nodeLength = nodeText.length;
                
                if (!startNode && charCount + nodeLength > globalIndex) {{
                    startNode = n;
                    startOffset = globalIndex - charCount;
                    endOffset = startOffset + textToFind.length;
                    
                    // Check if end is in same node
                    if (endOffset <= nodeLength) {{
                        endNode = n;
                    }} else {{
                        // End is in a later node
                        var remaining = textToFind.length - (nodeLength - startOffset);
                        endOffset = remaining;
                    }}
                    break;
                }}
                charCount += nodeLength;
            }}
            
            if (!startNode) {{
                return false;
            }}
            
            // If end is in same node
            if (endNode) {{
                range.setStart(startNode, startOffset);
                range.setEnd(endNode, endOffset);
            }} else {{
                // Find end node
                charCount = 0;
                var targetEnd = globalIndex + textToFind.length;
                for (var i = 0; i < nodeList.length; i++) {{
                    var n = nodeList[i];
                    var nodeText = n.textContent;
                    var nodeLength = nodeText.length;
                    
                    if (charCount + nodeLength >= targetEnd) {{
                        endNode = n;
                        endOffset = targetEnd - charCount;
                        break;
                    }}
                    charCount += nodeLength;
                }}
                
                if (!endNode) {{
                    // Fallback: end at start node
                    endNode = startNode;
                    endOffset = startNode.textContent.length;
                }}
                
                range.setStart(startNode, startOffset);
                range.setEnd(endNode, endOffset);
            }}
            
            selection.addRange(range);
            
            // Also focus the editor to ensure selection is visible
            editor.focus();
            
            return true;
            """
            result = self.driver.execute_script(script, editor)
            return bool(result)
        except Exception as e:
            return False

    def _press_key(self, name: str) -> bool:
        key_map = {
            'enter': Keys.ENTER,
            'return': Keys.ENTER,
            'tab': Keys.TAB,
            'backspace': Keys.BACKSPACE,
            'delete': Keys.DELETE,
            'esc': Keys.ESCAPE,
            'escape': Keys.ESCAPE,
            'space': Keys.SPACE,
            'left': Keys.ARROW_LEFT,
            'right': Keys.ARROW_RIGHT,
            'up': Keys.ARROW_UP,
            'down': Keys.ARROW_DOWN,
        }
        k = key_map.get(name.strip().lower())
        if not k:
            return False
        return self._send_keys(k)

    def _find_menu_item(self, label: str):
        """Find menu item (div.menu-item) by label text."""
        label_norm = label.strip()
        label_lower = label_norm.lower()
        
        # Try to find menu items by exact text match
        try:
            menu_items = self.driver.find_elements(By.CSS_SELECTOR, ".menu-item")
            for item in menu_items:
                text_content = (item.text or '').strip()
                if label_lower == text_content.lower():
                    return item
        except Exception:
            pass
        
        # Try XPath as fallback
        try:
            xpath = f"//div[@class='menu-item' and normalize-space(.)='{label_norm}']"
            el = self.driver.find_element(By.XPATH, xpath)
            if el:
                return el
        except Exception:
            pass
        
        return None

    def _find_clickable_by_label(self, label: str, case_sensitive: bool = False):
        # Try a few strategies to find a clickable element matching the label
        label_norm = label.strip()
        label_lower = label_norm.lower()
        
        # Strategy 0: Try menu items first for common menu names
        menu_names = ['file', 'edit', 'view', 'insert', 'format', 'tools', 'help']
        if label_lower in menu_names:
            menu_item = self._find_menu_item(label_norm)
            if menu_item is not None:
                return menu_item
        
        # Strategy 1: Try XPath with exact matches first
        xpaths_exact = [
            f"//button[normalize-space(.)='{label_norm}']",
            f"//a[normalize-space(.)='{label_norm}']",
            f"//*[@role='button' and normalize-space(.)='{label_norm}']",
            f"//*[@aria-label='{label_norm}']",
            f"//input[@value='{label_norm}']",
        ]
        for xp in xpaths_exact:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el:
                    return el
            except Exception:
                continue
        
        # Strategy 2: Case-insensitive search by finding all clickable elements and filtering in Python
        # This is better for title/alt attributes which may have different casing
        try:
            # Find all buttons, links, and elements with role='button'
            candidates = self.driver.find_elements(By.XPATH, "//button | //a | //*[@role='button']")
            for el in candidates:
                # Check title attribute
                title = el.get_attribute('title') or ''
                aria_label = el.get_attribute('aria-label') or ''
                text_content = (el.text or '').strip()
                
                # Check value for inputs
                value = el.get_attribute('value') or ''
                
                # Check image alt text (for icon buttons)
                try:
                    img = el.find_element(By.TAG_NAME, 'img')
                    alt = img.get_attribute('alt') or ''
                except:
                    alt = ''
                
                # Case-insensitive comparison
                matches = [
                    label_lower in title.lower(),
                    label_lower in aria_label.lower(),
                    label_lower == text_content.lower(),
                    label_lower == value.lower(),
                    label_lower in alt.lower(),
                    label_lower == title.lower().strip(),  # Exact match on title (case-insensitive)
                    label_lower == alt.lower().strip(),  # Exact match on alt (case-insensitive)
                ]
                
                if any(matches):
                    return el
        except Exception:
            pass
        
        # Strategy 3: Try menu items as fallback (if not already tried)
        if label_lower not in menu_names:
            menu_item = self._find_menu_item(label_norm)
            if menu_item is not None:
                return menu_item
        
        # Strategy 4: Contains-text fallbacks with XPath
        contains_xpaths = [
            f"//button[contains(normalize-space(.), '{label_norm}')]",
            f"//a[contains(normalize-space(.), '{label_norm}')]",
            f"//*[@role='button' and contains(normalize-space(.), '{label_norm}')]",
        ]
        for xp in contains_xpaths:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el:
                    return el
            except Exception:
                continue
        
        return None

    def execute_action_from_text(self, step_text: str) -> Optional[str]:
        """
        Execute action from text description.
        Returns: String describing the action executed, or None if failed.
        """
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")

            # 1) File upload
            filename = detect_file_upload(step_text) if step_text else None
            if filename:
                file_path = os.path.join(self.files_dir, filename)
                if os.path.exists(file_path):
                    uploaded = self.upload_file(file_path)
                    if uploaded:
                        time.sleep(1.0)
                        return f"upload file: {filename}"

            text_lower = step_text.lower()

            # 2) Input into specific form field (e.g., "Input 'X' in the Y field" or "Input your name in the Y field")
            # Pattern: "Input 'text' in the field_name field" or "Input text in the field_name field" or "Input your name in the field_name field"
            input_field_pattern = r"input\s+(?:['\"]([^'\"]+)['\"]|([^\s]+(?:\s+[^\s]+)*?))\s+in\s+(?:the\s+)?([\w\s]+?)\s+field"
            input_match = re.search(input_field_pattern, text_lower)
            if input_match:
                content = (input_match.group(1) or input_match.group(2)).strip()
                field_name = input_match.group(3).strip()
                field = self._find_form_field(field_name)
                if field:
                    try:
                        # Handle special cases like "your name" -> use a default or the literal text
                        if content.lower() == "your name":
                            content = "Your Name"  # Or could use a default name
                        field.clear()
                        field.send_keys(content)
                        time.sleep(0.3)
                        return f"input text in {field_name} field: '{content}'"
                    except Exception:
                        pass

            # 2.5) Typing text into the editor (general case)
            # Extract quoted content to type
            m = re.search(r"[\"\'""'']([^\"\'""'']+)[\"\'""'']", step_text)
            wants_text_input = any(kw in text_lower for kw in ["type", "enter", "input", "write", "fill in", "paste"]) or ("into the editor" in text_lower)
            if wants_text_input and m:
                content = m.group(1)
                # Only if not already handled by field-specific input above
                if not input_match:
                    if self._focus_editor():
                        self._send_keys(content)
                        time.sleep(0.5)
                        return f"type text: '{content}'"

            # 3) Press a key (e.g., Enter)
            mkey = re.search(r"press\s+([A-Za-z]+)", text_lower)
            if mkey:
                keyname = mkey.group(1)
                if self._press_key(keyname):
                    time.sleep(0.3)
                    return f"press key: {keyname}"

            # 4) Click by label (button/link/aria/menu-item)
            # Prefer quoted labels if present
            labels = re.findall(r"[\"\'""'']([^\"\'""'']+)[\"\'""'']", step_text)
            tried = False
            for label in labels:
                el = self._find_clickable_by_label(label)
                if el is not None:
                    tried = True
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
                        time.sleep(0.1)
                        el.click()
                        time.sleep(1.0)
                        # Check if it's a menu item
                        tag_name = el.tag_name.lower()
                        class_name = el.get_attribute('class') or ''
                        if tag_name == 'div' and 'menu-item' in class_name:
                            return f"click menu: '{label}'"
                        else:
                            return f"click button: '{label}'"
                    except Exception:
                        continue

            # 4.5) Extract button/menu name from patterns like "Click the X icon", "Click X", "Click on X icon", "Click the 'File' section"
            # Patterns: "Click the {name} icon", "Click {name} icon", "Click on the {name} icon", "Click {name}", "Click the 'X' section"
            # Updated to handle multi-word names better
            click_patterns = [
                r"click\s+(?:the\s+)?([a-z\s]+?)\s+icon(?:\s+button)?",  # "Click the New Comment icon"
                r"click\s+(?:on\s+)?(?:the\s+)?([a-z\s]+?)(?:\s+icon)?(?:\s+button)?(?:$|\.|,|;)",  # More flexible
                r"click\s+(?:the\s+)?([a-z\s]+?)(?:$|\.|,|;)",  # "Click the New Comment" or "Click the 'File' section"
            ]
            for pattern in click_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    button_name = match.group(1).strip()
                    # Remove common stop words that might interfere, but keep "section" context for menu items
                    is_section = 'section' in button_name
                    button_name = re.sub(r'\b(button|item|option|element|toolbar|menu)\b', '', button_name).strip()
                    # If it was a section, also remove "section" word
                    if is_section:
                        button_name = re.sub(r'\bsection\b', '', button_name).strip()
                    
                    if button_name and len(button_name) > 1:  # Ensure we have a meaningful name
                        el = self._find_clickable_by_label(button_name)
                        if el is not None:
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
                                time.sleep(0.1)
                                el.click()
                                time.sleep(1.0)
                                # Check if it's a menu item
                                tag_name = el.tag_name.lower()
                                class_name = el.get_attribute('class') or ''
                                if tag_name == 'div' and 'menu-item' in class_name:
                                    return f"click menu: '{button_name}'"
                                else:
                                    return f"click button: '{button_name}'"
                            except Exception:
                                continue

            # 6) Select option from dropdown/select field (e.g., "Select 'High Priority' from the comment priority field")
            select_pattern = r"select\s+(?:['\"]([^'\"]+)['\"]|([^\s]+(?:\s+[^\s]+)*?))\s+from\s+(?:the\s+)?([\w\s]+?)\s+field"
            select_match = re.search(select_pattern, text_lower)
            if select_match:
                option_text = (select_match.group(1) or select_match.group(2)).strip()
                field_name = select_match.group(3).strip()
                field = self._find_form_field(field_name)
                if field and field.tag_name.lower() == 'select':
                    try:
                        from selenium.webdriver.support.ui import Select
                        select = Select(field)
                        # Try to select by visible text
                        try:
                            select.select_by_visible_text(option_text)
                            time.sleep(0.3)
                            return f"select '{option_text}' from {field_name} field"
                        except:
                            # Try by partial text match
                            for option in select.options:
                                if option_text.lower() in option.text.lower():
                                    select.select_by_visible_text(option.text)
                                    time.sleep(0.3)
                                    return f"select '{option_text}' from {field_name} field"
                            # Try by value
                            option_value = option_text.lower().replace(' ', '-')
                            try:
                                select.select_by_value(option_value)
                                time.sleep(0.3)
                                return f"select '{option_text}' from {field_name} field"
                            except:
                                pass
                    except Exception:
                        pass

            # 7) Select text in the editor - PRIORITIZE PATTERNS WITH QUOTED TEXT
            # Pattern 1 (HIGHEST PRIORITY): Patterns with quoted text - "Select the 'X' paragraph" or "Select 'X' to make it bold"
            # Check if there's any quoted text in a select statement
            quoted_select_pattern = r"select\s+(?:the\s+)?(?:title\s+)?['\"]([^'\"]+)['\"]"
            quoted_match = re.search(quoted_select_pattern, step_text, re.IGNORECASE)
            if quoted_match:
                text_to_select = quoted_match.group(1).strip()
                if self._select_text_in_editor(text_to_select):
                    time.sleep(0.3)
                    return f"select text in editor: '{text_to_select}'"
            
            # Pattern 2: "Select the 'X' paragraph/text/section/title" or "Select 'X' paragraph/text/section"
            select_text_pattern1 = r"select\s+(?:the\s+)?(?:['\"]([^'\"]+)['\"]|([^\s]+(?:\s+[^\s]+)*?))\s+(?:paragraph|text|section|title)(?:\s+with\s+the\s+cursor)?"
            select_text_match1 = re.search(select_text_pattern1, text_lower)
            if select_text_match1:
                # Prioritize quoted text if available
                text_to_select = select_text_match1.group(1) if select_text_match1.group(1) else select_text_match1.group(2)
                text_to_select = text_to_select.strip()
                if self._select_text_in_editor(text_to_select):
                    time.sleep(0.3)
                    return f"select text in editor: '{text_to_select}'"
            
            # Pattern 3: "Select the title 'X' to make it bold" or "Select 'X' to make it bold" (without paragraph/text word)
            select_text_pattern2 = r"select\s+(?:the\s+)?(?:title\s+)?(?:['\"]([^'\"]+)['\"]|([^\s]+(?:\s+[^\s]+)*?))\s+to\s+"
            select_text_match2 = re.search(select_text_pattern2, text_lower)
            if select_text_match2:
                # Prioritize quoted text if available
                text_to_select = select_text_match2.group(1) if select_text_match2.group(1) else select_text_match2.group(2)
                text_to_select = text_to_select.strip()
                if self._select_text_in_editor(text_to_select):
                    time.sleep(0.3)
                    return f"select text in editor: '{text_to_select}'"
            
            # Pattern 4: "Select 'X' with the cursor" (general selection without specific keyword)
            select_text_pattern3 = r"select\s+(?:the\s+)?(?:['\"]([^'\"]+)['\"]|([^\s]+(?:\s+[^\s]+)*?))\s+with\s+the\s+cursor"
            select_text_match3 = re.search(select_text_pattern3, text_lower)
            if select_text_match3:
                # Prioritize quoted text if available
                text_to_select = select_text_match3.group(1) if select_text_match3.group(1) else select_text_match3.group(2)
                text_to_select = text_to_select.strip()
                if self._select_text_in_editor(text_to_select):
                    time.sleep(0.3)
                    return f"select text in editor: '{text_to_select}'"

            # 5) Generic keyword-based buttons (e.g., 'open', 'cancel', 'ok') when no quotes
            generic_map = [
                ("open", "Open"), ("cancel", "Cancel"), ("ok", "OK"), ("create", "Create"), ("save", "Save"), ("upload", "Upload"),
                ("bold", "Bold"), ("italic", "Italic"), ("underline", "Underline"),
                ("new comment", "New Comment"), ("spell check", "Spell Check"),
            ]
            for kw, label in generic_map:
                if kw in text_lower:
                    el = self._find_clickable_by_label(label)
                    if el is not None:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
                            time.sleep(0.1)
                            el.click()
                            time.sleep(1.0)
                            return f"click button: '{label}'"
                        except Exception:
                            continue

            # If nothing matched
            return None
        except Exception as e:
            return None

    def upload_file(self, file_path: str) -> bool:
        """
        Upload a file to a file input element on the page.
        Tries to find file input elements and set their value using Selenium's send_keys.
        """
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            
            # Ensure file path is absolute
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            if not os.path.exists(file_path):
                return False
            
            # Find all file input elements
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            
            # Try to find by ID patterns common in MiniWord
            if not file_inputs:
                common_ids = ['image-file', 'document-file', 'file-input', 'file-upload']
                for input_id in common_ids:
                    try:
                        file_input = self.driver.find_element(By.ID, input_id)
                        if file_input:
                            file_inputs = [file_input]
                            break
                    except:
                        continue
            
            # Also try by name attribute
            if not file_inputs:
                common_names = ['imageFile', 'documentFile', 'fileInput']
                for name in common_names:
                    try:
                        file_input = self.driver.find_element(By.NAME, name)
                        if file_input:
                            file_inputs = [file_input]
                            break
                    except:
                        continue
            
            if not file_inputs:
                return False
            
            # Try to upload to each file input (even if hidden, we can still use send_keys)
            for file_input in file_inputs:
                try:
                    # Make sure the input is visible by scrolling it into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", file_input)
                    time.sleep(0.2)
                    
                    # Use send_keys to upload the file (works even if input is not visible)
                    file_input.send_keys(file_path)
                    
                    # Wait for file to be processed and trigger change event
                    time.sleep(1.5)
                    return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False

    def click_bbox_center(self, bbox: Tuple[int, int, int, int], wait_after: float = 2.0, step_text: str = ""):
        # bbox format: (x_topleft, y_topleft, x_bottomright, y_bottomright)
        x_tl, y_tl, x_br, y_br = bbox
        cx = (x_tl + x_br) // 2
        cy = (y_tl + y_br) // 2
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            
            # Check if this step involves file upload
            filename = detect_file_upload(step_text) if step_text else None
            if filename:
                file_path = os.path.join(self.files_dir, filename)
                if os.path.exists(file_path):
                    print(f"    Detected file upload action for: {filename}")
                    # First try to find and click the file input to trigger file dialog
                    # Then upload the file
                    uploaded = self.upload_file(file_path)
                    if uploaded:
                        time.sleep(wait_after)
                        return
            
            # Small delay to ensure page is stable
            time.sleep(0.1)
            
            # Use JavaScript to dispatch proper mouse events
            # This simulates a real click better than just element.click()
            script = f"""
            var element = document.elementFromPoint({cx}, {cy});
            if (element) {{
                // Scroll element into view first
                element.scrollIntoView({{behavior: 'instant', block: 'center', inline: 'center'}});
                
                // Get element's position
                var rect = element.getBoundingClientRect();
                var clickX = rect.left + rect.width / 2;
                var clickY = rect.top + rect.height / 2;
                
                // Create and dispatch mouse events in proper sequence
                var mouseDown = new MouseEvent('mousedown', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: clickX,
                    clientY: clickY,
                    button: 0
                }});
                
                var mouseUp = new MouseEvent('mouseup', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: clickX,
                    clientY: clickY,
                    button: 0
                }});
                
                var clickEvent = new MouseEvent('click', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: clickX,
                    clientY: clickY,
                    button: 0
                }});
                
                element.dispatchEvent(mouseDown);
                element.dispatchEvent(mouseUp);
                element.dispatchEvent(clickEvent);
                
                console.log('Clicked element:', element.tagName, element.className);
                return true;
            }} else {{
                console.error('No element found at ({cx}, {cy})');
                return false;
            }}
            """
            result = self.driver.execute_script(script)
            if result:
                print(f"    ✓ Clicked at ({cx}, {cy})")
            else:
                print(f"    ⚠️ Click may have failed at ({cx}, {cy})")
            
            # Wait for UI to update
            time.sleep(wait_after)
            
        except Exception as e:
            print(f"Warning: Click failed: {e}")
            time.sleep(wait_after)


# ===============================
# Main pipeline
# ===============================

class TextToImagePipeline:
    def __init__(self, vision_model_path: str, work_dir: str, base_url: str = "http://localhost:8001", files_dir: str = "/shared/nas/data/m1/jiateng5/Mini_Word/file_and_images"):
        self.vision_model_path = vision_model_path
        self.work_dir = work_dir
        self.base_url = base_url
        self.files_dir = files_dir
        os.makedirs(self.work_dir, exist_ok=True)
        self.detector = BboxDetector(vision_model_path)
        self.annotator = ImageAnnotator()
        self.shooter = ScreenshotCapture(base_url)
        self.executor = ActionExecutor(self.shooter.driver, files_dir)

    def initialize(self):
        print("Initializing Qwen2.5-VL model...")
        self.detector.initialize()
        print("Model ready.")

    def reset_page_to_initial_state(self):
        """Reset the page to its initial state by refreshing it."""
        try:
            if self.shooter.driver:
                # Refresh the page
                self.shooter.driver.get(f"{self.shooter.base_url}/index.html")
                # Wait for the page to load completely
                WebDriverWait(self.shooter.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "editor"))
                )
                # Small delay to ensure everything is ready
                time.sleep(0.5)
                print("    ✓ Page reset to initial state")
        except Exception as e:
            print(f"    Warning: Failed to reset page: {e}")

    def process_item(self, item_index: int, question: str, answer: str, sub_dir: str) -> List[str]:
        print(f"\nProcessing item {item_index}: {question}")
        
        # Reset page to initial state before processing each new item
        self.reset_page_to_initial_state()
        
        steps = extract_steps(answer)
        if not steps:
            print("No steps found; skipping this item.")
            return []
        # Format all actions
        formatted_steps: List[Tuple[str, str]] = []
        for i, step in enumerate(steps, 1):
            formatted = format_action_for_bbox(step)
            formatted_steps.append((step, formatted))
        # Set up directories
        item_dir = os.path.join(self.work_dir, sub_dir, f"item_{item_index:04d}")
        ann_dir = os.path.join(item_dir, "annotated")
        screenshots_dir = os.path.join(item_dir, "screenshots")
        os.makedirs(ann_dir, exist_ok=True)
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # We will capture named screenshots per step (begin/after); no initial saved here
        current_img = None
        saved_annotations: List[str] = []
        current_section: Optional[str] = None  # Track current section for second-level lookups
        current_icon: Optional[str] = None     # Track current icon for deep-level lookups
        
        # Helpers to find context (nearest previous section, then next icon after that section)
        section_re = re.compile(r"click\s+(?:the\s+)?[\"'“”‘’]?\s*([a-z0-9][a-z0-9\s_\-]*?)\s*[\"'“”‘’]?\s+section", re.IGNORECASE)
        icon_re = re.compile(r"click\s+(?:the\s+)?[\"'“”‘’]?\s*([a-z0-9][a-z0-9\s_\-]*?)\s*[\"'“”‘’]?\s+(?:icon|button)", re.IGNORECASE)

        def normalize_key(name: str) -> str:
            return name.lower().replace(' ', '_')

        def derive_context(idx: int) -> Tuple[Optional[str], Optional[str]]:
            # idx is 1-based in our loop; convert to 0-based for list access
            pos = idx - 1
            # 1) find nearest previous section sentence
            section_idx = None
            section_key_local: Optional[str] = None
            for j in range(pos - 1, -1, -1):
                s = formatted_steps[j][0]
                m = section_re.search(s)
                if m:
                    section_idx = j
                    section_key_local = normalize_key(m.group(1).strip())
                    break
            # 2) find first icon sentence after that section (up to current index - 1)
            icon_key_local: Optional[str] = None
            if section_idx is not None:
                for k in range(section_idx + 1, pos):
                    s2 = formatted_steps[k][0]
                    m2 = icon_re.search(s2)
                    if m2:
                        icon_name = m2.group(1).strip()
                        # Resolve icon key under the derived section if possible
                        resolved = self.detector.resolve_icon_key(section_key_local, icon_name) if section_key_local else None
                        icon_key_local = resolved or normalize_key(icon_name)
                        break
            return section_key_local, icon_key_local

        for i, (orig_step, fmt_step) in enumerate(formatted_steps, 1):
            # (1) Display text action
            print(f"\n  Step {i}/{len(formatted_steps)}: {orig_step}")
            
            # Capture pre-step screenshot (begin) for this step
            current_img = self.shooter.capture_named(item_dir, f"step_{i:03d}begin.png")
            time.sleep(0.5)
            
            # Derive context from full steps to avoid relying only on last immediate line
            derived_section, derived_icon = derive_context(i)
            context_section = derived_section or current_section
            context_icon = derived_icon or current_icon

            # Determine if the immediately previous step is a valid section click that matches the context section
            prev_section_valid = None
            if i > 1 and context_section:
                prev_step_text = formatted_steps[i-2][0]
                m_prev_sec = section_re.search(prev_step_text)
                if m_prev_sec:
                    prev_sec_name = m_prev_sec.group(1).strip()
                    prev_section_valid = (normalize_key(prev_sec_name) == context_section)
                else:
                    prev_section_valid = False

            # Detect bbox using current screenshot (try trajectory first, then vision model)
            bbox = self.detector.detect_bbox(
                current_img,
                fmt_step,
                original_action=orig_step,
                previous_section=context_section,
                previous_icon=context_icon,
                prev_section_valid=prev_section_valid,
            )
            
            # Update current_section if this step was a section click
            section_pattern = r"click\s+(?:the\s+)?['\"]?([a-z\s]+?)['\"]?\s+section"
            section_match = re.search(section_pattern, orig_step.lower())
            if section_match:
                section_name = section_match.group(1).strip()
                # Normalize like retrive.py; reset icon context when section changes
                current_section = self.detector._normalize_name_to_key(section_name)
                current_icon = None
            # Update current_icon if this step was an icon click
            icon_pattern = r"click\s+(?:the\s+)?['\"]?([a-z\s]+?)['\"]?\s+(?:icon|button)"
            icon_match = re.search(icon_pattern, orig_step.lower())
            if icon_match and current_section:
                icon_name = icon_match.group(1).strip()
                # Normalize like retrive.py (deep logic may use it)
                current_icon = self.detector._normalize_name_to_key(icon_name)
            if bbox is None:
                if 'cursor' in orig_step.lower():
                    print("    (2) bbox: skipped (cursor/editor action)")
                    # Save annotated image with centered instruction on the original screenshot
                    ann_path = os.path.join(ann_dir, f"step_{i:03d}.png")
                    center_text = f'Select in Editor: "{orig_step}"'
                    self.annotator.annotate_center_text(current_img, center_text, ann_path)
                    saved_annotations.append(ann_path)
                    # Execute editor-focused action without bbox
                    action_result = self.executor.execute_action_from_text(orig_step)
                    if action_result is None:
                        print(f"    (3) action: ❌ failed")
                        continue
                    print(f"    (3) action: {action_result}")
                    # Wait for UI to update then capture next screenshot
                    try:
                        WebDriverWait(self.shooter.driver, 5).until(
                            lambda d: d.execute_script("return document.readyState") == "complete"
                        )
                    except:
                        pass
                    time.sleep(2.5)
                    try:
                        self.shooter.driver.execute_script("return document.body.offsetHeight;")
                    except:
                        pass
                    time.sleep(0.5)
                    next_img = self.shooter.capture_next(item_dir)
                    current_img = next_img
                    continue
                else:
                    print("    (2) bbox: ❌ Could not detect")
                    print("    (3) action: skipped")
                    # Still capture post-step screenshot to maintain 2n images
                    self.shooter.capture_named(item_dir, f"step_{i:03d}after.png")
                    # Proceed to next step
                    continue
            else:
                x_tl, y_tl, x_br, y_br = bbox
                # (2) Only print bbox here
                print(f"    (2) bbox: [{x_tl}, {y_tl}, {x_br}, {y_br}]")
            
            # Generate and save annotated image using current screenshot
            ann_path = os.path.join(ann_dir, f"step_{i:03d}.png")
            self.annotator.annotate_and_save(current_img, bbox, orig_step, ann_path)
            saved_annotations.append(ann_path)
            
            # Execute action using text-based plan (do not click bbox center)
            action_result = self.executor.execute_action_from_text(orig_step)
            if action_result is None:
                # (3) Display action result
                print(f"    (3) action: ❌ failed")
                continue
            
            # (3) Display action result
            print(f"    (3) action: {action_result}")
            # If first step, print retrieval summary once after execution, then continue
            if i == 1:
                match_info = self.detector.last_match_info or {}
                src = match_info.get('source', 'unknown')
                path = match_info.get('path', '')
                desc = match_info.get('description', '')
                if src == 'model':
                    print("    (debug) first_step_source: vision_model")
                    if self.detector.last_failure_info:
                        print(f"    (debug) first_step_retrieval_failure: {self.detector.last_failure_info}")
                else:
                    if path or desc:
                        print(f"    (debug) first_step_retrieved: source={src}; path={path}; description={desc}")
                    else:
                        print(f"    (debug) first_step_retrieved: source={src}")
            
            # Wait for UI to fully update after action
            # Use multiple checks to ensure UI has changed
            try:
                # Wait for potential DOM changes or animations to complete
                WebDriverWait(self.shooter.driver, 5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except:
                pass
            
            # Additional wait for animations/async operations
            time.sleep(2.5)
            
            # Force a page refresh check to ensure changes are rendered
            try:
                # Try to trigger any pending layout/render updates
                self.shooter.driver.execute_script("return document.body.offsetHeight;")
            except:
                pass
            
            # Small additional wait
            time.sleep(0.5)
            
            # Capture post-step screenshot (after)
            next_img = self.shooter.capture_named(item_dir, f"step_{i:03d}after.png")
            current_img = next_img  # Update for next iteration
        
        print(f"  Completed {len(saved_annotations)} steps for item {item_index}")
        return saved_annotations
    
    def close(self):
        """Close the screenshot capture and WebDriver"""
        self.shooter.close()


def main():
    parser = argparse.ArgumentParser(description="MiniWord Text-to-Image Inference")
    parser.add_argument(
        "--vision_model",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/LLaMA-Factory/saves/qwen2_5vl-7b/full/sft_update",
        #default="Qwen/Qwen2.5-VL-7B-Instruct",
        help="Path to Qwen2.5-VL-7B fine-tuned model"
    )
    parser.add_argument(
        "--inputs",
        type=str,
        nargs='*',
        default=[
            "/shared/nas/data/m1/jiateng5/Mini_Word/inference/results_text/evaluate_data_combination2,3,4_inference_results.json",
        ],
        help="List of result JSON files (with question/answer pairs)"
    )
    parser.add_argument(
        "--files_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/file_and_images",
        help="Directory containing files to upload (images, documents, etc.)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference/text_to_image_output",
        help="Output directory for screenshots and annotations"
    )
    args = parser.parse_args()

    print(f"Using GPUs: {os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set')}")
    
    # Check if MiniWord is running
    try:
        import requests
        r = requests.get("http://localhost:8001", timeout=4)
        if r.status_code != 200:
            print("❌ Please start the MiniWord server first (python3 -m http.server 8001)")
            return
    except Exception:
        print("❌ Please start the MiniWord server first (python3 -m http.server 8001)")
        return

    pipeline = TextToImagePipeline(args.vision_model, args.output_dir, files_dir=args.files_dir)
    pipeline.initialize()

    # Read inputs
    total_items = 0
    for input_path in args.inputs:
        if not os.path.exists(input_path):
            print(f"Warning: input not found: {input_path}")
            continue
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"Warning: invalid data format in {input_path}")
            continue
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        print(f"\nProcessing file: {input_path} ({len(data)} items)")
        for idx, item in enumerate(tqdm(data, desc=f"{base_name}"), 1):
            question = item.get("question")
            answer = item.get("answer")
            if not question or not answer:
                continue
            sub_dir = base_name
            try:
                pipeline.process_item(idx, question, answer, sub_dir)
                total_items += 1
            except Exception as e:
                print(f"Error processing item {idx} in {base_name}: {e}")
    
    # Close the pipeline and WebDriver
    pipeline.close()
    print(f"\nDone. Processed {total_items} items.")


if __name__ == "__main__":
    main()
