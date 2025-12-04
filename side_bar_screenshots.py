#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniWord Sidebar Screenshot Tool
Automatically captures screenshots of sidebar content for each MiniWord function
"""

import os
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class MiniWordSidebarScreenshotTool:
    def __init__(self, base_url="http://localhost:8000", output_dir="/shared/nas/data/m1/jiateng5/Mini_Word/side_bar_image"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.driver = None
        self.function_ids = []
        self.setup_driver()
        self.create_output_dir()
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
    
    def create_output_dir(self):
        """Create output directory for screenshots"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"✓ Created output directory: {self.output_dir}")
    
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
        """Wait for the page to load completely"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "editor"))
            )
            time.sleep(2)  # Additional wait for dynamic content
            return True
        except TimeoutException:
            print("✗ Page load timeout")
            return False
    
    def close_any_open_modals(self):
        """Close any open modal dialogs that might block interactions"""
        try:
            # Check for chart insert modal
            modal = self.driver.find_element(By.ID, "chart-insert-modal")
            if modal.is_displayed():
                close_btn = self.driver.find_element(By.CLASS_NAME, "modal-close")
                close_btn.click()
                time.sleep(1)
                print("✓ Closed chart insert modal")
        except NoSuchElementException:
            pass  # No modal to close
        
        try:
            # Check for any other modals
            modals = self.driver.find_elements(By.CLASS_NAME, "modal")
            for modal in modals:
                if modal.is_displayed():
                    close_btn = modal.find_element(By.CLASS_NAME, "modal-close")
                    close_btn.click()
                    time.sleep(1)
                    print("✓ Closed modal dialog")
        except NoSuchElementException:
            pass  # No modals to close
    
    def switch_to_toolbar_section(self, section_name):
        """Switch to the specified toolbar section"""
        try:
            # Close any open modals first
            self.close_any_open_modals()
            
            # Find and click the menu item
            menu_item = self.driver.find_element(By.CSS_SELECTOR, f'[data-page="{section_name}"]')
            menu_item.click()
            time.sleep(3)  # Increased wait time for toolbar to switch
            
            # Verify the toolbar switched by checking if it's visible
            try:
                toolbar = self.driver.find_element(By.CSS_SELECTOR, f'#{section_name}-toolbar')
                if toolbar.is_displayed():
                    print(f"✓ Switched to {section_name} toolbar")
                    return True
                else:
                    print(f"✗ {section_name} toolbar not visible")
                    return False
            except NoSuchElementException:
                print(f"✗ {section_name} toolbar element not found")
                return False
                
        except Exception as e:
            print(f"✗ Error switching to {section_name} toolbar: {e}")
            return False
    
    def click_function_button(self, function_id, function_name):
        """Click a specific function button using dynamic discovery"""
        try:
            # Close any modals that might be open first
            self.close_any_open_modals()
            
            # Get the category and switch to the correct toolbar first
            category = self.get_category_for_function(function_id)
            if category and category != 'file':  # File toolbar is already active by default
                if not self.switch_to_toolbar_section(category):
                    print(f"✗ Failed to switch to {category} toolbar for {function_name}")
                    return False
            
            # Now try to find and click the button
            button = self.find_button_anywhere(function_id, function_name)
            
            if button:
                # Check if this button opens a modal (like insert_chart)
                if self.button_opens_modal(function_id):
                    button.click()
                    time.sleep(2)
                    # Don't close the modal, let it stay open for screenshot
                else:
                    button.click()
                    time.sleep(1)
                
                print(f"✓ Clicked button: {function_name} ({function_id})")
                return True
            else:
                print(f"✗ Button not found: {function_name} ({function_id}) in {category} toolbar")
                return False
                
        except Exception as e:
            print(f"✗ Error clicking button {function_id}: {e}")
            return False
    
    def handle_submenu_functions(self, function_id, function_name, category):
        """Handle functions that may have submenus by automatically detecting them"""
        try:
            # First, try to click the main button to see if it opens a submenu
            if self.click_function_button(function_id, function_name):
                time.sleep(1)
                
                # Check if any submenu appeared after clicking
                submenu_items = self.detect_submenu_items()
                
                if submenu_items:
                    print(f"  📋 Found {len(submenu_items)} submenu items for {function_name}")
                    results = []
                    
                    for submenu_item in submenu_items:
                        print(f"  📋 Processing submenu: {submenu_item['name']} ({submenu_item['id']})")
                        
                        # Click the submenu item
                        if self.click_submenu_item(submenu_item['id'], submenu_item['name']):
                            # Take screenshot for this submenu item
                            if self.take_sidebar_screenshot(submenu_item['id'], submenu_item['name'], category):
                                results.append(True)
                            else:
                                results.append(False)
                        else:
                            results.append(False)
                        
                        # Click main button again to reopen submenu for next item
                        if len(submenu_items) > 1:  # Only if there are more items
                            self.click_function_button(function_id, function_name)
                            time.sleep(1)
                    
                    return sum(results)  # Return count of successful submenu captures
                else:
                    # No submenu found, this is a regular function
                    print(f"  📋 No submenu detected for {function_name}, treating as regular function")
                    if self.take_sidebar_screenshot(function_id, function_name, category):
                        return 1  # Return 1 for successful regular function
                    else:
                        return 0  # Return 0 for failed regular function
            else:
                print(f"✗ Failed to click main button: {function_name}")
                return 0
                
        except Exception as e:
            print(f"✗ Error handling function {function_id}: {e}")
            return 0
    
    def detect_submenu_items(self):
        """Automatically detect all visible submenu items"""
        submenu_items = []
        
        try:
            # Look for common submenu containers
            submenu_selectors = [
                '.submenu',
                '.submenu-content',
                '.dropdown-menu',
                '.context-menu',
                '[class*="submenu"]',
                '[class*="dropdown"]'
            ]
            
            for selector in submenu_selectors:
                try:
                    submenu_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submenu_container and submenu_container.is_displayed():
                        # Find all submenu items within this container
                        items = submenu_container.find_elements(By.CSS_SELECTOR, '.submenu-item, .dropdown-item, [data-page]')
                        
                        for item in items:
                            if item.is_displayed():
                                # Extract item information
                                item_id = item.get_attribute('data-page') or item.get_attribute('id')
                                item_name = (item.get_attribute('title') or 
                                           item.get_attribute('aria-label') or 
                                           item.text.strip() or 
                                           f"Submenu Item {len(submenu_items) + 1}")
                                
                                if item_id and item_name:
                                    submenu_items.append({
                                        'id': item_id,
                                        'name': item_name
                                    })
                        
                        if submenu_items:
                            break  # Found submenu items, no need to check other selectors
                            
                except NoSuchElementException:
                    continue
            
            return submenu_items
            
        except Exception as e:
            print(f"  ⚠️ Error detecting submenu items: {e}")
            return []
    
    def click_submenu_item(self, submenu_id, submenu_name):
        """Click a specific submenu item"""
        try:
            # Try multiple selectors to find the submenu item
            submenu_selectors = [
                f'.submenu-item[data-page="{submenu_id}"]',
                f'[data-page="{submenu_id}"]',
                f'[id="{submenu_id}"]',
                f'[title*="{submenu_name}"]',
                f'[aria-label*="{submenu_name}"]'
            ]
            
            for selector in submenu_selectors:
                try:
                    submenu_item = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submenu_item and submenu_item.is_displayed():
                        submenu_item.click()
                        time.sleep(1)
                        print(f"  ✓ Clicked submenu item: {submenu_name}")
                        return True
                except NoSuchElementException:
                    continue
            
            print(f"  ✗ Submenu item not found: {submenu_name}")
            return False
            
        except Exception as e:
            print(f"  ✗ Error clicking submenu item {submenu_name}: {e}")
            return False
    
    
    def find_button_anywhere(self, function_id, function_name):
        """Find a button anywhere on the page using multiple strategies"""
        # Try multiple selectors to find the button
        selectors = [
            f'[data-page="{function_id}"]',
            f'[data-testid="btn-{function_id.replace("_", "-")}"]',
            f'button[title*="{function_name}"]',
            f'button[aria-label*="{function_name}"]',
            f'[title*="{function_name}"]',
            f'[aria-label*="{function_name}"]'
        ]
        
        for selector in selectors:
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if button and button.is_displayed():
                    return button
            except NoSuchElementException:
                continue
        
        return None
    
    def button_opens_modal(self, function_id):
        """Check if a button opens a modal dialog by detecting modal-related attributes"""
        try:
            # Look for buttons that have modal-related attributes or classes
            button = self.driver.find_element(By.CSS_SELECTOR, f'[data-page="{function_id}"]')
            
            # Check for modal-related attributes
            modal_indicators = [
                'data-modal', 'data-dialog', 'data-popup',
                'class*="modal"', 'class*="dialog"', 'class*="popup"'
            ]
            
            for indicator in modal_indicators:
                if button.get_attribute(indicator.replace('class*="', '').replace('"', '')):
                    return True
            
            # Check if button text/attributes suggest it opens a modal
            button_text = button.get_attribute('title') or button.get_attribute('aria-label') or ''
            modal_keywords = ['insert', 'add', 'create', 'new', 'setup', 'settings']
            
            if any(keyword in button_text.lower() for keyword in modal_keywords):
                return True
                
            return False
            
        except NoSuchElementException:
            # If we can't find the button, assume it doesn't open a modal
            return False
    
    def get_category_for_function(self, function_id):
        """Get the category/toolbar section for a function by finding which toolbar contains it"""
        try:
            # Try to find the button in each toolbar section
            toolbar_sections = ['file', 'edit', 'view', 'insert', 'format', 'tools', 'help']
            
            for section in toolbar_sections:
                try:
                    # Look for the button in this toolbar section
                    button = self.driver.find_element(By.CSS_SELECTOR, f'#{section}-toolbar [data-page="{function_id}"]')
                    if button:
                        return section
                except NoSuchElementException:
                    continue
            
            # If not found in any specific toolbar, try alternative selectors
            for section in toolbar_sections:
                try:
                    # Try different selectors
                    selectors = [
                        f'#{section}-toolbar [data-testid*="{function_id}"]',
                        f'#{section}-toolbar button[title*="{function_id}"]',
                        f'#{section}-toolbar [aria-label*="{function_id}"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if button:
                                return section
                        except NoSuchElementException:
                            continue
                except:
                    continue
            
            # Default to file if not found
            print(f"⚠️ Could not determine category for {function_id}, defaulting to 'file'")
            return 'file'
            
        except Exception as e:
            print(f"⚠️ Error determining category for {function_id}: {e}")
            return 'file'
    
    def take_sidebar_screenshot(self, function_id, function_name, category):
        """Take a screenshot of only the sidebar content area"""
        try:
            # Wait for sidebar to be visible and content to load
            sidebar = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "sidebar"))
            )
            
            # Additional wait for content to populate
            time.sleep(3)
            
            # Check if sidebar is visible
            if sidebar.is_displayed():
                # Create filename with category prefix
                filename = f"{function_id}_{category}"
                screenshot_path = os.path.join(self.output_dir, f"{filename}.png")
                
                # Try sidebar.screenshot() first, fallback to full page if it fails
                try:
                    sidebar.screenshot(screenshot_path)
                    print(f"✓ Sidebar screenshot saved: {screenshot_path}")
                    return True
                except Exception as sidebar_error:
                    print(f"⚠️ Sidebar screenshot failed, trying full page: {sidebar_error}")
                    # Fallback: take full page screenshot
                    self.driver.save_screenshot(screenshot_path)
                    print(f"✓ Full page screenshot saved: {screenshot_path}")
                    return True
            else:
                print(f"✗ Sidebar not visible for {function_name}")
                return False
                
        except TimeoutException:
            print(f"✗ Sidebar timeout for {function_name}")
            return False
        except Exception as e:
            print(f"✗ Error taking sidebar screenshot for {function_name}: {e}")
            return False
    
    def capture_all_sidebar_screenshots(self):
        """Capture screenshots of sidebar content for all functions"""
        if not self.function_ids:
            print("✗ No function IDs loaded")
            return
        
        successful_captures = 0
        total_functions = len(self.function_ids)
        
        print(f"\n🚀 Starting to capture {total_functions} sidebar screenshots...")
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
        
        # Process each function
        for i, func in enumerate(self.function_ids, 1):
            function_id = func['id']
            function_name = func['name']
            category = func['category']
            
            print(f"\n[{i}/{total_functions}] Processing: {function_name} ({function_id}) - Category: {category}")
            print("-" * 60)
            
            # Handle the function (including submenus)
            result = self.handle_submenu_functions(function_id, function_name, category)
            if result > 0:
                successful_captures += result  # Add count of successful captures
            else:
                print(f"✗ Failed to process function: {function_name}")
            
            # Small delay between functions
            time.sleep(1)
        
        # Generate summary report
        self.create_summary_report(successful_captures, total_functions)
        
        print(f"\n🎉 Sidebar screenshot capture completed!")
        print(f"✓ Successfully captured: {successful_captures}/{total_functions} functions")
        print(f"📁 Screenshots saved in: {self.output_dir}")
        print(f"📂 Full path: {os.path.abspath(self.output_dir)}")
    
    def create_summary_report(self, successful_captures, total_functions):
        """Create a summary report of the screenshot session"""
        try:
            report_path = os.path.join(self.output_dir, "screenshot_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("MiniWord Sidebar Screenshot Report\n")
                f.write("=" * 40 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Functions: {total_functions}\n")
                f.write(f"Successful Captures: {successful_captures}\n")
                f.write(f"Failed Captures: {total_functions - successful_captures}\n")
                f.write(f"Success Rate: {(successful_captures/total_functions)*100:.1f}%\n\n")
                
                f.write("Function List:\n")
                f.write("-" * 20 + "\n")
                for func in self.function_ids:
                    f.write(f"- {func['name']} ({func['id']}) - {func['category']}\n")
            
            print(f"✓ Summary report created: {report_path}")
        except Exception as e:
            print(f"✗ Error creating summary report: {e}")
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser driver closed")

def main():
    """Main function to run the sidebar screenshot tool"""
    print("MiniWord Sidebar Screenshot Tool")
    print("=" * 40)
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code == 200:
            print("✓ MiniWord server is running on localhost:8000")
        else:
            print("✗ MiniWord server is not responding properly")
            return
    except:
        print("✗ MiniWord server is not running. Please start it first:")
        print("  python3 -m http.server 8000")
        return
    
    # Initialize and run screenshot tool
    tool = MiniWordSidebarScreenshotTool()
    
    try:
        tool.capture_all_sidebar_screenshots()
    except KeyboardInterrupt:
        print("\n⚠️ Screenshot capture interrupted by user")
    except Exception as e:
        print(f"✗ Error during screenshot capture: {e}")
    finally:
        tool.close()

if __name__ == "__main__":
    main()
