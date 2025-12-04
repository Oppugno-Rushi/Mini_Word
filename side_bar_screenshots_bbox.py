#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniWord Sidebar Screenshot Tool with Bounding Box Detection
Captures full screenshots, detects sidebar bounding box, highlights it, and crops sidebar images
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
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class MiniWordSidebarBboxScreenshotTool:
    def __init__(self, base_url="http://localhost:8000", output_dir="/shared/nas/data/m1/jiateng5/Mini_Word/side_bar_image_bbox"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.bbox_dir = os.path.join(output_dir, "full_screenshots_with_bbox")
        self.sidebar_dir = os.path.join(output_dir, "cropped_sidebars")
        self.button_bbox_dir = os.path.join(output_dir, "button_image_bbox")
        self.sidebar_elements_dir = os.path.join(output_dir, "sidebar_elements_bbox")
        self.menu_bar_dir = os.path.join(output_dir, "menu_bar_bbox")
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
        for directory in [self.output_dir, self.bbox_dir, self.sidebar_dir, self.button_bbox_dir, self.sidebar_elements_dir, self.menu_bar_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"✓ Created directory: {directory}")
    
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
                            if self.take_bbox_screenshot(submenu_item['id'], submenu_item['name'], category):
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
                    if self.take_bbox_screenshot(function_id, function_name, category):
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
    
    def get_sidebar_bbox(self):
        """Get sidebar bounding box coordinates and dimensions"""
        try:
            # Wait for sidebar to be visible
            sidebar = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "sidebar"))
            )
            
            # Additional wait for content to populate
            time.sleep(2)
            
            if sidebar.is_displayed():
                # Get element location and size
                location = sidebar.location
                size = sidebar.size
                
                # Calculate coordinates
                x = location['x']
                y = location['y'] 
                width = size['width']
                height = size['height']
                
                bbox_info = {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'right': x + width,
                    'bottom': y + height
                }
                
                print(f"✓ Sidebar bbox detected: x={x}, y={y}, w={width}, h={height}")
                return bbox_info
            else:
                print("✗ Sidebar not visible")
                return None
                
        except TimeoutException:
            print("✗ Sidebar timeout")
            return None
        except Exception as e:
            print(f"✗ Error getting sidebar bbox: {e}")
            return None
    
    def highlight_bbox_on_image(self, image_path, bbox_info, output_path):
        """Highlight the sidebar bounding box on the full screenshot"""
        try:
            # Open the image
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            
            # Define bbox coordinates
            x1 = bbox_info['x']
            y1 = bbox_info['y']
            x2 = bbox_info['right']
            y2 = bbox_info['bottom']
            
            # Draw a thick red rectangle around the sidebar
            draw.rectangle([x1, y1, x2, y2], outline='red', width=4)
            
            # Add a label
            try:
                # Try to use a default font, fallback to basic if not available
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Draw label background
            label_text = "SIDEBAR"
            label_bbox = draw.textbbox((0, 0), label_text, font=font)
            label_width = label_bbox[2] - label_bbox[0]
            label_height = label_bbox[3] - label_bbox[1]
            
            # Position label at top-left of sidebar
            label_x = x1 + 5
            label_y = y1 + 5
            
            # Draw label background
            draw.rectangle([label_x-2, label_y-2, label_x+label_width+2, label_y+label_height+2], 
                          fill='red', outline='red')
            
            # Draw label text
            draw.text((label_x, label_y), label_text, fill='white', font=font)
            
            # Save the highlighted image
            image.save(output_path)
            print(f"✓ Bbox highlighted image saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error highlighting bbox: {e}")
            return False
    
    def crop_sidebar_from_full_screenshot(self, full_screenshot_path, bbox_info, output_path):
        """Crop sidebar area from full screenshot using bbox coordinates"""
        try:
            # Open the full screenshot
            full_image = Image.open(full_screenshot_path)
            
            # Crop the sidebar area
            sidebar_image = full_image.crop((
                bbox_info['x'],
                bbox_info['y'], 
                bbox_info['right'],
                bbox_info['bottom']
            ))
            
            # Save the cropped sidebar
            sidebar_image.save(output_path)
            print(f"✓ Cropped sidebar saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error cropping sidebar: {e}")
            return False
    
    def get_all_buttons_in_toolbar(self, toolbar_section):
        """Get all buttons in a specific toolbar section with their bbox information"""
        try:
            # Switch to the toolbar section first
            if not self.switch_to_toolbar_section(toolbar_section):
                print(f"✗ Failed to switch to {toolbar_section} toolbar")
                return []
            
            # Wait for toolbar to be visible
            time.sleep(2)
            
            # Find the toolbar container
            toolbar = self.driver.find_element(By.CSS_SELECTOR, f'#{toolbar_section}-toolbar')
            if not toolbar.is_displayed():
                print(f"✗ {toolbar_section} toolbar not visible")
                return []
            
            # Find all buttons in the toolbar
            button_selectors = [
                'button[data-page]',
                '[data-page]',
                'button[title]',
                'button[aria-label]',
                '.toolbar-button',
                '.btn'
            ]
            
            buttons_info = []
            found_buttons = set()  # To avoid duplicates
            
            for selector in button_selectors:
                try:
                    buttons = toolbar.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.size['width'] > 0 and button.size['height'] > 0:
                            # Get button information
                            button_id = (button.get_attribute('data-page') or 
                                       button.get_attribute('id') or 
                                       button.get_attribute('title') or 
                                       f"button_{len(buttons_info)}")
                            
                            # Skip if we already found this button
                            if button_id in found_buttons:
                                continue
                            found_buttons.add(button_id)
                            
                            # Get button location and size
                            location = button.location
                            size = button.size
                            
                            button_info = {
                                'id': button_id,
                                'name': (button.get_attribute('title') or 
                                        button.get_attribute('aria-label') or 
                                        button.text.strip() or 
                                        button_id),
                                'x': location['x'],
                                'y': location['y'],
                                'width': size['width'],
                                'height': size['height'],
                                'right': location['x'] + size['width'],
                                'bottom': location['y'] + size['height']
                            }
                            
                            buttons_info.append(button_info)
                            
                except NoSuchElementException:
                    continue
            
            print(f"✓ Found {len(buttons_info)} buttons in {toolbar_section} toolbar")
            return buttons_info
            
        except Exception as e:
            print(f"✗ Error getting buttons in {toolbar_section} toolbar: {e}")
            return []
    
    def highlight_single_bbox_on_image(self, image_path, button_info, toolbar_section, output_path):
        """Highlight a single button bounding box on the full screenshot"""
        try:
            # Open the image
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            
            # Try to use a default font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            except:
                font = ImageFont.load_default()
            
            # Draw rectangle around the single button
            x1 = button_info['x']
            y1 = button_info['y']
            x2 = button_info['right']
            y2 = button_info['bottom']
            
            # Draw thick red rectangle
            draw.rectangle([x1, y1, x2, y2], outline='red', width=4)
            
            # Add button label
            label_text = button_info['name']
            if len(label_text) > 20:
                label_text = label_text[:17] + "..."
            
            # Position label at top-left of button
            label_x = x1 + 5
            label_y = y1 + 5
            
            # Draw label background
            label_bbox = draw.textbbox((0, 0), label_text, font=font)
            label_width = label_bbox[2] - label_bbox[0]
            label_height = label_bbox[3] - label_bbox[1]
            
            draw.rectangle([label_x-3, label_y-3, label_x+label_width+3, label_y+label_height+3], 
                          fill='red', outline='red')
            
            # Draw label text
            draw.text((label_x, label_y), label_text, fill='white', font=font)
            
            # No title needed - just the bbox annotation is sufficient
            
            # Save the highlighted image
            image.save(output_path)
            print(f"✓ Single bbox highlighted image saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error highlighting single bbox: {e}")
            return False
    
    def create_individual_button_screenshots(self, full_screenshot_path, buttons_info, toolbar_section):
        """Create individual button screenshots with single bbox highlighting"""
        try:
            successful_screenshots = 0
            
            for i, button_info in enumerate(buttons_info):
                try:
                    # Create filename for individual button screenshot
                    safe_name = button_info['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
                    button_filename = f"{toolbar_section}_{button_info['id']}_{safe_name}_bbox.png"
                    button_path = os.path.join(self.button_bbox_dir, button_filename)
                    
                    # Create individual screenshot with single bbox highlighting
                    if self.highlight_single_bbox_on_image(full_screenshot_path, button_info, toolbar_section, button_path):
                        successful_screenshots += 1
                        print(f"  ✓ Created individual screenshot: {button_filename}")
                    else:
                        print(f"  ✗ Failed to create screenshot for button {button_info['name']}")
                    
                except Exception as e:
                    print(f"  ✗ Error creating screenshot for button {button_info['name']}: {e}")
                    continue
            
            print(f"✓ Successfully created {successful_screenshots}/{len(buttons_info)} individual button screenshots")
            return successful_screenshots
            
        except Exception as e:
            print(f"✗ Error creating individual button screenshots: {e}")
            return 0
    
    def capture_toolbar_button_bboxes(self, toolbar_section):
        """Capture all buttons in a toolbar section with individual bbox screenshots"""
        try:
            print(f"\n🔧 Capturing {toolbar_section} toolbar buttons...")
            print("-" * 50)
            
            # Get all buttons in the toolbar
            buttons_info = self.get_all_buttons_in_toolbar(toolbar_section)
            if not buttons_info:
                print(f"✗ No buttons found in {toolbar_section} toolbar")
                return False
            
            # Take full page screenshot
            full_screenshot_path = os.path.join(self.button_bbox_dir, f"{toolbar_section}_toolbar_full.png")
            self.driver.save_screenshot(full_screenshot_path)
            print(f"✓ Full screenshot saved: {full_screenshot_path}")
            
            # Create individual button screenshots with single bbox highlighting
            screenshot_count = self.create_individual_button_screenshots(full_screenshot_path, buttons_info, toolbar_section)
            
            print(f"✓ Successfully processed {toolbar_section} toolbar: {len(buttons_info)} buttons, {screenshot_count} individual screenshots created")
            return True
            
        except Exception as e:
            print(f"✗ Error capturing {toolbar_section} toolbar buttons: {e}")
            return False
    
    def get_sidebar_interactive_elements(self):
        """Get all interactive elements within the sidebar (input fields, buttons, etc.)"""
        try:
            # Wait for sidebar to be visible
            sidebar = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "sidebar"))
            )
            
            if not sidebar.is_displayed():
                print("✗ Sidebar not visible")
                return []
            
            # Find all interactive elements in the sidebar
            interactive_selectors = [
                'input[type="text"]',
                'input[type="number"]',
                'input[type="email"]',
                'input[type="password"]',
                'input[type="search"]',
                'textarea',
                'select',
                'button',
                '[contenteditable="true"]',
                '[role="button"]',
                '[role="textbox"]',
                '[role="combobox"]',
                '.input-field',
                '.form-control',
                '.btn',
                '.button',
                '[onclick]',
                '[data-action]',
                '[data-toggle]'
            ]
            
            elements_info = []
            found_elements = set()  # To avoid duplicates
            
            for selector in interactive_selectors:
                try:
                    elements = sidebar.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.size['width'] > 0 and element.size['height'] > 0:
                            # Get element information
                            element_id = (element.get_attribute('id') or 
                                        element.get_attribute('name') or 
                                        element.get_attribute('data-id') or 
                                        element.get_attribute('class') or 
                                        f"element_{len(elements_info)}")
                            
                            # Skip if we already found this element
                            if element_id in found_elements:
                                continue
                            found_elements.add(element_id)
                            
                            # Get element location and size
                            location = element.location
                            size = element.size
                            
                            # Determine element type
                            element_type = self.get_element_type(element)
                            
                            element_info = {
                                'id': element_id,
                                'name': (element.get_attribute('placeholder') or 
                                        element.get_attribute('title') or 
                                        element.get_attribute('aria-label') or 
                                        element.text.strip() or 
                                        element_type),
                                'type': element_type,
                                'x': location['x'],
                                'y': location['y'],
                                'width': size['width'],
                                'height': size['height'],
                                'right': location['x'] + size['width'],
                                'bottom': location['y'] + size['height']
                            }
                            
                            elements_info.append(element_info)
                            
                except NoSuchElementException:
                    continue
            
            print(f"✓ Found {len(elements_info)} interactive elements in sidebar")
            return elements_info
            
        except Exception as e:
            print(f"✗ Error getting sidebar interactive elements: {e}")
            return []
    
    def get_element_type(self, element):
        """Determine the type of an interactive element"""
        tag_name = element.tag_name.lower()
        
        if tag_name == 'input':
            input_type = element.get_attribute('type') or 'text'
            return f"input_{input_type}"
        elif tag_name == 'textarea':
            return "textarea"
        elif tag_name == 'select':
            return "select"
        elif tag_name == 'button':
            return "button"
        elif element.get_attribute('contenteditable') == 'true':
            return "contenteditable"
        elif element.get_attribute('role'):
            return f"role_{element.get_attribute('role')}"
        else:
            return tag_name
    
    def get_menu_bar_items(self):
        """Get all menu bar items (File, Edit, View, etc.)"""
        try:
            # Find the menu bar container
            menu_bar_selectors = [
                '.menu-bar',
                '.menu',
                '.nav',
                '.navigation',
                '[role="menubar"]',
                '.top-menu'
            ]
            
            menu_bar = None
            for selector in menu_bar_selectors:
                try:
                    menu_bar = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if menu_bar.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            
            if not menu_bar:
                # Fallback: look for menu items directly
                menu_items = self.driver.find_elements(By.CSS_SELECTOR, '[data-page]')
                menu_items = [item for item in menu_items if item.is_displayed() and 'toolbar' not in item.get_attribute('data-page', '')]
            else:
                # Find menu items within the menu bar
                menu_items = menu_bar.find_elements(By.CSS_SELECTOR, '[data-page], .menu-item, .nav-item, a, button')
            
            items_info = []
            found_items = set()
            
            for item in menu_items:
                if item.is_displayed() and item.size['width'] > 0 and item.size['height'] > 0:
                    # Get item information
                    item_id = (item.get_attribute('data-page') or 
                             item.get_attribute('id') or 
                             item.get_attribute('href') or 
                             item.text.strip() or 
                             f"menu_item_{len(items_info)}")
                    
                    # Skip if we already found this item
                    if item_id in found_items:
                        continue
                    found_items.add(item_id)
                    
                    # Get item location and size
                    location = item.location
                    size = item.size
                    
                    item_info = {
                        'id': item_id,
                        'name': (item.text.strip() or 
                               item.get_attribute('title') or 
                               item.get_attribute('aria-label') or 
                               item_id),
                        'type': 'menu_item',
                        'x': location['x'],
                        'y': location['y'],
                        'width': size['width'],
                        'height': size['height'],
                        'right': location['x'] + size['width'],
                        'bottom': location['y'] + size['height']
                    }
                    
                    items_info.append(item_info)
            
            print(f"✓ Found {len(items_info)} menu bar items")
            return items_info
            
        except Exception as e:
            print(f"✗ Error getting menu bar items: {e}")
            return []
    
    def create_sidebar_elements_screenshots(self, full_screenshot_path, elements_info, function_name):
        """Create individual screenshots for sidebar interactive elements"""
        try:
            successful_screenshots = 0
            
            for i, element_info in enumerate(elements_info):
                try:
                    # Create filename for individual element screenshot
                    safe_name = element_info['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
                    element_filename = f"sidebar_{function_name}_{element_info['type']}_{safe_name}_bbox.png"
                    element_path = os.path.join(self.sidebar_elements_dir, element_filename)
                    
                    # Create individual screenshot with single bbox highlighting
                    if self.highlight_single_bbox_on_image(full_screenshot_path, element_info, "sidebar", element_path):
                        successful_screenshots += 1
                        print(f"  ✓ Created sidebar element screenshot: {element_filename}")
                    else:
                        print(f"  ✗ Failed to create screenshot for element {element_info['name']}")
                    
                except Exception as e:
                    print(f"  ✗ Error creating screenshot for element {element_info['name']}: {e}")
                    continue
            
            print(f"✓ Successfully created {successful_screenshots}/{len(elements_info)} sidebar element screenshots")
            return successful_screenshots
            
        except Exception as e:
            print(f"✗ Error creating sidebar element screenshots: {e}")
            return 0
    
    def create_menu_bar_screenshots(self, full_screenshot_path, menu_items_info):
        """Create individual screenshots for menu bar items"""
        try:
            successful_screenshots = 0
            
            for i, item_info in enumerate(menu_items_info):
                try:
                    # Create filename for individual menu item screenshot
                    safe_name = item_info['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
                    item_filename = f"menubar_{item_info['id']}_{safe_name}_bbox.png"
                    item_path = os.path.join(self.menu_bar_dir, item_filename)
                    
                    # Create individual screenshot with single bbox highlighting
                    if self.highlight_single_bbox_on_image(full_screenshot_path, item_info, "menubar", item_path):
                        successful_screenshots += 1
                        print(f"  ✓ Created menu bar screenshot: {item_filename}")
                    else:
                        print(f"  ✗ Failed to create screenshot for menu item {item_info['name']}")
                    
                except Exception as e:
                    print(f"  ✗ Error creating screenshot for menu item {item_info['name']}: {e}")
                    continue
            
            print(f"✓ Successfully created {successful_screenshots}/{len(menu_items_info)} menu bar screenshots")
            return successful_screenshots
            
        except Exception as e:
            print(f"✗ Error creating menu bar screenshots: {e}")
            return 0
    
    def take_bbox_screenshot(self, function_id, function_name, category):
        """Take full screenshot, detect sidebar bbox, highlight it, crop sidebar, and capture sidebar elements"""
        try:
            # Wait for page to stabilize
            time.sleep(3)
            
            # Get sidebar bounding box
            bbox_info = self.get_sidebar_bbox()
            if not bbox_info:
                print(f"✗ Could not detect sidebar bbox for {function_name}")
                return False
            
            # Create filenames
            base_filename = f"{function_id}_{category}"
            full_screenshot_path = os.path.join(self.bbox_dir, f"{base_filename}_full.png")
            bbox_highlighted_path = os.path.join(self.bbox_dir, f"{base_filename}_bbox.png")
            sidebar_cropped_path = os.path.join(self.sidebar_dir, f"{base_filename}_sidebar.png")
            
            # Take full page screenshot
            self.driver.save_screenshot(full_screenshot_path)
            print(f"✓ Full screenshot saved: {full_screenshot_path}")
            
            # Highlight bbox on the screenshot
            if self.highlight_bbox_on_image(full_screenshot_path, bbox_info, bbox_highlighted_path):
                print(f"✓ Bbox highlighted screenshot saved: {bbox_highlighted_path}")
            else:
                print(f"✗ Failed to highlight bbox for {function_name}")
                return False
            
            # Crop sidebar from full screenshot
            if self.crop_sidebar_from_full_screenshot(full_screenshot_path, bbox_info, sidebar_cropped_path):
                print(f"✓ Cropped sidebar saved: {sidebar_cropped_path}")
            else:
                print(f"✗ Failed to crop sidebar for {function_name}")
                return False
            
            # Capture sidebar interactive elements
            elements_info = self.get_sidebar_interactive_elements()
            if elements_info:
                elements_count = self.create_sidebar_elements_screenshots(full_screenshot_path, elements_info, function_name)
                print(f"✓ Captured {elements_count} sidebar interactive elements for {function_name}")
            else:
                print(f"ℹ No interactive elements found in sidebar for {function_name}")
            
            return True
                
        except Exception as e:
            print(f"✗ Error taking bbox screenshot for {function_name}: {e}")
            return False
    
    def capture_all_bbox_screenshots(self):
        """Capture screenshots with bbox detection for all functions and toolbar buttons"""
        if not self.function_ids:
            print("✗ No function IDs loaded")
            return
        
        successful_captures = 0
        total_functions = len(self.function_ids)
        
        print(f"\n🚀 Starting to capture {total_functions} bbox screenshots...")
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
        
        # First, capture menu bar items
        print(f"\n📋 PHASE 1: Capturing menu bar items...")
        print("=" * 60)
        
        menu_items_info = self.get_menu_bar_items()
        successful_menu_captures = 0
        
        if menu_items_info:
            # Take full page screenshot for menu bar
            menu_full_screenshot_path = os.path.join(self.menu_bar_dir, "menubar_full.png")
            self.driver.save_screenshot(menu_full_screenshot_path)
            print(f"✓ Menu bar full screenshot saved: {menu_full_screenshot_path}")
            
            # Create individual menu bar screenshots
            successful_menu_captures = self.create_menu_bar_screenshots(menu_full_screenshot_path, menu_items_info)
            print(f"✓ Menu bar capture completed: {successful_menu_captures}/{len(menu_items_info)} items")
        else:
            print("ℹ No menu bar items found")
        
        # Second, capture all toolbar button bboxes
        print(f"\n🔧 PHASE 2: Capturing toolbar button bboxes...")
        print("=" * 60)
        
        toolbar_sections = ['file', 'edit', 'view', 'insert', 'format', 'tools', 'help']
        successful_toolbar_captures = 0
        
        for toolbar_section in toolbar_sections:
            if self.capture_toolbar_button_bboxes(toolbar_section):
                successful_toolbar_captures += 1
            time.sleep(1)  # Small delay between toolbars
        
        print(f"\n✓ Toolbar button capture completed: {successful_toolbar_captures}/{len(toolbar_sections)} toolbars")
        
        # Third, process each function for sidebar screenshots
        print(f"\n📋 PHASE 3: Capturing sidebar screenshots...")
        print("=" * 60)
        
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
        self.create_summary_report(successful_captures, total_functions, successful_toolbar_captures, len(toolbar_sections), successful_menu_captures, len(menu_items_info) if menu_items_info else 0)
        
        print(f"\n🎉 Complete bbox screenshot capture finished!")
        print(f"✓ Menu bar screenshots: {successful_menu_captures}/{len(menu_items_info) if menu_items_info else 0} items")
        print(f"✓ Toolbar button screenshots: {successful_toolbar_captures}/{len(toolbar_sections)} toolbars")
        print(f"✓ Sidebar screenshots: {successful_captures}/{total_functions} functions")
        print(f"📁 Full screenshots with bbox saved in: {self.bbox_dir}")
        print(f"📁 Cropped sidebars saved in: {self.sidebar_dir}")
        print(f"📁 Individual button bbox screenshots saved in: {self.button_bbox_dir}")
        print(f"📁 Sidebar elements bbox screenshots saved in: {self.sidebar_elements_dir}")
        print(f"📁 Menu bar bbox screenshots saved in: {self.menu_bar_dir}")
        print(f"📂 Full path: {os.path.abspath(self.output_dir)}")
    
    def create_summary_report(self, successful_captures, total_functions, successful_toolbar_captures, total_toolbars, successful_menu_captures, total_menu_items):
        """Create a summary report of the screenshot session"""
        try:
            report_path = os.path.join(self.output_dir, "bbox_screenshot_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("MiniWord Complete Bbox Screenshot Report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("MENU BAR SCREENSHOTS:\n")
                f.write("-" * 25 + "\n")
                f.write(f"Total Menu Items: {total_menu_items}\n")
                f.write(f"Successful Captures: {successful_menu_captures}\n")
                f.write(f"Failed Captures: {total_menu_items - successful_menu_captures}\n")
                if total_menu_items > 0:
                    f.write(f"Success Rate: {(successful_menu_captures/total_menu_items)*100:.1f}%\n\n")
                else:
                    f.write(f"Success Rate: N/A (no menu items found)\n\n")
                
                f.write("TOOLBAR BUTTON SCREENSHOTS:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total Toolbars: {total_toolbars}\n")
                f.write(f"Successful Captures: {successful_toolbar_captures}\n")
                f.write(f"Failed Captures: {total_toolbars - successful_toolbar_captures}\n")
                f.write(f"Success Rate: {(successful_toolbar_captures/total_toolbars)*100:.1f}%\n\n")
                
                f.write("SIDEBAR SCREENSHOTS:\n")
                f.write("-" * 25 + "\n")
                f.write(f"Total Functions: {total_functions}\n")
                f.write(f"Successful Captures: {successful_captures}\n")
                f.write(f"Failed Captures: {total_functions - successful_captures}\n")
                f.write(f"Success Rate: {(successful_captures/total_functions)*100:.1f}%\n\n")
                
                f.write("OUTPUT STRUCTURE:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Full screenshots with bbox: {self.bbox_dir}\n")
                f.write(f"Cropped sidebars: {self.sidebar_dir}\n")
                f.write(f"Individual button bbox screenshots: {self.button_bbox_dir}\n")
                f.write(f"Sidebar elements bbox screenshots: {self.sidebar_elements_dir}\n")
                f.write(f"Menu bar bbox screenshots: {self.menu_bar_dir}\n\n")
                
                f.write("FUNCTION LIST:\n")
                f.write("-" * 20 + "\n")
                for func in self.function_ids:
                    f.write(f"- {func['name']} ({func['id']}) - {func['category']}\n")
                
                f.write("\nTOOLBAR SECTIONS:\n")
                f.write("-" * 20 + "\n")
                toolbar_sections = ['file', 'edit', 'view', 'insert', 'format', 'tools', 'help']
                for section in toolbar_sections:
                    f.write(f"- {section.upper()} toolbar\n")
            
            print(f"✓ Summary report created: {report_path}")
        except Exception as e:
            print(f"✗ Error creating summary report: {e}")
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser driver closed")

def main():
    """Main function to run the bbox screenshot tool"""
    print("MiniWord Sidebar Bbox Screenshot Tool")
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
    
    # Initialize and run bbox screenshot tool
    tool = MiniWordSidebarBboxScreenshotTool()
    
    try:
        tool.capture_all_bbox_screenshots()
    except KeyboardInterrupt:
        print("\n⚠️ Screenshot capture interrupted by user")
    except Exception as e:
        print(f"✗ Error during screenshot capture: {e}")
    finally:
        tool.close()

if __name__ == "__main__":
    main()
