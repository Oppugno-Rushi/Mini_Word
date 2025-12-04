#!/usr/bin/env python3
"""
Execute text-planned actions on MiniWord and capture screenshots per step.

Flow per item (question/answer):
- Extract numbered actions from the answer (strip <think> blocks, clean bullets/numbering)
- Open MiniWord at http://localhost:8001/index.html
- Capture initial screenshot
- For each action:
  - Execute the action via text-driven rules (type, click-by-label, upload, keypress)
  - Capture a screenshot after the action
- Save outputs under: <output_dir>/<base_name>/item_XXXX/{steps.txt, screenshots/}
"""

import os
import re
import json
import time
import argparse
from typing import List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


def strip_think_blocks(text: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)


def extract_steps(answer: str) -> List[str]:
    """Extract one-sentence actions from an answer string.
    - Remove <think> blocks
    - Split by newlines
    - Remove numeric/bullet prefixes
    - Drop empty lines
    """
    cleaned = strip_think_blocks(answer or "")
    lines = [ln.strip() for ln in cleaned.split("\n")]
    steps: List[str] = []
    for ln in lines:
        if not ln:
            continue
        ln = re.sub(r"^\s*\d+\s*[\.)-]\s*", "", ln)  # 1.  / 1)  / 1 -
        ln = re.sub(r"^[-•]\s*", "", ln)                 # bullets
        if ln:
            steps.append(ln)
    return steps


