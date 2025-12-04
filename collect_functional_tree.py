#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniWord Functional Tree Collector
Merges trajectory building and bbox screenshot functionality into a unified tool.

This script:
1. Discovers and navigates through all functional buttons
2. Captures three images for each node (tab/function/submenu/element):
   - begin.png (state before click)
   - action.png (begin with bbox of the clickable)
   - end.png (state after click; for leaf elements equals begin)
3. Organizes everything into a structured function_tree directory
4. Generates a comprehensive trajectory.json with begin, action_image, and end fields

Outputs:
- function_tree/
  - initial_overview.png
  - <category>/{begin.png, action.png, end.png}
  - <category>/<function_id>/{begin.png, action.png, end.png}
  - <category>/<function_id>/<submenu_or_element>/{begin.png, action.png, end.png}
- trajectory.json (enhanced tree structure with begin/action_image/end paths)
"""

import os
import time
import json
import shutil
from typing import Dict, List, Optional
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PIL import Image, ImageDraw, ImageFont


class MiniWordFunctionalTreeCollector:
    def __init__(self, base_url: str = "http://localhost:8000", output_dir: str = "function_tree_10") -> None:
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
            time.sleep(0.3)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.driver.save_screenshot(path)
            return True
        except Exception:
            return False

    def wait_for_modal(self, modal_id: str = "chart-insert-modal", timeout: int = 5):
        try:
            assert self.driver is not None
            el = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.ID, modal_id))
            )
            return el
        except Exception:
            return None

    def take_modal_screenshot(self, path: str, modal_id: str = "chart-insert-modal", timeout: int = 5) -> bool:
        try:
            assert self.driver is not None
            modal = self.wait_for_modal(modal_id, timeout)
            if modal is None:
                return False
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

    def get_sidebar_interactive_elements(self) -> List[Dict[str, any]]:
        """Get all interactive elements within the sidebar (input fields, buttons, etc.)"""
        try:
            # Wait for sidebar to be visible
            sidebar = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "sidebar"))
            )
            
            if not sidebar.is_displayed():
                print("✗ Sidebar not visible")
                return []
            
            # Comprehensive list of interactive element selectors
            interactive_selectors = [
                # Basic input types
                'input[type="text"]',
                'input[type="number"]',
                'input[type="email"]',
                'input[type="password"]',
                'input[type="search"]',
                'input[type="tel"]',
                'input[type="url"]',
                'input[type="date"]',
                'input[type="time"]',
                'input[type="datetime-local"]',
                'input[type="color"]',
                'input[type="range"]',
                'input[type="checkbox"]',
                'input[type="radio"]',
                'input[type="file"]',
                'input[type="hidden"]',
                
                # Form elements
                'textarea',
                'select',
                'button',
                'input',  # Catch all input elements
                
                # Interactive elements
                '[contenteditable="true"]',
                '[contenteditable]',
                '[role="button"]',
                '[role="textbox"]',
                '[role="combobox"]',
                '[role="checkbox"]',
                '[role="radio"]',
                '[role="slider"]',
                '[role="spinbutton"]',
                '[role="switch"]',
                '[role="tab"]',
                '[role="menuitem"]',
                '[role="option"]',
                
                # Common CSS classes
                '.input-field',
                '.form-control',
                '.form-input',
                '.form-field',
                '.btn',
                '.button',
                '.clickable',
                '.interactive',
                '.selectable',
                '.editable',
                
                # Elements with event handlers
                '[onclick]',
                '[onchange]',
                '[oninput]',
                '[onfocus]',
                '[onblur]',
                '[onkeydown]',
                '[onkeyup]',
                '[onmousedown]',
                '[onmouseup]',
                '[onmouseover]',
                '[onmouseout]',
                
                # Data attributes
                '[data-action]',
                '[data-toggle]',
                '[data-target]',
                '[data-id]',
                '[data-value]',
                '[data-click]',
                '[data-change]',
                
                # Color picker specific elements
                '.color-picker',
                '.color-swatch',
                '.color-button',
                '.color-input',
                '[data-color]',
                '[style*="background-color"]',
                '[style*="color"]',
                
                # Margin/Spacing specific elements
                '.margin-input',
                '.spacing-input',
                '.size-input',
                '.dimension-input',
                '[data-margin]',
                '[data-spacing]',
                '[data-size]',
                '[data-width]',
                '[data-height]',
                
                # Generic interactive elements
                'a[href]',
                'label[for]',
                'summary',  # For details/summary elements
                'details',
                
                # Custom elements that might be interactive
                'div[onclick]',
                'span[onclick]',
                'div[role]',
                'span[role]',
                'div[tabindex]',
                'span[tabindex]',
                
                # Elements with cursor pointer (likely clickable)
                '[style*="cursor: pointer"]',
                '[style*="cursor:pointer"]',
                
                # Elements that can receive focus
                '[tabindex]',
                '[tabindex="0"]',
                '[tabindex="-1"]'
            ]
            
            elements_info = []
            found_locations = set()  # Track by location to avoid true duplicates
            
            for selector in interactive_selectors:
                try:
                    elements = sidebar.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.size['width'] > 0 and element.size['height'] > 0:
                            # Get element location and size
                            location = element.location
                            size = element.size
                            
                            # Create a unique identifier based on location and size
                            location_key = f"{location['x']},{location['y']},{size['width']},{size['height']}"
                            
                            # Skip if we already found an element at this exact location
                            if location_key in found_locations:
                                continue
                            found_locations.add(location_key)
                            
                            # Generate a unique element ID
                            element_id = self.generate_element_id(element, len(elements_info))
                            
                            # Determine element type
                            element_type = self.get_element_type(element)
                            
                            # Get element name/description
                            element_name = self.get_element_name(element, element_type)
                            
                            element_info = {
                                'id': element_id,
                                'name': element_name,
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
                except Exception as e:
                    print(f"Warning: Error processing selector '{selector}': {e}")
                    continue
            
            print(f"✓ Found {len(elements_info)} interactive elements in sidebar")
            return elements_info
            
        except Exception as e:
            print(f"✗ Error getting sidebar interactive elements: {e}")
            return []

    def get_specific_interactive_elements(self, function_id: str) -> List[Dict[str, any]]:
        """Get specific interactive elements for certain functions like color pickers and margin inputs"""
        try:
            assert self.driver is not None
            sidebar = self.driver.find_element(By.ID, "sidebar")
            if not sidebar.is_displayed():
                return []
            
            additional_elements = []
            
            # For color picker functions, look for color swatches and color buttons
            if 'color' in function_id.lower():
                color_selectors = [
                    # Color swatches/buttons
                    '.color-swatch',
                    '.color-button', 
                    '.color-item',
                    '.color-option',
                    '[data-color]',
                    '[style*="background-color"]',
                    '[style*="background:"]',
                    # Color picker inputs
                    'input[type="color"]',
                    '.color-picker input',
                    '.color-input',
                    # Color palette elements
                    '.color-palette .color',
                    '.color-grid .color',
                    '.color-list .color'
                ]
                
                for selector in color_selectors:
                    try:
                        elements = sidebar.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.size['width'] > 0 and element.size['height'] > 0:
                                location = element.location
                                size = element.size
                                
                                # Get color information
                                try:
                                    bg_color = element.value_of_css_property('background-color')
                                    if bg_color and bg_color not in ['rgba(0, 0, 0, 0)', 'transparent', 'initial', 'inherit']:
                                        color_name = f"Color_{bg_color.replace('#', '').replace('rgb', '').replace('rgba', '').replace('(', '').replace(')', '')}"
                                    else:
                                        color_name = f"Color_{len(additional_elements)}"
                                except:
                                    color_name = f"Color_{len(additional_elements)}"
                                
                                element_info = {
                                    'id': f"color_{color_name}_{len(additional_elements)}",
                                    'name': f"Color: {color_name}",
                                    'type': 'color_swatch',
                                    'x': location['x'],
                                    'y': location['y'],
                                    'width': size['width'],
                                    'height': size['height'],
                                    'right': location['x'] + size['width'],
                                    'bottom': location['y'] + size['height']
                                }
                                additional_elements.append(element_info)
                    except Exception:
                        continue
            
            # For page setup functions, look for margin input fields
            elif 'page_setup' in function_id.lower() or 'margin' in function_id.lower():
                margin_selectors = [
                    # Margin input fields
                    'input[name*="margin"]',
                    'input[name*="top"]',
                    'input[name*="bottom"]', 
                    'input[name*="left"]',
                    'input[name*="right"]',
                    'input[placeholder*="margin"]',
                    'input[placeholder*="top"]',
                    'input[placeholder*="bottom"]',
                    'input[placeholder*="left"]',
                    'input[placeholder*="right"]',
                    '.margin-input',
                    '.margin-field',
                    '.spacing-input',
                    '.dimension-input',
                    '[data-margin]',
                    '[data-spacing]'
                ]
                
                for selector in margin_selectors:
                    try:
                        elements = sidebar.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.size['width'] > 0 and element.size['height'] > 0:
                                location = element.location
                                size = element.size
                                
                                # Get field name
                                field_name = (element.get_attribute('name') or 
                                            element.get_attribute('placeholder') or 
                                            element.get_attribute('data-label') or 
                                            f"margin_field_{len(additional_elements)}")
                                
                                element_info = {
                                    'id': f"margin_{field_name}_{len(additional_elements)}",
                                    'name': f"Margin: {field_name}",
                                    'type': 'margin_input',
                                    'x': location['x'],
                                    'y': location['y'],
                                    'width': size['width'],
                                    'height': size['height'],
                                    'right': location['x'] + size['width'],
                                    'bottom': location['y'] + size['height']
                                }
                                additional_elements.append(element_info)
                    except Exception:
                        continue
            
            return additional_elements
            
        except Exception as e:
            print(f"Warning: Error getting specific interactive elements: {e}")
            return []

    def generate_element_id(self, element, index: int) -> str:
        """Generate a unique element ID"""
        # Try to get a meaningful ID first
        element_id = (element.get_attribute('id') or 
                     element.get_attribute('name') or 
                     element.get_attribute('data-id') or 
                     element.get_attribute('data-testid'))
        
        if element_id:
            return element_id
        
        # If no meaningful ID, create one based on element properties
        tag_name = element.tag_name.lower()
        element_type = element.get_attribute('type') or ''
        element_class = element.get_attribute('class') or ''
        
        # Create a descriptive ID
        if element_type:
            return f"{tag_name}_{element_type}_{index}"
        elif element_class:
            # Use first class name
            first_class = element_class.split()[0] if element_class else ''
            return f"{tag_name}_{first_class}_{index}" if first_class else f"{tag_name}_{index}"
        else:
            return f"{tag_name}_{index}"

    def get_element_name(self, element, element_type: str) -> str:
        """Get a descriptive name for the element"""
        # Try various attributes for a meaningful name
        name_attributes = [
            'placeholder',
            'title', 
            'aria-label',
            'aria-labelledby',
            'data-label',
            'data-name',
            'alt',
            'value'
        ]
        
        for attr in name_attributes:
            value = element.get_attribute(attr)
            if value and value.strip():
                return value.strip()
        
        # Try to get text content
        text_content = element.text.strip()
        if text_content and len(text_content) < 50:  # Avoid very long text
            return text_content
        
        # Try to get the element's value
        try:
            value = element.get_attribute('value')
            if value and value.strip():
                return value.strip()
        except:
            pass
        
        # Try to get background color for color elements
        try:
            bg_color = element.value_of_css_property('background-color')
            if bg_color and bg_color != 'rgba(0, 0, 0, 0)' and bg_color != 'transparent':
                return f"Color: {bg_color}"
        except:
            pass
        
        # Fallback to element type
        return element_type

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
        # Ensure any stale modals are closed before clicking
        self.close_any_open_modals()
        for sel in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                ActionChains(self.driver).move_to_element(el).click().perform()
                time.sleep(0.6)
                return True
            except NoSuchElementException:
                continue
            except Exception:
                continue
        return False

    def get_button_bbox(self, function_id: str) -> Optional[Dict[str, int]]:
        """Get bounding box coordinates for a specific button"""
        assert self.driver is not None
        selectors = [
            f"[data-page='{function_id}']",
            f"[data-testid='btn-{function_id.replace('_','-')}']",
            f"button[title*='{function_id}']",
            f"button[aria-label*='{function_id}']",
        ]
        
        for sel in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    location = el.location
                    size = el.size
                    return {
                        'x': location['x'],
                        'y': location['y'],
                        'width': size['width'],
                        'height': size['height'],
                        'right': location['x'] + size['width'],
                        'bottom': location['y'] + size['height']
                    }
            except NoSuchElementException:
                continue
        return None

    def get_button_description(self, function_id: str, element_name: str = "") -> str:
        """Get a human-readable description for a button/function"""
        # Create descriptions based on function ID and element name
        descriptions = {
            # File operations
            'file_new': 'Create a new document',
            'file_open': 'Open an existing document',
            'file_save': 'Save the current document',
            'file_print': 'Print the document',
            'web_refresh': 'Refresh the web page',
            'web_close': 'Close the current page',
            'new_tab': 'Open a new browser tab',
            'toggle_pagination': 'Toggle pagination mode',
            
            # Edit operations
            'edit_undo': 'Undo the last action',
            'edit_redo': 'Redo the last undone action',
            'edit_cut': 'Cut selected text',
            'edit_copy': 'Copy selected text',
            'edit_paste': 'Paste text from clipboard',
            'find': 'Find text in the document',
            'replace': 'Find and replace text',
            'mw2_clear_all': 'Clear all formatting',
            'mw2_format_painter': 'Copy and apply formatting',
            
            # View operations
            'view_zoom_in': 'Zoom in to make text larger',
            'view_zoom_out': 'Zoom out to make text smaller',
            'view_preview': 'Preview the document for printing',
            'layout_page_setup': 'Configure page layout settings',
            'mw2_sidebar_toggle': 'Show or hide the sidebar',
            'mw2_ruler_toggle': 'Show or hide the ruler',
            'mw2_show_invisibles': 'Show or hide invisible characters',
            'mw2_focus_mode': 'Enter focus mode to minimize distractions',
            'mw2_night_mode': 'Toggle dark mode for better night viewing',
            
            # Insert operations
            'insert_image': 'Insert an image into the document',
            'insert_table': 'Insert a table into the document',
            'insert_chart': 'Insert a chart or graph',
            'insert_link': 'Insert a hyperlink',
            'insert_equation': 'Insert a mathematical equation',
            'insert_symbol': 'Insert special characters or symbols',
            'mw2_section_break': 'Insert a section break',
            'mw2_template_library': 'Access document templates',
            
            # Format operations
            'bold': 'Make text bold',
            'italic': 'Make text italic',
            'underline': 'Underline text',
            'strikethrough': 'Strike through text',
            'align_left': 'Align text to the left',
            'align_center': 'Center align text',
            'align_right': 'Align text to the right',
            'align_justify': 'Justify text alignment',
            'text_color': 'Change text color',
            'highlight': 'Highlight text with background color',
            'format_painter': 'Copy formatting from one text to another',
            'clear_format': 'Remove all formatting from text',
            'mw2_superscript': 'Make text superscript',
            'mw2_subscript': 'Make text subscript',
            'mw2_line_spacing': 'Adjust line spacing',
            'mw2_page_setup': 'Configure page settings',
            'mw2_header_footer': 'Edit document headers and footers',
            
            # Tools operations
            'review_spelling': 'Check spelling and grammar',
            'review_comment': 'Add comments to the document',
            'bulleted_list': 'Create a bulleted list',
            'numbered_list': 'Create a numbered list',
            'indent_increase': 'Increase text indentation',
            'indent_decrease': 'Decrease text indentation',
            'mw2_char_count': 'Show character count statistics',
            
            # Help operations
            'app_settings': 'Access application settings',
            'layout_page_break': 'Insert a page break',
            'mw2_share': 'Share the document with others'
        }
        
        # Return specific description if available, otherwise create a generic one
        if function_id in descriptions:
            return descriptions[function_id]
        elif element_name:
            # For sidebar elements, create description based on element name
            if '×' in element_name or 'x' in element_name:
                return 'Close the current dialog or sidebar'
            elif 'back' in element_name.lower():
                return 'Return to the previous menu or section'
            elif 'apply' in element_name.lower():
                return 'Apply the current settings or formatting'
            elif 'cancel' in element_name.lower():
                return 'Cancel the current operation'
            elif 'save' in element_name.lower():
                return 'Save the current changes'
            elif 'create' in element_name.lower():
                return 'Create a new item or document'
            elif 'insert' in element_name.lower():
                return 'Insert the selected item into the document'
            elif 'toggle' in element_name.lower():
                return 'Toggle the current setting on or off'
            elif 'reset' in element_name.lower():
                return 'Reset to default settings'
            elif 'enter' in element_name.lower() or 'input' in element_name.lower():
                return 'Input field for entering text or data'
            elif 'select' in element_name.lower():
                return 'Select from available options'
            else:
                return f'Execute action: {element_name}'
        else:
            return f'Function: {function_id}'

    def get_menu_bar_bbox(self, tab_id: str) -> Optional[Dict[str, int]]:
        """Get bounding box coordinates for a menu bar item"""
        assert self.driver is not None
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, f".menu-bar .menu-item[data-page='{tab_id}']")
            if el.is_displayed():
                location = el.location
                size = el.size
                return {
                    'x': location['x'],
                    'y': location['y'],
                    'width': size['width'],
                    'height': size['height'],
                    'right': location['x'] + size['width'],
                    'bottom': location['y'] + size['height']
                }
        except Exception:
            pass
        return None

    def click_submenu_item(self, submenu_id: str) -> bool:
        """Click on a submenu item"""
        assert self.driver is not None
        
        # Try multiple selectors to find the submenu item
        selectors = [
            f"#{submenu_id}",
            f"[data-page='{submenu_id}']",
            f"[data-testid='{submenu_id}']",
            f".submenu-item[data-page='{submenu_id}']",
            f".submenu-item#{submenu_id}",
            f"li#{submenu_id}",
            f"a#{submenu_id}",
            f"div#{submenu_id}",
            f"span#{submenu_id}"
        ]
        
        for sel in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    ActionChains(self.driver).move_to_element(el).click().perform()
                    time.sleep(0.6)
                    self.close_any_open_modals()
                    return True
            except NoSuchElementException:
                continue
            except Exception:
                continue
        
        # If CSS selectors fail, try XPath for text-based selection
        try:
            # Look for elements containing the submenu text
            if submenu_id == "copy_plain":
                xpath_selectors = [
                    "//div[contains(text(), 'Direct Copy')]",
                    "//div[contains(text(), 'Direct')]",
                    "//div[@data-page='copy_plain']"
                ]
            elif submenu_id == "copy_formatted":
                xpath_selectors = [
                    "//div[contains(text(), 'Formatted Copy')]",
                    "//div[contains(text(), 'Formatted')]",
                    "//div[@data-page='copy_formatted']"
                ]
            else:
                xpath_selectors = [f"//div[@data-page='{submenu_id}']"]
            
            for xpath in xpath_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed() and el.size['width'] > 0 and el.size['height'] > 0:
                            ActionChains(self.driver).move_to_element(el).click().perform()
                            time.sleep(0.6)
                            self.close_any_open_modals()
                            return True
                except Exception:
                    continue
        except Exception:
            pass
        
        return False

    def get_submenu_bbox(self, submenu_id: str) -> Optional[Dict[str, int]]:
        """Get bounding box coordinates for a submenu item"""
        assert self.driver is not None
        
        print(f"    🔍 Looking for submenu bbox: {submenu_id}")
        
        # Try multiple selectors to find the submenu item
        selectors = [
            f"#{submenu_id}",
            f"[data-page='{submenu_id}']",
            f"[data-testid='{submenu_id}']",
            f".submenu-item[data-page='{submenu_id}']",
            f".submenu-item#{submenu_id}",
            f"li#{submenu_id}",
            f"a#{submenu_id}",
            f"div#{submenu_id}",
            f"span#{submenu_id}"
        ]
        
        for sel in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    location = el.location
                    size = el.size
                    print(f"    ✓ Found submenu element with selector: {sel}")
                    return {
                        'x': location['x'],
                        'y': location['y'],
                        'width': size['width'],
                        'height': size['height'],
                        'right': location['x'] + size['width'],
                        'bottom': location['y'] + size['height']
                    }
            except NoSuchElementException:
                continue
            except Exception as e:
                print(f"    ⚠️ Error with selector {sel}: {e}")
                continue
        
        # If CSS selectors fail, try XPath for text-based selection
        try:
            # Look for elements containing the submenu text
            if submenu_id == "copy_plain":
                xpath_selectors = [
                    "//div[contains(text(), 'Direct Copy')]",
                    "//div[contains(text(), 'Direct')]",
                    "//div[@data-page='copy_plain']",
                    "//div[contains(@class, 'submenu-item') and contains(text(), 'Direct')]"
                ]
            elif submenu_id == "copy_formatted":
                xpath_selectors = [
                    "//div[contains(text(), 'Formatted Copy')]",
                    "//div[contains(text(), 'Formatted')]",
                    "//div[@data-page='copy_formatted']",
                    "//div[contains(@class, 'submenu-item') and contains(text(), 'Formatted')]"
                ]
            else:
                xpath_selectors = [f"//div[@data-page='{submenu_id}']"]
            
            for xpath in xpath_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    print(f"    🔍 Found {len(elements)} elements with XPath: {xpath}")
                    for el in elements:
                        if el.is_displayed() and el.size['width'] > 0 and el.size['height'] > 0:
                            location = el.location
                            size = el.size
                            print(f"    ✓ Found submenu element with XPath: {xpath}")
                            return {
                                'x': location['x'],
                                'y': location['y'],
                                'width': size['width'],
                                'height': size['height'],
                                'right': location['x'] + size['width'],
                                'bottom': location['y'] + size['height']
                            }
                except Exception as e:
                    print(f"    ⚠️ Error with XPath {xpath}: {e}")
                    continue
        except Exception as e:
            print(f"    ⚠️ Error in XPath search: {e}")
        
        print(f"    ✗ Could not find submenu element: {submenu_id}")
        return None

    def get_modal_interactive_elements(self, modal_id: str = "chart-insert-modal") -> List[Dict[str, any]]:
        """Get all interactive elements within a modal (buttons, inputs, selects, etc.)"""
        try:
            assert self.driver is not None
            modal = self.wait_for_modal(modal_id, timeout=6)
            if modal is None or not modal.is_displayed():
                return []

            interactive_selectors = [
                'button',
                'input',
                'textarea',
                'select',
                '[role="button"]',
                '[role="textbox"]',
                '[role="combobox"]',
                '[role="radio"]',
                '[role="checkbox"]',
                'label[for]',
                '[onclick]',
                '[onchange]',
                '[oninput]'
            ]

            elements_info: List[Dict[str, any]] = []
            found_locations = set()

            for selector in interactive_selectors:
                try:
                    elements = modal.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.size['width'] > 0 and element.size['height'] > 0:
                            location = element.location
                            size = element.size
                            location_key = f"{location['x']},{location['y']},{size['width']},{size['height']}"
                            if location_key in found_locations:
                                continue
                            found_locations.add(location_key)

                            element_id = self.generate_element_id(element, len(elements_info))
                            element_type = self.get_element_type(element)
                            element_name = self.get_element_name(element, element_type)

                            elements_info.append({
                                'id': element_id,
                                'name': element_name,
                                'type': element_type,
                                'x': location['x'],
                                'y': location['y'],
                                'width': size['width'],
                                'height': size['height'],
                                'right': location['x'] + size['width'],
                                'bottom': location['y'] + size['height']
                            })
                except Exception:
                    continue

            print(f"✓ Found {len(elements_info)} interactive elements in modal '{modal_id}'")
            return elements_info
        except Exception as e:
            print(f"✗ Error getting modal interactive elements: {e}")
            return []

    def _element_to_bbox(self, el) -> Optional[Dict[str, int]]:
        try:
            if not el.is_displayed():
                return None
            location = el.location
            size = el.size
            if size['width'] <= 0 or size['height'] <= 0:
                return None
            return {
                'x': location['x'],
                'y': location['y'],
                'width': size['width'],
                'height': size['height'],
                'right': location['x'] + size['width'],
                'bottom': location['y'] + size['height']
            }
        except Exception:
            return None

    def get_modal_area_elements(self, modal_id: str = "chart-insert-modal") -> List[Dict[str, any]]:
        """Capture labeled areas/containers within a modal (header/body/footer, input groups, sections)."""
        try:
            assert self.driver is not None
            modal = self.wait_for_modal(modal_id, timeout=6)
            if modal is None or not modal.is_displayed():
                return []

            area_selectors = [
                '.modal-content',
                '.modal-header',
                '.modal-body',
                '.modal-footer',
                '.input-group',
                '#detected-tables-section',
                '#detected-tables-list'
            ]

            areas: List[Dict[str, any]] = []
            seen = set()

            for selector in area_selectors:
                try:
                    elements = modal.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        bbox = self._element_to_bbox(el)
                        if not bbox:
                            continue
                        key = f"{bbox['x']},{bbox['y']},{bbox['width']},{bbox['height']}"
                        if key in seen:
                            continue
                        seen.add(key)

                        # Name: prefer label inside input-group
                        name = self.get_element_name(el, 'container')
                        # Improve naming for specific containers
                        try:
                            if 'input-group' in (el.get_attribute('class') or ''):
                                labels = el.find_elements(By.TAG_NAME, 'label')
                                if labels:
                                    label_text = labels[0].text.strip()
                                    if label_text:
                                        name = label_text
                        except Exception:
                            pass

                        # ID generation for areas
                        area_id = self.generate_element_id(el, len(areas))

                        areas.append({
                            'id': area_id,
                            'name': name or 'area',
                            'type': 'area',
                            **bbox
                        })
                except Exception:
                    continue

            print(f"✓ Found {len(areas)} area elements in modal '{modal_id}'")
            return areas
        except Exception as e:
            print(f"✗ Error getting modal area elements: {e}")
            return []

    def get_specific_modal_elements(self, modal_id: str = "chart-insert-modal") -> List[Dict[str, any]]:
        """Ensure key Insert Chart modal controls/areas are captured with meaningful names."""
        try:
            assert self.driver is not None
            modal = self.wait_for_modal(modal_id, timeout=6)
            if modal is None or not modal.is_displayed():
                return []

            targets = [
                (By.CSS_SELECTOR, '#chart-type', 'Chart Type'),
                (By.CSS_SELECTOR, '#chart-title', 'Chart Title'),
                (By.CSS_SELECTOR, 'input[name="data-source"][value="auto"]', 'Data Source: Auto'),
                (By.CSS_SELECTOR, 'input[name="data-source"][value="manual"]', 'Data Source: Manual'),
                (By.CSS_SELECTOR, '#detected-tables-section', 'Detected Tables'),
                (By.CSS_SELECTOR, '#detected-tables-list', 'Detected Tables List'),
                (By.CSS_SELECTOR, '.modal-close', 'Close Modal'),
                (By.CSS_SELECTOR, '.modal-footer .btn-secondary', 'Cancel'),
                (By.CSS_SELECTOR, '#insert-chart-btn', 'Insert Chart')
            ]

            results: List[Dict[str, any]] = []
            seen = set()

            for by, sel, friendly in targets:
                try:
                    els = modal.find_elements(by, sel)
                    for el in els:
                        bbox = self._element_to_bbox(el)
                        if not bbox:
                            continue
                        key = f"{bbox['x']},{bbox['y']},{bbox['width']},{bbox['height']}"
                        if key in seen:
                            continue
                        seen.add(key)
                        el_id = self.generate_element_id(el, len(results))
                        el_type = self.get_element_type(el)
                        results.append({
                            'id': el_id,
                            'name': friendly,
                            'type': el_type,
                            **bbox
                        })
                except Exception:
                    continue

            print(f"✓ Found {len(results)} specific modal elements in '{modal_id}'")
            return results
        except Exception as e:
            print(f"✗ Error getting specific modal elements: {e}")
            return []

    def capture_modal_elements(self, function_id: str, modal_id: str, overview_path: str, fn_dir: str, node: Dict) -> None:
        """Capture modal elements for a specific function; elements become leaf nodes under the function."""
        try:
            modal_elements = self.get_modal_interactive_elements(modal_id)
            area_elements = self.get_modal_area_elements(modal_id)
            specific_elements = self.get_specific_modal_elements(modal_id) if function_id == 'insert_chart' else []

            # Merge and deduplicate by bbox
            all_elements: List[Dict[str, any]] = []
            seen = set()
            for collection in [modal_elements, area_elements, specific_elements]:
                for element in collection:
                    key = f"{element['x']},{element['y']},{element['width']},{element['height']}"
                    if key in seen:
                        continue
                    seen.add(key)
                    all_elements.append(element)

            if not all_elements:
                return
            print(f"  📋 Found {len(all_elements)} modal elements for {function_id}")

            for element in all_elements:
                element_id = element['id']
                element_name = element['name']

                safe_name = element_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('×', 'x').replace('\n', '_').replace('________________________________', '_')
                if len(safe_name) > 50:
                    safe_name = safe_name[:50]

                element_dir = os.path.join(fn_dir, safe_name)
                os.makedirs(element_dir, exist_ok=True)

                element_begin_path = os.path.join(element_dir, "begin.png")
                element_action_path = os.path.join(element_dir, "action.png")
                element_end_path = os.path.join(element_dir, "end.png")
                try:
                    shutil.copyfile(overview_path, element_begin_path)
                    shutil.copyfile(overview_path, element_end_path)
                except Exception:
                    pass

                if self.create_bbox_image(element_begin_path, element, element_action_path, element_name):
                    if element_id not in node["action"]:
                        node["action"][element_id] = {
                            "begin": element_begin_path,
                            "end": element_end_path,
                            "action_image": element_action_path,
                            "action": {},
                            "coordinates_bbox": {
                                'x': element['x'],
                                'y': element['y'],
                                'width': element['width'],
                                'height': element['height'],
                                'right': element['right'],
                                'bottom': element['bottom']
                            },
                            "description": self.get_button_description(element_id, element_name)
                        }
                    print(f"  ✓ Created modal element folder: {safe_name}")
        except Exception as e:
            print(f"  ✗ Error capturing modal elements: {e}")

    def capture_sidebar_elements_for_submenu(self, function_id: str, submenu_id: str, overview_path: str, node: Dict) -> None:
        """Capture sidebar elements for a specific submenu using parent end state as begin for elements"""
        try:
            # Capture sidebar interactive elements
            sidebar_elements = self.get_sidebar_interactive_elements()
            if sidebar_elements:
                print(f"    📋 Found {len(sidebar_elements)} sidebar elements for {submenu_id}")
                
                # Additional detection for specific cases
                additional_elements = self.get_specific_interactive_elements(submenu_id)
                if additional_elements:
                    print(f"    🎨 Found {len(additional_elements)} additional specific elements for {submenu_id}")
                    sidebar_elements.extend(additional_elements)
                
                for element in sidebar_elements:
                    element_id = element['id']
                    element_name = element['name']
                    
                    # Create a safe folder name for the element
                    safe_name = element_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('×', 'x').replace('\n', '_').replace('________________________________', '_')
                    if len(safe_name) > 50:
                        safe_name = safe_name[:50]
                    
                    # Create subfolder for this sidebar element under the submenu
                    element_dir = os.path.join(os.path.dirname(overview_path), safe_name)
                    os.makedirs(element_dir, exist_ok=True)
                    
                    # Create begin/action/end for this element (we don't click the leaf element)
                    element_begin_path = os.path.join(element_dir, "begin.png")
                    element_action_path = os.path.join(element_dir, "action.png")
                    element_end_path = os.path.join(element_dir, "end.png")
                    try:
                        shutil.copyfile(overview_path, element_begin_path)
                        shutil.copyfile(overview_path, element_end_path)
                    except Exception as _:
                        pass
                    
                    # Create bbox image for this sidebar element based on begin
                    if self.create_bbox_image(element_begin_path, element, element_action_path, element_name):
                        # Add to trajectory structure
                        if element_id not in node["action"][submenu_id]["action"]:
                            node["action"][submenu_id]["action"][element_id] = {
                                "begin": element_begin_path,
                                "end": element_end_path,
                                "action_image": element_action_path,
                                "action": {},
                                "coordinates_bbox": {
                                    'x': element['x'],
                                    'y': element['y'],
                                    'width': element['width'],
                                    'height': element['height'],
                                    'right': element['right'],
                                    'bottom': element['bottom']
                                },
                                "description": self.get_button_description(element_id, element_name)
                            }
                        print(f"    ✓ Created sidebar element folder for {submenu_id}: {safe_name}")
        except Exception as e:
            print(f"    ✗ Error capturing sidebar elements for {submenu_id}: {e}")

    def create_bbox_image(self, screenshot_path: str, bbox_info: Dict[str, int], output_path: str, label: str = "") -> bool:
        """Create a bbox highlighted image from a screenshot"""
        try:
            # Open the screenshot
            image = Image.open(screenshot_path)
            draw = ImageDraw.Draw(image)
            
            # Draw rectangle around the bbox
            x1 = bbox_info['x']
            y1 = bbox_info['y']
            x2 = bbox_info['right']
            y2 = bbox_info['bottom']
            
            # Draw thick red rectangle (no labels, just the bbox)
            draw.rectangle([x1, y1, x2, y2], outline='red', width=4)
            
            # Save the highlighted image
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path)
            return True
            
        except Exception as e:
            print(f"✗ Error creating bbox image: {e}")
            return False

    def build_functional_tree(self) -> Dict[str, object]:
        assert self.driver is not None

        trajectory: Dict[str, object] = {
            "initial page": {
                "begin": "",
                "end": "",
                "action_image": "",
                "action": {},
                "coordinates_bbox": {},
                "description": "Initial page of MiniWord application"
            }
        }

        print("🎯 MiniWord Functional Tree Collector")
        print("=" * 50)
        print("This tool will capture screenshots and bbox images for all functions")
        print("=" * 50)

        # Plan: gather tabs and per-tab functions
        tabs = self.discover_menu_tabs()
        tab_to_functions: Dict[str, List[Dict[str, str]]] = {}
        for tab in tabs:
            tab_id = tab["id"]
            self.switch_to_tab(tab_id)
            tab_to_functions[tab_id] = self.discover_toolbar_buttons()
        total_functions = sum(len(funcs) for funcs in tab_to_functions.values())
        print(f"\n🚀 Starting to capture {total_functions} function screenshots and bbox images...")
        print("=" * 60)

        # Initial page screenshot
        initial_path = os.path.join(self.output_dir, "initial_overview.png")
        self.take_fullpage_screenshot(initial_path)
        trajectory["initial page"]["begin"] = initial_path
        trajectory["initial page"]["end"] = initial_path

        # Execute: per tab
        for tab in tabs:
            tab_id = tab["id"]
            trajectory["initial page"]["action"].setdefault(tab_id, {
                "begin": "", 
                "end": "", 
                "action_image": "",
                "action": {}, 
                "coordinates_bbox": {},
                "description": ""
            })

            # Prepare category directory and begin/action for tab
            category_dir = os.path.join(self.output_dir, tab_id)
            os.makedirs(category_dir, exist_ok=True)
            cat_begin = os.path.join(category_dir, "begin.png")
            try:
                shutil.copyfile(initial_path, cat_begin)
            except Exception as _:
                pass
            # Create menu bar bbox image for this tab (drawn on begin)
            menu_bbox = self.get_menu_bar_bbox(tab_id)
            if menu_bbox:
                cat_action = os.path.join(category_dir, "action.png")
                if self.create_bbox_image(cat_begin, menu_bbox, cat_action, tab_id.upper()):
                    trajectory["initial page"]["action"][tab_id]["action_image"] = cat_action
                    trajectory["initial page"]["action"][tab_id]["coordinates_bbox"] = menu_bbox
                    trajectory["initial page"]["action"][tab_id]["description"] = f"Switch to {tab_id.upper()} toolbar section"
                    print(f"✓ Created menu bar bbox for {tab_id}")

            # Click tab and capture end
            if self.switch_to_tab(tab_id):
                cat_end = os.path.join(category_dir, "end.png")
                self.take_fullpage_screenshot(cat_end)
                trajectory["initial page"]["action"][tab_id]["begin"] = cat_begin
                trajectory["initial page"]["action"][tab_id]["end"] = cat_end

            functions = tab_to_functions.get(tab_id, [])
            print(f"\n📂 Processing {tab_id.upper()} section ({len(functions)} functions)")
            print("-" * 40)

            # Process functions
            successful_captures = 0
            for fn in functions:
                fn_id = fn["id"]
                node = {
                    "begin": None, 
                    "end": None, 
                    "action_image": "",
                    "action": {}, 
                    "coordinates_bbox": {},
                    "description": ""
                }

                # Submenu items as nested actions without screenshots
                submenu_items = self.discover_submenu_items(fn.get("submenu", ""))
                
                # Special handling for edit_copy - add hardcoded submenu items
                if fn_id == "edit_copy":
                    hardcoded_submenus = [
                        {"id": "copy_plain", "title": "Direct Copy"},
                        {"id": "copy_formatted", "title": "Formatted Copy"}
                    ]
                    submenu_items.extend(hardcoded_submenus)
                    print(f"  🔧 Added hardcoded submenus for edit_copy: {[sm['id'] for sm in hardcoded_submenus]}")
                
                for sm in submenu_items:
                    node["action"][sm["id"]] = {
                        "begin": None, 
                        "end": None, 
                        "action_image": "",
                        "action": {}, 
                        "coordinates_bbox": {},
                        "description": ""
                    }

                # Prepare directories for function-level overview
                fn_dir = os.path.join(category_dir, fn_id)
                os.makedirs(fn_dir, exist_ok=True)
                fn_begin_path = os.path.join(fn_dir, "begin.png")
                fn_action_path = os.path.join(fn_dir, "action.png")
                fn_end_path = os.path.join(fn_dir, "end.png")

                # Click to open sidebar/modal then take screenshot of the page including sidebar when present
                idx = functions.index(fn) + 1
                print(f"[{idx}/{len(functions)}] Capturing: {fn_id} ({fn_id})")
                # Capture begin before clicking
                self.switch_to_tab(tab_id)
                self.take_fullpage_screenshot(fn_begin_path)

                # Create bbox image for this function on begin
                button_bbox = self.get_button_bbox(fn_id)
                if button_bbox:
                    if self.create_bbox_image(fn_begin_path, button_bbox, fn_action_path, fn_id):
                        node["action_image"] = fn_action_path
                        node["coordinates_bbox"] = button_bbox
                        node["description"] = self.get_button_description(fn_id)
                        print(f"✓ Created action image for {fn_id}")

                # Now click to get end state
                if self.click_toolbar_button(fn_id):
                    # Special handling for edit_copy - need to process both submenu options
                    if fn_id == "edit_copy":
                        print(f"  🔄 Special handling for edit_copy - processing both submenu options")
                        
                        # First, take screenshot of the submenu as function end
                        self.take_fullpage_screenshot(fn_end_path)
                        time.sleep(0.5)
                        
                        # Get bbox for Direct Copy BEFORE clicking it
                        copy_plain_bbox = self.get_submenu_bbox("copy_plain")
                        copy_plain_begin = os.path.join(fn_dir, "copy_plain", "begin.png")
                        copy_plain_action = os.path.join(fn_dir, "copy_plain", "action.png")
                        copy_plain_end = os.path.join(fn_dir, "copy_plain", "end.png")
                        os.makedirs(os.path.dirname(copy_plain_begin), exist_ok=True)
                        try:
                            shutil.copyfile(fn_end_path, copy_plain_begin)
                        except Exception as _:
                            pass
                        if copy_plain_bbox:
                            if self.create_bbox_image(copy_plain_begin, copy_plain_bbox, copy_plain_action, "Direct Copy"):
                                print(f"  ✓ Created bbox image for Direct Copy submenu item")
                        else:
                            print(f"  ⚠️ Could not find bbox for Direct Copy submenu item")
                        
                        # Process Direct Copy
                        if self.click_submenu_item("copy_plain"):
                            print(f"  ✓ Clicked Direct Copy, now capturing correct sidebar")
                            # Take screenshot with correct sidebar for Direct Copy as end
                            os.makedirs(os.path.dirname(copy_plain_end), exist_ok=True)
                            if not self.take_sidebar_screenshot(copy_plain_end):
                                self.take_fullpage_screenshot(copy_plain_end)
                            time.sleep(0.2)
                            
                            # Update the submenu node for copy_plain
                            if "copy_plain" in node["action"]:
                                node["action"]["copy_plain"]["begin"] = copy_plain_begin
                                node["action"]["copy_plain"]["end"] = copy_plain_end
                                if copy_plain_bbox:
                                    node["action"]["copy_plain"]["action_image"] = copy_plain_action
                                    node["action"]["copy_plain"]["coordinates_bbox"] = copy_plain_bbox
                                node["action"]["copy_plain"]["description"] = "Direct Copy - Copy text without formatting"
                                print(f"  ✓ Updated copy_plain status")
                            
                            # Capture sidebar elements for Direct Copy
                            self.capture_sidebar_elements_for_submenu(fn_id, "copy_plain", copy_plain_end, node)
                            
                            # Go back to submenu for Formatted Copy
                            self.click_toolbar_button(fn_id)  # Click Copy button again to show submenu
                            time.sleep(0.5)
                        else:
                            print(f"  ✗ Failed to click Direct Copy")
                        
                        # Get bbox for Formatted Copy BEFORE clicking it
                        copy_formatted_bbox = self.get_submenu_bbox("copy_formatted")
                        copy_formatted_begin = os.path.join(fn_dir, "copy_formatted", "begin.png")
                        copy_formatted_action = os.path.join(fn_dir, "copy_formatted", "action.png")
                        copy_formatted_end = os.path.join(fn_dir, "copy_formatted", "end.png")
                        os.makedirs(os.path.dirname(copy_formatted_begin), exist_ok=True)
                        try:
                            shutil.copyfile(fn_end_path, copy_formatted_begin)
                        except Exception as _:
                            pass
                        if copy_formatted_bbox:
                            if self.create_bbox_image(copy_formatted_begin, copy_formatted_bbox, copy_formatted_action, "Formatted Copy"):
                                print(f"  ✓ Created bbox image for Formatted Copy submenu item")
                        else:
                            print(f"  ⚠️ Could not find bbox for Formatted Copy submenu item")
                        
                        # Process Formatted Copy
                        if self.click_submenu_item("copy_formatted"):
                            print(f"  ✓ Clicked Formatted Copy, now capturing correct sidebar")
                            # Take screenshot with correct sidebar for Formatted Copy
                            os.makedirs(os.path.dirname(copy_formatted_end), exist_ok=True)
                            if not self.take_sidebar_screenshot(copy_formatted_end):
                                self.take_fullpage_screenshot(copy_formatted_end)
                            time.sleep(0.2)
                            
                            # Update the submenu node for copy_formatted
                            if "copy_formatted" in node["action"]:
                                node["action"]["copy_formatted"]["begin"] = copy_formatted_begin
                                node["action"]["copy_formatted"]["end"] = copy_formatted_end
                                if copy_formatted_bbox:
                                    node["action"]["copy_formatted"]["action_image"] = copy_formatted_action
                                    node["action"]["copy_formatted"]["coordinates_bbox"] = copy_formatted_bbox
                                node["action"]["copy_formatted"]["description"] = "Formatted Copy - Copy text with formatting"
                                print(f"  ✓ Updated copy_formatted status")
                            
                            # Capture sidebar elements for Formatted Copy
                            self.capture_sidebar_elements_for_submenu(fn_id, "copy_formatted", copy_formatted_end, node)
                        else:
                            print(f"  ✗ Failed to click Formatted Copy")
                        
                        successful_captures += 1
                        print(f"✓ Successfully captured {fn_id} with both submenu options")
                    else:
                        # Normal processing for other functions. For insert_chart, prefer modal capture
                        if fn_id == "insert_chart":
                            if not self.take_modal_screenshot(fn_end_path, modal_id="chart-insert-modal"):
                                # Fallbacks if modal screenshot fails
                                if not self.take_sidebar_screenshot(fn_end_path):
                                    self.take_fullpage_screenshot(fn_end_path)
                            time.sleep(0.2)
                            successful_captures += 1
                            print(f"✓ Successfully captured {fn_id} (modal)")
                        else:
                            if not self.take_sidebar_screenshot(fn_end_path):
                                self.take_fullpage_screenshot(fn_end_path)
                            time.sleep(0.2)
                            successful_captures += 1
                            print(f"✓ Successfully captured {fn_id}")
                    # After click, record function begin/end
                    node["begin"] = fn_begin_path
                    node["end"] = fn_end_path

                    # Capture sidebar interactive elements as the deepest layer (only for non-edit_copy functions)
                    if fn_id != "edit_copy":
                        if fn_id == "insert_chart":
                            # Substitute sidebar detection with modal detection
                            self.capture_modal_elements(fn_id, "chart-insert-modal", fn_end_path, fn_dir, node)
                            # Close modal to avoid interference with subsequent captures
                            self.close_any_open_modals()
                        else:
                            sidebar_elements = self.get_sidebar_interactive_elements()
                            if sidebar_elements:
                                print(f"  📋 Found {len(sidebar_elements)} sidebar elements for {fn_id}")
                                
                                # Additional detection for specific cases like color pickers and margin inputs
                                additional_elements = self.get_specific_interactive_elements(fn_id)
                                if additional_elements:
                                    print(f"  🎨 Found {len(additional_elements)} additional specific elements")
                                    sidebar_elements.extend(additional_elements)
                                
                                for element in sidebar_elements:
                                    element_id = element['id']
                                    element_name = element['name']
                                    
                                    # Create a safe folder name for the element
                                    safe_name = element_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('×', 'x').replace('\n', '_').replace('________________________________', '_')
                                    # Limit the folder name length to avoid filesystem issues
                                    if len(safe_name) > 50:
                                        safe_name = safe_name[:50]
                                    
                                    # Create subfolder for this sidebar element
                                    element_dir = os.path.join(fn_dir, safe_name)
                                    os.makedirs(element_dir, exist_ok=True)
                                    
                                    # Create begin/action/end for this element
                                    element_begin_path = os.path.join(element_dir, "begin.png")
                                    element_action_path = os.path.join(element_dir, "action.png")
                                    element_end_path = os.path.join(element_dir, "end.png")
                                    try:
                                        shutil.copyfile(fn_end_path, element_begin_path)
                                        shutil.copyfile(fn_end_path, element_end_path)
                                    except Exception as _:
                                        pass
                                    
                                    # Create bbox image for this sidebar element based on begin
                                    if self.create_bbox_image(element_begin_path, element, element_action_path, element_name):
                                        # Add to trajectory structure
                                        if element_id not in node["action"]:
                                            node["action"][element_id] = {
                                                "begin": element_begin_path,
                                                "end": element_end_path,  # Same as begin for leaf
                                                "action_image": element_action_path,
                                                "action": {},
                                                "coordinates_bbox": {
                                                    'x': element['x'],
                                                    'y': element['y'],
                                                    'width': element['width'],
                                                    'height': element['height'],
                                                    'right': element['right'],
                                                    'bottom': element['bottom']
                                                },
                                                "description": self.get_button_description(element_id, element_name)
                                            }
                                        print(f"  ✓ Created sidebar element folder: {safe_name}")
                else:
                    print(f"✗ Failed to click button for {fn_id}")

                # Record function node status to nested overview
                if node.get("begin") is None:
                    node["begin"] = fn_begin_path
                if node.get("end") is None:
                    # In case click failed, set end same as begin
                    node["end"] = fn_begin_path
                trajectory["initial page"]["action"][tab_id]["action"][fn_id] = node

        print("\n" + "=" * 60)
        print("🎉 Functional tree collection completed!")
        print(f"📁 Screenshots and bbox images saved in: {self.output_dir}")

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

    tool = MiniWordFunctionalTreeCollector()
    try:
        tool.navigate_home()
        trajectory = tool.build_functional_tree()
        # Persist trajectory.json at repo root alongside output dir
        traj_path = os.path.join(tool.output_dir, "trajectory.json")
        with open(traj_path, "w", encoding="utf-8") as f:
            json.dump(trajectory, f, ensure_ascii=False, indent=2)
        print(f"✓ Trajectory saved to: {traj_path}")
        print(f"✓ Screenshots and bbox images saved under: {tool.output_dir}")
    except KeyboardInterrupt:
        print("⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        tool.close()


if __name__ == "__main__":
    main()
