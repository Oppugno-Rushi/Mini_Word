#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniWord Trajectory Auto Screenshot Tool
Automatically discovers toolbar tabs and buttons, captures screenshots, and
builds a trajectory.json describing the function tree.

Outputs:
- function_screenshots_trajectory/
  - initial_overview.png
  - <category>/overview.png
  - <category>/<function_id>.png
- trajectory.json (tree structure)
"""

import os
import time
import json
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class MiniWordTrajectoryScreenshot:
    def __init__(self, base_url: str = "http://localhost:8000", output_dir: str = "function_screenshots_trajectory") -> None:
        self.base_url = base_url
        self.output_dir = output_dir
        self.driver: Optional[webdriver.Chrome] = None
        self.setup_driver()
        self.ensure_output_dir()

    def setup_driver(self) -> None:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")

        self.driver = webdriver.Chrome(options=chrome_options)

    def ensure_output_dir(self) -> None:
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        try:
            assert self.driver is not None
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "editor"))
            )
            time.sleep(1)
            return True
        except TimeoutException:
            return False

    def navigate_home(self) -> None:
        assert self.driver is not None
        self.driver.get(f"{self.base_url}/index.html")
        self.wait_for_page_load()

    def take_fullpage_screenshot(self, path: str) -> bool:
        try:
            assert self.driver is not None
            # Keep fixed window-size (1920x1080) to match legacy screenshots
            time.sleep(0.3)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.driver.save_screenshot(path)
            return True
        except Exception:
            return False

    def take_sidebar_screenshot(self, path: str, timeout: int = 5) -> bool:
        try:
            assert self.driver is not None
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "sidebar"))
            )
            # Keep fixed window-size (1920x1080) to match legacy screenshots
            time.sleep(0.3)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.driver.save_screenshot(path)
            return True
        except Exception:
            return False

    def close_any_open_modals(self) -> None:
        assert self.driver is not None
        try:
            chart_modal = self.driver.find_element(By.ID, "chart-insert-modal")
            if chart_modal.is_displayed():
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, ".modal-close")
                    close_btn.click()
                    time.sleep(0.25)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            modals = self.driver.find_elements(By.CSS_SELECTOR, ".modal")
            for modal in modals:
                if modal.is_displayed():
                    try:
                        close_btn = modal.find_element(By.CSS_SELECTOR, ".modal-close, .close, [onclick*='close']")
                        close_btn.click()
                        time.sleep(0.25)
                    except Exception:
                        continue
        except Exception:
            pass

    def discover_menu_tabs(self) -> List[Dict[str, str]]:
        assert self.driver is not None
        items = self.driver.find_elements(By.CSS_SELECTOR, ".menu-bar .menu-item")
        tabs: List[Dict[str, str]] = []
        for el in items:
            tab_id = el.get_attribute("data-page") or ""
            label = (el.text or tab_id).strip()
            if tab_id:
                tabs.append({"id": tab_id, "label": label})
        return tabs

    def switch_to_tab(self, tab_id: str) -> bool:
        assert self.driver is not None
        try:
            self.close_any_open_modals()
            el = self.driver.find_element(By.CSS_SELECTOR, f".menu-bar .menu-item[data-page='{tab_id}']")
            ActionChains(self.driver).move_to_element(el).click().perform()
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def get_visible_toolbar_container(self) -> Optional[object]:
        assert self.driver is not None
        containers = self.driver.find_elements(By.CSS_SELECTOR, "#dynamic-toolbar .toolbar-content")
        for c in containers:
            try:
                display = c.value_of_css_property("display")
                if display != "none":
                    return c
            except Exception:
                continue
        return None

    def discover_toolbar_buttons(self) -> List[Dict[str, str]]:
        container = self.get_visible_toolbar_container()
        if container is None:
            return []
        buttons = container.find_elements(By.CSS_SELECTOR, "button.toolbar-btn")
        result: List[Dict[str, str]] = []
        for b in buttons:
            fn_id = b.get_attribute("data-page") or ""
            title = b.get_attribute("title") or fn_id
            submenu = b.get_attribute("data-submenu") or ""
            if fn_id:
                result.append({"id": fn_id, "title": title, "submenu": submenu})
        return result

    def discover_submenu_items(self, submenu_id: str) -> List[Dict[str, str]]:
        if not submenu_id:
            return []
        assert self.driver is not None
        try:
            submenu_el = self.driver.find_element(By.CSS_SELECTOR, f"#{submenu_id}")
            items = submenu_el.find_elements(By.CSS_SELECTOR, ".submenu-item")
            result: List[Dict[str, str]] = []
            for it in items:
                sid = it.get_attribute("data-page") or ""
                label = it.text.strip() or sid
                if sid:
                    result.append({"id": sid, "title": label})
            return result
        except Exception:
            return []

    def click_toolbar_button(self, function_id: str) -> bool:
        assert self.driver is not None
        selectors = [
            f"[data-page='{function_id}']",
            f"[data-testid='btn-{function_id.replace('_','-')}']",
            f"button[title*='{function_id}']",
            f"button[aria-label*='{function_id}']",
            f"button[title*='{function_id.replace('_',' ')}']",
            f"button[aria-label*='{function_id.replace('_',' ')}']",
        ]
        for sel in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                ActionChains(self.driver).move_to_element(el).click().perform()
                time.sleep(0.6)
                self.close_any_open_modals()
                return True
            except NoSuchElementException:
                continue
            except Exception:
                continue
        return False

    def build_trajectory(self) -> Dict[str, object]:
        assert self.driver is not None

        trajectory: Dict[str, object] = {
            "initial page": {
                "status": "",
                "action": {}
            }
        }

        print("🎯 MiniWord Complete Auto Screenshot Tool")
        print("=" * 50)
        print("This tool will capture screenshots of all 62 function icons")
        print("=" * 50)

        # Plan: gather tabs and per-tab functions
        tabs = self.discover_menu_tabs()
        tab_to_functions: Dict[str, List[Dict[str, str]]] = {}
        for tab in tabs:
            tab_id = tab["id"]
            self.switch_to_tab(tab_id)
            tab_to_functions[tab_id] = self.discover_toolbar_buttons()
        total_functions = sum(len(funcs) for funcs in tab_to_functions.values())
        print(f"\n🚀 Starting to capture {total_functions} function screenshots...")
        print("=" * 60)

        # Initial page screenshot
        initial_path = os.path.join(self.output_dir, "initial_overview.png")
        self.take_fullpage_screenshot(initial_path)
        trajectory["initial page"]["status"] = initial_path

        # Execute: per tab
        for tab in tabs:
            tab_id = tab["id"]
            trajectory["initial page"]["action"].setdefault(tab_id, {"status": "", "action": {}})

            # Switch and capture category overview
            if self.switch_to_tab(tab_id):
                category_dir = os.path.join(self.output_dir, tab_id)
                os.makedirs(category_dir, exist_ok=True)
                cat_overview = os.path.join(category_dir, "overview.png")
                self.take_fullpage_screenshot(cat_overview)
                trajectory["initial page"]["action"][tab_id]["status"] = cat_overview

            functions = tab_to_functions.get(tab_id, [])
            print(f"\n📂 Processing {tab_id.upper()} section ({len(functions)} functions)")
            print("-" * 40)

            # Process functions
            successful_captures = 0
            for fn in functions:
                fn_id = fn["id"]
                node = {"status": None, "action": {}}

                # Submenu items as nested actions without screenshots
                submenu_items = self.discover_submenu_items(fn.get("submenu", ""))
                for sm in submenu_items:
                    node["action"][sm["id"]] = {"status": None, "action": {}}

                # Prepare directories for function-level overview
                fn_dir = os.path.join(category_dir, fn_id)
                os.makedirs(fn_dir, exist_ok=True)
                fn_overview = os.path.join(fn_dir, "overview.png")

                # Click to open sidebar/modal then take screenshot of the page including sidebar when present
                idx = functions.index(fn) + 1
                print(f"[{idx}/{len(functions)}] Capturing: {fn_id} ({fn_id})")
                if self.click_toolbar_button(fn_id):
                    if not self.take_sidebar_screenshot(fn_overview):
                        self.take_fullpage_screenshot(fn_overview)
                    time.sleep(0.2)
                    successful_captures += 1
                    print(f"✓ Successfully captured {fn_id}")
                else:
                    print(f"✗ Failed to click button for {fn_id}")

                # Record function node status to nested overview
                node["status"] = fn_overview
                trajectory["initial page"]["action"][tab_id]["action"][fn_id] = node

        print("\n" + "=" * 60)
        print("🎉 Screenshot capture completed!")
        print(f"📁 Screenshots saved in: {self.output_dir}")

        return trajectory

    def close(self) -> None:
        if self.driver:
            self.driver.quit()


def check_server() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:8000", timeout=4)
        return r.status_code == 200
    except Exception:
        return False


def main() -> None:
    if not check_server():
        print("❌ Please start the MiniWord server first (python3 -m http.server 8000)")
        return

    tool = MiniWordTrajectoryScreenshot()
    try:
        tool.navigate_home()
        trajectory = tool.build_trajectory()
        # Persist trajectory.json at repo root alongside output dir
        traj_path = os.path.join(tool.output_dir, "trajectory.json")
        with open(traj_path, "w", encoding="utf-8") as f:
            json.dump(trajectory, f, ensure_ascii=False, indent=2)
        print(f"✓ Trajectory saved to: {traj_path}")
        print(f"✓ Screenshots saved under: {tool.output_dir}")
    except KeyboardInterrupt:
        print("⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        tool.close()


if __name__ == "__main__":
    main()