def detect_file_upload(step_text: str) -> Optional[str]:
    step_lower = (step_text or "").lower()
    keywords = [
        'select the file', 'select file', 'select a file', 'select the image file',
        'choose file', 'choose the file', 'upload', 'select document', 'file named',
        'image file', 'document file', 'select'
    ]
    if not any(k in step_lower for k in keywords):
        return None
    # quoted filename
    m = re.search(r"['\"]([\w\-_]+\.(txt|html|htm|md|png|jpg|jpeg|gif|pdf|doc|docx))['\"]", step_text, re.IGNORECASE)
    if m:
        return m.group(1)
    # unquoted filename
    m = re.search(r"\b([\w\-_]+\.(txt|html|htm|md|png|jpg|jpeg|gif|pdf|doc|docx))\b", step_text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


class ActionExecutor:
    def __init__(self, driver, files_dir: str):
        self.driver = driver
        self.files_dir = files_dir

    def _focus_editor(self) -> bool:
        try:
            try:
                editor = self.driver.find_element(By.ID, "editor")
            except Exception:
                editor = None
            if editor is None:
                candidates = self.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true'], textarea, input[type='text']")
                editor = candidates[0] if candidates else None
            if editor is None:
                return False
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", editor)
            try:
                editor.click()
            except Exception:
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

    def _press_key(self, name: str) -> bool:
        key_map = {
            'enter': Keys.ENTER, 'return': Keys.ENTER, 'tab': Keys.TAB,
            'backspace': Keys.BACKSPACE, 'delete': Keys.DELETE,
            'esc': Keys.ESCAPE, 'escape': Keys.ESCAPE, 'space': Keys.SPACE,
            'left': Keys.ARROW_LEFT, 'right': Keys.ARROW_RIGHT,
            'up': Keys.ARROW_UP, 'down': Keys.ARROW_DOWN,
        }
        k = key_map.get((name or "").strip().lower())
        return self._send_keys(k) if k else False

    def _find_clickable_by_label(self, label: str):
        label_norm = (label or "").strip()
        xpaths = [
            f"//button[normalize-space(.)='{label_norm}']",
            f"//a[normalize-space(.)='{label_norm}']",
            f"//*[@role='button' and normalize-space(.)='{label_norm}']",
            f"//*[@aria-label='{label_norm}']",
            f"//*[contains(@title, '{label_norm}')]",
            f"//input[@value='{label_norm}']",
            f"//*[normalize-space(text())='{label_norm}']",
        ]
        for xp in xpaths:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el:
                    return el
            except Exception:
                continue
        # contains fallbacks (case-insensitive)
        lower = label_norm.lower()
        contains_xps = [
            f"//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]",
            f"//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]",
            f"//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]",
            f"//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]",
            f"//*[contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]",
            f"//*[@data-testid and contains(translate(@data-testid, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]",
            f"//*[@data-page and contains(translate(@data-page, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower.replace(' ', '_')}')]",
            f"//img[@alt and contains(translate(@alt, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lower}')]//ancestor::button[1]",
        ]
        for xp in contains_xps:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el:
                    return el
            except Exception:
                continue
        return None

    def _ensure_menu_section(self, section: str) -> None:
        """Ensure the top menu section (File/Edit/View/Insert/Format/Tools/Help) is active."""
        sec = (section or "").strip().lower()
        try:
            xp = f"//div[contains(@class,'menu-item') and translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='{sec}']"
            el = self.driver.find_element(By.XPATH, xp)
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
            el.click()
            time.sleep(0.15)
        except Exception:
            pass

    def _click_element(self, el) -> bool:
        """Scroll element into view and click it (dispatching real DOM events)."""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
            time.sleep(0.05)
            el.click()
            return True
        except Exception:
            return False

    def upload_file(self, file_path: str) -> bool:
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                print(f"    ⚠️ File not found: {file_path}")
                return False
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if not file_inputs:
                ids = ['image-file', 'document-file', 'file-input', 'file-upload']
                for input_id in ids:
                    try:
                        el = self.driver.find_element(By.ID, input_id)
                        if el:
                            file_inputs = [el]
                            break
                    except Exception:
                        continue
            if not file_inputs:
                names = ['imageFile', 'documentFile', 'fileInput']
                for nm in names:
                    try:
                        el = self.driver.find_element(By.NAME, nm)
                        if el:
                            file_inputs = [el]
                            break
                    except Exception:
                        continue
            if not file_inputs:
                print("    ⚠️ No file input element found for upload")
                return False
            for el in file_inputs:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    time.sleep(0.2)
                    el.send_keys(file_path)
                    print(f"    ✓ Uploaded file: {os.path.basename(file_path)}")
                    time.sleep(1.0)
                    return True
                except Exception:
                    continue
            return False
        except Exception as e:
            print(f"Warning: File upload failed: {e}")
            return False

    def execute_action_from_text(self, step_text: str) -> bool:
        try:
            if self.driver is None:
                raise Exception("Driver not initialized")
            # 1) file upload
            filename = detect_file_upload(step_text)
            if filename:
                fp = os.path.join(self.files_dir, filename)
                if os.path.exists(fp):
                    print(f"    Action(upload): {filename}")
                    if self.upload_file(fp):
                        time.sleep(0.5)
                        return True
            lower = (step_text or "").lower()
            # 2) typing into editor if quoted content present
            m = re.search(r"[\"\'“”‘’]([^\"\'“”‘’]+)[\"\'“”‘’]", step_text or "")
            wants_text = any(k in lower for k in ["type", "enter", "input", "write", "fill in", "paste"]) or ("into the editor" in lower)
            if wants_text and m:
                content = m.group(1)
                if self._focus_editor():
                    print(f"    Action(type): '{content}'")
                    self._send_keys(content)
                    time.sleep(0.3)
                    return True
            # 3) press key
            mkey = re.search(r"press\s+([A-Za-z]+)", lower)
            if mkey:
                key = mkey.group(1)
                print(f"    Action(key): {key}")
                if self._press_key(key):
                    time.sleep(0.2)
                    return True
            # 3.1) nth icon under section pattern
            micon = re.search(r"(first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)\s+icon(?:\s+button)?\s+under\s+the\s+[\"']?(file|edit|view|insert|format|tools|help)[\"']?\s+section", lower)
            if micon:
                ord_word = micon.group(1)
                sec = micon.group(2)
                ord_map = {"first":1, "second":2, "third":3, "fourth":4, "fifth":5}
                if ord_word.isdigit():
                    nth = int(ord_word)
                else:
                    nth = ord_map.get(re.sub(r"(st|nd|rd|th)$", "", ord_word), ord_map.get(ord_word, 1))
                self._ensure_menu_section(sec)
                try:
                    # visible toolbar for section
                    xp_toolbar = f"//div[contains(@class,'toolbar-content') and contains(@data-group, '{sec}') and not(contains(@style,'display: none'))]"
                    toolbar = self.driver.find_element(By.XPATH, xp_toolbar)
                    buttons = toolbar.find_elements(By.CSS_SELECTOR, ".toolbar-btn")
                    if buttons and 1 <= nth <= len(buttons):
                        el = buttons[nth - 1]
                        if self._click_element(el):
                            print(f"    Action(click nth icon): {sec} #{nth}")
                            time.sleep(0.3)
                            return True
                except Exception:
                    pass
            # 3.5) specific UI intents
            # New Comment icon under Tools
            if "new comment" in lower or ("comment" in lower and "icon" in lower):
                self._ensure_menu_section("tools")
                el = self._find_clickable_by_label("New Comment")
                if el is not None and self._click_element(el):
                    print("    Action(click): 'New Comment'")
                    time.sleep(0.3)
                    return True
            # Page Setup icon under View (4th icon)
            if "page setup" in lower:
                self._ensure_menu_section("view")
                el = self._find_clickable_by_label("Page Setup")
                if el is not None and self._click_element(el):
                    print("    Action(click): 'Page Setup'")
                    time.sleep(0.3)
                    return True
            # Comment Content field
            if "comment content" in lower or ("comment" in lower and "content" in lower):
                # find label then input/textarea nearby
                try:
                    fld = None
                    # label by text
                    xp = "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'comment content')]"
                    lab = self.driver.find_element(By.XPATH, xp)
                    # search within same container for input/textarea
                    container = lab
                    for _ in range(3):
                        try:
                            fld = container.find_element(By.XPATH, ".//textarea|.//input")
                            break
                        except Exception:
                            try:
                                container = container.find_element(By.XPATH, "..")
                            except Exception:
                                break
                    if fld is None:
                        # fallback any textarea on page
                        cand = self.driver.find_elements(By.TAG_NAME, "textarea")
                        fld = cand[0] if cand else None
                    if fld is not None:
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", fld)
                        try:
                            fld.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].focus();", fld)
                        m2 = re.search(r"[\"\'“”‘’]([^\"\'“”‘’]+)[\"\'“”‘’]", step_text or "")
                        content = m2.group(1) if m2 else ""
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).send_keys(content).perform()
                        print(f"    Action(type into Comment Content): '{content}'")
                        time.sleep(0.3)
                        return True
                except Exception:
                    pass
            # Comment Author field
            if "comment author" in lower or ("author" in lower and "comment" in lower):
                try:
                    fld = None
                    xp = "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'comment author')]"
                    lab = self.driver.find_element(By.XPATH, xp)
                    container = lab
                    for _ in range(3):
                        try:
                            fld = container.find_element(By.XPATH, ".//input|.//textarea")
                            break
                        except Exception:
                            try:
                                container = container.find_element(By.XPATH, "..")
                            except Exception:
                                break
                    if fld is None:
                        # fallback inputs
                        cand = self.driver.find_elements(By.CSS_SELECTOR, "input")
                        fld = cand[0] if cand else None
                    if fld is not None:
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", fld)
                        try:
                            fld.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].focus();", fld)
                        m2 = re.search(r"[\"\'“”‘’]([^\"\'“”‘’]+)[\"\'“”‘’]", step_text or "")
                        content = m2.group(1) if m2 else "Your Name"
                        from selenium.webdriver.common.action_chains import ActionChains
                        # clear existing value then type
                        try:
                            fld.clear()
                        except Exception:
                            pass
                        ActionChains(self.driver).send_keys(content).perform()
                        print(f"    Action(type into Comment Author): '{content}'")
                        time.sleep(0.3)
                        return True
                except Exception:
                    pass

            # 4) click by label (prefer quoted labels)
            labels = re.findall(r"[\"\'“”‘’]([^\"\'“”‘’]+)[\"\'“”‘’]", step_text or "")
            for label in labels:
                el = self._find_clickable_by_label(label)
                if el is not None and self._click_element(el):
                    print(f"    Action(click): '{label}'")
                    time.sleep(0.5)
                    return True
            # 5) toolbar hotkeys for common formatting
            if "bold" in lower:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL).perform()
                    print("    Action(hotkey): Ctrl+B")
                    time.sleep(0.3)
                    return True
                except Exception:
                    pass
            if "italic" in lower:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('i').key_up(Keys.CONTROL).perform()
                    print("    Action(hotkey): Ctrl+I")
                    time.sleep(0.3)
                    return True
                except Exception:
                    pass
            if "underline" in lower:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('u').key_up(Keys.CONTROL).perform()
                    print("    Action(hotkey): Ctrl+U")
                    time.sleep(0.3)
                    return True
                except Exception:
                    pass
            # 6) targeted inputs (author/name fields)
            if any(k in lower for k in ["author", "your name", "name"]):
                try:
                    candidates = self.driver.find_elements(By.CSS_SELECTOR, "input, textarea")
                    for el in candidates:
                        ph = (el.get_attribute('placeholder') or '').lower()
                        nm = (el.get_attribute('name') or '').lower()
                        idv = (el.get_attribute('id') or '').lower()
                        if any(x in ph+nm+idv for x in ["author", "name"]):
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
                            try:
                                el.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].focus();", el)
                            m2 = re.search(r"[\"\'“”‘’]([^\"\'“”‘’]+)[\"\'“”‘’]", step_text or "")
                            content = m2.group(1) if m2 else "User"
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(self.driver).send_keys(content).perform()
                            print(f"    Action(type into field): '{content}'")
                            time.sleep(0.3)
                            return True
                except Exception:
                    pass
            # 7) simple dropdown selection (Select 'X' ...)
            msel = re.search(r"select\s+[\"\'“”‘’]([^\"\'“”‘’]+)[\"\'“”‘’]", lower)
            if msel:
                target = msel.group(1)
                try:
                    opened = False
                    for el in self.driver.find_elements(By.CSS_SELECTOR, "select, [role='listbox'], .dropdown, .select, .menu"):
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
                            el.click()
                            opened = True
                            time.sleep(0.2)
                            break
                        except Exception:
                            continue
                    if opened:
                        tx = target.lower()
                        opt_xps = [
                            f"//option[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{tx}')]",
                            f"//*[@role='option' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{tx}')]",
                            f"//*[contains(@class,'option') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{tx}')]",
                        ]
                        for xp in opt_xps:
                            try:
                                opt = self.driver.find_element(By.XPATH, xp)
                                opt.click()
                                print(f"    Action(select): '{target}'")
                                time.sleep(0.3)
                                return True
                            except Exception:
                                continue
                except Exception:
                    pass
            # 8) generic keywords (add broader set)
            generic = [("open", "Open"), ("cancel", "Cancel"), ("ok", "OK"), ("create", "Create"), ("save", "Save"), ("upload", "Upload"), ("format", "Format"), ("tools", "Tools")]
            for kw, lab in generic:
                if kw in lower:
                    el = self._find_clickable_by_label(lab)
                    if el is not None:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", el)
                            time.sleep(0.1)
                            el.click()
                            print(f"    Action(click): '{lab}' (from '{kw}')")
                            time.sleep(0.5)
                            return True
                        except Exception:
                            continue
            # If nothing matched, raise so caller can log the issue clearly
            raise ValueError(f"Unrecognized or ambiguous action: {step_text}")
        except Exception as e:
            print(f"Warning: Text-based action failed: {e}")
            return False


