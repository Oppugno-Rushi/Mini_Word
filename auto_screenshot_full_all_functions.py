#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniWord Complete Auto Screenshot Tool
Automatically captures screenshots of all 62 MiniWord function icons
"""

import os
import time
import json
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class MiniWordCompleteScreenshotTool:
    def __init__(self, base_url="http://localhost:8000", output_dir="function_screenshots"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.driver = None
        self.function_ids = []
        self.setup_driver()
        self.create_output_dirs()
        self.load_function_ids()
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
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
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Chrome driver initialized successfully")
        except Exception as e:
            print(f"✗ Error initializing Chrome driver: {e}")
            print("Please ensure Chrome and ChromeDriver are installed")
            raise
    
    def create_output_dirs(self):
        """Create output directories for screenshots"""
        categories = ['file', 'edit', 'view', 'insert', 'format', 'tools', 'help']
        for category in categories:
            category_dir = os.path.join(self.output_dir, category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        print(f"✓ Created output directories: {self.output_dir}")
    
    def load_function_ids(self):
        """Load all function IDs from the JSON file"""
        try:
            with open('explainations_for_botton.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Mapping between JSON IDs and HTML data-page attributes
            id_mapping = {
                'open_new_tab': 'new_tab',
                'web_refresh': 'web_refresh', 
                'web_close': 'web_close',
                'toggle_pagination': 'toggle_pagination'
            }
            
            # Extract all function IDs from the JSON structure
            for section_name, section_data in data['MiniWord_Button_Documentation']['sections'].items():
                if 'buttons' in section_data:
                    for button in section_data['buttons']:
                        if 'id' in button:
                            json_id = button['id']
                            # Use mapped ID if available, otherwise use original
                            html_id = id_mapping.get(json_id, json_id)
                            
                            self.function_ids.append({
                                'id': html_id,  # Use HTML-compatible ID
                                'json_id': json_id,  # Keep original JSON ID for reference
                                'name': button.get('name', button['id']),
                                'category': section_name.lower()
                            })
            
            print(f"✓ Loaded {len(self.function_ids)} function IDs from JSON")
            return True
        except Exception as e:
            print(f"✗ Error loading function IDs: {e}")
            return False
    
    def wait_for_page_load(self, timeout=10):
        """Wait for the page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "editor"))
            )
            time.sleep(2)  # Additional wait for any animations
            return True
        except TimeoutException:
            print("✗ Page load timeout")
            return False
    
    def close_any_open_modals(self):
        """Close any open modals that might be blocking clicks"""
        try:
            # Check for chart modal
            chart_modal = self.driver.find_element(By.ID, "chart-insert-modal")
            if chart_modal.is_displayed():
                print("🔧 Closing chart modal...")
                close_btn = self.driver.find_element(By.CSS_SELECTOR, ".modal-close")
                close_btn.click()
                time.sleep(0.5)
                print("✓ Chart modal closed")
        except:
            pass  # Modal not open or not found
        
        try:
            # Check for any other modals
            modals = self.driver.find_elements(By.CSS_SELECTOR, ".modal")
            for modal in modals:
                if modal.is_displayed():
                    print("🔧 Closing other modal...")
                    # Try to find close button
                    close_btn = modal.find_element(By.CSS_SELECTOR, ".modal-close, .close, [onclick*='close']")
                    close_btn.click()
                    time.sleep(0.5)
        except:
            pass  # No modals to close

    def switch_to_toolbar_section(self, section_name):
        """Switch to a specific toolbar section (File, Edit, View, etc.)"""
        try:
            # First close any open modals
            self.close_any_open_modals()
            
            # Click on the menu item to switch toolbar
            menu_item = self.driver.find_element(By.CSS_SELECTOR, f'[data-page="{section_name}"]')
            menu_item.click()
            time.sleep(1)  # Wait for toolbar to switch
            print(f"✓ Switched to {section_name} toolbar")
            return True
        except Exception as e:
            print(f"✗ Error switching to {section_name} toolbar: {e}")
            return False

    def click_function_button(self, function_id, section_name):
        """Click on a specific function button"""
        try:
            # First ensure we're in the right toolbar section
            if not self.switch_to_toolbar_section(section_name):
                return False
            
            # Special handling for insert_chart - it opens a modal
            if function_id == 'insert_chart':
                print(f"🔧 Special handling for {function_id} (modal function)")
                # The modal should already be open, just take screenshot
                return True
            
            # Try different selectors to find the button
            selectors = [
                f'[data-page="{function_id}"]',
                f'[data-testid="btn-{function_id.replace("_", "-")}"]',
                f'button[title*="{function_id}"]',
                f'button[aria-label*="{function_id}"]',
                f'button[title*="{function_id.replace("_", " ")}"]',
                f'button[aria-label*="{function_id.replace("_", " ")}"]'
            ]
            
            button = None
            for selector in selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if button:
                # Scroll to button if needed
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)
                
                # Click the button
                ActionChains(self.driver).move_to_element(button).click().perform()
                time.sleep(2)  # Wait for sidebar to load
                
                # Close any modals that might have opened
                self.close_any_open_modals()
                
                return True
            else:
                print(f"✗ Could not find button for function: {function_id}")
                # Debug: print available buttons
                self.debug_available_buttons(section_name)
                return False
                
        except Exception as e:
            print(f"✗ Error clicking button {function_id}: {e}")
            return False
    
    def debug_available_buttons(self, section_name):
        """Debug function to print available buttons in current section"""
        try:
            print(f"🔍 Debug: Available buttons in {section_name} section:")
            buttons = self.driver.find_elements(By.CSS_SELECTOR, '.toolbar-btn')
            for i, btn in enumerate(buttons[:10]):  # Show first 10 buttons
                data_page = btn.get_attribute('data-page')
                title = btn.get_attribute('title')
                print(f"  {i+1}. data-page='{data_page}', title='{title}'")
            if len(buttons) > 10:
                print(f"  ... and {len(buttons) - 10} more buttons")
        except Exception as e:
            print(f"Debug error: {e}")
    
    def take_full_page_screenshot(self, filename):
        """Take a full page screenshot"""
        try:
            # Get the full page dimensions
            total_width = self.driver.execute_script("return document.body.scrollWidth")
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Set window size to capture full page
            self.driver.set_window_size(total_width, total_height)
            time.sleep(1)
            
            # Take screenshot
            screenshot_path = os.path.join(self.output_dir, f"{filename}.png")
            self.driver.save_screenshot(screenshot_path)
            print(f"✓ Screenshot saved: {screenshot_path}")
            return True
        except Exception as e:
            print(f"✗ Error taking screenshot {filename}: {e}")
            return False
    
    def take_sidebar_screenshot(self, filename, category):
        """Take a screenshot focused on the sidebar content"""
        try:
            # Wait for sidebar to be visible
            sidebar = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "sidebar"))
            )
            
            # Check if sidebar is visible
            if sidebar.is_displayed():
                # Take screenshot of the entire page
                screenshot_path = os.path.join(self.output_dir, category, f"{filename}.png")
                self.driver.save_screenshot(screenshot_path)
                print(f"✓ Sidebar screenshot saved: {screenshot_path}")
                return True
            else:
                print(f"✗ Sidebar not visible for {filename}")
                return False
        except TimeoutException:
            print(f"✗ Sidebar timeout for {filename}")
            return False
        except Exception as e:
            print(f"✗ Error taking sidebar screenshot {filename}: {e}")
            return False
    
    def capture_all_functions(self):
        """Capture screenshots of all 62 function icons"""
        if not self.function_ids:
            print("✗ No function IDs loaded")
            return
        
        successful_captures = 0
        total_functions = len(self.function_ids)
        
        print(f"\n🚀 Starting to capture {total_functions} function screenshots...")
        print("=" * 60)
        
        # Navigate to the main page first
        try:
            self.driver.get(f"{self.base_url}/index.html")
            if not self.wait_for_page_load():
                print("✗ Failed to load main page")
                return
        except Exception as e:
            print(f"✗ Error loading main page: {e}")
            return
        
        # Group functions by category for better organization
        functions_by_category = {}
        for func in self.function_ids:
            category = func['category']
            if category not in functions_by_category:
                functions_by_category[category] = []
            functions_by_category[category].append(func)
        
        # Process each category
        for category, functions in functions_by_category.items():
            print(f"\n📂 Processing {category.upper()} section ({len(functions)} functions)")
            print("-" * 40)
            
            # Force close all modals at the start of each section
            self.close_any_open_modals()
            
            for i, function_info in enumerate(functions, 1):
                function_id = function_info['id']
                function_name = function_info['name']
                
                print(f"[{i}/{len(functions)}] Capturing: {function_name} ({function_id})")
                
                try:
                    # Click the function button (with section switching)
                    if self.click_function_button(function_id, category):
                        # Take screenshot
                        if self.take_sidebar_screenshot(function_id, category):
                            successful_captures += 1
                            print(f"✓ Successfully captured {function_name}")
                        else:
                            print(f"✗ Failed to capture screenshot for {function_name}")
                    else:
                        print(f"✗ Failed to click button for {function_name}")
                    
                    # Small delay between captures
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"✗ Error processing {function_name}: {e}")
                    continue
        
        print("\n" + "=" * 60)
        print(f"🎉 Screenshot capture completed!")
        print(f"✓ Successfully captured: {successful_captures}/{total_functions} functions")
        print(f"📁 Screenshots saved in: {self.output_dir}")
        
        # Create a summary file
        self.create_summary_file(successful_captures, total_functions)
    
    def create_summary_file(self, successful, total):
        """Create a summary file of the screenshot session"""
        try:
            summary_path = os.path.join(self.output_dir, "screenshot_summary.txt")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("MiniWord Function Screenshot Summary\n")
                f.write("=" * 40 + "\n\n")
                f.write(f"Total functions: {total}\n")
                f.write(f"Successfully captured: {successful}\n")
                f.write(f"Failed captures: {total - successful}\n")
                f.write(f"Success rate: {(successful/total)*100:.1f}%\n\n")
                f.write("Screenshots organized by category:\n")
                f.write("- file/\n")
                f.write("- edit/\n")
                f.write("- view/\n")
                f.write("- insert/\n")
                f.write("- format/\n")
                f.write("- tools/\n")
                f.write("- help/\n")
            
            print(f"✓ Summary file created: {summary_path}")
        except Exception as e:
            print(f"✗ Error creating summary file: {e}")
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser driver closed")

def check_server():
    """Check if the MiniWord server is running"""
    try:
        import requests
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            print("✓ MiniWord server is running on localhost:8000")
            return True
        else:
            print("✗ MiniWord server is not responding properly")
            return False
    except:
        print("✗ MiniWord server is not running")
        return False

def main():
    """Main function to run the screenshot tool"""
    print("🎯 MiniWord Complete Auto Screenshot Tool")
    print("=" * 50)
    print("This tool will capture screenshots of all 62 function icons")
    print("=" * 50)
    
    # Check if server is running
    if not check_server():
        print("\n❌ Please start the MiniWord server first:")
        print("   python3 -m http.server 8000")
        print("   or")
        print("   ./start_server.sh")
        return
    
    # Check if JSON file exists
    if not os.path.exists('explainations_for_botton.json'):
        print("❌ explainations_for_botton.json file not found!")
        return
    
    # Initialize and run screenshot tool
    tool = MiniWordCompleteScreenshotTool()
    
    try:
        tool.capture_all_functions()
    except KeyboardInterrupt:
        print("\n⚠️ Screenshot capture interrupted by user")
    except Exception as e:
        print(f"❌ Error during screenshot capture: {e}")
    finally:
        tool.close()

if __name__ == "__main__":
    main()