class ScreenshotCapture:
    def __init__(self, base_url: str = "http://localhost:8001", user_data_dir: Optional[str] = None):
        self.base_url = base_url
        self.counter = 0
        self.driver = None
        if user_data_dir is None:
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            base_profiles_dir = os.path.join(project_dir, "chrome_profiles")
            os.makedirs(base_profiles_dir, exist_ok=True)
            import uuid
            unique_id = f"chrome_user_data_{os.getpid()}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
            user_data_dir = os.path.join(base_profiles_dir, unique_id)
        self.user_data_dir = user_data_dir
        self._setup_driver()

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument("--remote-debugging-port=0")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(f"{self.base_url}/index.html")
        WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.ID, "editor")))
        time.sleep(0.5)

    def capture_initial(self, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "screenshot_initial.png")
        try:
            time.sleep(0.2)
            self.driver.save_screenshot(path)
            print(f"    ✓ Initial screenshot: {path}")
        except Exception as e:
            print(f"Warning: Failed to capture initial screenshot: {e}")
        self.counter = 1
        return path

    def capture_next(self, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"screenshot_{self.counter:04d}.png")
        try:
            time.sleep(0.2)
            self.driver.save_screenshot(path)
            print(f"    ✓ Screenshot: {path}")
        except Exception as e:
            print(f"Warning: Failed to capture screenshot: {e}")
        self.counter += 1
        return path

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        finally:
            try:
                if self.user_data_dir and os.path.exists(self.user_data_dir) and "chrome_user_data_" in os.path.basename(self.user_data_dir):
                    import shutil
                    shutil.rmtree(self.user_data_dir, ignore_errors=True)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Execute actions and capture screenshots per step")
    parser.add_argument(
        "--inputs",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference/results_text/evaluate_data_combination2,3,4_inference_results.json",
        help="Path to result JSON file (list of dicts with question/answer)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/inference/execute_action_output",
        help="Directory to save per-step screenshots"
    )
    parser.add_argument(
        "--files_dir",
        type=str,
        default="/shared/nas/data/m1/jiateng5/Mini_Word/file_and_images",
        help="Directory containing files to upload when actions require it"
    )
    args = parser.parse_args()

    # Check MiniWord server
    try:
        import requests
        r = requests.get("http://localhost:8001", timeout=5)
        if r.status_code != 200:
            print("❌ Please start the MiniWord server (python3 -m http.server 8001) before running.")
            return
    except Exception:
        print("❌ Please start the MiniWord server (python3 -m http.server 8001) before running.")
        return

    if not os.path.exists(args.inputs):
        print(f"❌ Input JSON not found: {args.inputs}")
        return

    with open(args.inputs, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("❌ Invalid input format: expected a list")
        return

    base_name = os.path.splitext(os.path.basename(args.inputs))[0]
    shooter = ScreenshotCapture()
    executor = ActionExecutor(shooter.driver, args.files_dir)

    processed = 0
    for idx, item in enumerate(data, 1):
        question = item.get("question")
        answer = item.get("answer")
        if not question or not answer:
            continue
        steps = extract_steps(answer)
        if not steps:
            print(f"Skipping item {idx}: no steps found")
            continue

        item_dir = os.path.join(args.output_dir, base_name, f"item_{idx:04d}")
        shots_dir = os.path.join(item_dir, "screenshots")
        os.makedirs(shots_dir, exist_ok=True)

        # Save steps text with numbering
        steps_txt = os.path.join(item_dir, "steps.txt")
        with open(steps_txt, 'w', encoding='utf-8') as sf:
            for sidx, step in enumerate(steps, 1):
                sf.write(f"{sidx}. {step}\n")

        print(f"\nItem {idx}: {question}")
        # Initial screenshot (pre-steps)
        shooter.capture_initial(shots_dir)

        for sidx, step in enumerate(steps, 1):
            print(f"  Step {sidx}/{len(steps)}: {step}")
            # Execute text-based action; if ambiguous, log exception and continue
            try:
                executor.execute_action_from_text(step)
            except Exception as e:
                print(f"❌ Step {sidx} failed: {e}")
            # Wait for UI to settle
            try:
                WebDriverWait(shooter.driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")
            except Exception:
                pass
            time.sleep(0.3)
            # Capture post-action screenshot to reflect state change
            next_img = shooter.capture_next(shots_dir)
            print(f"    ✓ Captured screenshot after action: {next_img}")

        processed += 1
        # Reset MiniWord to initial state for next item
        try:
            shooter.driver.get(f"{shooter.base_url}/index.html")
            WebDriverWait(shooter.driver, 10).until(EC.presence_of_element_located((By.ID, "editor")))
            time.sleep(0.3)
        except Exception:
            pass

    shooter.close()
    print(f"\nDone. Processed {processed} items.")


if __name__ == "__main__":
    main()


