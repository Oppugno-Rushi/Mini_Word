// MiniWord Main Application - Page Switching Version
class MiniWord {
    constructor() {
        this.editor = document.getElementById('editor');
        this.sidebar = document.getElementById('sidebar');
        this.sidebarTitle = document.getElementById('sidebar-title');
        this.sidebarContent = document.getElementById('sidebar-content');
        this.sidebarClose = document.getElementById('sidebar-close');
        
        this.currentPage = 'home';
        this.currentDocument = {
            content: '',
            title: 'Untitled Document',
            modified: false
        };
        
        // Internal MiniWord clipboard (safer, does not depend on browser permissions)
        this.internalClipboard = {
            plainText: '',
            html: '',
            hasContent: false,
            type: null // 'plain' | 'formatted'
        };
        
        this.paginationMode = true; // Default to paginated mode
        this.tempContent = null;
        
        // Initialize zoom level
        this.currentZoom = 100;
        
        
        // Comments properties
        this.documentComments = [];
        this.commentId = 0;
        this.selectedText = '';
        this.commentAuthor = 'Reviewer';
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.showPage('home');
        this.updateStatus();
        // Initialize comments
        this.initializeComments();
        // Load saved settings
        this.loadSettings();
        // Default show file toolbar
        this.switchToolbar('file');
        // Hide sidebar initially
        this.sidebar.classList.add('hidden');
        // Initialize with paginated layout
        this.createPaginatedLayout();
        // Initialize zoom level
        this.initializeZoom();
        // Initialize page orientation
        this.initializePageOrientation();
        // Check for shared document
        this.checkForSharedDocument();
    }
    
    setupEventListeners() {
        // Menu bar events - dynamic toolbar switching
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const menuType = e.target.dataset.page;
                this.switchToolbar(menuType);
                // Hide sidebar when clicking menu items
                this.sidebar.classList.add('hidden');
            });
        });
        
        // Toolbar button events
        document.querySelectorAll('.toolbar-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const button = e.target.closest('.toolbar-btn');
                const page = button.dataset.page;
                const submenu = button.dataset.submenu;
                
                if (submenu) {
                    this.toggleSubmenu(submenu, button);
                } else {
                    // Show page for all toolbar buttons (including bulleted_list and numbered_list)
                    this.showPage(page);
                }
            });
        });
        
        // Submenu item events
        document.querySelectorAll('.submenu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = e.target.dataset.page;
                this.showPage(page);
                this.hideSubmenu();
            });
        });
        
        // Click elsewhere to hide submenu
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.toolbar-btn[data-submenu]') && !e.target.closest('.submenu-container')) {
                this.hideSubmenu();
            }
        });
        
        // Sidebar close button
        this.sidebarClose.addEventListener('click', () => {
            this.sidebar.classList.add('hidden');
        });
        
        // Editor events
        this.editor.addEventListener('input', () => {
            this.currentDocument.modified = true;
            this.updateStatus();
        });
        
        this.editor.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
        
        // Add click event listener to ensure cursor positioning works
        this.editor.addEventListener('click', (e) => {
            // Allow links to work normally - don't interfere with link clicks
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                // Let the link handle its own click event
                return;
            }
            // Ensure the editor maintains focus for cursor positioning
            this.editor.focus();
        });
        
        // Add click event listeners to page-content elements for cursor positioning
        document.addEventListener('click', (e) => {
            // Allow links to work normally - don't interfere with link clicks
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                // Let the link handle its own click event
                return;
            }
            
            const pageContent = e.target.closest('.page-content');
            if (pageContent && pageContent.contentEditable) {
                // Ensure the page content element can receive focus
                pageContent.focus();
            }
        });
        
        // File input events
        document.addEventListener('change', (e) => {
            if (e.target.id === 'file-input') {
                const fileStatus = document.getElementById('file-status');
                
                if (e.target.files.length > 0) {
                    const file = e.target.files[0];
                    fileStatus.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
                } else {
                    fileStatus.textContent = 'No file selected';
                }
            }
            
        });
        
        
    }
    
    switchToolbar(menuType) {
        // Hide all toolbar content
        document.querySelectorAll('.toolbar-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // Remove active state from all menu items
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Show corresponding toolbar
        const targetToolbar = document.getElementById(`${menuType}-toolbar`);
        if (targetToolbar) {
            targetToolbar.style.display = 'flex';
        }
        
        // Activate corresponding menu item
        const activeMenuItem = document.querySelector(`[data-page="${menuType}"]`);
        if (activeMenuItem) {
            activeMenuItem.classList.add('active');
        }
    }
    
    handleKeyboardShortcuts(e) {
        const isCtrl = e.ctrlKey || e.metaKey;
        
        if (isCtrl) {
            switch (e.key) {
                case 'n':
                    e.preventDefault();
                    this.showPage('file_new');
                    break;
                case 'o':
                    e.preventDefault();
                    this.showPage('file_open');
                    break;
                case 's':
                    e.preventDefault();
                    this.showPage('file_save');
                    break;
                case 'p':
                    e.preventDefault();
                    this.showPage('file_print');
                    break;
                case 'z':
                    e.preventDefault();
                    this.showPage('edit_undo');
                    break;
                case 'y':
                    e.preventDefault();
                    this.showPage('edit_redo');
                    break;
                case 'x':
                    e.preventDefault();
                    this.showPage('edit_cut');
                    break;
                case 'c':
                    e.preventDefault();
                    // Open formatted copy page for Ctrl+C within MiniWord's help/sidebar system
                    this.showPage('copy_formatted');
                    break;
                case 'v':
                    e.preventDefault();
                    this.showPage('edit_paste');
                    break;
                case 'f':
                    e.preventDefault();
                    this.showPage('find');
                    break;
                case 'h':
                    e.preventDefault();
                    this.showPage('replace');
                    break;
                case 'k':
                    e.preventDefault();
                    this.clearAllFormatting();
                    break;
                case 'j':
                    e.preventDefault();
                    this.activateFormatPainter();
                    break;
                case '=':
                case '+':
                    e.preventDefault();
                    this.zoomIn();
                    break;
                case '-':
                    e.preventDefault();
                    this.zoomOut();
                    break;
                case '0':
                    e.preventDefault();
                    this.resetZoom();
                    break;
                case 'b':
                    e.preventDefault();
                    this.showPage('bold');
                    break;
                case 'i':
                    e.preventDefault();
                    this.showPage('italic');
                    break;
                case 'u':
                    e.preventDefault();
                    this.showPage('underline');
                    break;
                case 'r':
                    e.preventDefault();
                    this.refreshWebPage();
                    break;
                case 'w':
                    e.preventDefault();
                    this.closeWebPage();
                    break;
            }
        }
        
        // Handle F5 for refresh
        if (e.key === 'F5') {
            e.preventDefault();
            this.refreshWebPage();
        }
        
        
        // Handle Ctrl+T for new tab
        if (isCtrl && e.key === 't') {
            e.preventDefault();
            this.openNewTab();
        }
    }
    
    showPage(pageId) {
        this.currentPage = pageId;
        
        // Special handling for chart insert - show sidebar AND modal
        if (pageId === 'insert_chart') {
            // Show sidebar with function description
            this.sidebar.classList.remove('hidden');
            this.renderPage(pageId);
            
            // Also show the modal
            this.showChartInsertModal();
            return;
        }
        
        // Only show sidebar for specific function pages, not for menu categories
        const menuCategories = ['file', 'edit', 'view', 'insert', 'format', 'tools', 'help'];
        // Special case: table_insert should show in sidebar
        if (!menuCategories.includes(pageId) || pageId === 'table_insert') {
            this.sidebar.classList.remove('hidden');
        } else {
            this.sidebar.classList.add('hidden');
        }
        
        // Update button status
        document.querySelectorAll('.toolbar-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeBtn = document.querySelector(`[data-page="${pageId}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
        
        // Show corresponding page content
        this.renderPage(pageId);
        
        // Special handling for specific pages
    }
    
    renderPage(pageId) {
        console.log('renderPage called with pageId:', pageId); // Debug log
        const pageContent = this.getPageContent(pageId);
        console.log('Page content:', pageContent); // Debug log
        this.sidebarTitle.textContent = pageContent.title;
        this.sidebarContent.innerHTML = pageContent.content;
        
        
        // Load current settings when Application Settings page is loaded
        if (pageId === 'app_settings') {
            this.loadCurrentSettings();
        }
        
        // Check if buttons are rendered
        if (pageId === 'insert_chart') {
            const refreshBtn = document.querySelector('button[onclick*="detectTablesInDocument"]');
            const testBtn = document.querySelector('button[onclick*="testTableDetection"]');
            console.log('Refresh button found:', !!refreshBtn); // Debug log
            console.log('Test button found:', !!testBtn); // Debug log
        }
        
        // Bind page-specific events
        this.bindPageEvents(pageId);
    }
    
    getPageContent(pageId) {
        const pages = {
            'home': {
                title: 'Welcome to MiniWord',
                content: `
                    <div class="page-content">
                        <h2>Welcome to MiniWord</h2>
                        <p>This is a simulated Word environment that provides complete document editing functionality.</p>
                        <div class="feature-grid">
                            <div class="feature-card">
                                <img src="miniword_buttons_png/file_new.png" alt="New">
                                <h4>New Document</h4>
                                <p>Create blank document</p>
                            </div>
                            <div class="feature-card">
                                <img src="miniword_buttons_png/file_open.png" alt="Open">
                                <h4>Open Document</h4>
                                <p>Open existing document</p>
                            </div>
                            <div class="feature-card">
                                <img src="miniword_buttons_png/file_save.png" alt="Save">
                                <h4>Save Document</h4>
                                <p>Save current document</p>
                            </div>
                        </div>
                        <p>Click toolbar buttons or use keyboard shortcuts to start editing documents.</p>
                    </div>
                `
            },
            
            'file': {
                title: 'File Operations',
                content: `
                    <div class="page-content">
                        <h2>File Operations</h2>
                        <p>Manage your document files</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('file_new')">
                                <img src="miniword_buttons_png/file_new.png" alt="New">
                                <h4>New Document</h4>
                                <p>Create blank document</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('file_open')">
                                <img src="miniword_buttons_png/file_open.png" alt="Open">
                                <h4>Open Document</h4>
                                <p>Open existing document</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('file_save')">
                                <img src="miniword_buttons_png/file_save.png" alt="Save">
                                <h4>Save Document</h4>
                                <p>Save current document</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('file_print')">
                                <img src="miniword_buttons_png/file_print.png" alt="Print">
                                <h4>Print Document</h4>
                                <p>Print current document</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'file_new': {
                title: 'New Document',
                content: `
                    <div class="page-content">
                        <h2>New Document</h2>
                        <p>Create a new document with custom settings</p>
                        <div class="form-group">
                            <label>Document Title:</label>
                            <input type="text" id="new-doc-title" placeholder="Enter document title" value="Untitled Document">
                        </div>
                        <div class="form-group">
                            <label>Document Type:</label>
                            <select id="new-doc-type">
                                <option value="blank">Blank Document</option>
                                <option value="letter">Business Letter</option>
                                <option value="report">Project Report</option>
                                <option value="memo">Internal Memo</option>
                                <option value="resume">Personal Resume</option>
                                <option value="newsletter">Newsletter</option>
                                <option value="invoice">Invoice</option>
                            </select>
                        </div>
                        <div class="warning-box">
                            <strong>Note:</strong> Creating a new document will replace the current document. Save your work first if needed.
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.createNewDocument()">Create Document</button>
                            <button class="btn" onclick="miniWord.showPage('file')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'file_open': {
                title: 'Open Document',
                content: `
                    <div class="page-content">
                        <h2>Open Document</h2>
                        <p>Open existing document files</p>
                        <div class="form-group">
                            <label>Select File:</label>
                            <div class="file-input-wrapper">
                                <input type="file" id="file-input" accept=".txt,.html,.htm,.md" style="display: none;">
                                <button type="button" class="file-select-btn" onclick="document.getElementById('file-input').click()">
                                    Choose File
                                </button>
                                <span id="file-status" class="file-status-text">No file selected</span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Or enter document content:</label>
                            <textarea id="content-input" rows="6" placeholder="Paste document content..."></textarea>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.openDocument()">Open Document</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'file_save': {
                title: 'Save Document',
                content: `
                    <div class="page-content">
                        <h2>Save Document</h2>
                        <p>Save current document to file</p>
                        <div class="form-group">
                            <label>Filename:</label>
                            <input type="text" id="save-filename" placeholder="Enter filename" value="${this.currentDocument.title || 'Untitled Document'}">
                        </div>
                        <div class="form-group">
                            <label>Save Fo  rmat:</label>
                            <select id="save-format">
                                <option value="html">HTML Document</option>
                                <option value="txt">Plain Text</option>
                                <option value="md">Markdown</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.saveDocument()">Save Document</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'file_print': {
                title: 'Print Document',
                content: `
                    <div class="page-content">
                        <h2>Print Document</h2>
                        <p>Print current document</p>
                        <div class="form-group">
                            <label>Printer:</label>
                            <select id="printer-select">
                                <option value="default">Default Printer</option>
                                <option value="pdf">Save as PDF</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Page Range:</label>
                            <select id="page-range">
                                <option value="all">All Pages</option>
                                <option value="current">Current Page</option>
                                <option value="custom">Custom Range</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.printDocument()">Print</button>
                            <button class="btn" onclick="miniWord.showPage('view_preview')">Preview</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            
            'web_refresh': {
                title: 'Refresh Page',
                content: `
                    <div class="page-content">
                        <h2>Refresh Page</h2>
                        <p>Reload the current web page</p>
                        <div class="warning-box">
                            <strong>Warning:</strong> This will reload the entire page. Any unsaved changes will be lost.
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.refreshWebPage()">Refresh Page</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'web_close': {
                title: 'Close Page',
                content: `
                    <div class="page-content">
                        <h2>Close Page</h2>
                        <p>Close the current browser tab/window</p>
                        <div class="warning-box">
                            <strong>Note:</strong> This will attempt to close the current tab. If the tab cannot be closed programmatically, you'll need to close it manually.
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.closeWebPage()">Close Page</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            
            'new_tab': {
                title: 'Open New Tab',
                content: `
                    <div class="page-content">
                        <h2>Open New Tab</h2>
                        <p>Open a new browser tab with a fresh MiniWord instance</p>
                        <div class="info-box">
                            <strong>Info:</strong> This will open a new tab with MiniWord. You can work on multiple documents simultaneously.
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.openNewTab()">Open New Tab</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'toggle_pagination': {
                title: 'Toggle Pagination',
                content: `
                    <div class="page-content">
                        <h2>Toggle Pagination</h2>
                        <p>Switch between paginated view (like Microsoft Word) and continuous text view</p>
                        <div class="info-box">
                            <strong>Current Mode:</strong> <span id="current-mode">Pagination</span>
                        </div>
                        <div class="warning-box">
                            <strong>Note:</strong> Switching modes will reformat your document content.
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.togglePagination()">Toggle Mode</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'edit': {
                title: 'Edit Operations',
                content: `
                    <div class="page-content">
                        <h2>Edit Operations</h2>
                        <p>Basic editing functions</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('edit_undo')">
                                <img src="miniword_buttons_png/edit_undo.png" alt="Undo">
                                <h4>Undo</h4>
                                <p>Undo the last operation</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('edit_redo')">
                                <img src="miniword_buttons_png/edit_redo.png" alt="Redo">
                                <h4>Redo</h4>
                                <p>Redo the undone operation</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('edit_cut')">
                                <img src="miniword_buttons_png/edit_cut.png" alt="Cut">
                                <h4>Cut</h4>
                                <p>Cut selected content</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('copy_plain')">
                                <img src="miniword_buttons_png/edit_copy.png" alt="Direct Copy">
                                <h4>Direct Copy</h4>
                                <p>Copy selected text without formatting</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('copy_formatted')">
                                <img src="miniword_icons_set2/mw2_styles.png" alt="Formatted Copy">
                                <h4>Formatted Copy</h4>
                                <p>Copy selected text with all formatting</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('edit_paste')">
                                <img src="miniword_buttons_png/edit_paste.png" alt="Paste">
                                <h4>Paste</h4>
                                <p>Paste clipboard content</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'edit_undo': {
                title: 'Undo Operation',
                content: `
                    <div class="page-content">
                        <h2>Undo Operation</h2>
                        <p>Undo the last operation</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.undo()">Undo (Ctrl+Z)</button>
                            <button class="btn" onclick="miniWord.showPage('edit')">Back to Edit</button>
                        </div>
                    </div>
                `
            },
            
            'edit_redo': {
                title: 'Redo Operation',
                content: `
                    <div class="page-content">
                        <h2>Redo Operation</h2>
                        <p>Redo the undone operation</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.redo()">Redo (Ctrl+Y)</button>
                            <button class="btn" onclick="miniWord.showPage('edit')">Back to Edit</button>
                        </div>
                    </div>
                `
            },
            
            'edit_cut': {
                title: 'Cut Content',
                content: `
                    <div class="page-content">
                        <h2>Cut Content</h2>
                        <p>Cut selected content to clipboard</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.cut()">Cut (Ctrl+X)</button>
                            <button class="btn" onclick="miniWord.showPage('edit')">Back to Edit</button>
                        </div>
                    </div>
                `
            },
            
            'edit_paste': {
                title: 'Paste Content',
                content: `
                    <div class="page-content">
                        <h2>Paste Content</h2>
                        <p>Paste content from clipboard with different options</p>
                        <div class="feature-info">
                            <h3>Paste Options:</h3>
                            <ul>
                                <li><strong>Smart Paste:</strong> Automatically detects and pastes formatted or plain text</li>
                                <li><strong>Plain Text:</strong> Paste as plain text only (removes formatting)</li>
                                <li><strong>Formatted:</strong> Paste with all formatting preserved</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.paste()">Smart Paste (Ctrl+V)</button>
                            <button class="btn btn-secondary" onclick="miniWord.pastePlainText()">Paste Plain Text</button>
                            <button class="btn btn-secondary" onclick="miniWord.pasteFormatted()">Paste Formatted</button>
                            <button class="btn" onclick="miniWord.showPage('edit')">Back to Edit</button>
                        </div>
                    </div>
                `
            },
            
            'find': {
                title: 'Find Text',
                content: `
                    <div class="page-content">
                        <h2>Find Text</h2>
                        <p>Find specified text in document</p>
                        <div class="form-group">
                            <label>Find Content:</label>
                            <input type="text" id="find-text" placeholder="Enter text to find">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="case-sensitive"> Case sensitive
                            </label>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.findText()">Find</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'replace': {
                title: 'Find and Replace',
                content: `
                    <div class="page-content">
                        <h2>Find and Replace</h2>
                        <p>Find and replace text in document</p>
                        <div class="form-group">
                            <label>Find Content:</label>
                            <input type="text" id="replace-find" placeholder="Enter text to find">
                        </div>
                        <div class="form-group">
                            <label>Replace With:</label>
                            <input type="text" id="replace-with" placeholder="Enter replacement text">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="replace-case-sensitive"> Case sensitive
                            </label>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.replaceText()">Replace All</button>
                            <button class="btn" onclick="miniWord.showPage('home')">Cancel</button>
                        </div>
                    </div>
                `
            },
            
            'bold': {
                title: 'Bold Format',
                content: `
                    <div class="page-content">
                        <h2>Bold Format</h2>
                        <p>Set selected text to bold</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.toggleBold()">Apply Bold (Ctrl+B)</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'italic': {
                title: 'Italic Format',
                content: `
                    <div class="page-content">
                        <h2>Italic Format</h2>
                        <p>Set selected text to italic</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.toggleItalic()">Apply Italic (Ctrl+I)</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'underline': {
                title: 'Underline Format',
                content: `
                    <div class="page-content">
                        <h2>Underline Format</h2>
                        <p>Add underline to selected text</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.toggleUnderline()">Apply Underline (Ctrl+U)</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'text_color': {
                title: 'Text Color',
                content: `
                    <div class="page-content">
                        <h2>Text Color</h2>
                        <p>Change color of selected text</p>
                        <div class="form-group">
                            <label>Select Color:</label>
                            <input type="color" id="font-color" value="#000000" style="width: 60px; height: 40px; border: 2px solid #ccc; border-radius: 4px;">
                        </div>
                        <div class="color-palette" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0;">
                            <div class="color-option" style="background-color: #000000; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#000000" onclick="document.getElementById('font-color').value='#000000'; miniWord.applyColorDirect('#000000');"></div>
                            <div class="color-option" style="background-color: #ff0000; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ff0000" onclick="document.getElementById('font-color').value='#ff0000'; miniWord.applyColorDirect('#ff0000');"></div>
                            <div class="color-option" style="background-color: #00ff00; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#00ff00" onclick="document.getElementById('font-color').value='#00ff00'; miniWord.applyColorDirect('#00ff00');"></div>
                            <div class="color-option" style="background-color: #0000ff; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#0000ff" onclick="document.getElementById('font-color').value='#0000ff'; miniWord.applyColorDirect('#0000ff');"></div>
                            <div class="color-option" style="background-color: #ffff00; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ffff00" onclick="document.getElementById('font-color').value='#ffff00'; miniWord.applyColorDirect('#ffff00');"></div>
                            <div class="color-option" style="background-color: #ff00ff; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ff00ff" onclick="document.getElementById('font-color').value='#ff00ff'; miniWord.applyColorDirect('#ff00ff');"></div>
                            <div class="color-option" style="background-color: #00ffff; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#00ffff" onclick="document.getElementById('font-color').value='#00ffff'; miniWord.applyColorDirect('#00ffff');"></div>
                            <div class="color-option" style="background-color: #808080; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#808080" onclick="document.getElementById('font-color').value='#808080'; miniWord.applyColorDirect('#808080');"></div>
                        </div>
                        <div class="button-group" style="margin-top: 20px;">
                            <button class="btn btn-primary" onclick="miniWord.fontColor()" style="background-color: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-right: 10px;">🎨 Apply Color</button>
                            <button class="btn" onclick="miniWord.showPage('format')" style="background-color: #6c757d; color: white; padding: 12px 24px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;">Back to Format</button>
                        </div>
                        <div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; font-size: 14px; color: #666;">
                            <strong>Instructions:</strong><br>
                            1. First select the text in the editor to set color<br>
                            2. Choose color (click color square or use color picker)<br>
                            3. Click "Apply Color" button
                        </div>
                    </div>
                `
            },
            
            'insert_table': {
                title: 'Insert Table',
                content: `
                    <div class="page-content">
                        <h2>Insert Table</h2>
                        <p>Insert a table into your document with customizable rows and columns.</p>
                        
                        
                        <div class="input-group">
                            <label>Select Table Size:</label>
                            <div class="table-preview" id="table-size-preview"></div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.insertSelectedTable()">Insert Table</button>
                            <button class="btn" onclick="miniWord.showPage('insert')">Back to Insert</button>
                        </div>
                    </div>
                `
            },

            'insert_chart': {
                title: 'Insert Chart',
                content: `
                    <div class="page-content">
                        <h2>Insert Chart</h2>
                        <p>Insert various types of charts in document based on table data.</p>
                        
                        <div class="feature-info">
                            <h3>Features:</h3>
                            <ul>
                                <li>📊 Bar Chart - Display data as vertical bars</li>
                                <li>🥧 Pie Chart - Show data as proportional slices</li>
                                <li>🔍 Auto-detect tables in document</li>
                                <li>✏️ Manual data input option</li>
                            </ul>
                            
                            <h3>How to use:</h3>
                            <ol>
                                <li>Insert a table in your document</li>
                                <li>Click "Insert Chart" button</li>
                                <li>Select chart type and options</li>
                                <li>Choose data source (auto-detect or manual)</li>
                                <li>Click "Insert Chart" to add to document</li>
                            </ol>
                        </div>
                    </div>
                `
            },
            
            'help': {
                title: 'Help and Instructions',
                content: `
                    <div class="page-content">
                        <h2>Help and Instructions</h2>
                        <p>MiniWord User Guide and Interactive Help</p>
                        
                        <!-- Quick Actions -->
                        <div class="help-actions">
                            <h3>Quick Actions</h3>
                            <div class="button-group">
                                <button class="btn btn-primary" onclick="miniWord.showKeyboardShortcuts()">Show Keyboard Shortcuts</button>
                                <button class="btn btn-info" onclick="miniWord.showTutorial()">Start Tutorial</button>
                                <button class="btn btn-warning" onclick="miniWord.resetToDefaults()">Reset to Defaults</button>
                                <button class="btn btn-success" onclick="miniWord.exportHelp()">Export Help Guide</button>
                            </div>
                        </div>
                        
                        <!-- Interactive Help -->
                        <div class="interactive-help">
                            <h3>Interactive Help</h3>
                            <div class="form-group">
                                <label>Search Help:</label>
                                <input type="text" id="help-search" placeholder="Type your question here..." onkeyup="miniWord.searchHelp(this.value)">
                                <button class="btn btn-sm" onclick="miniWord.clearHelpSearch()">Clear</button>
                            </div>
                            <div id="help-results" class="help-results"></div>
                        </div>
                        
                        <!-- Quick Tips -->
                        <div class="quick-tips">
                            <h3>Quick Tips</h3>
                            <div class="tip-card" onclick="miniWord.showTip('formatting')">
                                <h4>💡 Formatting Tips</h4>
                                <p>Learn about text formatting options</p>
                            </div>
                            <div class="tip-card" onclick="miniWord.showTip('tables')">
                                <h4>📊 Table Management</h4>
                                <p>How to create and manage tables</p>
                            </div>
                            <div class="tip-card" onclick="miniWord.showTip('lists')">
                                <h4>📝 Lists and Bullets</h4>
                                <p>Creating bulleted and numbered lists</p>
                            </div>
                            <div class="tip-card" onclick="miniWord.showTip('comments')">
                                <h4>💬 Comments and Reviews</h4>
                                <p>Adding and managing comments</p>
                            </div>
                        </div>
                        
                        <!-- System Information -->
                        <div class="system-info">
                            <h3>System Information</h3>
                            <div class="info-grid">
                                <div class="info-item">
                                    <strong>Version:</strong> <span id="app-version">MiniWord 1.0</span>
                                </div>
                                <div class="info-item">
                                    <strong>Last Updated:</strong> <span id="last-updated">Today</span>
                                </div>
                                <div class="info-item">
                                    <strong>Document Status:</strong> <span id="doc-status">Ready</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Keyboard Shortcuts (Collapsible) -->
                        <div class="keyboard-shortcuts">
                        <h3>Keyboard Shortcuts</h3>
                            <button class="btn btn-sm" onclick="miniWord.toggleShortcuts()">Toggle Shortcuts</button>
                            <div id="shortcuts-list" class="shortcuts-list" style="display: none;">
                                <div class="shortcut-category">
                                    <h4>File Operations</h4>
                                    <ul>
                                        <li><kbd>Ctrl+N</kbd> New Document</li>
                                        <li><kbd>Ctrl+O</kbd> Open Document</li>
                                        <li><kbd>Ctrl+S</kbd> Save Document</li>
                                        <li><kbd>Ctrl+P</kbd> Print Document</li>
                        </ul>
                                </div>
                                <div class="shortcut-category">
                                    <h4>Edit Operations</h4>
                                    <ul>
                                        <li><kbd>Ctrl+Z</kbd> Undo</li>
                                        <li><kbd>Ctrl+Y</kbd> Redo</li>
                                        <li><kbd>Ctrl+X</kbd> Cut</li>
                                        <li><kbd>Ctrl+C</kbd> Copy</li>
                                        <li><kbd>Ctrl+V</kbd> Paste</li>
                                        <li><kbd>Ctrl+F</kbd> Find</li>
                                        <li><kbd>Ctrl+H</kbd> Replace</li>
                                    </ul>
                                </div>
                                <div class="shortcut-category">
                                    <h4>Formatting</h4>
                                    <ul>
                                        <li><kbd>Ctrl+B</kbd> Bold</li>
                                        <li><kbd>Ctrl+I</kbd> Italic</li>
                                        <li><kbd>Ctrl+U</kbd> Underline</li>
                                        <li><kbd>Ctrl+K</kbd> Clear Formatting</li>
                                        <li><kbd>Ctrl+J</kbd> Format Painter</li>
                                    </ul>
                                </div>
                                <div class="shortcut-category">
                                    <h4>View Operations</h4>
                                    <ul>
                                        <li><kbd>Ctrl++</kbd> Zoom In</li>
                                        <li><kbd>Ctrl+-</kbd> Zoom Out</li>
                                        <li><kbd>Ctrl+0</kbd> Reset Zoom</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('home')">Back to Home</button>
                        </div>
                    </div>
                `
            },
            
            'insert': {
                title: 'Insert Operations',
                content: `
                    <div class="page-content">
                        <h2>Insert Operations</h2>
                        <p>Insert various elements in document</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('insert_image')">
                                <img src="miniword_buttons_png/insert_image.png" alt="Insert Image">
                                <h4>Insert Image</h4>
                                <p>Insert image in document</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('insert_table')">
                                <img src="miniword_buttons_png/insert_table.png" alt="Insert Table">
                                <h4>Insert Table</h4>
                                <p>Create and insert table</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('insert_chart')">
                                <img src="miniword_buttons_png/insert_chart.png" alt="Insert Chart">
                                <h4>Insert Chart</h4>
                                <p>Insert various types of charts</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('insert_link')">
                                <img src="miniword_buttons_png/insert_link.png" alt="Insert Link">
                                <h4>Insert Link</h4>
                                <p>Insert hyperlink</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('insert_equation')">
                                <img src="miniword_buttons_png/insert_equation.png" alt="Insert Equation">
                                <h4>Insert Equation</h4>
                                <p>Insert mathematical equation</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('insert_symbol')">
                                <img src="miniword_buttons_png/insert_symbol.png" alt="Insert Symbol">
                                <h4>Insert Symbol</h4>
                                <p>Insert special symbols</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'format': {
                title: 'Format Operations',
                content: `
                    <div class="page-content">
                        <h2>Format Operations</h2>
                        <p>Set text and paragraph formatting</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('bold')">
                                <img src="miniword_buttons_png/bold.png" alt="Bold">
                                <h4>Bold</h4>
                                <p>Set text to bold</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('italic')">
                                <img src="miniword_buttons_png/italic.png" alt="Italic">
                                <h4>Italic</h4>
                                <p>Set text to italic</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('underline')">
                                <img src="miniword_buttons_png/underline.png" alt="Underline">
                                <h4>Underline</h4>
                                <p>Add underline to text</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('strikethrough')">
                                <img src="miniword_buttons_png/strikethrough.png" alt="Strikethrough">
                                <h4>Strikethrough</h4>
                                <p>Add strikethrough to text</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('text_color')">
                                <img src="miniword_buttons_png/text_color.png" alt="Text Color">
                                <h4>Text Color</h4>
                                <p>Set text color</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('highlight')">
                                <img src="miniword_buttons_png/highlight.png" alt="Highlight">
                                <h4>Highlight</h4>
                                <p>Highlight text</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('align_left')">
                                <img src="miniword_buttons_png/align_left.png" alt="Align Left">
                                <h4>Align Left</h4>
                                <p>Align text to left</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('align_center')">
                                <img src="miniword_buttons_png/align_center.png" alt="Center">
                                <h4>Center</h4>
                                <p>Center align text</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('align_right')">
                                <img src="miniword_buttons_png/align_right.png" alt="Align Right">
                                <h4>Align Right</h4>
                                <p>Align text to right</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('align_justify')">
                                <img src="miniword_buttons_png/align_justify.png" alt="Justify">
                                <h4>Justify</h4>
                                <p>Justify text alignment</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'tools': {
                title: 'Tool Operations',
                content: `
                    <div class="page-content">
                        <h2>Tool Operations</h2>
                        <p>Use various editing tools</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('review_spelling')">
                                <img src="miniword_buttons_png/review_spelling.png" alt="Spell Check">
                                <h4>Spell Check</h4>
                                <p>Check spelling errors in document</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('review_comment')">
                                <img src="miniword_buttons_png/review_comment.png" alt="New Comment">
                                <h4>New Comment</h4>
                                <p>Add comments and reviews</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('bulleted_list')">
                                <img src="miniword_buttons_png/bulleted_list.png" alt="Bulleted List">
                                <h4>Bulleted List</h4>
                                <p>Create bulleted list</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('numbered_list')">
                                <img src="miniword_buttons_png/numbered_list.png" alt="Numbered List">
                                <h4>Numbered List</h4>
                                <p>Create numbered list</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('indent_increase')">
                                <img src="miniword_buttons_png/indent_increase.png" alt="Increase Indent">
                                <h4>Increase Indent</h4>
                                <p>Increase paragraph indentation</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('indent_decrease')">
                                <img src="miniword_buttons_png/indent_decrease.png" alt="Decrease Indent">
                                <h4>Decrease Indent</h4>
                                <p>Decrease paragraph indentation</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'view': {
                title: 'View Operations',
                content: `
                    <div class="page-content">
                        <h2>View Operations</h2>
                        <p>Adjust document display mode</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('view_zoom_in')">
                                <img src="miniword_buttons_png/view_zoom_in.png" alt="Zoom In">
                                <h4>Zoom In</h4>
                                <p>Zoom in document display</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('view_zoom_out')">
                                <img src="miniword_buttons_png/view_zoom_out.png" alt="Zoom Out">
                                <h4>Zoom Out</h4>
                                <p>Zoom out document display</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('view_preview')">
                                <img src="miniword_buttons_png/view_preview.png" alt="Print Preview">
                                <h4>Print Preview</h4>
                                <p>Preview print effect</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('layout_page_setup')">
                                <img src="miniword_buttons_png/layout_page_setup.png" alt="Page Setup">
                                <h4>Page Setup</h4>
                                <p>Set page layout</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'view_zoom_in': {
                title: 'Zoom In View',
                content: `
                    <div class="page-content">
                        <h2>Zoom In View</h2>
                        <p>Increase document display scale for better readability</p>
                        <div class="zoom-info">
                            <h4>Current Zoom Level: <span class="zoom-level-display">100%</span></h4>
                        </div>
                        <div class="form-group">
                            <label>Select Zoom Level:</label>
                            <select id="zoom-in-level">
                                <option value="125">125%</option>
                                <option value="150">150%</option>
                                <option value="175">175%</option>
                                <option value="200">200%</option>
                                <option value="250">250%</option>
                                <option value="300">300%</option>
                                <option value="400">400%</option>
                                <option value="500">500%</option>
                            </select>
                        </div>
                        <div class="zoom-shortcuts">
                            <h4>Quick Actions:</h4>
                            <ul>
                                <li><strong>Ctrl + Plus (+):</strong> Zoom in by 25%</li>
                                <li><strong>Ctrl + Minus (-):</strong> Zoom out by 25%</li>
                                <li><strong>Ctrl + 0:</strong> Reset to 100%</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.zoomIn()">Apply Zoom In</button>
                            <button class="btn btn-secondary" onclick="miniWord.resetZoom()">Reset to 100%</button>
                            <button class="btn" onclick="miniWord.showPage('view')">Back to View</button>
                        </div>
                    </div>
                `
            },
            
            'view_zoom_out': {
                title: 'Zoom Out View',
                content: `
                    <div class="page-content">
                        <h2>Zoom Out View</h2>
                        <p>Decrease document display scale to see more content</p>
                        <div class="zoom-info">
                            <h4>Current Zoom Level: <span class="zoom-level-display">100%</span></h4>
                        </div>
                        <div class="form-group">
                            <label>Select Zoom Level:</label>
                            <select id="zoom-out-level">
                                <option value="25">25%</option>
                                <option value="50">50%</option>
                                <option value="75">75%</option>
                                <option value="90">90%</option>
                                <option value="100">100%</option>
                            </select>
                        </div>
                        <div class="zoom-shortcuts">
                            <h4>Quick Actions:</h4>
                            <ul>
                                <li><strong>Ctrl + Plus (+):</strong> Zoom in by 25%</li>
                                <li><strong>Ctrl + Minus (-):</strong> Zoom out by 25%</li>
                                <li><strong>Ctrl + 0:</strong> Reset to 100%</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.zoomOut()">Apply Zoom Out</button>
                            <button class="btn btn-secondary" onclick="miniWord.resetZoom()">Reset to 100%</button>
                            <button class="btn" onclick="miniWord.showPage('view')">Back to View</button>
                        </div>
                    </div>
                `
            },
            
            'view_preview': {
                title: 'Print Preview',
                content: `
                    <div class="page-content">
                        <h2>Print Preview</h2>
                        <p>Preview document print effect</p>
                        <div class="preview-container">
                            <div class="preview-page">
                                <h3>Preview Page</h3>
                                <p>This will show the document print preview effect</p>
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.printDocument()">Print</button>
                            <button class="btn" onclick="miniWord.showPage('view')">Back to View</button>
                        </div>
                    </div>
                `
            },
            
            'layout_page_setup': {
                title: 'Page Setup',
                content: `
                    <div class="page-content">
                        <h2>Page Setup</h2>
                        <p>Set document page layout</p>
                        
                        <div class="page-setup-container">
                            <div class="setup-section">
                                <h3>Page Orientation:</h3>
                                <div class="orientation-group">
                                    <label class="radio-label">
                                        <input type="radio" name="page-orientation" value="portrait" checked>
                                        <span class="radio-text">Portrait</span>
                                    </label>
                                    <label class="radio-label">
                                        <input type="radio" name="page-orientation" value="landscape">
                                        <span class="radio-text">Landscape</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.applyPageOrientation()">Apply Orientation</button>
                            <button class="btn btn-secondary" onclick="miniWord.resetPageOrientation()">Reset to Portrait</button>
                            <button class="btn" onclick="miniWord.showPage('view')">Back to View</button>
                        </div>
                    </div>
                `
            },
            
            
            'insert_image': {
                title: 'Insert Image',
                content: `
                    <div class="page-content">
                        <h2>Insert Image</h2>
                        <p>Insert image in document</p>
                        <div class="form-group">
                            <label>Select Image File:</label>
                            <input type="file" id="image-file" accept="image/*">
                        </div>
                        <div class="form-group">
                            <label>Image Size:</label>
                            <select id="image-size">
                                <option value="small">Small</option>
                                <option value="medium">Medium</option>
                                <option value="large">Large</option>
                                <option value="custom">Custom</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.insertImage()">Insert Image</button>
                            <button class="btn" onclick="miniWord.showPage('insert')">Back to Insert</button>
                        </div>
                    </div>
                `
            },
            
            
            'insert_link': {
                title: 'Insert Link',
                content: `
                    <div class="page-content">
                        <h2>Insert Link</h2>
                        <p>Insert hyperlink in document</p>
                        <div class="form-group">
                            <label>Link URL:</label>
                            <input type="url" id="link-url" placeholder="https://example.com">
                        </div>
                        <div class="form-group">
                            <label>Display Text:</label>
                            <input type="text" id="link-text" placeholder="Link display text">
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.insertLink()">Insert Link</button>
                            <button class="btn" onclick="miniWord.showPage('insert')">Back to Insert</button>
                        </div>
                    </div>
                `
            },
            
            'insert_equation': {
                title: 'Insert Equation',
                content: `
                    <div class="page-content">
                        <h2>Insert Equation</h2>
                        <p>Insert mathematical equations in your document with proper formatting</p>
                        
                        <div class="form-group">
                            <label>Equation Type:</label>
                            <select id="equation-type" onchange="miniWord.updateEquationPreview()">
                                <option value="basic">Basic Equation</option>
                                <option value="fraction">Fraction</option>
                                <option value="root">Square Root</option>
                                <option value="power">Power/Exponent</option>
                                <option value="integral">Integral</option>
                                <option value="sum">Summation</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label>Equation Content:</label>
                            <textarea id="equation-content" rows="3" placeholder="Enter equation content..." oninput="miniWord.updateEquationPreview()"></textarea>
                            <div id="equation-instructions" style="font-size: 12px; color: #666; margin-top: 5px;">
                                <strong>Instructions:</strong><br>
                                • Basic: Enter any mathematical expression (e.g., "2x + 3 = 7")<br>
                                • Fraction: Use "/" to separate numerator and denominator (e.g., "a/b")<br>
                                • Power: Use "^" to separate base and exponent (e.g., "x^2")<br>
                                • Root: Enter the expression under the root (e.g., "x + 1")<br>
                                • Integral: Enter the function to integrate (e.g., "x^2")<br>
                                • Summation: Enter the expression to sum (e.g., "i^2")
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Preview:</label>
                            <div id="equation-preview" style="
                                border: 1px solid #ddd; 
                                padding: 15px; 
                                background: #f9f9f9; 
                                border-radius: 4px; 
                                text-align: center;
                                min-height: 50px;
                                font-family: 'Times New Roman', serif;
                                font-size: 18px;
                                color: #333;
                            ">
                                Preview will appear here...
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.insertEquation()">Insert Equation</button>
                            <button class="btn" onclick="miniWord.showPage('insert')">Back to Insert</button>
                        </div>
                    </div>
                `
            },
            
            'insert_symbol': {
                title: 'Insert Symbol',
                content: `
                    <div class="page-content">
                        <h2>Insert Symbol</h2>
                        <p>Click on any symbol below to insert it at your cursor position</p>
                        
                        <div class="form-group">
                            <label>Special Characters:</label>
                            <div class="symbol-grid">
                                <div class="symbol-item" onclick="miniWord.insertSymbol('→')" title="Right Arrow">→ Right Arrow</div>
                                <div class="symbol-item" onclick="miniWord.insertSymbol('←')" title="Left Arrow">← Left Arrow</div>
                                <div class="symbol-item" onclick="miniWord.insertSymbol('↑')" title="Up Arrow">↑ Up Arrow</div>
                                <div class="symbol-item" onclick="miniWord.insertSymbol('↓')" title="Down Arrow">↓ Down Arrow</div>
                                <div class="symbol-item" onclick="miniWord.insertSymbol('★')" title="Star">★ Star</div>
                                <div class="symbol-item" onclick="miniWord.insertSymbol('♥')" title="Heart">♥ Heart</div>
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('insert')">Back to Insert</button>
                        </div>
                    </div>
                `
            },
            
            'strikethrough': {
                title: 'Strikethrough Format',
                content: `
                    <div class="page-content">
                        <h2>Strikethrough Format</h2>
                        <p>Add strikethrough to selected text</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.toggleStrikethrough()">Apply Strikethrough</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'highlight': {
                title: 'Highlight Display',
                content: `
                    <div class="page-content">
                        <h2>Highlight Display</h2>
                        <p>Add highlight background to selected text</p>
                        <div class="form-group">
                            <label>Highlight Color:</label>
                            <input type="color" id="highlight-color" value="#ffff00" style="width: 60px; height: 40px; border: 2px solid #ccc; border-radius: 4px;">
                        </div>
                        <div class="color-palette" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0;">
                            <div class="color-option" style="background-color: #ffff00; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ffff00" onclick="document.getElementById('highlight-color').value='#ffff00'; miniWord.applyHighlightDirect('#ffff00');"></div>
                            <div class="color-option" style="background-color: #ffcccc; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ffcccc" onclick="document.getElementById('highlight-color').value='#ffcccc'; miniWord.applyHighlightDirect('#ffcccc');"></div>
                            <div class="color-option" style="background-color: #ccffcc; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ccffcc" onclick="document.getElementById('highlight-color').value='#ccffcc'; miniWord.applyHighlightDirect('#ccffcc');"></div>
                            <div class="color-option" style="background-color: #ccccff; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ccccff" onclick="document.getElementById('highlight-color').value='#ccccff'; miniWord.applyHighlightDirect('#ccccff');"></div>
                            <div class="color-option" style="background-color: #ffffcc; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ffffcc" onclick="document.getElementById('highlight-color').value='#ffffcc'; miniWord.applyHighlightDirect('#ffffcc');"></div>
                            <div class="color-option" style="background-color: #ffccff; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ffccff" onclick="document.getElementById('highlight-color').value='#ffccff'; miniWord.applyHighlightDirect('#ffccff');"></div>
                            <div class="color-option" style="background-color: #ccffff; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#ccffff" onclick="document.getElementById('highlight-color').value='#ccffff'; miniWord.applyHighlightDirect('#ccffff');"></div>
                            <div class="color-option" style="background-color: #f0f0f0; width: 40px; height: 40px; border: 2px solid #ccc; border-radius: 4px; cursor: pointer;" data-color="#f0f0f0" onclick="document.getElementById('highlight-color').value='#f0f0f0'; miniWord.applyHighlightDirect('#f0f0f0');"></div>
                        </div>
                        <div class="button-group" style="margin-top: 20px;">
                            <button class="btn btn-primary" onclick="miniWord.applyHighlight()" style="background-color: #28a745; color: white; padding: 12px 24px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-right: 10px;">🖍️ Apply Highlight</button>
                            <button class="btn" onclick="miniWord.showPage('format')" style="background-color: #6c757d; color: white; padding: 12px 24px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;">Back to Format</button>
                        </div>
                        <div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; font-size: 14px; color: #666;">
                            <strong>Usage Instructions:</strong><br>
                            1. First select the text you want to highlight in the editor<br>
                            2. Choose highlight color (click color squares or use color picker)<br>
                            3. Click "Apply Highlight" button
                        </div>
                    </div>
                `
            },
            
            'format_painter': {
                title: 'Format Painter',
                content: `
                    <div class="page-content">
                        <h2>Format Painter</h2>
                        <p>Copy format and apply to other text</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.activateFormatPainter()">Activate Format Painter</button>
                            <button class="btn btn-primary" onclick="miniWord.applyFormatPainter()">Apply Format Painter</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'clear_format': {
                title: 'Clear Format',
                content: `
                    <div class="page-content">
                        <h2>Clear Format</h2>
                        <p>Clear all formatting from selected text</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.clearFormat()">Clear Format</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'align_left': {
                title: 'Left Align',
                content: `
                    <div class="page-content">
                        <h2>Left Align</h2>
                        <p>Left align selected text or paragraph</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.alignLeft()">Apply Left Align</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'align_center': {
                title: 'Center Align',
                content: `
                    <div class="page-content">
                        <h2>Center Align</h2>
                        <p>Center align selected text or paragraph</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.alignCenter()">Apply Center Align</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'align_right': {
                title: 'Right Align',
                content: `
                    <div class="page-content">
                        <h2>Right Align</h2>
                        <p>Right align selected text or paragraph</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.alignRight()">Apply Right Align</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'align_justify': {
                title: 'Justify Align',
                content: `
                    <div class="page-content">
                        <h2>Justify Align</h2>
                        <p>Justify align selected text or paragraph</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.alignJustify()">Apply Justify Align</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },
            
            'review_spelling': {
                title: 'Spell Check',
                content: `
                    <div class="page-content">
                        <h2>Spell Check</h2>
                        <p>Check spelling errors in document</p>
                        <div class="spelling-results">
                            <p>Checking spelling...</p>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.startSpellCheck()">Start Check</button>
                            <button class="btn" onclick="miniWord.showPage('tools')">Back to Tools</button>
                        </div>
                    </div>
                `
            },
            
            
            'review_comment': {
                title: 'New Comment',
                content: `
                    <div class="page-content">
                        <h2>Add Inline Comment</h2>
                        <p>Select text in the document and add a comment that will appear inline next to your selection.</p>
                        
                        <!-- Add New Comment -->
                        <div class="comment-form">
                            <h3>Comment Details</h3>
                            <div class="form-group">
                                <label>Comment Content:</label>
                                <textarea id="comment-text" rows="4" placeholder="Enter your comment here..." style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; resize: vertical;"></textarea>
                            </div>
                            <div class="form-group">
                                <label>Comment Author:</label>
                                <input type="text" id="comment-author" placeholder="Enter your name" value="Reviewer" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            </div>
                            <div class="form-group">
                                <label>Comment Priority:</label>
                                <select id="comment-priority" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                    <option value="low">Low Priority</option>
                                    <option value="normal" selected>Normal Priority</option>
                                    <option value="high">High Priority</option>
                                    <option value="urgent">Urgent</option>
                                </select>
                            </div>
                            <div class="button-group">
                                <button class="btn btn-primary" onclick="miniWord.addInlineComment()">Add Comment to Selected Text</button>
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('tools')">Back to Tools</button>
                        </div>
                    </div>
                `
            },
            
            'bulleted_list': {
                title: 'Bulleted List',
                content: `
                    <div class="page-content">
                        <h2>Bulleted List</h2>
                        <p>Add bullet points to your text. Place your cursor before any text and click the bullet button to add bullet points.</p>
                        
                        
                        
                        <!-- List Management -->
                        <div class="list-management">
                            <h3>List Management</h3>
                            <div class="button-group">
                                <button class="btn btn-primary" onclick="miniWord.insertBulletedList()">Add Bullet</button>
                            </div>
                        </div>
                        
                        
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('tools')">Back to Tools</button>
                        </div>
                    </div>
                `
            },
            
            'numbered_list': {
                title: 'Numbered List',
                content: `
                    <div class="page-content">
                        <h2>Numbered List</h2>
                        <p>Add numbered lists to your text. Place your cursor before any text and click the number button to add numbered lists.</p>
                        
                        
                        
                        <!-- List Management -->
                        <div class="list-management">
                            <h3>List Management</h3>
                            <div class="button-group">
                                <button class="btn btn-primary" onclick="miniWord.insertNumberedList()">Add Number</button>
                            </div>
                        </div>
                        
                        
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('tools')">Back to Tools</button>
                        </div>
                    </div>
                `
            },
            
            'indent_increase': {
                title: 'Increase Indent',
                content: `
                    <div class="page-content">
                        <h2>Increase Indent</h2>
                        <p>Increase paragraph indentation</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.increaseIndent()">Increase Indent</button>
                            <button class="btn" onclick="miniWord.showPage('tools')">Back to Tools</button>
                        </div>
                    </div>
                `
            },
            
            'indent_decrease': {
                title: 'Decrease Indent',
                content: `
                    <div class="page-content">
                        <h2>Decrease Indent</h2>
                        <p>Decrease paragraph indentation</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.decreaseIndent()">Decrease Indent</button>
                            <button class="btn" onclick="miniWord.showPage('tools')">Back to Tools</button>
                        </div>
                    </div>
                `
            },
            
            'app_settings': {
                title: 'Application Settings',
                content: `
                    <div class="page-content">
                        <h2>Application Settings</h2>
                        <p>Configure various MiniWord options</p>
                        <div class="form-group">
                            <label>Default Font:</label>
                            <select id="default-font-family">
                                <option value="Arial">Arial</option>
                                <option value="Times New Roman">Times New Roman</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Default Font Size:</label>
                            <select id="default-font-size">
                                <option value="12">12px</option>
                                <option value="14">14px</option>
                                <option value="16">16px</option>
                                <option value="18">18px</option>
                                <option value="20">20px</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.applyDefaultFont()">Apply Default Font</button>
                            <button class="btn btn-primary" onclick="miniWord.saveSettings()">Save Settings</button>
                            <button class="btn" onclick="miniWord.showPage('help')">Back to Help</button>
                        </div>
                    </div>
                `
            },
            
            
            'layout_page_break': {
                title: 'Page Break',
                content: `
                    <div class="page-content">
                        <h2>Page Break</h2>
                        <p>Insert page break in document</p>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.insertPageBreak()">Insert Page Break</button>
                            <button class="btn" onclick="miniWord.showPage('help')">Back to Help</button>
                        </div>
                    </div>
                `
            },
            
            // New feature page - Advanced Editing Features
            'advanced_edit': {
                title: 'Advanced Editing',
                content: `
                    <div class="page-content">
                        <h2>Advanced Editing Features</h2>
                        <p>Provide more powerful document editing tools</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('word_count')">
                                <img src="miniword_buttons_png/review_spelling.png" alt="Word Count">
                                <h4>Word Count</h4>
                                <p>Count document words, paragraphs, etc.</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('document_properties')">
                                <img src="miniword_buttons_png/app_settings.png" alt="Document Properties">
                                <h4>Document Properties</h4>
                                <p>View and edit document properties</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('document_history')">
                                <img src="miniword_buttons_png/review_track.png" alt="Document History">
                                <h4>Document History</h4>
                                <p>View document modification history</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'word_count': {
                title: 'Word Count',
                content: `
                    <div class="page-content">
                        <h2>Word Count</h2>
                        <p>Count document detailed information</p>
                        <div class="stats-container">
                            <div class="stat-item">
                                <span class="stat-label">Total Words:</span>
                                <span class="stat-value" id="total-words">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Paragraphs:</span>
                                <span class="stat-value" id="paragraph-count">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Lines:</span>
                                <span class="stat-value" id="line-count">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Characters (no spaces):</span>
                                <span class="stat-value" id="char-count-no-spaces">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Characters (with spaces):</span>
                                <span class="stat-value" id="char-count-with-spaces">0</span>
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.updateWordCount()">Refresh Statistics</button>
                            <button class="btn" onclick="miniWord.showPage('advanced_edit')">Back to Advanced Editing</button>
                        </div>
                    </div>
                `
            },
            
            'document_properties': {
                title: 'Document Properties',
                content: `
                    <div class="page-content">
                        <h2>Document Properties</h2>
                        <p>View and edit document basic information</p>
                        <div class="form-group">
                            <label>Document Title:</label>
                            <input type="text" id="doc-title" placeholder="Enter document title">
                        </div>
                        <div class="form-group">
                            <label>Author:</label>
                            <input type="text" id="doc-author" placeholder="Enter author name">
                        </div>
                        <div class="form-group">
                            <label>Subject:</label>
                            <input type="text" id="doc-subject" placeholder="Enter document subject">
                        </div>
                        <div class="form-group">
                            <label>Keywords:</label>
                            <input type="text" id="doc-keywords" placeholder="Enter keywords, separated by commas">
                        </div>
                        <div class="form-group">
                            <label>Comments:</label>
                            <textarea id="doc-comments" rows="3" placeholder="Enter document comments"></textarea>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.saveDocumentProperties()">Save Properties</button>
                            <button class="btn" onclick="miniWord.showPage('advanced_edit')">Back to Advanced Editing</button>
                        </div>
                    </div>
                `
            },
            
            
            'document_history': {
                title: 'Document History',
                content: `
                    <div class="page-content">
                        <h2>Document History</h2>
                        <p>View document modification history</p>
                        <div class="history-list">
                            <div class="history-item">
                                <span class="history-time">2025-09-19 15:10:30</span>
                                <span class="history-action">Create Document</span>
                            </div>
                            <div class="history-item">
                                <span class="history-time">2025-09-19 15:12:45</span>
                                <span class="history-action">Add Text Content</span>
                            </div>
                            <div class="history-item">
                                <span class="history-time">2025-09-19 15:15:20</span>
                                <span class="history-action">Apply Bold Format</span>
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.refreshHistory()">Refresh History</button>
                            <button class="btn" onclick="miniWord.showPage('advanced_edit')">Back to Advanced Editing</button>
                        </div>
                    </div>
                `
            },
            
            // New feature page - Collaboration Features
            'collaboration': {
                title: 'Collaboration Features',
                content: `
                    <div class="page-content">
                        <h2>Collaboration Features</h2>
                        <p>Collaborate with others to edit documents</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.showPage('share_document')">
                                <img src="miniword_buttons_png/file_open.png" alt="Share Document">
                                <h4>Share Document</h4>
                                <p>Generate share link, invite others to collaborate</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('comments')">
                                <img src="miniword_buttons_png/review_comment.png" alt="Comments">
                                <h4>Comment System</h4>
                                <p>Add and manage document comments</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('version_control')">
                                <img src="miniword_buttons_png/review_track.png" alt="Version Control">
                                <h4>Version Control</h4>
                                <p>Manage different document versions</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.showPage('real_time_edit')">
                                <img src="miniword_buttons_png/edit_paste.png" alt="Real-time Editing">
                                <h4>Real-time Editing</h4>
                                <p>Multiple people edit document simultaneously</p>
                            </div>
                        </div>
                    </div>
                `
            },
            
            'share_document': {
                title: 'Share Document',
                content: `
                    <div class="page-content">
                        <h2>Share Document</h2>
                        <p>Generate share link, invite others to collaborate</p>
                        <div class="form-group">
                            <label>Share Permissions:</label>
                            <select id="share-permission">
                                <option value="view">View Only</option>
                                <option value="comment">View + Comment</option>
                                <option value="edit">Edit Permission</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Share Link:</label>
                            <div class="link-container">
                                <input type="text" id="share-link" readonly value="https://miniword.com/share/abc123">
                                <button class="btn btn-small" onclick="miniWord.copyShareLink()">Copy</button>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Validity Period:</label>
                            <select id="link-expiry">
                                <option value="1">1 day</option>
                                <option value="7">7 days</option>
                                <option value="30">30 days</option>
                                <option value="never">Never Expires</option>
                            </select>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.generateShareLink()">Generate New Link</button>
                            <button class="btn" onclick="miniWord.showPage('collaboration')">Back to Collaboration</button>
                        </div>
                    </div>
                `
            },
            
            'comments': {
                title: 'Comment System',
                content: `
                    <div class="page-content">
                        <h2>Comment System</h2>
                        <p>Manage all comments in document</p>
                        <div class="comments-list">
                            <div class="comment-item">
                                <div class="comment-header">
                                    <span class="comment-author">John Doe</span>
                                    <span class="comment-time">2 hours ago</span>
                                </div>
                                <div class="comment-content">Need to add more detailed explanation here</div>
                                <div class="comment-actions">
                                    <button class="btn btn-small">Reply</button>
                                    <button class="btn btn-small">Resolve</button>
                                </div>
                            </div>
                            <div class="comment-item">
                                <div class="comment-header">
                                    <span class="comment-author">Jane Smith</span>
                                    <span class="comment-time">1 hour ago</span>
                                </div>
                                <div class="comment-content">Suggest modifying the format of this paragraph</div>
                                <div class="comment-actions">
                                    <button class="btn btn-small">Reply</button>
                                    <button class="btn btn-small">Resolve</button>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Add New Comment:</label>
                            <textarea id="new-comment" rows="3" placeholder="Enter comment content..."></textarea>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.addComment()">Add Comment</button>
                            <button class="btn" onclick="miniWord.showPage('collaboration')">Back to Collaboration</button>
                        </div>
                    </div>
                `
            },
            
            'version_control': {
                title: 'Version Control',
                content: `
                    <div class="page-content">
                        <h2>Version Control</h2>
                        <p>Manage different document versions</p>
                        <div class="version-list">
                            <div class="version-item current">
                                <span class="version-name">v1.3 (Current Version)</span>
                                <span class="version-time">2025-09-19 15:20</span>
                                <span class="version-author">You</span>
                                <button class="btn btn-small">Restore</button>
                            </div>
                            <div class="version-item">
                                <span class="version-name">v1.2</span>
                                <span class="version-time">2025-09-19 14:30</span>
                                <span class="version-author">John Doe</span>
                                <button class="btn btn-small">Restore</button>
                            </div>
                            <div class="version-item">
                                <span class="version-name">v1.1</span>
                                <span class="version-time">2025-09-19 13:45</span>
                                <span class="version-author">Jane Smith</span>
                                <button class="btn btn-small">Restore</button>
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.createVersion()">Create New Version</button>
                            <button class="btn" onclick="miniWord.showPage('collaboration')">Back to Collaboration</button>
                        </div>
                    </div>
                `
            },
            
            'real_time_edit': {
                title: 'Real-time Editing',
                content: `
                    <div class="page-content">
                        <h2>Real-time Editing</h2>
                        <p>Multiple people edit document simultaneously</p>
                        <div class="online-users">
                            <h3>Online Users</h3>
                            <div class="user-list">
                                <div class="user-item">
                                    <span class="user-avatar">👤</span>
                                    <span class="user-name">You</span>
                                    <span class="user-status online">Online</span>
                                </div>
                                <div class="user-item">
                                    <span class="user-avatar">👤</span>
                                    <span class="user-name">John Doe</span>
                                    <span class="user-status online">Online</span>
                                </div>
                                <div class="user-item">
                                    <span class="user-avatar">👤</span>
                                    <span class="user-name">Jane Smith</span>
                                    <span class="user-status editing">Editing</span>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="enable-realtime"> Enable Real-time Editing
                            </label>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.toggleRealtimeEdit()">Toggle Real-time Editing</button>
                            <button class="btn" onclick="miniWord.showPage('collaboration')">Back to Collaboration</button>
                        </div>
                    </div>
                `
            },
            
            // New feature pages - Template functionality
            'templates': {
                title: 'Document Templates',
                content: `
                    <div class="page-content">
                        <h2>Document Templates</h2>
                        <p>Use predefined templates to quickly create documents</p>
                        <div class="template-grid">
                            <div class="template-card" onclick="miniWord.loadTemplate('business-letter')">
                                <img src="miniword_buttons_png/file_new.png" alt="Business Letter">
                                <h4>Business Letter</h4>
                                <p>Professional business letter template</p>
                            </div>
                            <div class="template-card" onclick="miniWord.loadTemplate('resume')">
                                <img src="miniword_buttons_png/file_new.png" alt="Resume">
                                <h4>Personal Resume</h4>
                                <p>Standard format resume template</p>
                            </div>
                            <div class="template-card" onclick="miniWord.loadTemplate('report')">
                                <img src="miniword_buttons_png/file_new.png" alt="Report">
                                <h4>Project Report</h4>
                                <p>Structured project report template</p>
                            </div>
                            <div class="template-card" onclick="miniWord.loadTemplate('memo')">
                                <img src="miniword_buttons_png/file_new.png" alt="Memo">
                                <h4>Internal Memo</h4>
                                <p>Company internal memo template</p>
                            </div>
                            <div class="template-card" onclick="miniWord.loadTemplate('newsletter')">
                                <img src="miniword_buttons_png/file_new.png" alt="Press Release">
                                <h4>Press Release</h4>
                                <p>Press release template</p>
                            </div>
                            <div class="template-card" onclick="miniWord.loadTemplate('invoice')">
                                <img src="miniword_buttons_png/file_new.png" alt="Invoice">
                                <h4>Invoice</h4>
                                <p>Standard invoice format template</p>
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.createCustomTemplate()">Create Custom Template</button>
                            <button class="btn" onclick="miniWord.showPage('file')">Back to File</button>
                        </div>
                    </div>
                `
            },
            
            // New feature pages - Export functionality
            'export_options': {
                title: 'Export Options',
                content: `
                    <div class="page-content">
                        <h2>Export Options</h2>
                        <p>Export document to different formats</p>
                        <div class="export-grid">
                            <div class="export-card" onclick="miniWord.exportDocument('pdf')">
                                <img src="miniword_buttons_png/file_print.png" alt="PDF">
                                <h4>PDF Document</h4>
                                <p>Export as PDF format</p>
                            </div>
                            <div class="export-card" onclick="miniWord.exportDocument('docx')">
                                <img src="miniword_buttons_png/file_save.png" alt="Word">
                                <h4>Word Document</h4>
                                <p>Export as .docx format</p>
                            </div>
                            <div class="export-card" onclick="miniWord.exportDocument('html')">
                                <img src="miniword_buttons_png/insert_link.png" alt="HTML">
                                <h4>HTML Web Page</h4>
                                <p>Export as HTML format</p>
                            </div>
                            <div class="export-card" onclick="miniWord.exportDocument('txt')">
                                <img src="miniword_buttons_png/file_new.png" alt="Plain Text">
                                <h4>Plain Text</h4>
                                <p>Export as .txt format</p>
                            </div>
                            <div class="export-card" onclick="miniWord.exportDocument('rtf')">
                                <img src="miniword_buttons_png/file_save.png" alt="RTF">
                                <h4>RTF Format</h4>
                                <p>Export as RTF format</p>
                            </div>
                            <div class="export-card" onclick="miniWord.exportDocument('odt')">
                                <img src="miniword_buttons_png/file_save.png" alt="OpenDocument">
                                <h4>OpenDocument</h4>
                                <p>Export as .odt format</p>
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('file')">Back to File</button>
                        </div>
                    </div>
                `
            },

            // New icon page definitions
            'mw2_clear_all': {
                title: 'Clear All Formatting',
                content: `
                    <div class="page-content">
                        <h2>Clear All Formatting</h2>
                        <p>Remove all formatting from selected text, including font, color, size, etc.</p>
                        <div class="feature-info">
                            <h3>How to use:</h3>
                            <ol>
                                <li>Select the text you want to clear formatting from</li>
                                <li>Click "Clear Selected Text Formatting" or press <strong>Ctrl+K</strong></li>
                                <li>Or click "Clear Entire Document" to remove all formatting</li>
                            </ol>
                        </div>
                        <div class="warning-box">
                            <strong>Note:</strong> This action cannot be undone. Make sure to save your document first.
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.clearAllFormatting()">Clear Selected Text Formatting</button>
                            <button class="btn btn-danger" onclick="miniWord.clearAllDocumentFormatting()">Clear Entire Document</button>
                        </div>
                    </div>
                `
            },

            'mw2_format_painter': {
                title: 'Format Painter',
                content: `
                    <div class="page-content">
                        <h2>Format Painter</h2>
                        <p>Copy comprehensive formatting from one text and apply it to another</p>
                        <div class="feature-info">
                            <h3>How to use:</h3>
                            <ol>
                                <li><strong>Select source text</strong> with the formatting you want to copy</li>
                                <li><strong>Click "Copy Format"</strong> or press <strong>Ctrl+J</strong></li>
                                <li><strong>Select target text</strong> where you want to apply the formatting</li>
                                <li><strong>Click "Apply Format"</strong> to paste the formatting</li>
                            </ol>
                            <div class="tip-box">
                                <strong>Tip:</strong> The Format Painter stays active until you apply formatting or deactivate it manually.
                            </div>
                        </div>
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.activateFormatPainter()">Copy Format</button>
                            <button class="btn btn-success" onclick="miniWord.applyFormatPainter()">Apply Format</button>
                            <button class="btn btn-secondary" onclick="miniWord.deactivateFormatPainter()">Deactivate</button>
                        </div>
                    </div>
                `
            },

            'mw2_sidebar_toggle': {
                title: 'Toggle Sidebar',
                content: `
                    <div class="page-content">
                        <h2>Toggle Sidebar</h2>
                        <p>Show or hide left function panel</p>
                        <div class="feature-info">
                            <h3>Feature Description:</h3>
                            <ul>
                                <li>Toggle sidebar display status</li>
                                <li>Provide more space for editing area</li>
                                <li>Quick access to function panel</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.toggleSidebar()">Toggle Sidebar</button>
                        </div>
                    </div>
                `
            },

            'mw2_ruler_toggle': {
                title: 'Toggle Ruler',
                content: `
                    <div class="page-content">
                        <h2>Toggle Ruler</h2>
                        <p>Show or hide page ruler</p>
                        <div class="feature-info">
                            <h3>Feature Description:</h3>
                            <ul>
                                <li>Display horizontal and vertical rulers</li>
                                <li>Help precisely adjust page layout</li>
                                <li>Set margins and indentation</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.toggleRuler()">Toggle Ruler</button>
                        </div>
                    </div>
                `
            },

            'mw2_show_invisibles': {
                title: 'Show Hidden Characters',
                content: `
                    <div class="page-content">
                        <h2>Show Hidden Characters</h2>
                        <p>Show hidden characters in document, such as spaces, tabs, paragraph marks, etc.</p>
                        <div class="feature-info">
                            <h3>Displayable Content:</h3>
                            <ul>
                                <li>Space characters (·)</li>
                                <li>Tab characters (→)</li>
                                <li>Paragraph marks (¶)</li>
                                <li>Line breaks</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.toggleInvisibles()">Toggle Hidden Characters</button>
                        </div>
                    </div>
                `
            },

            'mw2_focus_mode': {
                title: 'Focus Mode',
                content: `
                    <div class="page-content">
                        <h2>Focus Mode</h2>
                        <p>Hide all distracting elements, focus on document editing</p>
                        <div class="feature-info">
                            <h3>Focus Mode Features:</h3>
                            <ul>
                                <li>Hide toolbar and menu</li>
                                <li>Highlight editing area</li>
                                <li>Reduce visual distractions</li>
                                <li>Improve writing efficiency</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.toggleFocusMode()">Toggle Focus Mode</button>
                        </div>
                    </div>
                `
            },

            'mw2_night_mode': {
                title: 'Night Mode',
                content: `
                    <div class="page-content">
                        <h2>Night Mode</h2>
                        <p>Switch to dark theme to protect eyes</p>
                        <div class="feature-info">
                            <h3>Night Mode Features:</h3>
                            <ul>
                                <li>Dark background, light text</li>
                                <li>Reduce blue light radiation</li>
                                <li>Suitable for night use</li>
                                <li>Customizable color scheme</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.toggleNightMode()">Toggle Night Mode</button>
                        </div>
                    </div>
                `
            },

            'mw2_section_break': {
                title: 'Section Break',
                content: `
                    <div class="page-content">
                        <h2>Section Break</h2>
                        <p>Insert section break in document for different page settings</p>
                        <div class="feature-info">
                            <h3>Section Break Types:</h3>
                            <ul>
                                <li>Next Page Section Break</li>
                                <li>Continuous Section Break</li>
                                <li>Even Page Section Break</li>
                                <li>Odd Page Section Break</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.insertSectionBreak()">Insert Section Break</button>
                        </div>
                    </div>
                `
            },

            'mw2_template_library': {
                title: 'Template Library',
                content: `
                    <div class="page-content">
                        <h2>Template Library</h2>
                        <p>Create new documents from preset templates</p>
                        <div class="feature-grid">
                            <div class="feature-card" onclick="miniWord.createFromTemplate('letter')">
                                <h4>Business Letter</h4>
                                <p>Standard business letter template</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.createFromTemplate('report')">
                                <h4>Report</h4>
                                <p>Professional report template</p>
                            </div>
                            <div class="feature-card" onclick="miniWord.createFromTemplate('resume')">
                                <h4>Resume</h4>
                                <p>Personal resume template</p>
                            </div>
                        </div>
                    </div>
                `
            },

            'mw2_superscript': {
                title: 'Superscript',
                content: `
                    <div class="page-content">
                        <h2>Superscript</h2>
                        <p>Set selected text to superscript format</p>
                        <div class="feature-info">
                            <h3>Usage Scenarios:</h3>
                            <ul>
                                <li>Mathematical formulas (x², x³)</li>
                                <li>Chemical symbols (H₂O)</li>
                                <li>Footnote markers</li>
                                <li>Copyright symbols</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.applySuperscript()">Apply Superscript</button>
                        </div>
                    </div>
                `
            },

            'mw2_subscript': {
                title: 'Subscript',
                content: `
                    <div class="page-content">
                        <h2>Subscript</h2>
                        <p>Set selected text to subscript format</p>
                        <div class="feature-info">
                            <h3>Usage Scenarios:</h3>
                            <ul>
                                <li>Chemical formulas (H₂O, CO₂)</li>
                                <li>Mathematical formulas (x₁, x₂)</li>
                                <li>Scientific symbols</li>
                                <li>Variable markers</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.applySubscript()">Apply Subscript</button>
                        </div>
                    </div>
                `
            },

            'mw2_line_spacing': {
                title: 'Line Spacing',
                content: `
                    <div class="page-content">
                        <h2>Line Spacing</h2>
                        <p>Adjust spacing between text lines</p>
                        <div class="feature-info">
                            <h3>Line Spacing Options:</h3>
                            <ul>
                                <li>Double line spacing (2.0x)</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.setLineSpacing(2)">Double (2.0x)</button>
                        </div>
                    </div>
                `
            },


            'mw2_page_setup': {
                title: 'Page Setup',
                content: `
                    <div class="page-content">
                        <h2>Page Setup</h2>
                        <p>Set document page layout</p>
                        
                        <div class="page-setup-container">
                            <div class="setup-section">
                                <h3>Page Size:</h3>
                                <select id="page-size" class="page-size-select">
                                    <option value="A4">A4 (210 × 297 mm)</option>
                                    <option value="A3">A3 (297 × 420 mm)</option>
                                    <option value="Letter">Letter (8.5 × 11 in)</option>
                                    <option value="Legal">Legal (8.5 × 14 in)</option>
                                    <option value="A5">A5 (148 × 210 mm)</option>
                                    <option value="B4">B4 (250 × 353 mm)</option>
                                </select>
                            </div>
                            
                            <div class="setup-section">
                                <h3>Margins (cm):</h3>
                                <div class="margins-grid">
                                    <div class="margin-input">
                                        <label for="margin-top">Top:</label>
                                        <input type="number" id="margin-top" step="0.1" min="0" max="10" value="2.54">
                                    </div>
                                    <div class="margin-input">
                                        <label for="margin-bottom">Bottom:</label>
                                        <input type="number" id="margin-bottom" step="0.1" min="0" max="10" value="2.54">
                                    </div>
                                    <div class="margin-input">
                                        <label for="margin-left">Left:</label>
                                        <input type="number" id="margin-left" step="0.1" min="0" max="10" value="3.18">
                                    </div>
                                    <div class="margin-input">
                                        <label for="margin-right">Right:</label>
                                        <input type="number" id="margin-right" step="0.1" min="0" max="10" value="3.18">
                                    </div>
                                </div>
                                <div class="margin-presets">
                                    <button type="button" class="preset-btn" onclick="miniWord.setMarginPreset('normal')">Normal</button>
                                    <button type="button" class="preset-btn" onclick="miniWord.setMarginPreset('narrow')">Narrow</button>
                                    <button type="button" class="preset-btn" onclick="miniWord.setMarginPreset('wide')">Wide</button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn btn-primary" onclick="miniWord.applyPageSetup()">Apply Settings</button>
                            <button class="btn btn-secondary" onclick="miniWord.resetPageSetup()">Reset to Default</button>
                            <button class="btn" onclick="miniWord.showPage('format')">Back to Format</button>
                        </div>
                    </div>
                `
            },



            'mw2_header_footer': {
                title: 'Header & Footer',
                content: `
                    <div class="page-content">
                        <h2>Header & Footer</h2>
                        <p>Edit header and footer content</p>
                        <div class="feature-info">
                            <h3>Header & Footer Features:</h3>
                            <ul>
                                <li>Add page numbers</li>
                                <li>Insert date and time</li>
                                <li>Add document title</li>
                                <li>Custom header and footer</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.editHeader()">Edit Header</button>
                            <button class="btn" onclick="miniWord.editFooter()">Edit Footer</button>
                        </div>
                    </div>
                `
            },


            'mw2_char_count': {
                title: 'Character Count',
                content: `
                    <div class="page-content">
                        <h2>Character Count</h2>
                        <p>Display detailed character statistics</p>
                        <div class="feature-info">
                            <h3>Character Count Includes:</h3>
                            <ul>
                                <li>Total characters (with spaces)</li>
                                <li>Character count (without spaces)</li>
                                <li>Chinese character count</li>
                                <li>English character count</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showCharCount()">Show Character Count</button>
                        </div>
                    </div>
                `
            },





            'mw2_share': {
                title: 'Share Document',
                content: `
                    <div class="page-content">
                        <h2>Share Document</h2>
                        <p>Share your document with others for collaboration and review</p>
                        
                        <!-- Share Link Generation -->
                        <div class="share-link-section">
                            <h3>Generate Share Link</h3>
                        <div class="button-group">
                                <button class="btn btn-primary" onclick="miniWord.generateShareLink()">Generate Link</button>
                        </div>
                            <div id="share-link-display" class="share-link-display" style="display: none;">
                                <h4>Share Link:</h4>
                                <div class="link-container">
                                    <input type="text" id="generated-link" readonly>
                                    <button class="btn btn-sm" onclick="miniWord.copyToClipboard('generated-link')">Copy</button>
                    </div>
                        </div>
                        </div>
                        
                        <!-- Social Media Sharing -->
                        <div class="social-sharing">
                            <h3>Social Media Sharing</h3>
                            <div class="social-buttons">
                                <button class="btn btn-social twitter" onclick="miniWord.shareToTwitter()">🐦 Twitter</button>
                                <button class="btn btn-social facebook" onclick="miniWord.shareToFacebook()">📘 Facebook</button>
                                <button class="btn btn-social linkedin" onclick="miniWord.shareToLinkedIn()">💼 LinkedIn</button>
                                <button class="btn btn-social whatsapp" onclick="miniWord.shareToWhatsApp()">💬 WhatsApp</button>
                        </div>
                        </div>
                        
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.showPage('help')">Back to Help</button>
                        </div>
                    </div>
                `
            },

            // Submenu pages
            'copy_plain': {
                title: 'Direct Copy',
                content: `
                    <div class="page-content">
                        <h2>Direct Copy</h2>
                        <p>Copy selected text without formatting</p>
                        <div class="feature-info">
                            <h3>Feature Description:</h3>
                            <ul>
                                <li>Copy plain text content</li>
                                <li>No formatting information included</li>
                                <li>Suitable for pasting into plain text editors</li>
                                <li>Reduce file size</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.copyPlainText()">Copy Plain Text</button>
                        </div>
                    </div>
                `
            },

            'copy_formatted': {
                title: 'Formatted Copy',
                content: `
                    <div class="page-content">
                        <h2>Formatted Copy</h2>
                        <p>Copy selected text with all formatting</p>
                        <div class="feature-info">
                            <h3>Feature Description:</h3>
                            <ul>
                                <li>Preserve font, color, size and other formatting</li>
                                <li>Maintain paragraph formatting</li>
                                <li>Suitable for pasting into other document editors</li>
                                <li>Maintain original appearance</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.copyFormattedText()">Copy Formatted Text</button>
                        </div>
                    </div>
                `
            },

            'table_insert': {
                title: 'Insert Table',
                content: `
                    <div class="page-content">
                        <h2>Insert Table</h2>
                        <p>Insert new table in document</p>
                        <div class="feature-info">
                            <h3>Table Options:</h3>
                            <ul>
                                <li>Select number of rows and columns</li>
                                <li>Set table style</li>
                                <li>Auto-adjust column width</li>
                                <li>Add table title</li>
                            </ul>
                        </div>
                        <div class="form-group">
                            <label>Select Table Size:</label>
                            <div class="table-preview" id="table-preview"></div>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.insertTable()">Insert Table</button>
                        </div>
                    </div>
                `
            },

            'table_merge': {
                title: 'Merge Cells',
                content: `
                    <div class="page-content">
                        <h2>Merge Cells</h2>
                        <p>Merge selected table cells into one</p>
                        <div class="feature-info">
                            <h3>Merge Features:</h3>
                            <ul>
                                <li>Horizontal cell merge</li>
                                <li>Vertical cell merge</li>
                                <li>Merge multiple cells</li>
                                <li>Maintain content format</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.mergeCells()">Merge Cells</button>
                        </div>
                    </div>
                `
            },

            'table_split': {
                title: 'Split Cells',
                content: `
                    <div class="page-content">
                        <h2>Split Cells</h2>
                        <p>Split selected cell into multiple cells</p>
                        <div class="feature-info">
                            <h3>Split Features:</h3>
                            <ul>
                                <li>Horizontal cell split</li>
                                <li>Vertical cell split</li>
                                <li>Specify split count</li>
                                <li>Maintain original content</li>
                            </ul>
                        </div>
                        <div class="button-group">
                            <button class="btn" onclick="miniWord.splitCells()">Split Cells</button>
                        </div>
                    </div>
                `
            }
        };
        
        // If page not found, try to get button info and create dynamic page
        if (!pages[pageId]) {
            const button = document.querySelector(`[data-page="${pageId}"]`);
            if (button) {
                const buttonTitle = button.getAttribute('title') || 'Function';
                const buttonIcon = button.querySelector('img');
                const iconSrc = buttonIcon ? buttonIcon.src : '';
                const iconAlt = buttonIcon ? buttonIcon.alt : '';
                
                return {
                    title: buttonTitle || 'Function',
                    content: `
                        <div class="page-content">
                            <h2>${buttonTitle || 'Function'}</h2>
                            <div style="text-align: center; margin: 20px 0;">
                                ${iconSrc ? `<img src="${iconSrc}" alt="${iconAlt}" style="width: 64px; height: 64px; margin-bottom: 16px;">` : ''}
                            </div>
                            <p>This function is available through the toolbar button.</p>
                            <div class="feature-info">
                                <h3>How to use:</h3>
                                <ul>
                                    <li>Click the corresponding button in the toolbar</li>
                                    <li>Follow the on-screen instructions</li>
                                    <li>Use keyboard shortcuts if available</li>
                                </ul>
                            </div>
                            <div class="button-group">
                                <button class="btn" onclick="miniWord.showPage('home')">Back to Home</button>
                            </div>
                        </div>
                    `
                };
            }
        }
        
        return pages[pageId] || {
            title: 'Page Not Found',
            content: '<div class="page-content"><p>Page not found</p></div>'
        };
    }
    
    bindPageEvents(pageId) {
        // Bind page-specific events
        switch (pageId) {
            case 'text_color':
                this.bindColorEvents();
                break;
            case 'insert_table':
                this.initTablePage();
                break;
            case 'insert_chart':
                this.initChartPage();
                break;
            case 'review_comment':
                this.bindCommentEvents();
                break;
        }
    }
    
    bindColorEvents() {
        document.querySelectorAll('.color-option').forEach(option => {
            option.addEventListener('click', () => {
                const color = option.dataset.color;
                document.execCommand('foreColor', false, color);
                this.showMessage(`Font color set to ${color}`);
            });
        });
    }

    bindCommentEvents() {
        // Add event listener for the clear button
        const clearBtn = document.getElementById('clear-comment-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearCommentForm();
            });
        }
        
        // Also add event listener for any clear button with onclick
        document.querySelectorAll('button[onclick*="clearCommentForm"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearCommentForm();
            });
        });
    }

    initTablePage() {
        // Initialize table size preview
        this.createTableSizePreview();
    }

    initChartPage() {
        console.log('initChartPage called'); // Debug log
        // Wait for DOM to be ready, then detect tables
        setTimeout(() => {
            console.log('initChartPage: Starting table detection...'); // Debug log
            this.detectTablesInDocument();
            this.setupChartModalEvents();
        }, 100);
    }
    
    showChartInsertModal() {
        const modal = document.getElementById('chart-insert-modal');
        modal.style.display = 'block';
        
        // Detect tables in document
        this.detectTablesInDocument();
        // Setup chart modal events
        this.setupChartModalEvents();
        
        // Initialize modal events
        this.initChartModalEvents();
    }
    
    closeChartModal() {
        const modal = document.getElementById('chart-insert-modal');
        modal.style.display = 'none';
    }
    
    initChartModalEvents() {
        const modal = document.getElementById('chart-insert-modal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeChartModal();
            }
        });
    }
    
    
    // Function implementation methods
    createNewDocument() {
        const title = document.getElementById('new-doc-title').value || 'Untitled Document';
        const docType = document.getElementById('new-doc-type').value;
        
        // Check if current document has unsaved changes
        if (this.currentDocument.modified) {
            const shouldProceed = confirm('You have unsaved changes. Are you sure you want to create a new document? All unsaved changes will be lost.');
            if (!shouldProceed) {
                return;
            }
        }
        
        // Clear current content
        this.editor.innerHTML = '';
        
        // Create content based on document type
        let content = '';
        switch (docType) {
            case 'letter':
                content = this.createBusinessLetterTemplate();
                break;
            case 'report':
                content = this.createReportTemplate();
                break;
            case 'memo':
                content = this.createMemoTemplate();
                break;
            case 'resume':
                content = this.createResumeTemplate();
                break;
            case 'newsletter':
                content = this.createNewsletterTemplate();
                break;
            case 'invoice':
                content = this.createInvoiceTemplate();
                break;
            default:
                content = 'Welcome to MiniWord! Start typing your document content...';
        }
        
        // Update document properties
        this.currentDocument.title = title;
        this.currentDocument.type = docType;
        this.currentDocument.modified = false;
        
        // Create paginated layout with the new content
        this.tempContent = this.parsePlainText(content);
        this.createPaginatedLayout();
        
        // Update status
        this.updateStatus();
        this.showMessage(`New ${docType} document "${title}" created successfully`);
        
        // Return to file menu
        this.showPage('file');
    }
    
    
    // Template creation functions
    createBusinessLetterTemplate() {
        return `[Your Name]
[Your Address]
[City, State ZIP Code]
[Your Email]
[Your Phone Number]
[Date]

[Recipient Name]
[Recipient Title]
[Company Name]
[Company Address]
[City, State ZIP Code]

Dear [Recipient Name],

I am writing to you regarding [subject of the letter]. 

[Body paragraph 1 - State the purpose of your letter clearly and concisely.]

[Body paragraph 2 - Provide supporting details, facts, or examples that support your main point.]

[Body paragraph 3 - If applicable, include any additional information or call to action.]

I look forward to hearing from you soon. Please feel free to contact me if you have any questions or need additional information.

Sincerely,

[Your Name]
[Your Title]`;
    }
    
    createReportTemplate() {
        return `[REPORT TITLE]

Prepared by: [Your Name]
Date: [Current Date]
Department: [Department Name]

EXECUTIVE SUMMARY

[Provide a brief overview of the report's main findings and recommendations.]

TABLE OF CONTENTS

1. Introduction
2. Methodology
3. Findings
4. Analysis
5. Recommendations
6. Conclusion

1. INTRODUCTION

[Describe the purpose of the report, the problem being addressed, and the scope of the investigation.]

2. METHODOLOGY

[Explain the methods used to gather data and conduct the analysis.]

3. FINDINGS

[Present the key findings from your research or investigation.]

4. ANALYSIS

[Analyze the findings and discuss their implications.]

5. RECOMMENDATIONS

[Provide specific, actionable recommendations based on your analysis.]

6. CONCLUSION

[Summarize the key points and restate the main recommendations.]

REFERENCES

[List any sources or references used in the report.]`;
    }
    
    createMemoTemplate() {
        return `MEMORANDUM

TO: [Recipient Name(s)]
FROM: [Your Name]
DATE: [Current Date]
SUBJECT: [Subject Line]

[Body of the memo - State the purpose clearly and provide necessary details.]

[If applicable, include any action items or next steps.]

[Closing remarks or call to action.]`;
    }
    
    createResumeTemplate() {
        return `[Your Full Name]
[Your Address]
[City, State ZIP Code]
[Your Email] | [Your Phone Number]

PROFESSIONAL SUMMARY

[Write a brief, compelling summary of your professional background and key qualifications.]

EXPERIENCE

[Job Title] | [Company Name] | [Dates of Employment]
[City, State]
• [Achievement or responsibility]
• [Achievement or responsibility]
• [Achievement or responsibility]

[Job Title] | [Company Name] | [Dates of Employment]
[City, State]
• [Achievement or responsibility]
• [Achievement or responsibility]
• [Achievement or responsibility]

EDUCATION

[Degree] | [Institution Name] | [Graduation Year]
[City, State]

SKILLS

• [Skill 1]
• [Skill 2]
• [Skill 3]
• [Skill 4]

CERTIFICATIONS

• [Certification 1] | [Issuing Organization] | [Date]
• [Certification 2] | [Issuing Organization] | [Date]`;
    }
    
    createNewsletterTemplate() {
        return `[NEWSLETTER TITLE]
Volume [X], Issue [X] | [Date]

TABLE OF CONTENTS

• [Article 1 Title] - Page 2
• [Article 2 Title] - Page 3
• [Article 3 Title] - Page 4
• [Upcoming Events] - Page 5

FEATURED STORY

[Article Title]

[Article content - Write engaging content for your featured story.]

OTHER STORIES

[Article 2 Title]

[Article 2 content]

[Article 3 Title]

[Article 3 content]

UPCOMING EVENTS

• [Event 1] - [Date] - [Location]
• [Event 2] - [Date] - [Location]
• [Event 3] - [Date] - [Location]

CONTACT INFORMATION

[Your Organization Name]
[Address]
[Phone Number]
[Email Address]
[Website]`;
    }
    
    createInvoiceTemplate() {
        return `INVOICE

Invoice #: [Invoice Number]
Date: [Invoice Date]
Due Date: [Due Date]

BILL TO:
[Client Name]
[Client Address]
[City, State ZIP Code]

FROM:
[Your Company Name]
[Your Address]
[City, State ZIP Code]
[Phone Number]
[Email Address]

DESCRIPTION OF SERVICES:

Item Description                    Quantity    Rate    Amount
─────────────────────────────────────────────────────────────
[Service/Product 1]                 [Qty]      $[Rate]  $[Amount]
[Service/Product 2]                 [Qty]      $[Rate]  $[Amount]
[Service/Product 3]                 [Qty]      $[Rate]  $[Amount]

SUBTOTAL:                          $[Subtotal]
TAX ([Tax Rate]%):                 $[Tax Amount]
TOTAL:                             $[Total Amount]

PAYMENT TERMS: [Payment terms, e.g., "Net 30 days"]

Thank you for your business!

[Your Name]
[Your Title]`;
    }
    
    openDocument() {
        const fileInput = document.getElementById('file-input');
        const contentInput = document.getElementById('content-input');
        
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            const fileExtension = file.name.split('.').pop().toLowerCase();
            
            // Check file size (limit to 10MB for performance)
            const maxSize = 10 * 1024 * 1024; // 10MB
            if (file.size > maxSize) {
                this.showMessage(`File is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum size is 10MB.`, 'error');
                return;
            }
            
            // Check if file type is supported
            if (!['txt', 'html', 'htm', 'md'].includes(fileExtension)) {
                this.showMessage(`File type .${fileExtension} is not supported. Please use .txt, .html, or .md files.`, 'error');
                return;
            }
            
            // Show loading message for large files
            if (file.size > 1024 * 1024) { // 1MB
                this.showMessage('Loading large file, please wait...', 'info');
            }
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    // For HTML files, use innerHTML directly
                    if (['html', 'htm'].includes(fileExtension)) {
                        this.editor.innerHTML = e.target.result;
                    } 
                    // For text and markdown files, properly format content
                    else {
                        const textContent = e.target.result;
                        let htmlContent;
                        
                        // Handle markdown files specially
                        if (fileExtension === 'md') {
                            htmlContent = this.parseMarkdown(textContent);
                        } else {
                            // Handle plain text files
                            htmlContent = this.parsePlainText(textContent);
                        }
                        
                        // Store the content temporarily
                        this.tempContent = htmlContent;
                    }
                    
                    this.currentDocument.title = file.name;
                    this.currentDocument.modified = false;
                    this.updateStatus();
                    this.showMessage(`Document "${file.name}" opened successfully`);
                    
                    // Create paginated layout
                    this.createPaginatedLayout();
                    
                    // Ensure scrolling works
                    this.ensureScrolling();
                    
                    
                    this.showPage('home');
                } catch (error) {
                    this.showMessage('Error reading file: ' + error.message, 'error');
                }
            };
            
            reader.onerror = () => {
                this.showMessage('Error reading file', 'error');
            };
            
            reader.readAsText(file, 'UTF-8');
        } else if (contentInput.value) {
            this.editor.innerHTML = contentInput.value;
            this.currentDocument.modified = false;
            this.updateStatus();
            this.showMessage('Document opened');
            this.showPage('home');
        }
    }
    
    // Ensure scrolling works properly
    ensureScrolling() {
        // Force the editor to have proper overflow settings
        this.editor.style.setProperty('overflow', 'visible', 'important');
        this.editor.style.setProperty('max-height', 'none', 'important');
        this.editor.style.setProperty('height', 'auto', 'important');
        
        // Ensure the editor container allows scrolling
        const editorContainer = this.editor.parentElement;
        if (editorContainer) {
            editorContainer.style.setProperty('overflow-y', 'auto', 'important');
            editorContainer.style.setProperty('overflow-x', 'hidden', 'important');
            editorContainer.style.setProperty('max-height', '100%', 'important');
        }
        
        // Force a reflow to ensure scrollbars appear
        this.editor.offsetHeight;
        
        // Ensure scrollbar is visible on the container
        if (editorContainer && editorContainer.scrollHeight > editorContainer.clientHeight) {
            editorContainer.style.setProperty('overflow-y', 'scroll', 'important');
        }
    }
    
    // Create paginated layout like Microsoft Word
    createPaginatedLayout() {
        // Clear existing content
        this.editor.innerHTML = '';
        
        // Get the content from tempContent or current editor content
        let content = '';
        if (this.tempContent) {
            // Extract text content from HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = this.tempContent;
            content = tempDiv.textContent || tempDiv.innerText || '';
            this.tempContent = null; // Clear temp content
        } else {
            content = this.editor.textContent || this.editor.innerText || '';
        }
        
        if (!content.trim()) {
            // Create empty page for new documents
            this.createNewPage('Welcome to MiniWord! Click the toolbar buttons to start using various features.');
            return;
        }
        
        // Split content into pages
        this.splitContentIntoPages(content);
    }
    
    // Split content into multiple pages
    splitContentIntoPages(content) {
        const lines = content.split('\n');
        const pages = [];
        let currentPage = [];
        let currentPageHeight = 0;
        
        // Approximate page height (considering margins and padding)
        const maxPageHeight = 297 - 50; // 297mm - 50mm for margins
        const lineHeight = 1.6; // line-height in em
        const fontSize = 14; // font-size in px
        const mmPerLine = (fontSize * lineHeight) * 0.264583; // Convert px to mm
        
        const maxLinesPerPage = Math.floor(maxPageHeight / mmPerLine);
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Check if adding this line would exceed page capacity
            if (currentPage.length >= maxLinesPerPage && line.trim() !== '') {
                // Create a new page
                pages.push(currentPage.join('\n'));
                currentPage = [];
            }
            
            currentPage.push(line);
        }
        
        // Add the last page if it has content
        if (currentPage.length > 0) {
            pages.push(currentPage.join('\n'));
        }
        
        // Create page elements
        pages.forEach((pageContent, index) => {
            this.createNewPage(pageContent, index + 1);
        });
        
        // Update page count in status bar
        this.updatePageCount(pages.length);
    }
    
    // Create a new page element
    createNewPage(content, pageNumber = null) {
        const page = document.createElement('div');
        page.className = 'page';
        
        const pageContent = document.createElement('div');
        pageContent.className = 'page-content';
        pageContent.contentEditable = true;
        
        // Parse content into proper HTML
        const htmlContent = this.parsePlainText(content);
        pageContent.innerHTML = htmlContent;
        
        // Add page number if specified
        if (pageNumber) {
            const pageNumberElement = document.createElement('div');
            pageNumberElement.style.cssText = `
                position: absolute;
                bottom: 10mm;
                right: 25mm;
                font-size: 12px;
                color: #666;
            `;
            pageNumberElement.textContent = `Page ${pageNumber}`;
            page.appendChild(pageNumberElement);
        }
        
        page.appendChild(pageContent);
        this.editor.appendChild(page);
        
        // Add event listeners for content editing
        pageContent.addEventListener('input', () => {
            this.currentDocument.modified = true;
            this.updateStatus();
        });
        
        pageContent.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = e.clipboardData.getData('text/plain');
            document.execCommand('insertText', false, text);
        });
    }
    
    // Update page count in status bar
    updatePageCount(totalPages) {
        const pageInfo = document.getElementById('page-info');
        if (pageInfo) {
            pageInfo.textContent = `Page 1 of ${totalPages}`;
        }
    }
    
    // Toggle between paginated and continuous view
    togglePagination() {
        if (this.paginationMode) {
            // Switch to continuous mode
            this.switchToContinuousMode();
        } else {
            // Switch to paginated mode
            this.switchToPaginatedMode();
        }
        
        this.paginationMode = !this.paginationMode;
        this.showMessage(`Switched to ${this.paginationMode ? 'paginated' : 'continuous'} view`);
        this.showPage('home');
    }
    
    // Switch to continuous text mode
    switchToContinuousMode() {
        // Get all content from pages
        const pages = this.editor.querySelectorAll('.page-content');
        let allContent = '';
        
        pages.forEach(page => {
            allContent += page.textContent + '\n';
        });
        
        // Clear editor and create continuous content
        this.editor.innerHTML = '';
        this.editor.style.padding = '20px';
        this.editor.style.backgroundColor = 'white';
        this.editor.contentEditable = true;
        this.editor.innerHTML = this.parsePlainText(allContent);
        
        // Update status
        const pageInfo = document.getElementById('page-info');
        if (pageInfo) {
            pageInfo.textContent = 'Continuous View';
        }
    }
    
    // Switch to paginated mode
    switchToPaginatedMode() {
        // Get current content
        const content = this.editor.textContent || this.editor.innerText || '';
        
        // Clear editor
        this.editor.innerHTML = '';
        this.editor.style.padding = '0';
        this.editor.style.backgroundColor = '#f5f5f5';
        
        // Create paginated layout
        if (content.trim()) {
            this.splitContentIntoPages(content);
        } else {
            this.createNewPage('Welcome to MiniWord! Click the toolbar buttons to start using various features.');
        }
    }
    
    // Force text wrapping for all content in the editor
    forceTextWrapping() {
        // Apply wrapping styles to all elements in the editor
        const allElements = this.editor.querySelectorAll('*');
        allElements.forEach(element => {
            element.style.setProperty('max-width', '100%', 'important');
            element.style.setProperty('word-wrap', 'break-word', 'important');
            element.style.setProperty('word-break', 'break-word', 'important');
            element.style.setProperty('overflow-wrap', 'break-word', 'important');
            element.style.setProperty('white-space', 'normal', 'important');
            element.style.setProperty('box-sizing', 'border-box', 'important');
        });
        
        // Special handling for links
        const links = this.editor.querySelectorAll('a');
        links.forEach(link => {
            link.style.setProperty('word-break', 'break-all', 'important');
            link.style.setProperty('overflow-wrap', 'break-word', 'important');
        });
        
        // Special handling for code blocks
        const codeBlocks = this.editor.querySelectorAll('pre, code');
        codeBlocks.forEach(block => {
            block.style.setProperty('white-space', 'pre-wrap', 'important');
            block.style.setProperty('word-wrap', 'break-word', 'important');
            block.style.setProperty('word-break', 'break-word', 'important');
            block.style.setProperty('max-width', '100%', 'important');
            block.style.setProperty('overflow-x', 'auto', 'important');
        });
        
        // Special handling for tables
        const tables = this.editor.querySelectorAll('table');
        tables.forEach(table => {
            table.style.setProperty('max-width', '100%', 'important');
            table.style.setProperty('table-layout', 'fixed', 'important');
        });
    }
    
    // Parse plain text files into proper HTML
    parsePlainText(textContent) {
        // Handle different line break types and create proper paragraphs
        let htmlContent = textContent
            // Normalize line breaks
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            // Split into paragraphs (double line breaks or more)
            .split(/\n\s*\n/)
            // Convert each paragraph to HTML
            .map(paragraph => {
                // Trim whitespace
                const trimmed = paragraph.trim();
                if (!trimmed) return '';
                
                // Convert single line breaks to <br> within paragraphs
                const withBreaks = trimmed.replace(/\n/g, '<br>');
                return `<p>${withBreaks}</p>`;
            })
            // Join paragraphs
            .join('');
        
        // If no paragraphs were created (single line), wrap in one paragraph
        if (!htmlContent) {
            htmlContent = `<p>${textContent.replace(/\n/g, '<br>')}</p>`;
        }
        
        return htmlContent;
    }
    
    // Parse markdown files into HTML
    parseMarkdown(textContent) {
        let htmlContent = textContent
            // Normalize line breaks
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            // Convert headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Convert bold and italic
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Convert code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // Convert links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
            // Split into paragraphs
            .split(/\n\s*\n/)
            .map(paragraph => {
                const trimmed = paragraph.trim();
                if (!trimmed) return '';
                
                // Skip if it's already a header or code block
                if (trimmed.startsWith('<h') || trimmed.startsWith('<pre>')) {
                    return trimmed;
                }
                
                // Convert single line breaks to <br> within paragraphs
                const withBreaks = trimmed.replace(/\n/g, '<br>');
                return `<p>${withBreaks}</p>`;
            })
            .join('');
        
        // If no paragraphs were created, wrap in one paragraph
        if (!htmlContent) {
            htmlContent = `<p>${textContent.replace(/\n/g, '<br>')}</p>`;
        }
        
        return htmlContent;
    }
    
    saveDocument() {
        const filename = document.getElementById('save-filename').value;
        const format = document.getElementById('save-format').value;
        
        this.currentDocument.content = this.editor.innerHTML;
        this.currentDocument.modified = false;
        
        // Use the document title as the filename if no custom filename is provided
        const finalFilename = filename || this.currentDocument.title || 'Untitled Document';
        
        const blob = new Blob([this.editor.innerHTML], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = finalFilename + '.' + format;
        a.click();
        URL.revokeObjectURL(url);
        
        this.updateStatus();
        this.showMessage('Document saved');
        this.showPage('home');
    }
    
    printDocument() {
        window.print();
        this.showMessage('Printing...');
    }
    
    
    
    refreshHistory() {
        // Refresh the webpage
        window.location.reload();
        this.showMessage('Page refreshed');
    }
    
    // Close the current web page/tab
    closeWebPage() {
        // Check if there are unsaved changes
        if (this.currentDocument.modified) {
            const shouldClose = confirm('You have unsaved changes. Are you sure you want to close the page?');
            if (!shouldClose) {
                return;
            }
        }
        
        // Try to close the current tab/window
        try {
            // Check if the window was opened by a script
            if (window.opener && !window.opener.closed) {
                window.close();
            } else {
                // If not opened by script, show instructions
                this.showMessage('This tab cannot be closed automatically. Please use Ctrl+W (or Cmd+W on Mac) or click the X button to close the tab.');
                
                // Alternative: try to navigate to about:blank
                setTimeout(() => {
                    if (confirm('Would you like to navigate to a blank page instead?')) {
                        window.location.href = 'about:blank';
                    }
                }, 1000);
            }
        } catch (error) {
            // If window.close() fails, show message
            this.showMessage('Cannot close this tab automatically. Please close it manually using Ctrl+W or the browser\'s close button.');
        }
    }
    
    // Refresh the current web page
    refreshWebPage() {
        // Check if there are unsaved changes
        if (this.currentDocument.modified) {
            const shouldRefresh = confirm('You have unsaved changes. Are you sure you want to refresh the page? All changes will be lost.');
            if (!shouldRefresh) {
                return;
            }
        }
        
        // Refresh the page
        window.location.reload();
    }
    
    
    // Open a new tab with fresh MiniWord instance
    openNewTab() {
        try {
            // Open new tab with the same URL
            const newWindow = window.open(window.location.href, '_blank');
            
            if (newWindow) {
                this.showMessage('New tab opened successfully!');
            } else {
                // If popup was blocked, show instructions
                this.showMessage('Popup blocked! Please allow popups for this site or manually open a new tab and navigate to: ' + window.location.href);
            }
        } catch (error) {
            this.showMessage('Error opening new tab: ' + error.message);
        }
    }
    
    undo() {
        document.execCommand('undo');
        this.showMessage('Undone');
    }
    
    redo() {
        document.execCommand('redo');
        this.showMessage('Redone');
    }
    
    cut() {
        try {
            const selection = window.getSelection();
            if (selection.rangeCount === 0) {
                this.showMessage('Please select text to cut first');
                return;
            }
            
            const selectedText = selection.toString();
            // Update internal MiniWord clipboard (plain text only for cut)
            this.internalClipboard = {
                plainText: selectedText,
                html: '',
                hasContent: true,
                type: 'plain'
            };
            
            // Best-effort: also try to write to system clipboard, but internal clipboard is the source of truth
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(selectedText).catch(() => {
                    // Ignore failures – internal clipboard still works
                });
            }
            
            // Remove the selected content from the document
            selection.deleteFromDocument();
            this.showMessage('Text cut (stored in MiniWord clipboard)');
        } catch (error) {
            console.error('Cut error:', error);
            this.showMessage('Cut failed', 'error');
        }
    }
    
    copy() {
        try {
            const selection = window.getSelection();
            if (selection.rangeCount === 0) {
                this.showMessage('Please select text to copy first');
                return;
            }
            
            const selectedText = selection.toString();
            // Update internal MiniWord clipboard (plain text)
            this.internalClipboard = {
                plainText: selectedText,
                html: '',
                hasContent: true,
                type: 'plain'
            };
            
            // Best-effort: also try to write to system clipboard
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(selectedText).then(() => {
                    this.showMessage('Text copied (MiniWord clipboard + system clipboard)');
                }).catch(() => {
                    this.showMessage('Text copied (MiniWord clipboard only)');
                });
            } else {
                this.showMessage('Text copied (MiniWord clipboard only)');
            }
        } catch (error) {
            console.error('Copy error:', error);
            this.showMessage('Copy failed', 'error');
        }
    }
    
    async paste() {
        try {
            this.editor.focus();
            
            // First, try MiniWord's internal clipboard (reliable, no browser permissions)
            if (this.internalClipboard && this.internalClipboard.hasContent) {
                if (this.internalClipboard.html) {
                    this.insertHTMLAtCursor(this.internalClipboard.html);
                } else if (this.internalClipboard.plainText) {
                    this.insertTextAtCursor(this.internalClipboard.plainText);
                } else {
                    this.showMessage('MiniWord clipboard is empty');
                    return;
                }
                
                this.showMessage('Content pasted from MiniWord clipboard');
                this.currentDocument.modified = true;
                this.updateStatus();
                return;
            }
            
            // If internal clipboard is empty, best-effort: try system clipboard (may be blocked by browser)
            if (navigator.clipboard && navigator.clipboard.readText && window.isSecureContext) {
                try {
                    const text = await navigator.clipboard.readText();
                    if (text && text.trim()) {
                        this.insertTextAtCursor(text);
                        this.showMessage('Text pasted from system clipboard');
                        this.currentDocument.modified = true;
                        this.updateStatus();
                    } else {
                        this.showMessage('No text found in system clipboard');
                    }
                } catch (clipboardError) {
                    console.log('Clipboard API failed, trying fallback:', clipboardError);
                    this.showPasteFallback();
                }
            } else {
                this.showPasteFallback();
            }
        } catch (error) {
            console.error('Paste error:', error);
            this.showPasteFallback();
        }
    }
    
    // Fallback method when clipboard API fails
    showPasteFallback() {
        this.showMessage('Please use Ctrl+V to paste content directly into the editor', 'info');
        
        // Add a temporary paste event listener
        const pasteHandler = (e) => {
            e.preventDefault();
            
            // Try to get HTML content first (for formatted paste)
            const html = e.clipboardData.getData('text/html');
            const text = e.clipboardData.getData('text/plain');
            
            // Debug: Log what we're getting from clipboard
            console.log('=== PASTE DEBUG ===');
            console.log('Paste HTML content:', html);
            console.log('Paste plain text:', text);
            console.log('HTML length:', html ? html.length : 0);
            console.log('Available clipboard types:', e.clipboardData.types);
            
            if (html && html.trim() !== '') {
                console.log('Using HTML paste');
                // Insert HTML with formatting preserved
                this.insertHTMLAtCursor(html);
                this.showMessage('Formatted content pasted successfully');
                this.currentDocument.modified = true;
                this.updateStatus();
            } else if (text) {
                // Fallback to plain text
                this.insertTextAtCursor(text);
                this.showMessage('Content pasted successfully');
                this.currentDocument.modified = true;
                this.updateStatus();
            }
            
            // Remove the listener after use
            this.editor.removeEventListener('paste', pasteHandler);
        };
        
        this.editor.addEventListener('paste', pasteHandler);
        
        // Focus the editor to make it ready for paste
        this.editor.focus();
    }
    
    // Fallback method for formatted paste (preserves HTML formatting)
    showPasteFormattedFallback() {
        this.showMessage('Please use Ctrl+V to paste content directly into the editor', 'info');
        
        // Add a temporary paste event listener for formatted content
        const pasteHandler = (e) => {
            e.preventDefault();
            
            // Get both HTML and plain text from clipboard
            const html = e.clipboardData.getData('text/html');
            const text = e.clipboardData.getData('text/plain');
            
            // Debug: Log what we're getting from clipboard
            console.log('=== FORMATTED PASTE FALLBACK DEBUG ===');
            console.log('Paste HTML content:', html);
            console.log('Paste plain text:', text);
            console.log('HTML length:', html ? html.length : 0);
            console.log('Available clipboard types:', e.clipboardData.types);
            
            if (html && html.trim() !== '') {
                console.log('Using HTML paste (formatting preserved)');
                // Insert HTML with formatting preserved
                this.insertHTMLAtCursor(html);
                this.showMessage('Formatted content pasted successfully');
                this.currentDocument.modified = true;
                this.updateStatus();
            } else if (text) {
                console.log('No HTML available, using plain text');
                // Fallback to plain text
                this.insertTextAtCursor(text);
                this.showMessage('Plain text pasted (no formatting available)');
                this.currentDocument.modified = true;
                this.updateStatus();
            } else {
                this.showMessage('No content available in clipboard');
            }
            
            // Remove the listener after use
            this.editor.removeEventListener('paste', pasteHandler);
        };
        
        this.editor.addEventListener('paste', pasteHandler);
        
        // Focus the editor to make it ready for paste
        this.editor.focus();
    }
    
    // Fallback method for plain text paste (strips all formatting)
    showPastePlainTextFallback() {
        this.showMessage('Please use Ctrl+V to paste content directly into the editor', 'info');
        
        // Add a temporary paste event listener for plain text only
        const pasteHandler = (e) => {
            e.preventDefault();
            
            // Get both HTML and plain text from clipboard
            const html = e.clipboardData.getData('text/html');
            const text = e.clipboardData.getData('text/plain');
            
            // Debug: Log what we're getting from clipboard
            console.log('=== PLAIN TEXT PASTE DEBUG ===');
            console.log('Paste HTML content:', html);
            console.log('Paste plain text:', text);
            console.log('HTML length:', html ? html.length : 0);
            console.log('Available clipboard types:', e.clipboardData.types);
            
            // Always use plain text, even if HTML is available
            if (text && text.trim() !== '') {
                console.log('Using plain text paste (formatting stripped)');
                // Force plain text insertion (strip any potential HTML)
                const plainText = text.replace(/<[^>]*>/g, ''); // Remove any HTML tags
                console.log('Fallback - Stripped HTML, plain text:', plainText);
                // Insert as plain text (no formatting)
                this.insertTextAtCursor(plainText);
                this.showMessage('Plain text pasted successfully (formatting removed)');
                this.currentDocument.modified = true;
                this.updateStatus();
            } else {
                this.showMessage('No text content available in clipboard');
            }
            
            // Remove the listener after use
            this.editor.removeEventListener('paste', pasteHandler);
        };
        
        this.editor.addEventListener('paste', pasteHandler);
        
        // Focus the editor to make it ready for paste
        this.editor.focus();
    }
    
    // Paste plain text only (removes formatting)
    async pastePlainText() {
        try {
            this.editor.focus();
            
            // Prefer MiniWord internal clipboard
            if (this.internalClipboard && this.internalClipboard.hasContent && this.internalClipboard.plainText) {
                this.insertTextAtCursor(this.internalClipboard.plainText);
                this.showMessage('Plain text pasted from MiniWord clipboard');
                this.currentDocument.modified = true;
                this.updateStatus();
                return;
            }
            
            // Fallback: try system clipboard (may be blocked)
            if (navigator.clipboard && navigator.clipboard.readText && window.isSecureContext) {
                try {
                    const text = await navigator.clipboard.readText();
                    if (text && text.trim()) {
                        this.insertTextAtCursor(text);
                        this.showMessage('Plain text pasted from system clipboard');
                        this.currentDocument.modified = true;
                        this.updateStatus();
                    } else {
                        this.showMessage('No text found in system clipboard');
                    }
                } catch (clipboardError) {
                    this.showPasteFallback();
                }
            } else {
                this.showPasteFallback();
            }
        } catch (error) {
            console.error('Plain text paste error:', error);
            this.showPasteFallback();
        }
    }
    
    // Force plain text paste - completely strips all formatting
    forcePlainTextPaste() {
        console.log('=== FORCE PLAIN TEXT PASTE ===');
        
        this.showMessage('Please use Ctrl+V to paste content directly into the editor', 'info');
        
        // Add a temporary paste event listener that FORCES plain text
        const pasteHandler = (e) => {
            e.preventDefault();
            
            console.log('=== FORCE PLAIN TEXT HANDLER ===');
            console.log('Available clipboard types:', e.clipboardData.types);
            
            // Get both HTML and plain text
            const html = e.clipboardData.getData('text/html');
            const text = e.clipboardData.getData('text/plain');
            
            console.log('HTML content:', html);
            console.log('Plain text content:', text);
            
            // ALWAYS use plain text, even if HTML is available
            let finalText = '';
            
            if (text && text.trim() !== '') {
                // Use the plain text directly
                finalText = text;
                console.log('Using clipboard plain text:', finalText);
            } else if (html && html.trim() !== '') {
                // Extract plain text from HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                finalText = tempDiv.textContent || tempDiv.innerText || '';
                console.log('Extracted plain text from HTML:', finalText);
            } else {
                console.log('No content available in clipboard');
                this.showMessage('No text content available in clipboard');
                this.editor.removeEventListener('paste', pasteHandler);
                return;
            }
            
            // STRIP ALL HTML TAGS AND FORMATTING
            finalText = finalText.replace(/<[^>]*>/g, ''); // Remove HTML tags
            finalText = finalText.replace(/&nbsp;/g, ' '); // Replace non-breaking spaces
            finalText = finalText.replace(/&amp;/g, '&'); // Replace HTML entities
            finalText = finalText.replace(/&lt;/g, '<');
            finalText = finalText.replace(/&gt;/g, '>');
            finalText = finalText.replace(/&quot;/g, '"');
            finalText = finalText.trim();
            
            console.log('Final plain text (all formatting stripped):', finalText);
            
            if (finalText) {
                // Insert as COMPLETELY plain text using the most basic method
                this.insertCompletelyPlainText(finalText);
                this.showMessage('Plain text pasted successfully (ALL formatting removed)');
                this.currentDocument.modified = true;
                this.updateStatus();
            } else {
                this.showMessage('No text content available in clipboard');
            }
            
            // Remove the listener after use
            this.editor.removeEventListener('paste', pasteHandler);
        };
        
        this.editor.addEventListener('paste', pasteHandler);
        
        // Focus the editor to make it ready for paste
        this.editor.focus();
    }
    
    // Insert completely plain text - NO formatting whatsoever
    insertCompletelyPlainText(text) {
        console.log('=== INSERT COMPLETELY PLAIN TEXT ===');
        console.log('Text to insert:', text);
        
        try {
            const selection = window.getSelection();
            
            if (selection.rangeCount > 0) {
                // There's a selection, replace it
                const range = selection.getRangeAt(0);
                range.deleteContents();
                
                // Create a plain text node
                const textNode = document.createTextNode(text);
                range.insertNode(textNode);
                
                // Position cursor at the end of inserted text
                range.setStartAfter(textNode);
                range.setEndAfter(textNode);
                selection.removeAllRanges();
                selection.addRange(range);
            } else {
                // No selection, insert at cursor position
                const range = document.createRange();
                const sel = window.getSelection();
                
                if (this.editor.contains(sel.anchorNode)) {
                    range.setStart(sel.anchorNode, sel.anchorOffset);
                    range.setEnd(sel.anchorNode, sel.anchorOffset);
                } else {
                    range.selectNodeContents(this.editor);
                    range.collapse(false);
                }
                
                // Create a plain text node
                const textNode = document.createTextNode(text);
                range.insertNode(textNode);
                
                // Position cursor at the end of inserted text
                range.setStartAfter(textNode);
                range.setEndAfter(textNode);
                sel.removeAllRanges();
                sel.addRange(range);
            }
            
            // Trigger input event to update document state
            this.editor.dispatchEvent(new Event('input', { bubbles: true }));
            
            console.log('Plain text inserted successfully');
            
        } catch (error) {
            console.error('Error inserting plain text:', error);
            // Ultimate fallback - append as plain text
            this.editor.textContent += text;
        }
    }
    
    // Paste formatted content (preserves HTML formatting)
    async pasteFormatted() {
        try {
            this.editor.focus();
            
            // Prefer MiniWord internal clipboard (formatted HTML if available)
            if (this.internalClipboard && this.internalClipboard.hasContent) {
                if (this.internalClipboard.html) {
                    this.insertHTMLAtCursor(this.internalClipboard.html);
                    this.showMessage('Formatted content pasted from MiniWord clipboard');
                } else if (this.internalClipboard.plainText) {
                    this.insertTextAtCursor(this.internalClipboard.plainText);
                    this.showMessage('Plain text pasted from MiniWord clipboard (no formatting available)');
                } else {
                    this.showMessage('MiniWord clipboard is empty');
                    return;
                }
                
                this.currentDocument.modified = true;
                this.updateStatus();
                return;
            }
            
            // Fallback: try system clipboard with HTML support (may be blocked)
            if (navigator.clipboard && navigator.clipboard.read && window.isSecureContext) {
                try {
                    const clipboardItems = await navigator.clipboard.read();
                    const clipboardItem = clipboardItems[0];
                    
                    if (clipboardItem.types.includes('text/html')) {
                        const htmlBlob = await clipboardItem.getType('text/html');
                        const html = await htmlBlob.text();
                        this.insertHTMLAtCursor(html);
                        this.showMessage('Formatted content pasted from system clipboard');
                        this.currentDocument.modified = true;
                        this.updateStatus();
                    } else if (clipboardItem.types.includes('text/plain')) {
                        const textBlob = await clipboardItem.getType('text/plain');
                        const text = await textBlob.text();
                        this.insertTextAtCursor(text);
                        this.showMessage('Text content pasted from system clipboard');
                        this.currentDocument.modified = true;
                        this.updateStatus();
                    } else {
                        this.showMessage('No content available in system clipboard');
                    }
                } catch (clipboardError) {
                    console.log('Clipboard API failed, trying fallback with HTML support:', clipboardError);
                    this.showPasteFallback();
                }
            } else {
                console.log('Clipboard API not available, using fallback with HTML support');
                this.showPasteFallback();
            }
        } catch (error) {
            console.error('Formatted paste error:', error);
            this.showPasteFallback();
        }
    }
    
    // Simple function to insert text at cursor position
    insertTextAtCursor(text) {
        try {
            this.editor.focus();
            const selection = window.getSelection();
            
            // Ensure text is truly plain (strip any HTML)
            const plainText = text.replace(/<[^>]*>/g, '').trim();
            console.log('Inserting plain text:', plainText);
            
            if (selection.rangeCount > 0) {
                // There's a selection, replace it
                const range = selection.getRangeAt(0);
                range.deleteContents();
                const textNode = document.createTextNode(plainText);
                range.insertNode(textNode);
                
                // Position cursor at the end of inserted text
                range.setStartAfter(textNode);
                range.setEndAfter(textNode);
                selection.removeAllRanges();
                selection.addRange(range);
            } else {
                // No selection, insert at cursor position or end
                const range = document.createRange();
                const sel = window.getSelection();
                
                // Try to find cursor position in editor
                if (this.editor.contains(sel.anchorNode)) {
                    range.setStart(sel.anchorNode, sel.anchorOffset);
                    range.setEnd(sel.anchorNode, sel.anchorOffset);
                } else {
                    // No cursor in editor, append to end
                    range.selectNodeContents(this.editor);
                    range.collapse(false);
                }
                
                const textNode = document.createTextNode(plainText);
                range.insertNode(textNode);
                
                // Position cursor at the end of inserted text
                range.setStartAfter(textNode);
                range.setEndAfter(textNode);
                sel.removeAllRanges();
                sel.addRange(range);
            }
            
            // Trigger input event to update document state
            this.editor.dispatchEvent(new Event('input', { bubbles: true }));
            
        } catch (error) {
            // Fallback: append to end of editor as plain text
            const plainText = text.replace(/<[^>]*>/g, '').trim();
            this.editor.textContent += plainText;
        }
    }
    
    // Function to insert HTML content at cursor position
    insertHTMLAtCursor(html) {
        try {
            // Debug: Log the HTML being inserted
            console.log('=== INSERT DEBUG ===');
            console.log('Inserting HTML:', html);
            console.log('HTML length:', html.length);
            
            this.editor.focus();
            const selection = window.getSelection();
            
            // Ensure the editor has contentEditable enabled for proper HTML insertion
            if (!this.editor.isContentEditable) {
                this.editor.contentEditable = true;
            }
            
            // Try a simpler approach first - direct innerHTML insertion
            if (html.includes('style=') || html.includes('<span') || html.includes('<div')) {
                console.log('HTML contains formatting, using direct insertion');
                
                // Create a temporary element to test the HTML
                const testDiv = document.createElement('div');
                testDiv.innerHTML = html;
                console.log('Test div innerHTML:', testDiv.innerHTML);
                
                // Check if we have styled elements
                const styledElements = testDiv.querySelectorAll('[style]');
                console.log('Found styled elements:', styledElements.length);
                styledElements.forEach((el, index) => {
                    console.log(`Element ${index}:`, el.outerHTML);
                    console.log(`Element ${index} styles:`, el.style.cssText);
                });
            }
            
            if (selection.rangeCount > 0) {
                // There's a selection, replace it
                const range = selection.getRangeAt(0);
                range.deleteContents();
                
                // Create a temporary div to parse HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                
                // Insert all child nodes with preserved formatting
                const fragment = document.createDocumentFragment();
                while (tempDiv.firstChild) {
                    const child = tempDiv.firstChild;
                    
                    // If it's an element with styles, ensure they're preserved
                    if (child.nodeType === Node.ELEMENT_NODE) {
                        // Ensure the element maintains its styling
                        const computedStyle = window.getComputedStyle(child);
                        if (child.style.cssText) {
                            // Preserve existing inline styles
                            child.style.cssText = child.style.cssText;
                        }
                    }
                    
                    fragment.appendChild(child);
                }
                
                range.insertNode(fragment);
                
                // Position cursor at the end of inserted content
                range.collapse(false);
                selection.removeAllRanges();
                selection.addRange(range);
            } else {
                // No selection, insert at cursor position or end
                const range = document.createRange();
                const sel = window.getSelection();
                
                // Try to find cursor position in editor
                if (this.editor.contains(sel.anchorNode)) {
                    range.setStart(sel.anchorNode, sel.anchorOffset);
                    range.setEnd(sel.anchorNode, sel.anchorOffset);
                } else {
                    // No cursor in editor, append to end
                    range.selectNodeContents(this.editor);
                    range.collapse(false);
                }
                
                // Create a temporary div to parse HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                
                // Debug: Log the HTML being inserted
                console.log('=== INSERT HTML DEBUG ===');
                console.log('HTML to insert:', html);
                console.log('Contains bold:', html.includes('font-weight: bold') || html.includes('font-weight:bold'));
                console.log('Contains italic:', html.includes('font-style: italic') || html.includes('font-style:italic'));
                
                // Insert all child nodes with preserved formatting
                const fragment = document.createDocumentFragment();
                while (tempDiv.firstChild) {
                    const child = tempDiv.firstChild;
                    
                    // If it's an element with styles, ensure they're preserved
                    if (child.nodeType === Node.ELEMENT_NODE) {
                        // Ensure the element maintains its styling
                        const computedStyle = window.getComputedStyle(child);
                        if (child.style.cssText) {
                            // Preserve existing inline styles
                            child.style.cssText = child.style.cssText;
                            console.log('Preserving styles for element:', child.tagName, child.style.cssText);
                        }
                    }
                    
                    fragment.appendChild(child);
                }
                
                range.insertNode(fragment);
                
                // Position cursor at the end of inserted content
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            }
            
            // Trigger input event to update document state
            this.editor.dispatchEvent(new Event('input', { bubbles: true }));
            
        } catch (error) {
            // Fallback: insert as plain text
            this.insertTextAtCursor(html);
        }
    }
    
    findText() {
        const text = document.getElementById('find-text').value;
        const caseSensitive = document.getElementById('case-sensitive').checked;
        this.highlightText(text, caseSensitive);
        this.showMessage(`Find: ${text}`);
    }
    
    replaceText() {
        const findText = document.getElementById('replace-find').value;
        const replaceText = document.getElementById('replace-with').value;
        const caseSensitive = document.getElementById('replace-case-sensitive').checked;
        this.replaceTextInDocument(findText, replaceText, caseSensitive);
        this.showMessage(`Replaced: ${findText} -> ${replaceText}`);
    }
    
    findNextText() {
        const findText = document.getElementById('replace-find').value;
        const caseSensitive = document.getElementById('replace-case-sensitive').checked;
        
        if (!findText) {
            this.showMessage('Please enter text to find');
            return;
        }
        
        // First highlight all occurrences
        this.highlightText(findText, caseSensitive);
        
        // Find the next occurrence and scroll to it
        const marks = this.editor.querySelectorAll('mark');
        if (marks.length === 0) {
            this.showMessage('No more occurrences found');
            return;
        }
        
        // Find the first unselected mark or the next one
        let nextMark = null;
        for (let mark of marks) {
            if (!mark.classList.contains('selected')) {
                nextMark = mark;
                break;
            }
        }
        
        if (!nextMark) {
            // If all are selected, start from the beginning
            nextMark = marks[0];
            // Clear all selections
            marks.forEach(mark => mark.classList.remove('selected'));
        }
        
        // Mark this occurrence as selected
        nextMark.classList.add('selected');
        nextMark.style.backgroundColor = 'orange';
        
        // Scroll to the selected mark
        nextMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        this.showMessage(`Found occurrence ${Array.from(marks).indexOf(nextMark) + 1} of ${marks.length}`);
    }
    
    
    // Text formatting functions
    toggleBold() {
        this.applyFormatting('bold');
        this.showMessage('Bold formatting applied');
    }
    
    toggleItalic() {
        this.applyFormatting('italic');
        this.showMessage('Italic formatting applied');
    }
    
    toggleUnderline() {
        this.applyFormatting('underline');
        this.showMessage('Underline formatting applied');
    }
    
    toggleStrikethrough() {
        this.applyFormatting('strikeThrough');
        this.showMessage('Strikethrough formatting applied');
    }
    
    // General formatting functions
    applyFormatting(command, value = null) {
        if (document.queryCommandSupported(command)) {
            document.execCommand(command, false, value);
        } else {
            // If execCommand is not supported, use modern methods
            this.applyModernFormatting(command, value);
        }
    }
    
    // Modern formatting methods
    applyModernFormatting(command, value = null) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return;
        
        const range = selection.getRangeAt(0);
        const selectedText = selection.toString();
        
        if (selectedText) {
            // Has selected text
            const span = document.createElement('span');
            span.style.fontWeight = command === 'bold' ? 'bold' : 'normal';
            span.style.fontStyle = command === 'italic' ? 'italic' : 'normal';
            span.style.textDecoration = command === 'underline' ? 'underline' : 
                                      command === 'strikeThrough' ? 'line-through' : 'none';
            
            if (command === 'foreColor' && value) {
                span.style.color = value;
            }
            if (command === 'fontSize' && value) {
                span.style.fontSize = value;
            }
            
            span.textContent = selectedText;
            range.deleteContents();
            range.insertNode(span);
        } else {
            // No selected text, insert formatted placeholder at cursor position
            const span = document.createElement('span');
            span.style.fontWeight = command === 'bold' ? 'bold' : 'normal';
            span.style.fontStyle = command === 'italic' ? 'italic' : 'normal';
            span.style.textDecoration = command === 'underline' ? 'underline' : 
                                      command === 'strikeThrough' ? 'line-through' : 'none';
            span.textContent = 'Formatted Text';
            range.insertNode(span);
            
            // Select inserted text
            const newRange = document.createRange();
            newRange.selectNodeContents(span);
            selection.removeAllRanges();
            selection.addRange(newRange);
        }
    }
    
    // Text alignment functions
    alignLeft() {
        this.applyFormatting('justifyLeft');
        this.showMessage('Left alignment applied');
    }
    
    alignCenter() {
        this.applyFormatting('justifyCenter');
        this.showMessage('Center alignment applied');
    }
    
    alignRight() {
        this.applyFormatting('justifyRight');
        this.showMessage('Right alignment applied');
    }
    
    alignJustify() {
        this.applyFormatting('justifyFull');
        this.showMessage('Justify alignment applied');
    }
    
    // Font control functions
    setFontSize(size) {
        this.applyFormatting('fontSize', size);
        this.showMessage(`Font size set to ${size}px`);
    }
    
    setTextColor(color) {
        this.applyFormatting('foreColor', color);
        this.showMessage(`Text color set to ${color}`);
    }
    
    setHighlightColor(color) {
        this.applyFormatting('backColor', color);
        this.showMessage(`Highlight color set to ${color}`);
    }
    
    // Helper function to check if cursor is in the main editor
    isCursorInEditor() {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return false;
        
        const range = selection.getRangeAt(0);
        const container = range.commonAncestorContainer;
        
        // Check if the container is within the main editor
        let element = container;
        while (element && element !== document.body) {
            if (element === this.editor || element.id === 'editor') {
                return true;
            }
            element = element.parentNode;
        }
        
        return false;
    }
    
    // List functions
    insertBulletedList() {
        // Check if cursor is in the main editor
        if (!this.isCursorInEditor()) {
            this.showMessage('Please place your cursor in the main text area to add bullet points');
            return;
        }
        
        // Always try to add bullet to current line first
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const cursorPosition = range.startOffset;
            const textNode = range.startContainer;
            
            // Check if we're at the beginning of text or in an empty line
            if (cursorPosition === 0 || textNode.textContent.trim() === '') {
                this.addBulletToCurrentLine();
            } else {
                // Check if we're in a paragraph with text
                const container = range.commonAncestorContainer;
                let paragraph = container;
                while (paragraph && paragraph.nodeType !== Node.ELEMENT_NODE) {
                    paragraph = paragraph.parentNode;
                }
                
                if (paragraph && (paragraph.tagName === 'P' || paragraph.tagName === 'DIV')) {
                    this.addBulletToCurrentLine();
                } else {
                    // Use the standard formatting approach
        this.applyFormatting('insertUnorderedList');
        this.showMessage('Bulleted list inserted');
                }
            }
        } else {
            this.addBulletToCurrentLine();
        }
    }

    addBulletToCurrentLine() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const container = range.commonAncestorContainer;
            
            // Find the current paragraph or line
            let paragraph = container;
            while (paragraph && paragraph.nodeType !== Node.ELEMENT_NODE) {
                paragraph = paragraph.parentNode;
            }
            
            // If we're in a paragraph, add bullet to it
            if (paragraph && (paragraph.tagName === 'P' || paragraph.tagName === 'DIV')) {
                // Check if paragraph already has a bullet
                if (paragraph.classList.contains('bulleted-list') || paragraph.querySelector('ul, ol')) {
                    this.showMessage('This paragraph already has a list format');
                    return;
                }
                
                // Get the text content
                const text = paragraph.textContent.trim();
                if (text) {
                    // Create a bulleted list with the current text
                    const listHTML = `<ul class="bulleted-list" style="list-style-type: disc; margin-left: 20px;"><li>${text}</li></ul>`;
                    paragraph.outerHTML = listHTML;
                    this.showMessage('Bullet point added to current line');
                } else {
                    // If no text, create a new bulleted list item
                    const listHTML = `<ul class="bulleted-list" style="list-style-type: disc; margin-left: 20px;"><li>New item</li></ul>`;
                    paragraph.outerHTML = listHTML;
                    this.showMessage('New bulleted list created');
                }
            } else {
                // If not in a paragraph, create a new bulleted list
                const listHTML = `<ul class="bulleted-list" style="list-style-type: disc; margin-left: 20px;"><li>New item</li></ul>`;
                this.insertContent(listHTML);
                this.showMessage('New bulleted list created');
            }
        } else {
            // If no selection, create a new bulleted list at cursor position
            const listHTML = `<ul class="bulleted-list" style="list-style-type: disc; margin-left: 20px;"><li>New item</li></ul>`;
            this.insertContent(listHTML);
            this.showMessage('New bulleted list created');
        }
    }
    
    insertNumberedList() {
        // Check if cursor is in the main editor
        if (!this.isCursorInEditor()) {
            this.showMessage('Please place your cursor in the main text area to add numbered lists');
            return;
        }
        
        this.applyFormatting('insertOrderedList');
        this.showMessage('Numbered list inserted');
    }
    
    // Indent functions
    increaseIndent() {
        this.applyFormatting('indent');
        this.showMessage('Increase indent');
    }
    
    decreaseIndent() {
        this.applyFormatting('outdent');
        this.showMessage('Decrease indent');
    }
    
    // Superscript/subscript functions
    applySuperscript() {
        this.applyFormatting('superscript');
        this.showMessage('Superscript format applied');
    }
    
    applySubscript() {
        this.applyFormatting('subscript');
        this.showMessage('Subscript format applied');
    }
    
    // Clear format function (enhanced version)
    clearFormat() {
        try {
            // Ensure the editor is focused
            this.editor.focus();
            
            const selection = window.getSelection();
            
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const selectedText = selection.toString();
                
                if (selectedText && selectedText.trim() !== '') {
                    // Text is selected, clear formatting from selected text
                    this.clearAllFormatting();
                } else {
                    // No text selected, clear formatting from current paragraph or entire document
                    this.clearFormatFromCurrentPosition(range);
                }
            } else {
                // No selection, clear formatting from entire document
                this.clearFormatFromEntireDocument();
            }
            
        } catch (error) {
            console.error('Error clearing format:', error);
            this.showMessage('Error clearing format', 'error');
        }
    }
    
    // Clear formatting from current position (paragraph or document)
    clearFormatFromCurrentPosition(range) {
        try {
            const container = range.commonAncestorContainer;
            const element = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
            
            // Find the closest paragraph or block element
            let targetElement = element;
            if (element && !element.closest('p, div, h1, h2, h3, h4, h5, h6')) {
                const paragraph = element.closest('p') || element.closest('div');
                if (paragraph) {
                    targetElement = paragraph;
                }
            }
            
            if (targetElement) {
                // Clear formatting from the paragraph
                const textContent = targetElement.textContent;
                targetElement.innerHTML = '';
                targetElement.textContent = textContent;
                this.showMessage('Formatting cleared from current paragraph');
            } else {
                // Fallback: clear formatting from entire document
                this.clearFormatFromEntireDocument();
            }
            
            // Mark document as modified
            this.currentDocument.modified = true;
            this.updateStatus();
            
        } catch (error) {
            console.error('Error clearing format from current position:', error);
            this.showMessage('Error clearing format', 'error');
        }
    }
    
    // Clear formatting from entire document
    clearFormatFromEntireDocument() {
        try {
            const editor = this.editor;
            const textContent = editor.textContent;
            
            // Clear the editor
            editor.innerHTML = '';
            
            // Create a single paragraph with plain text
            const paragraph = document.createElement('p');
            paragraph.textContent = textContent;
            editor.appendChild(paragraph);
            
            // Mark document as modified
            this.currentDocument.modified = true;
            this.updateStatus();
            
            this.showMessage('Formatting cleared from entire document');
            
        } catch (error) {
            console.error('Error clearing format from entire document:', error);
            this.showMessage('Error clearing format', 'error');
        }
    }
    
    // Clear formatting functions
    clearAllFormatting() {
        try {
            const selection = window.getSelection();
            if (selection.rangeCount === 0) {
                this.showMessage('Please select text to clear formatting', 'error');
                return;
            }
            
            const range = selection.getRangeAt(0);
            const selectedText = selection.toString();
            
            if (!selectedText || selectedText.trim() === '') {
                this.showMessage('Please select text to clear formatting', 'error');
                return;
            }
            
            // Get the common ancestor container
            const container = range.commonAncestorContainer;
            const containerElement = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
            
            // If selection spans multiple elements, we need to handle it differently
            if (range.startContainer !== range.endContainer) {
                this.clearFormattingAcrossElements(range);
            } else {
                this.clearFormattingInElement(range);
            }
            
            // Mark document as modified
            this.currentDocument.modified = true;
            this.updateStatus();
            
            this.showMessage('All formatting cleared from selected text');
            
        } catch (error) {
            console.error('Error clearing formatting:', error);
            this.showMessage('Error clearing formatting', 'error');
        }
    }
    
    clearFormattingInElement(range) {
        try {
            const selectedText = range.toString();
            const textNode = document.createTextNode(selectedText);
            
            // Delete the selected content
            range.deleteContents();
            
            // Insert plain text
            range.insertNode(textNode);
            
            // Select the new text node
            range.selectNode(textNode);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            
        } catch (error) {
            console.error('Error clearing formatting in element:', error);
            throw error;
        }
    }
    
    clearFormattingAcrossElements(range) {
        try {
            // Extract all content and create a single text node
            const contents = range.extractContents();
            const textContent = contents.textContent;
            
            // Create a plain text node
            const textNode = document.createTextNode(textContent);
            
            // Insert the plain text
            range.insertNode(textNode);
            
            // Select the new text
            const newRange = document.createRange();
            newRange.selectNode(textNode);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(newRange);
            
        } catch (error) {
            console.error('Error clearing formatting across elements:', error);
            throw error;
        }
    }
    
    // Clear formatting from entire document
    clearAllDocumentFormatting() {
        if (confirm('This will remove ALL formatting from the entire document. Are you sure?')) {
            const editor = this.editor;
            
            // Get all text content
            const textContent = editor.textContent;
            
            // Clear the editor
            editor.innerHTML = '';
            
            // Create a single paragraph with plain text
            const paragraph = document.createElement('p');
            paragraph.textContent = textContent;
            editor.appendChild(paragraph);
            
            // Mark document as modified
            this.currentDocument.modified = true;
            this.updateStatus();
            
            this.showMessage('All formatting cleared from entire document');
        }
    }
    
    // Format painter functions
    activateFormatPainter() {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) {
            this.showMessage('Please select text to copy format from first', 'error');
            return;
        }
        
        const range = selection.getRangeAt(0);
        const selectedText = selection.toString();
        
        if (!selectedText || selectedText.trim() === '') {
            this.showMessage('Please select text to copy format from first', 'error');
            return;
        }
        
        const element = range.commonAncestorContainer.nodeType === Node.TEXT_NODE ? 
                       range.commonAncestorContainer.parentElement : 
                       range.commonAncestorContainer;
        
        // Get comprehensive format information
        const computedStyle = window.getComputedStyle(element);
        
        // Get comprehensive format information
        this.copiedFormat = {
            // Text formatting
            fontWeight: element.style.fontWeight || computedStyle.fontWeight,
            fontStyle: element.style.fontStyle || computedStyle.fontStyle,
            textDecoration: element.style.textDecoration || computedStyle.textDecoration,
            textDecorationLine: element.style.textDecorationLine || computedStyle.textDecorationLine,
            textDecorationStyle: element.style.textDecorationStyle || computedStyle.textDecorationStyle,
            textDecorationColor: element.style.textDecorationColor || computedStyle.textDecorationColor,
            
            // Font properties
            fontSize: element.style.fontSize || computedStyle.fontSize,
            fontFamily: element.style.fontFamily || computedStyle.fontFamily,
            color: element.style.color || computedStyle.color,
            backgroundColor: element.style.backgroundColor || computedStyle.backgroundColor,
            
            // Text effects
            textShadow: element.style.textShadow || computedStyle.textShadow,
            textTransform: element.style.textTransform || computedStyle.textTransform,
            letterSpacing: element.style.letterSpacing || computedStyle.letterSpacing,
            wordSpacing: element.style.wordSpacing || computedStyle.wordSpacing,
            
            // Paragraph formatting
            textAlign: element.style.textAlign || computedStyle.textAlign,
            lineHeight: element.style.lineHeight || computedStyle.lineHeight,
            textIndent: element.style.textIndent || computedStyle.textIndent,
            
            // Borders and spacing
            border: element.style.border || computedStyle.border,
            padding: element.style.padding || computedStyle.padding,
            margin: element.style.margin || computedStyle.margin
        };
        
        // Set format painter mode
        this.formatPainterActive = true;
        document.body.style.cursor = 'crosshair';
        
        // Add visual indicator
        this.showFormatPainterIndicator();
        
        this.showMessage('Format copied! Now select text to apply formatting to');
    }
    
    
    applyFormatPainter() {
        if (!this.copiedFormat) {
            this.showMessage('Please activate Format Painter first to copy formatting', 'error');
            return;
        }
        
        const selection = window.getSelection();
        if (selection.rangeCount === 0) {
            this.showMessage('Please select text to apply formatting to', 'error');
            return;
        }
        
        const range = selection.getRangeAt(0);
        const selectedText = selection.toString();
        
        if (!selectedText || selectedText.trim() === '') {
            this.showMessage('Please select text to apply formatting to', 'error');
            return;
        }
        
        try {
            // Create span with copied formatting
            const span = document.createElement('span');
            
            // Apply all copied format properties
            Object.keys(this.copiedFormat).forEach(property => {
                if (this.copiedFormat[property] && this.copiedFormat[property] !== 'none') {
                    span.style[property] = this.copiedFormat[property];
                }
            });
            
            span.textContent = selectedText;
            
            // Replace selected content
            range.deleteContents();
            range.insertNode(span);
            
            // Mark document as modified
            this.currentDocument.modified = true;
            this.updateStatus();
            
            this.showMessage('Format applied successfully');
            
            // Auto-deactivate after successful application
            this.deactivateFormatPainter();
            
        } catch (error) {
            console.error('Error applying format:', error);
            this.showMessage('Error applying format', 'error');
        }
    }
    
    showFormatPainterIndicator() {
        // Create visual indicator
        const indicator = document.createElement('div');
        indicator.id = 'format-painter-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #007acc;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        indicator.textContent = 'Format Painter Active - Click text to apply format';
        document.body.appendChild(indicator);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 5000);
    }
    
    deactivateFormatPainter() {
        this.formatPainterActive = false;
        this.copiedFormat = null;
        document.body.style.cursor = 'default';
        
        // Remove indicator
        const indicator = document.getElementById('format-painter-indicator');
        if (indicator) {
            indicator.remove();
        }
        
        this.showMessage('Format Painter deactivated');
    }
    
    // View control functions
    toggleSidebar() {
        this.sidebar.classList.toggle('hidden');
        this.showMessage('Sidebar toggled');
    }
    
    toggleRuler() {
        const rulerContainer = document.getElementById('ruler-container');
        if (!rulerContainer) {
            this.showMessage('Error: Ruler container not found', 'error');
            return;
        }
        
        const isVisible = rulerContainer.classList.contains('show');
        
        if (isVisible) {
            rulerContainer.classList.remove('show');
            this.showMessage('Ruler hidden');
        } else {
            rulerContainer.classList.add('show');
            this.updateRulerMarks();
            this.showMessage('Ruler shown');
        }
    }
    
    updateRulerMarks() {
        const horizontalMarks = document.getElementById('horizontal-marks');
        const verticalMarks = document.getElementById('vertical-marks');
        
        if (!horizontalMarks || !verticalMarks) return;
        
        // Clear existing marks
        horizontalMarks.innerHTML = '';
        verticalMarks.innerHTML = '';
        
        // Add horizontal marks (every 50px = 1cm approximately)
        const containerWidth = this.editor.offsetWidth;
        const containerHeight = this.editor.offsetHeight;
        
        for (let i = 0; i <= containerWidth; i += 50) {
            const mark = document.createElement('span');
            mark.textContent = Math.round(i / 50);
            mark.style.left = `${i + 20}px`; // Offset for vertical ruler
            mark.style.position = 'absolute';
            horizontalMarks.appendChild(mark);
        }
        
        // Add vertical marks
        for (let i = 0; i <= containerHeight; i += 50) {
            const mark = document.createElement('span');
            mark.textContent = Math.round(i / 50);
            mark.style.top = `${i + 20}px`; // Offset for horizontal ruler
            mark.style.position = 'absolute';
            verticalMarks.appendChild(mark);
        }
    }
    
    toggleInvisibles() {
        if (!this.editor) {
            this.showMessage('Error: Editor not found', 'error');
            return;
        }
        
        const isShowing = this.editor.classList.contains('show-invisibles');
        
        if (isShowing) {
            this.editor.classList.remove('show-invisibles');
            this.removeInvisibleMarkers();
            this.showMessage('Hidden characters hidden');
        } else {
            this.editor.classList.add('show-invisibles');
            this.addInvisibleMarkers();
            this.showMessage('Hidden characters shown');
        }
    }
    
    addInvisibleMarkers() {
        if (!this.editor) return;
        
        // Process all text nodes and add markers for spaces, tabs, etc.
        const walker = document.createTreeWalker(
            this.editor,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        
        textNodes.forEach(textNode => {
            const parent = textNode.parentNode;
            if (parent && parent !== this.editor) {
                const text = textNode.textContent;
                const newHTML = text
                    .replace(/ /g, '<span class="invisible-space"> </span>')
                    .replace(/\t/g, '<span class="invisible-tab">\t</span>')
                    .replace(/\n/g, '<span class="invisible-linebreak">\n</span>');
                
                if (newHTML !== text) {
                    const wrapper = document.createElement('span');
                    wrapper.innerHTML = newHTML;
                    parent.replaceChild(wrapper, textNode);
                }
            }
        });
        
        // Add paragraph markers
        const paragraphs = this.editor.querySelectorAll('p, h1, h2, h3, h4, h5, h6');
        paragraphs.forEach(p => {
            if (!p.querySelector('.invisible-paragraph')) {
                const marker = document.createElement('span');
                marker.className = 'invisible-paragraph';
                marker.innerHTML = '&nbsp;';
                p.appendChild(marker);
            }
        });
    }
    
    removeInvisibleMarkers() {
        if (!this.editor) return;
        
        // Remove all invisible character markers
        const markers = this.editor.querySelectorAll('.invisible-space, .invisible-tab, .invisible-paragraph, .invisible-linebreak');
        markers.forEach(marker => {
            const parent = marker.parentNode;
            if (parent) {
                parent.replaceChild(document.createTextNode(marker.textContent), marker);
                parent.normalize(); // Merge adjacent text nodes
            }
        });
    }
    
    toggleFocusMode() {
        document.body.classList.toggle('focus-mode');
        this.showMessage('Focus mode toggled');
    }
    
    toggleNightMode() {
        document.body.classList.toggle('night-mode');
        this.showMessage('Night mode toggled');
    }
    
    // Copy functions
    copyPlainText() {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) {
            this.showMessage('Please select text to copy first');
            return;
        }
        
        const text = selection.toString();
        
        // Store in internal MiniWord clipboard
        this.internalClipboard = {
            plainText: text,
            html: '',
            hasContent: true,
            type: 'plain'
        };
        
        // Best-effort: also try to write to system clipboard
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                this.showMessage('Plain text copied (MiniWord clipboard + system clipboard)');
            }).catch(() => {
                this.showMessage('Plain text copied (MiniWord clipboard only)');
            });
        } else {
            this.showMessage('Plain text copied (MiniWord clipboard only)');
        }
    }
    
    copyFormattedText() {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) {
            this.showMessage('Please select text to copy first');
            return;
        }
        
        const range = selection.getRangeAt(0);
        const selectedText = selection.toString();
        
        // Create a more robust HTML extraction that preserves all formatting
        const contents = range.cloneContents();
        const tempDiv = document.createElement('div');
        
        // Walk through all nodes and preserve their computed styles
        const walker = document.createTreeWalker(
            contents,
            NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        let node;
        const nodesToProcess = [];
        while (node = walker.nextNode()) {
            nodesToProcess.push(node);
        }
        
        // Process each node to preserve formatting
        nodesToProcess.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                const computedStyle = window.getComputedStyle(node);
                const inlineStyle = node.style.cssText;
                
                // Always ensure important styles are preserved as inline styles
                const importantStyles = [];
                
                // Color (most important for your case)
                if (computedStyle.color && computedStyle.color !== 'rgb(0, 0, 0)' && computedStyle.color !== 'rgb(0, 0, 0)') {
                    importantStyles.push(`color: ${computedStyle.color}`);
                }
                
                // Background color
                if (computedStyle.backgroundColor && computedStyle.backgroundColor !== 'rgba(0, 0, 0, 0)' && computedStyle.backgroundColor !== 'transparent') {
                    importantStyles.push(`background-color: ${computedStyle.backgroundColor}`);
                }
                
                // Font weight (BOLD)
                if (computedStyle.fontWeight && computedStyle.fontWeight !== 'normal' && computedStyle.fontWeight !== '400') {
                    importantStyles.push(`font-weight: ${computedStyle.fontWeight}`);
                }
                
                // Font style (ITALIC)
                if (computedStyle.fontStyle && computedStyle.fontStyle !== 'normal') {
                    importantStyles.push(`font-style: ${computedStyle.fontStyle}`);
                }
                
                // Text decoration
                if (computedStyle.textDecoration && computedStyle.textDecoration !== 'none') {
                    importantStyles.push(`text-decoration: ${computedStyle.textDecoration}`);
                }
                
                // Font size
                if (computedStyle.fontSize && computedStyle.fontSize !== '14px') {
                    importantStyles.push(`font-size: ${computedStyle.fontSize}`);
                }
                
                // Font family
                if (computedStyle.fontFamily && computedStyle.fontFamily !== 'Arial') {
                    importantStyles.push(`font-family: ${computedStyle.fontFamily}`);
                }
                
                // If we have important styles, merge them with existing inline styles
                if (importantStyles.length > 0) {
                    // Parse existing inline styles
                    const existingStyles = {};
                    if (inlineStyle && inlineStyle.trim() !== '') {
                        inlineStyle.split(';').forEach(style => {
                            const [property, value] = style.split(':').map(s => s.trim());
                            if (property && value) {
                                existingStyles[property] = value;
                            }
                        });
                    }
                    
                    // Add important styles, overriding existing ones
                    importantStyles.forEach(style => {
                        const [property, value] = style.split(':').map(s => s.trim());
                        if (property && value) {
                            existingStyles[property] = value;
                        }
                    });
                    
                    // Apply the merged styles
                    const mergedStyles = Object.entries(existingStyles)
                        .map(([prop, val]) => `${prop}: ${val}`)
                        .join('; ');
                    
                    node.style.cssText = mergedStyles;
                }
            }
        });
        
        tempDiv.appendChild(contents);
        const html = tempDiv.innerHTML;
        
        // Store in internal MiniWord clipboard (formatted)
        this.internalClipboard = {
            plainText: selectedText,
            html,
            hasContent: true,
            type: 'formatted'
        };
        
        if (navigator.clipboard && navigator.clipboard.write) {
            // Create a clipboard item with both HTML and plain text
            const clipboardItem = new ClipboardItem({
                'text/html': new Blob([html], { type: 'text/html' }),
                'text/plain': new Blob([selectedText], { type: 'text/plain' })
            });
            
            navigator.clipboard.write([clipboardItem]).then(() => {
                this.showMessage('Formatted text copied (MiniWord clipboard + system clipboard)');
            }).catch((error) => {
                console.log('Clipboard API failed:', error);
                this.showMessage('Formatted text copied (MiniWord clipboard only)');
            });
        } else {
            this.showMessage('Formatted text copied (MiniWord clipboard only)');
        }
    }
    
    // Test function for debugging copy/paste
    testCopyPaste() {
        console.log('=== TEST COPY/PASTE ===');
        
        // Create test HTML with green color
        const testHTML = '<span style="color: green; font-weight: bold;">Test Green Text</span>';
        console.log('Test HTML:', testHTML);
        
        // Try to insert it directly
        this.insertHTMLAtCursor(testHTML);
        
        // Also store it globally for manual testing
        window.testHTML = testHTML;
        console.log('Test HTML stored in window.testHTML');
        console.log('You can also test with: miniWord.insertHTMLAtCursor(window.testHTML)');
    }
    
    // Enhanced test function for copy/paste debugging
    testCopyPasteEnhanced() {
        console.log('=== ENHANCED TEST COPY/PASTE ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some test HTML with various formatting
        const testHTML = `
            <p>Normal text</p>
            <p><span style="font-weight: bold;">Bold text</span></p>
            <p><span style="font-style: italic;">Italic text</span></p>
            <p><span style="font-weight: bold; font-style: italic;">Bold and Italic text</span></p>
            <p><span style="color: red;">Red text</span></p>
            <p><span style="font-weight: bold; color: blue;">Bold blue text</span></p>
        `;
        
        this.editor.innerHTML = testHTML;
        this.showMessage('Enhanced test content inserted. Select text and try Formatted Copy, then Paste Formatted.');
        
        // Log the current HTML content
        console.log('Editor HTML:', this.editor.innerHTML);
        console.log('Contains bold:', this.editor.innerHTML.includes('font-weight: bold'));
        console.log('Contains italic:', this.editor.innerHTML.includes('font-style: italic'));
        console.log('Contains colors:', this.editor.innerHTML.includes('color: red') || this.editor.innerHTML.includes('color: blue'));
    }
    
    // Test function for plain text vs formatted paste
    testPasteFunctions() {
        console.log('=== TEST PASTE FUNCTIONS ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some test HTML with various formatting
        const testHTML = `
            <p><span style="font-weight: bold; color: red;">Bold Red Text</span></p>
            <p><span style="font-style: italic; color: blue;">Italic Blue Text</span></p>
            <p><span style="font-weight: bold; font-style: italic; color: green;">Bold Italic Green Text</span></p>
        `;
        
        this.editor.innerHTML = testHTML;
        this.showMessage('Test content inserted. Select text and try both "Paste Plain Text" and "Paste Formatted" to see the difference.');
        
        // Log the current HTML content
        console.log('Editor HTML:', this.editor.innerHTML);
        console.log('Instructions:');
        console.log('1. Select some formatted text');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Try "Paste Plain Text" - should strip all formatting');
        console.log('4. Try "Paste Formatted" - should preserve formatting');
    }
    
    // Quick test for plain text paste
    testPlainTextPaste() {
        console.log('=== TEST PLAIN TEXT PASTE ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some formatted text
        const formattedHTML = '<span style="font-weight: bold; color: red;">Bold Red Text</span>';
        this.editor.innerHTML = formattedHTML;
        
        console.log('Formatted HTML inserted:', formattedHTML);
        console.log('Now select this text and use "Formatted Copy", then try "Paste Plain Text"');
        console.log('The pasted text should be plain (no bold, no red color)');
        
        this.showMessage('Formatted text inserted. Select it, copy with "Formatted Copy", then test "Paste Plain Text"');
    }
    
    // Ultimate test for plain text paste
    testUltimatePlainTextPaste() {
        console.log('=== ULTIMATE PLAIN TEXT PASTE TEST ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert heavily formatted text
        const heavilyFormattedHTML = `
            <p><span style="font-weight: bold; color: red; font-size: 20px;">BOLD RED LARGE TEXT</span></p>
            <p><span style="font-style: italic; color: blue; text-decoration: underline;">ITALIC BLUE UNDERLINED TEXT</span></p>
            <p><span style="font-weight: bold; font-style: italic; color: green; background-color: yellow;">BOLD ITALIC GREEN YELLOW BACKGROUND TEXT</span></p>
        `;
        
        this.editor.innerHTML = heavilyFormattedHTML;
        
        console.log('Heavily formatted HTML inserted:', heavilyFormattedHTML);
        console.log('Instructions:');
        console.log('1. Select ALL the formatted text above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Use "Paste Plain Text" - should paste ONLY plain text (no formatting)');
        console.log('4. Check console logs to see the formatting being stripped');
        
        this.showMessage('Heavily formatted text inserted. Select it, copy with "Formatted Copy", then test "Paste Plain Text" - should be completely plain!');
    }
    
    // Test Direct Copy vs Formatted Copy behavior
    testDirectVsFormattedCopy() {
        console.log('=== TEST DIRECT COPY VS FORMATTED COPY ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert heavily formatted text
        const formattedHTML = `
            <p><span style="font-weight: bold; color: red;">BOLD RED TEXT</span></p>
            <p><span style="font-style: italic; color: blue;">ITALIC BLUE TEXT</span></p>
        `;
        
        this.editor.innerHTML = formattedHTML;
        
        console.log('Formatted HTML inserted:', formattedHTML);
        console.log('TEST INSTRUCTIONS:');
        console.log('1. Select the formatted text above');
        console.log('2. Use "Direct Copy" to copy it');
        console.log('3. Try "Paste Plain Text" - should paste PLAIN TEXT only');
        console.log('4. Try "Paste Formatted" - should paste PLAIN TEXT only (no HTML available)');
        console.log('');
        console.log('5. Now use "Formatted Copy" to copy the same text');
        console.log('6. Try "Paste Plain Text" - should paste PLAIN TEXT only');
        console.log('7. Try "Paste Formatted" - should paste WITH FORMATTING');
        
        this.showMessage('Formatted text inserted. Test both "Direct Copy" and "Formatted Copy" with both paste options!');
    }
    
    // Comprehensive test for all copy/paste combinations
    testAllCopyPasteCombinations() {
        console.log('=== COMPREHENSIVE COPY/PASTE TEST ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert heavily formatted text
        const formattedHTML = `
            <p><span style="font-weight: bold; color: red; font-size: 18px;">BOLD RED LARGE TEXT</span></p>
            <p><span style="font-style: italic; color: blue; text-decoration: underline;">ITALIC BLUE UNDERLINED TEXT</span></p>
            <p><span style="font-weight: bold; font-style: italic; color: green; background-color: yellow;">BOLD ITALIC GREEN YELLOW BACKGROUND TEXT</span></p>
        `;
        
        this.editor.innerHTML = formattedHTML;
        
        console.log('Heavily formatted HTML inserted:', formattedHTML);
        console.log('');
        console.log('=== TEST SCENARIOS ===');
        console.log('');
        console.log('SCENARIO 1: Direct Copy + Paste Plain Text');
        console.log('1. Select the formatted text above');
        console.log('2. Use "Direct Copy" to copy it');
        console.log('3. Use "Paste Plain Text"');
        console.log('EXPECTED: Plain text only (no formatting)');
        console.log('');
        console.log('SCENARIO 2: Direct Copy + Paste Formatted');
        console.log('1. Select the formatted text above');
        console.log('2. Use "Direct Copy" to copy it');
        console.log('3. Use "Paste Formatted"');
        console.log('EXPECTED: Plain text only (no HTML available)');
        console.log('');
        console.log('SCENARIO 3: Formatted Copy + Paste Plain Text');
        console.log('1. Select the formatted text above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Use "Paste Plain Text"');
        console.log('EXPECTED: Plain text only (formatting stripped)');
        console.log('');
        console.log('SCENARIO 4: Formatted Copy + Paste Formatted');
        console.log('1. Select the formatted text above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Use "Paste Formatted"');
        console.log('EXPECTED: Text with formatting preserved');
        console.log('');
        console.log('Check console logs for debugging information!');
        
        this.showMessage('Comprehensive test content inserted. Test all 4 scenarios above!');
    }
    
    // Simple test for Paste Plain Text functionality
    testPastePlainTextOnly() {
        console.log('=== TEST PASTE PLAIN TEXT ONLY ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some formatted text
        const formattedHTML = '<p><span style="font-weight: bold; color: red;">BOLD RED TEXT</span></p>';
        this.editor.innerHTML = formattedHTML;
        
        console.log('Formatted HTML inserted:', formattedHTML);
        console.log('');
        console.log('TEST INSTRUCTIONS:');
        console.log('1. Select the "BOLD RED TEXT" above');
        console.log('2. Use "Direct Copy" to copy it');
        console.log('3. Click "Paste Plain Text"');
        console.log('EXPECTED: Should paste "BOLD RED TEXT" as plain text (no bold, no red)');
        console.log('');
        console.log('4. Now use "Formatted Copy" to copy the same text');
        console.log('5. Click "Paste Plain Text" again');
        console.log('EXPECTED: Should paste "BOLD RED TEXT" as plain text (no bold, no red)');
        console.log('');
        console.log('Check console logs to see what\'s happening!');
        
        this.showMessage('Formatted text inserted. Test "Paste Plain Text" with both copy methods!');
    }
    
    // Debug test for Formatted Copy + Paste Formatted
    testFormattedCopyPaste() {
        console.log('=== DEBUG FORMATTED COPY + PASTE FORMATTED ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some formatted text
        const formattedHTML = '<p><span style="font-weight: bold; color: red;">BOLD RED TEXT</span></p>';
        this.editor.innerHTML = formattedHTML;
        
        console.log('Formatted HTML inserted:', formattedHTML);
        console.log('');
        console.log('DEBUG INSTRUCTIONS:');
        console.log('1. Select the "BOLD RED TEXT" above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Check console logs for "COPY DEBUG" - should show HTML with formatting');
        console.log('4. Click "Paste Formatted"');
        console.log('5. Check console logs for "PASTE DEBUG" - should show HTML being read');
        console.log('6. The pasted text should be BOLD and RED');
        console.log('');
        console.log('If it doesn\'t work, check the console logs to see where the issue is!');
        
        this.showMessage('Debug test content inserted. Follow the instructions and check console logs!');
    }
    
    // Simple test for both paste functions
    testBothPasteFunctions() {
        console.log('=== TEST BOTH PASTE FUNCTIONS ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some formatted text
        const formattedHTML = '<p><span style="font-weight: bold; color: red;">BOLD RED TEXT</span></p>';
        this.editor.innerHTML = formattedHTML;
        
        console.log('Formatted HTML inserted:', formattedHTML);
        console.log('');
        console.log('TEST INSTRUCTIONS:');
        console.log('');
        console.log('TEST 1: Formatted Copy + Paste Formatted');
        console.log('1. Select the "BOLD RED TEXT" above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Click "Paste Formatted"');
        console.log('EXPECTED: Should paste BOLD RED TEXT (with formatting)');
        console.log('');
        console.log('TEST 2: Formatted Copy + Paste Plain Text');
        console.log('1. Select the "BOLD RED TEXT" above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Click "Paste Plain Text"');
        console.log('EXPECTED: Should paste "BOLD RED TEXT" as plain text (no formatting)');
        console.log('');
        console.log('TEST 3: Direct Copy + Paste Plain Text');
        console.log('1. Select the "BOLD RED TEXT" above');
        console.log('2. Use "Direct Copy" to copy it');
        console.log('3. Click "Paste Plain Text"');
        console.log('EXPECTED: Should paste "BOLD RED TEXT" as plain text (no formatting)');
        console.log('');
        console.log('Check console logs for debugging information!');
        
        this.showMessage('Test content inserted. Test all 3 scenarios above!');
    }
    
    // Simple test for restored functionality
    testRestoredCopyPaste() {
        console.log('=== TEST RESTORED COPY/PASTE FUNCTIONALITY ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert some formatted text
        const formattedHTML = '<p><span style="font-weight: bold; color: red;">BOLD RED TEXT</span></p>';
        this.editor.innerHTML = formattedHTML;
        
        console.log('Formatted HTML inserted:', formattedHTML);
        console.log('');
        console.log('RESTORED FUNCTIONALITY TEST:');
        console.log('');
        console.log('1. Select the "BOLD RED TEXT" above');
        console.log('2. Use "Formatted Copy" to copy it');
        console.log('3. Click "Paste Formatted"');
        console.log('EXPECTED: Should paste BOLD RED TEXT (with formatting preserved)');
        console.log('');
        console.log('4. Now use "Direct Copy" to copy the same text');
        console.log('5. Click "Paste Plain Text"');
        console.log('EXPECTED: Should paste "BOLD RED TEXT" as plain text (no formatting)');
        console.log('');
        console.log('This should now work as it did before!');
        
        this.showMessage('Restored functionality test. Try Formatted Copy + Paste Formatted!');
    }
    
    // Test Format Painter with combined formatting
    testFormatPainterCombined() {
        console.log('=== TEST FORMAT PAINTER WITH COMBINED FORMATTING ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert text with combined formatting (bold + underline + color)
        const combinedHTML = '<p><span style="font-weight: bold; text-decoration: underline; color: red;">BOLD UNDERLINED RED TEXT</span></p>';
        this.editor.innerHTML = combinedHTML;
        
        console.log('Combined formatting HTML inserted:', combinedHTML);
        console.log('');
        console.log('FORMAT PAINTER TEST:');
        console.log('');
        console.log('1. Select the "BOLD UNDERLINED RED TEXT" above');
        console.log('2. Click the Format Painter icon');
        console.log('3. Click "Copy Format" button');
        console.log('4. Check console logs for "FORMAT PAINTER COPY DEBUG"');
        console.log('5. Select some plain text elsewhere');
        console.log('6. Click "Apply Format" button');
        console.log('7. Check console logs for "FORMAT PAINTER DEBUG"');
        console.log('8. The text should be BOLD, UNDERLINED, and RED');
        console.log('');
        console.log('If underline is missing, check the console logs to see what\'s being copied and applied!');
        
        this.showMessage('Format Painter test with combined formatting. Check console logs!');
    }
    
    // Comprehensive test for Format Painter with all formatting types
    testFormatPainterAllTypes() {
        console.log('=== COMPREHENSIVE FORMAT PAINTER TEST ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert text with ALL possible formatting
        const allFormatHTML = `
            <p><span style="font-weight: bold; font-style: italic; text-decoration: underline; color: red; background-color: yellow; font-size: 18px; text-transform: uppercase; letter-spacing: 2px;">BOLD ITALIC UNDERLINED RED YELLOW BACKGROUND LARGE UPPERCASE SPACED TEXT</span></p>
        `;
        this.editor.innerHTML = allFormatHTML;
        
        console.log('All formatting HTML inserted:', allFormatHTML);
        console.log('');
        console.log('COMPREHENSIVE FORMAT PAINTER TEST:');
        console.log('');
        console.log('This text has:');
        console.log('- Bold (font-weight: bold)');
        console.log('- Italic (font-style: italic)');
        console.log('- Underline (text-decoration: underline)');
        console.log('- Red color (color: red)');
        console.log('- Yellow background (background-color: yellow)');
        console.log('- Large size (font-size: 18px)');
        console.log('- Uppercase (text-transform: uppercase)');
        console.log('- Letter spacing (letter-spacing: 2px)');
        console.log('');
        console.log('TEST STEPS:');
        console.log('1. Select the formatted text above');
        console.log('2. Click the Format Painter icon');
        console.log('3. Click "Copy Format" button');
        console.log('4. Check console logs for "FORMAT PAINTER COPY DEBUG"');
        console.log('5. Select some plain text elsewhere');
        console.log('6. Click "Apply Format" button');
        console.log('7. Check console logs for "FORMAT PAINTER DEBUG"');
        console.log('8. The text should have ALL the formatting above');
        console.log('');
        console.log('If any formatting is missing, check the console logs to see what\'s being copied and applied!');
        
        this.showMessage('Comprehensive Format Painter test. Check console logs for all formatting!');
    }
    
    // Simple test for the improved Format Painter
    testImprovedFormatPainter() {
        console.log('=== TEST IMPROVED FORMAT PAINTER ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert text with multiple combined formatting
        const multiFormatHTML = '<p><span style="font-weight: bold; text-decoration: underline; color: red; background-color: yellow;">BOLD UNDERLINED RED YELLOW TEXT</span></p>';
        this.editor.innerHTML = multiFormatHTML;
        
        console.log('Multi-format HTML inserted:', multiFormatHTML);
        console.log('');
        console.log('IMPROVED FORMAT PAINTER TEST:');
        console.log('');
        console.log('This text has:');
        console.log('- Bold (font-weight: bold)');
        console.log('- Underline (text-decoration: underline)');
        console.log('- Red color (color: red)');
        console.log('- Yellow background (background-color: yellow)');
        console.log('');
        console.log('TEST STEPS:');
        console.log('1. Select the formatted text above');
        console.log('2. Click the Format Painter icon');
        console.log('3. Click "Copy Format" button');
        console.log('4. Check console logs for "FORMAT PAINTER COPY DEBUG"');
        console.log('5. You should see ALL 4 properties being captured');
        console.log('6. Select some plain text elsewhere');
        console.log('7. Click "Apply Format" button');
        console.log('8. Check console logs for "FORMAT PAINTER DEBUG"');
        console.log('9. You should see ALL 4 properties being applied');
        console.log('10. The text should be BOLD, UNDERLINED, RED, with YELLOW background');
        console.log('');
        console.log('The improved Format Painter should capture and apply ALL formatting!');
        
        this.showMessage('Improved Format Painter test. Check console logs for ALL formatting!');
    }
    
    // Simple test for the restored Format Painter
    testRestoredFormatPainter() {
        console.log('=== TEST RESTORED FORMAT PAINTER ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert text with basic formatting
        const basicFormatHTML = '<p><span style="font-weight: bold; text-decoration: underline; color: red;">BOLD UNDERLINED RED TEXT</span></p>';
        this.editor.innerHTML = basicFormatHTML;
        
        console.log('Basic format HTML inserted:', basicFormatHTML);
        console.log('');
        console.log('RESTORED FORMAT PAINTER TEST:');
        console.log('');
        console.log('This text has:');
        console.log('- Bold (font-weight: bold)');
        console.log('- Underline (text-decoration: underline)');
        console.log('- Red color (color: red)');
        console.log('');
        console.log('TEST STEPS:');
        console.log('1. Select the formatted text above');
        console.log('2. Click the Format Painter icon');
        console.log('3. Click "Copy Format" button');
        console.log('4. Check console logs for "FORMAT PAINTER COPY DEBUG"');
        console.log('5. Select some plain text elsewhere');
        console.log('6. Click "Apply Format" button');
        console.log('7. Check console logs for "FORMAT PAINTER DEBUG"');
        console.log('8. The text should be BOLD, UNDERLINED, and RED');
        console.log('');
        console.log('This is the restored simple version of Format Painter!');
        
        this.showMessage('Restored Format Painter test. Simple and straightforward!');
    }
    
    // Test for the original Format Painter
    testOriginalFormatPainter() {
        console.log('=== TEST ORIGINAL FORMAT PAINTER ===');
        
        // Clear editor first
        this.editor.innerHTML = '';
        
        // Insert text with formatting
        const formatHTML = '<p><span style="font-weight: bold; text-decoration: underline; color: red;">BOLD UNDERLINED RED TEXT</span></p>';
        this.editor.innerHTML = formatHTML;
        
        console.log('Format HTML inserted:', formatHTML);
        console.log('');
        console.log('ORIGINAL FORMAT PAINTER TEST:');
        console.log('');
        console.log('This text has:');
        console.log('- Bold (font-weight: bold)');
        console.log('- Underline (text-decoration: underline)');
        console.log('- Red color (color: red)');
        console.log('');
        console.log('TEST STEPS:');
        console.log('1. Select the formatted text above');
        console.log('2. Click the Format Painter icon');
        console.log('3. Click "Copy Format" button');
        console.log('4. Select some plain text elsewhere');
        console.log('5. Click "Apply Format" button');
        console.log('6. The text should be BOLD, UNDERLINED, and RED');
        console.log('');
        console.log('This is the original Format Painter - no debugging, simple and clean!');
        
        this.showMessage('Original Format Painter test. Clean and simple!');
    }
    
    
    
    // Table functions
    bindTableEvents() {
        const preview = document.getElementById('table-preview');
        if (!preview) return;
        preview.innerHTML = '';
        const table = document.createElement('table');
        table.style.borderCollapse = 'collapse';
        table.style.width = '100%';
        table.style.margin = '10px 0';
        for (let i = 1; i <= 5; i++) {
            const row = document.createElement('tr');
            for (let j = 1; j <= 5; j++) {
                const cell = document.createElement('td');
                cell.style.padding = '8px';
                cell.style.border = '1px solid #ccc';
                cell.style.cursor = 'pointer';
                cell.style.textAlign = 'center';
                cell.style.backgroundColor = '#f9f9f9';
                cell.textContent = `${i}×${j}`;
                cell.dataset.rows = i;
                cell.dataset.cols = j;
                cell.addEventListener('click', () => {
                    this.insertTable(i, j);
                    this.showMessage(`${i}×${j} table inserted`);
                });
                cell.addEventListener('mouseenter', () => {
                    cell.style.backgroundColor = '#e3f2fd';
                });
                cell.addEventListener('mouseleave', () => {
                    cell.style.backgroundColor = '#f9f9f9';
                });
                row.appendChild(cell);
            }
            table.appendChild(row);
        }
        preview.appendChild(table);
    }

    insertTable(rows = 3, cols = 3) {
        let table = '<table border="1" style="border-collapse: collapse; width: 100%; margin: 12px auto; display: table;">';
        for (let i = 0; i < rows; i++) {
            table += '<tr>';
            for (let j = 0; j < cols; j++) {
                table += '<td style="padding: 8px; border: 1px solid #ccc; height: 30px;">&nbsp;</td>';
            }
            table += '</tr>';
        }
        table += '</table>';
        
        document.execCommand('insertHTML', false, table);
        this.showMessage(`${rows}×${cols} table inserted`);
    }


    createTableSizePreview() {
        console.log('createTableSizePreview called'); // Debug log
        const preview = document.getElementById('table-size-preview');
        console.log('Preview element:', preview); // Debug log
        if (!preview) {
            console.error('Preview element not found!'); // Debug log
            return;
        }
        
        preview.innerHTML = '';
        
        // Create a 5x5 grid with proper layout
        for (let rows = 1; rows <= 5; rows++) {
            for (let cols = 1; cols <= 5; cols++) {
                const cell = document.createElement('div');
                cell.className = 'table-size-cell';
                cell.textContent = `${rows}×${cols}`;
                cell.dataset.rows = rows;
                cell.dataset.cols = cols;
                
                // Set default selection (3x3)
                if (rows === 3 && cols === 3) {
                    cell.classList.add('selected');
                    this.selectedTableSize = { rows: 3, cols: 3 };
                }
                
                cell.addEventListener('click', () => {
                    // Remove previous selection
                    preview.querySelectorAll('.table-size-cell').forEach(c => c.classList.remove('selected'));
                    // Add selection to clicked cell
                    cell.classList.add('selected');
                    this.selectedTableSize = { rows: rows, cols: cols };
                    console.log('Selected table size:', this.selectedTableSize); // Debug log
                });
                
                preview.appendChild(cell);
            }
        }
        console.log('Table size preview created with', preview.children.length, 'cells'); // Debug log
    }

    insertSelectedTable() {
        console.log('insertSelectedTable function called'); // Debug log
        
        // Get the currently selected cell
        const selectedCell = document.querySelector('#table-size-preview .table-size-cell.selected');
        console.log('Selected cell:', selectedCell); // Debug log
        
        if (selectedCell) {
            this.selectedTableSize = { 
                rows: parseInt(selectedCell.dataset.rows), 
                cols: parseInt(selectedCell.dataset.cols) 
            };
            console.log('Table size from selected cell:', this.selectedTableSize); // Debug log
        }
        
        if (!this.selectedTableSize) {
            this.selectedTableSize = { rows: 3, cols: 3 };
            console.log('Using default table size:', this.selectedTableSize); // Debug log
        }
        
        const { rows, cols } = this.selectedTableSize;
        console.log('Final table size:', rows, 'x', cols); // Debug log
        
        // Get table type selection - use default values since UI elements were removed
        const tableType = 'full-width'; // Default to full-width table
        const autoAdjustWidth = true; // Default to auto-adjust width
        const addTitle = false; // Default to no title
        
        console.log('Table type:', tableType); // Debug log
        
        // Use the appropriate table insertion method
        if (tableType === 'inline') {
            this.insertInlineTable(rows, cols);
        } else {
            this.insertTable(rows, cols);
        }
        
        // Add title if requested
        if (addTitle) {
            const titleHTML = '<p><strong>Table Title</strong></p>';
            this.insertContent(titleHTML);
        }
        
        this.showMessage(`${rows}×${cols} ${tableType} table inserted successfully`);
    }


    setupChartModalEvents() {
        // Handle data source radio buttons
        const dataSourceRadios = document.querySelectorAll('input[name="data-source"]');
        const detectedTablesSection = document.getElementById('detected-tables-section');
        
        dataSourceRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                // Hide all sections first
                const manualTableSection = document.getElementById('manual-table-section');
                if (manualTableSection) manualTableSection.style.display = 'none';
                if (detectedTablesSection) detectedTablesSection.style.display = 'none';
                
                // Show appropriate section based on selection
                if (radio.value === 'table') {
                    if (manualTableSection) manualTableSection.style.display = 'block';
                } else {
                    if (detectedTablesSection) detectedTablesSection.style.display = 'block';
                }
            });
        });

        // Handle chart type change
        const chartTypeSelect = document.getElementById('chart-type');
        chartTypeSelect.addEventListener('change', () => {
            this.updateChartPreview();
        });
    }

    testTableDetection() {
        console.log('=== TESTING TABLE DETECTION ===');
        console.log('1. Editor element:', this.editor);
        console.log('2. Editor exists:', !!this.editor);
        console.log('3. Editor ID:', this.editor ? this.editor.id : 'N/A');
        console.log('4. Editor innerHTML length:', this.editor ? this.editor.innerHTML.length : 'N/A');
        console.log('5. Editor innerHTML preview:', this.editor ? this.editor.innerHTML.substring(0, 300) : 'N/A');
        
        // Test different selectors
        const editorTables = this.editor ? this.editor.querySelectorAll('table') : [];
        const allTables = document.querySelectorAll('table');
        const bodyTables = document.body ? document.body.querySelectorAll('table') : [];
        
        console.log('6. Tables in editor:', editorTables.length);
        console.log('7. Tables in document:', allTables.length);
        console.log('8. Tables in body:', bodyTables.length);
        
        // Show table details
        if (allTables.length > 0) {
            console.log('9. First table details:');
            console.log('   - Tag name:', allTables[0].tagName);
            console.log('   - Class name:', allTables[0].className);
            console.log('   - InnerHTML:', allTables[0].innerHTML);
        }
        
        // Test detected-tables-list element
        const detectedTablesList = document.getElementById('detected-tables-list');
        console.log('10. detected-tables-list element:', detectedTablesList);
        console.log('11. detected-tables-list exists:', !!detectedTablesList);
        
        if (detectedTablesList) {
            console.log('12. detected-tables-list innerHTML:', detectedTablesList.innerHTML);
        }
        
        console.log('=== END TEST ===');
        
        // Now call the actual detection
        this.detectTablesInDocument();
    }

    detectTablesInDocument() {
        console.log('detectTablesInDocument called'); // Debug log
        console.log('Editor element:', this.editor); // Debug log
        console.log('Editor innerHTML:', this.editor ? this.editor.innerHTML.substring(0, 200) : 'No editor'); // Debug log
        
        // Try multiple selectors to find tables
        let tables = this.editor ? this.editor.querySelectorAll('table') : [];
        console.log('Found tables with querySelectorAll:', tables.length); // Debug log
        
        // Also try searching in the entire document
        const allTables = document.querySelectorAll('table');
        console.log('Found tables in entire document:', allTables.length); // Debug log
        
        // Use tables from editor if available, otherwise use all tables
        if (tables.length === 0 && allTables.length > 0) {
            console.log('Using tables from entire document'); // Debug log
            tables = allTables;
        }
        
        const detectedTablesList = document.getElementById('detected-tables-list');
        console.log('Detected tables list element:', detectedTablesList); // Debug log
        
        if (!detectedTablesList) {
            console.error('detected-tables-list element not found!'); // Debug log
            return;
        }
        
        if (tables.length === 0) {
            console.log('No tables found, showing "No tables detected" message'); // Debug log
            detectedTablesList.innerHTML = '<p style="color: #666; font-style: italic;">No tables detected in document</p>';
            return;
        }

        detectedTablesList.innerHTML = '';
        tables.forEach((table, index) => {
            const tableData = this.extractTableData(table);
            const tableItem = document.createElement('div');
            tableItem.className = 'table-item';
            tableItem.style.cssText = 'padding: 8px; border: 1px solid #e1e5e9; border-radius: 4px; margin-bottom: 8px; cursor: pointer; transition: background-color 0.2s;';
            tableItem.innerHTML = `
                <div style="font-weight: 500; margin-bottom: 4px;">Table ${index + 1}</div>
                <div style="font-size: 12px; color: #666;">${tableData.rows} rows × ${tableData.cols} columns</div>
                <div style="font-size: 11px; color: #999; margin-top: 2px;">Click to preview data</div>
            `;
            
            tableItem.addEventListener('click', () => {
                this.selectTableForChart(table, tableData, index);
            });
            
            tableItem.addEventListener('mouseenter', () => {
                tableItem.style.backgroundColor = '#f8f9fa';
            });
            
            tableItem.addEventListener('mouseleave', () => {
                tableItem.style.backgroundColor = 'white';
            });

            detectedTablesList.appendChild(tableItem);
        });
    }

    extractTableData(table) {
        const rows = table.querySelectorAll('tr');
        const cols = rows.length > 0 ? rows[0].querySelectorAll('td, th').length : 0;
        
        const data = [];
        rows.forEach(row => {
            const cells = row.querySelectorAll('td, th');
            const rowData = [];
            cells.forEach(cell => {
                rowData.push(cell.textContent.trim() || '');
            });
            data.push(rowData);
        });
        
        return {
            rows: rows.length,
            cols: cols,
            data: data
        };
    }

    selectTableForChart(table, tableData, index) {
        console.log('Selected table for chart:', tableData); // Debug log
        
        // Highlight selected table
        document.querySelectorAll('.table-item').forEach(item => {
            item.style.backgroundColor = 'white';
            item.style.borderColor = '#e1e5e9';
        });
        
        const selectedItem = document.querySelectorAll('.table-item')[index];
        selectedItem.style.backgroundColor = '#e3f2fd';
        selectedItem.style.borderColor = '#2196f3';
        
        // Store selected table data
        this.selectedTableData = tableData;
        this.selectedTableElement = table;
        
        // Update chart preview
        this.updateChartPreview();
    }

    updateChartPreview() {
        if (!this.selectedTableData) return;
        
        const chartType = document.getElementById('chart-type').value;
        const chartTitle = document.getElementById('chart-title').value || 'Chart';
        
        console.log('Updating chart preview:', chartType, chartTitle); // Debug log
    }

    insertSelectedChart() {
        console.log('insertSelectedChart called'); // Debug log
        
        const chartType = document.getElementById('chart-type').value;
        const chartTitle = document.getElementById('chart-title').value || 'Chart';
        const dataSource = document.querySelector('input[name="data-source"]:checked').value;
        
        let chartData;
        
        if (dataSource === 'table') {
            const tableHeaders = document.getElementById('table-headers').value;
            const tableData = document.getElementById('table-data').value;
            if (!tableHeaders.trim() || !tableData.trim()) {
                this.showMessage('Please enter both table headers and data');
                return;
            }
            chartData = this.parseManualTableData(tableHeaders, tableData);
        } else {
            // Auto-detect mode - check if any table is selected
            const selectedTableItem = document.querySelector('#detected-tables-list .table-item[style*="background-color: #e3f2fd"]');
            if (!selectedTableItem && !this.selectedTableData) {
                // Try to refresh table detection first
                console.log('No table selected, attempting to refresh detection...'); // Debug log
                this.detectTablesInDocument();
                
                // Check again after refresh
                const refreshedSelectedItem = document.querySelector('#detected-tables-list .table-item[style*="background-color: #e3f2fd"]');
                if (!refreshedSelectedItem && !this.selectedTableData) {
                    this.showMessage('Please select a table from the detected tables list or use manual table input');
                    return;
                }
            }
            
            // If no table is selected but we have selectedTableData, use it
            if (!this.selectedTableData) {
                // Try to get the first available table
                let tables = this.editor ? this.editor.querySelectorAll('table') : [];
                if (tables.length === 0) {
                    // Try searching in the entire document
                    tables = document.querySelectorAll('table');
                }
                if (tables.length === 0) {
                    this.showMessage('No tables found in document. Please insert a table first or use manual table input.');
                    return;
                }
                // Use the first table
                const firstTable = tables[0];
                this.selectedTableData = this.extractTableData(firstTable);
                console.log('Using first available table:', this.selectedTableData); // Debug log
            }
            
            chartData = this.selectedTableData.data;
        }
        
        if (!chartData || chartData.length === 0) {
            this.showMessage('No data available for chart generation');
            return;
        }
        
        console.log('Generating chart:', chartType, chartTitle, chartData); // Debug log
        console.log('Chart data structure:', JSON.stringify(chartData, null, 2)); // Debug log
        
        // Generate chart HTML
        const chartHTML = this.generateChartHTML(chartType, chartTitle, chartData);
        
        // Insert chart into editor using the proper content insertion method
        this.insertContent(chartHTML);
        this.showMessage(`${chartType} chart inserted successfully`);
        
        // Close modal
        this.closeChartModal();
    }

    parseManualData(data) {
        const lines = data.trim().split('\n');
        const parsedData = [];
        
        lines.forEach(line => {
            if (line.trim()) {
                const values = line.split(',').map(val => val.trim());
                parsedData.push(values);
            }
        });
        
        return parsedData;
    }

    generateChartHTML(chartType, title, data) {
        const chartId = 'chart_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Create a chart that integrates seamlessly with document flow
        let chartHTML = `
            <div class="inserted-chart-container" id="${chartId}_container" style="
                margin: 20px 0;
                padding: 15px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: #f9f9f9;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
                clear: both;
                display: block;
            ">
                <h3 style="margin: 0 0 8px 0; color: #333; text-align: center; font-size: 14px; font-weight: bold;">${title}</h3>
                <div class="chart-content" id="${chartId}" style="min-height: 200px; padding: 10px; background: white; border-radius: 3px;">
        `;
        
        if (chartType === 'bar') {
            chartHTML += this.generateBarChart(data);
        } else if (chartType === 'pie') {
            chartHTML += this.generatePieChart(data);
        }
        
        chartHTML += `
                </div>
                <div style="margin-top: 5px; font-size: 10px; color: #666; text-align: center;">
                    Chart Type: ${chartType.charAt(0).toUpperCase() + chartType.slice(1)} Chart
                </div>
            </div>
        `;
        
        return chartHTML;
    }

    generateBarChart(data) {
        if (data.length < 2) return '<p>Insufficient data for chart</p>';
        
        const headers = data[0];
        const values = data.slice(1);
        
        // If we have multiple columns, treat each column as a separate series
        if (headers.length > 2) {
            return this.generateMultiSeriesBarChart(data);
        }
        
        // Single series bar chart (original logic)
        let chartHTML = '<div style="display: flex; align-items: end; justify-content: center; gap: 20px; padding: 20px;">';
        const maxValue = Math.max(...values.map(row => 
            Math.max(...row.slice(1).map(val => parseFloat(val) || 0))
        ));
        
        values.forEach(row => {
            const label = row[0];
            const value = parseFloat(row[1]) || 0;
            const height = (value / maxValue) * 200;
            
            chartHTML += `
                <div style="display: flex; flex-direction: column; align-items: center; margin: 0 10px;">
                    <div style="width: 40px; height: ${height}px; background: linear-gradient(to top, #2196f3, #64b5f6); border-radius: 4px 4px 0 0; margin-bottom: 8px;"></div>
                    <div style="font-size: 12px; color: #666; text-align: center; max-width: 60px; word-wrap: break-word;">${label}</div>
                    <div style="font-size: 10px; color: #999; margin-top: 2px;">${value}</div>
                </div>
            `;
        });
        
        chartHTML += '</div>';
        return chartHTML;
    }

    generateMultiSeriesBarChart(data) {
        const headers = data[0];
        const values = data.slice(1);
        
        // Get all numeric columns (skip first column which is usually labels)
        const numericColumns = headers.slice(1);
        const colors = ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4'];
        
        // Calculate max value across all series
        let maxValue = 0;
        values.forEach(row => {
            numericColumns.forEach((_, colIndex) => {
                const value = parseFloat(row[colIndex + 1]) || 0;
                maxValue = Math.max(maxValue, value);
            });
        });
        
        let chartHTML = '<div style="display: flex; flex-direction: column; gap: 20px;">';
        
        // Create a bar for each data row
        values.forEach(row => {
            const rowLabel = row[0];
            chartHTML += `
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #333;">${rowLabel}</div>
                    <div style="display: flex; align-items: end; gap: 10px;">
            `;
            
            // Create bars for each column in this row
            numericColumns.forEach((header, colIndex) => {
                const value = parseFloat(row[colIndex + 1]) || 0;
                const height = (value / maxValue) * 150;
                const color = colors[colIndex % colors.length];
                
                chartHTML += `
                    <div style="display: flex; flex-direction: column; align-items: center; margin: 0 5px;">
                        <div style="width: 30px; height: ${height}px; background: linear-gradient(to top, ${color}, ${color}88); border-radius: 4px 4px 0 0; margin-bottom: 8px;"></div>
                        <div style="font-size: 11px; color: #666; text-align: center; max-width: 50px; word-wrap: break-word;">${header}</div>
                        <div style="font-size: 10px; color: #999; margin-top: 2px;">${value}</div>
                    </div>
                `;
            });
            
            chartHTML += `
                    </div>
                </div>
            `;
        });
        
        chartHTML += '</div>';
        return chartHTML;
    }

    generatePieChart(data) {
        if (data.length < 2) return '<p>Insufficient data for pie chart</p>';
        
        const headers = data[0];
        const values = data.slice(1);
        
        // For pie chart, we'll use the first row of data and treat each column as a slice
        if (values.length === 0) return '<p>No data available for pie chart</p>';
        
        const firstRow = values[0];
        const numericColumns = headers.slice(1);
        const colors = ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4'];
        
        // Clean and parse numeric values
        const cleanData = [];
        numericColumns.forEach((header, colIndex) => {
            const rawValue = firstRow[colIndex + 1];
            // Extract numeric part from string (e.g., "10Chart" -> 10)
            const numericValue = parseFloat(rawValue.toString().replace(/[^0-9.-]/g, '')) || 0;
            cleanData.push({
                label: header,
                value: numericValue
            });
        });
        
        // Calculate total for percentage calculation
        const total = cleanData.reduce((sum, item) => sum + item.value, 0);
        
        if (total === 0) return '<p>No numeric data available for pie chart</p>';
        
        // Create SVG pie chart
        const radius = 80;
        const centerX = 100;
        const centerY = 100;
        let currentAngle = 0;
        
        let chartHTML = `
            <div style="display: flex; align-items: center; justify-content: center; gap: 30px; flex-wrap: wrap;">
                <div style="position: relative; width: 200px; height: 200px;">
                    <svg width="200" height="200" style="transform: rotate(-90deg);">
        `;
        
        // Generate pie slices
        cleanData.forEach((item, index) => {
            const percentage = (item.value / total) * 100;
            const angle = (percentage / 100) * 360;
            const color = colors[index % colors.length];
            
            const startAngle = currentAngle;
            const endAngle = currentAngle + angle;
            
            // Convert angles to radians
            const startRad = (startAngle * Math.PI) / 180;
            const endRad = (endAngle * Math.PI) / 180;
            
            // Calculate arc path
            const x1 = centerX + radius * Math.cos(startRad);
            const y1 = centerY + radius * Math.sin(startRad);
            const x2 = centerX + radius * Math.cos(endRad);
            const y2 = centerY + radius * Math.sin(endRad);
            
            const largeArcFlag = angle > 180 ? 1 : 0;
            
            const pathData = `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
            
            chartHTML += `
                <path d="${pathData}" fill="${color}" stroke="white" stroke-width="2"/>
            `;
            
            currentAngle += angle;
        });
        
        chartHTML += `
                    </svg>
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px;">
        `;
        
        // Add legend
        cleanData.forEach((item, index) => {
            const percentage = (item.value / total) * 100;
            const color = colors[index % colors.length];
            
            chartHTML += `
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 20px; height: 20px; background: ${color}; border-radius: 50%; margin-right: 10px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
                    <div style="font-size: 14px; font-weight: 500;">
                        <div style="color: #333;">${item.label}</div>
                        <div style="color: #666; font-size: 12px;">${item.value} (${percentage.toFixed(1)}%)</div>
                    </div>
                </div>
            `;
        });
        
        chartHTML += `
                </div>
            </div>
        `;
        
        return chartHTML;
    }

    generateLineChart(data) {
        if (data.length < 2) return '<p>Insufficient data for line chart</p>';
        
        const headers = data[0];
        const values = data.slice(1);
        
        // For line chart with multiple series, we'll create separate lines for each column
        if (headers.length > 2) {
            return this.generateMultiSeriesLineChart(data);
        }
        
        // Single series line chart - treat each row as a data point
        const maxValue = Math.max(...values.map(row => {
            const rawValue = row[1];
            return parseFloat(rawValue.toString().replace(/[^0-9.-]/g, '')) || 0;
        }));
        
        if (maxValue === 0) return '<p>No numeric data available for line chart</p>';
        
        let chartHTML = '<div style="position: relative; height: 200px; border-left: 2px solid #333; border-bottom: 2px solid #333; background: #f8f9fa; padding-left: 40px; padding-bottom: 30px;">';
        
        // Add Y-axis labels
        for (let i = 0; i <= 4; i++) {
            const value = (maxValue / 4) * i;
            const height = (i / 4) * 180;
            chartHTML += `
                <div style="position: absolute; left: -35px; bottom: ${height}px; font-size: 10px; color: #666; transform: translateY(-50%);">${value.toFixed(0)}</div>
            `;
        }
        
        // Create line path
        let pathData = '';
        const points = [];
        
        values.forEach((row, index) => {
            const label = row[0];
            const rawValue = row[1];
            const value = parseFloat(rawValue.toString().replace(/[^0-9.-]/g, '')) || 0;
            const height = (value / maxValue) * 180;
            const left = (index / (values.length - 1)) * 100;
            
            points.push({ x: left, y: height, label, value });
            
            if (index === 0) {
                pathData += `M ${left}% ${height}px`;
            } else {
                pathData += ` L ${left}% ${height}px`;
            }
        });
        
        // Add SVG line
        chartHTML += `
            <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                <path d="${pathData}" stroke="#2196f3" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
        
        // Add data points
        points.forEach((point, index) => {
            chartHTML += `
                <div style="position: absolute; left: ${point.x}%; bottom: ${point.y}px; width: 12px; height: 12px; background: #2196f3; border-radius: 50%; transform: translateX(-50%); border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3);"></div>
                <div style="position: absolute; left: ${point.x}%; bottom: -25px; font-size: 11px; color: #666; transform: translateX(-50%); text-align: center; white-space: nowrap;">${point.label}</div>
            `;
        });
        
        chartHTML += '</div>';
        return chartHTML;
    }

    generateMultiSeriesLineChart(data) {
        const headers = data[0];
        const values = data.slice(1);
        const numericColumns = headers.slice(1);
        const colors = ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4'];
        
        // Calculate max value across all series with proper data cleaning
        let maxValue = 0;
        values.forEach(row => {
            numericColumns.forEach((_, colIndex) => {
                const rawValue = row[colIndex + 1];
                const value = parseFloat(rawValue.toString().replace(/[^0-9.-]/g, '')) || 0;
                maxValue = Math.max(maxValue, value);
            });
        });
        
        if (maxValue === 0) return '<p>No numeric data available for line chart</p>';
        
        let chartHTML = '<div style="position: relative; height: 200px; border-left: 2px solid #333; border-bottom: 2px solid #333; background: #f8f9fa; padding-left: 40px; padding-bottom: 30px;">';
        
        // Add Y-axis labels
        for (let i = 0; i <= 4; i++) {
            const value = (maxValue / 4) * i;
            const height = (i / 4) * 180;
            chartHTML += `
                <div style="position: absolute; left: -35px; bottom: ${height}px; font-size: 10px; color: #666; transform: translateY(-50%);">${value.toFixed(0)}</div>
            `;
        }
        
        // Create SVG for lines
        chartHTML += '<svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">';
        
        // Create lines for each series
        numericColumns.forEach((header, colIndex) => {
            const color = colors[colIndex % colors.length];
            let pathData = '';
            const points = [];
            
            values.forEach((row, index) => {
                const rawValue = row[colIndex + 1];
                const value = parseFloat(rawValue.toString().replace(/[^0-9.-]/g, '')) || 0;
                const height = (value / maxValue) * 180;
                const left = (index / (values.length - 1)) * 100;
                
                points.push({ x: left, y: height, value });
                
                if (index === 0) {
                    pathData += `M ${left}% ${height}px`;
                } else {
                    pathData += ` L ${left}% ${height}px`;
                }
            });
            
            // Add line path
            chartHTML += `<path d="${pathData}" stroke="${color}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
            
            // Add data points
            points.forEach((point, index) => {
                chartHTML += `
                    <circle cx="${point.x}%" cy="${point.y}px" r="6" fill="${color}" stroke="white" stroke-width="2"/>
                `;
            });
            
            // Add labels only for the first series to avoid overlap
            if (colIndex === 0) {
                values.forEach((row, index) => {
                    const left = (index / (values.length - 1)) * 100;
                    chartHTML += `
                        <text x="${left}%" y="100%" text-anchor="middle" font-size="11" fill="#666" dy="20">${row[0]}</text>
                    `;
                });
            }
        });
        
        chartHTML += '</svg>';
        
        // Add legend
        chartHTML += '<div style="position: absolute; top: -35px; right: 0; display: flex; gap: 15px; flex-wrap: wrap;">';
        numericColumns.forEach((header, colIndex) => {
            const color = colors[colIndex % colors.length];
            chartHTML += `
                <div style="display: flex; align-items: center; font-size: 11px; margin: 2px 0;">
                    <div style="width: 12px; height: 12px; background: ${color}; border-radius: 50%; margin-right: 5px; border: 1px solid white;"></div>
                    <span style="color: #333;">${header}</span>
                </div>
            `;
        });
        chartHTML += '</div>';
        
        chartHTML += '</div>';
        return chartHTML;
    }

    
    mergeCells() {
        this.showMessage('Merge Cells functionality');
    }
    
    splitCells() {
        this.showMessage('Split Cells functionality');
    }
    
    
    
    
    
    
    
    
    showCharCount() {
        const stats = this.calculateDocumentStatistics();
        this.showMessage(`Character count: ${stats.characters} characters (with spaces: ${stats.charactersWithSpaces})`);
    }
    
    highlightText(text, caseSensitive = false) {
        if (!text) return;
        
        const content = this.editor.innerHTML;
        const flags = caseSensitive ? 'g' : 'gi';
        const regex = new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), flags);
        const highlighted = content.replace(regex, `<mark style="background-color: yellow;">$&</mark>`);
        
        this.editor.innerHTML = highlighted;
    }
    
    replaceTextInDocument(findText, replaceText, caseSensitive = false) {
        if (!findText) return;
        
        const content = this.editor.innerHTML;
        const flags = caseSensitive ? 'g' : 'gi';
        const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), flags);
        const replaced = content.replace(regex, replaceText);
        
        this.editor.innerHTML = replaced;
    }
    
    updateStatus() {
        const wordCount = this.editor.textContent.length;
        document.getElementById('word-count').textContent = `Words: ${wordCount}`;
    }
    
    // Submenu related methods
    toggleSubmenu(submenuId, button) {
        console.log('toggleSubmenu called:', submenuId);
        const submenuContainer = document.getElementById('submenu-container');
        const submenu = document.getElementById(submenuId);
        
        console.log('submenuContainer:', submenuContainer);
        console.log('submenu:', submenu);
        
        if (submenu && submenu.classList.contains('active')) {
            this.hideSubmenu();
        } else {
            this.showSubmenu(submenuId, button);
        }
    }
    
    showSubmenu(submenuId, button) {
        const submenuContainer = document.getElementById('submenu-container');
        const submenu = document.getElementById(submenuId);
        
        if (submenu) {
            // Hide all submenus
            document.querySelectorAll('.submenu').forEach(sm => {
                sm.classList.remove('active');
                sm.style.display = 'none';
            });
            
            // Show selected submenu
            submenu.classList.add('active');
            submenu.style.display = 'block';
            submenuContainer.style.display = 'block';
            
            // Position submenu with improved logic
            const buttonRect = button.getBoundingClientRect();
            const toolbarRect = button.closest('.toolbar').getBoundingClientRect();
            
            // Position submenu below the button, aligned with toolbar
            const left = buttonRect.left;
            const top = toolbarRect.bottom + 5;
            
            submenuContainer.style.left = `${left}px`;
            submenuContainer.style.top = `${top}px`;
            submenuContainer.style.width = '150px';
            submenuContainer.style.minWidth = '150px';
            submenuContainer.style.maxWidth = '150px';
            submenuContainer.style.position = 'fixed';
            submenuContainer.style.zIndex = '1000';
        }
    }
    
    hideSubmenu() {
        const submenuContainer = document.getElementById('submenu-container');
        submenuContainer.style.display = 'none';
        document.querySelectorAll('.submenu').forEach(sm => {
            sm.classList.remove('active');
            sm.style.display = 'none';
        });
    }
    
    // New feature implementation methods
    
    toggleSidebar() {
        this.sidebar.classList.toggle('hidden');
        this.showMessage('Sidebar toggled');
    }
    
    toggleRuler() {
        const rulerContainer = document.getElementById('ruler-container');
        if (!rulerContainer) {
            this.showMessage('Error: Ruler container not found', 'error');
            return;
        }
        
        const isVisible = rulerContainer.classList.contains('show');
        
        if (isVisible) {
            rulerContainer.classList.remove('show');
            this.showMessage('Ruler hidden');
        } else {
            rulerContainer.classList.add('show');
            this.updateRulerMarks();
            this.showMessage('Ruler shown');
        }
    }
    
    toggleInvisibles() {
        if (!this.editor) {
            this.showMessage('Error: Editor not found', 'error');
            return;
        }
        
        const isShowing = this.editor.classList.contains('show-invisibles');
        
        if (isShowing) {
            this.editor.classList.remove('show-invisibles');
            this.removeInvisibleMarkers();
            this.showMessage('Hidden characters hidden');
        } else {
            this.editor.classList.add('show-invisibles');
            this.addInvisibleMarkers();
            this.showMessage('Hidden characters shown');
        }
    }
    
    toggleFocusMode() {
        document.body.classList.toggle('focus-mode');
        this.showMessage('Focus mode toggled');
    }
    
    toggleNightMode() {
        document.body.classList.toggle('night-mode');
        this.showMessage('Night mode toggled');
    }
    
    insertSectionBreak() {
        this.showMessage('Section break inserted');
    }
    
    // Load template function for the templates section
    loadTemplate(templateType) {
        const templates = {
            'business-letter': {
                title: 'Business Letter',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #0078d4; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #0078d4; text-align: center; font-size: 18px; font-weight: bold;">
                            📄 Business Letter Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <div style="text-align: right; margin-bottom: 30px;">
                                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p><strong>To:</strong></p>
                                <p>Company Name</p>
                                <p>Address</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p><strong>Dear Sir/Madam:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p>Body content...</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>Sincerely,</strong></p>
                                <p>Best regards!</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>From:</strong></p>
                                <p>Your Name</p>
                                <p>Your Position</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'resume': {
                title: 'Resume',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #ffc107; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #ffc107; text-align: center; font-size: 18px; font-weight: bold;">
                            👤 Resume Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">Personal Resume</h1>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Personal Information</h2>
                                <p><strong>Name:</strong></p>
                                <p><strong>Phone:</strong></p>
                                <p><strong>Email:</strong></p>
                                <p><strong>Address:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Education Background</h2>
                                <p><strong>School Name:</strong></p>
                                <p><strong>Major:</strong></p>
                                <p><strong>Degree:</strong></p>
                                <p><strong>Time:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Work Experience</h2>
                                <p><strong>Company Name:</strong></p>
                                <p><strong>Position:</strong></p>
                                <p><strong>Time:</strong></p>
                                <p><strong>Job Description:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Skills & Expertise</h2>
                                <p>Skill 1</p>
                                <p>Skill 2</p>
                                <p>Skill 3</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'report': {
                title: 'Report',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #28a745; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #28a745; text-align: center; font-size: 18px; font-weight: bold;">
                            📊 Report Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">Report Title</h1>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #28a745;">1. Overview</h2>
                                <p>Report overview content...</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #28a745;">2. Detailed Content</h2>
                                <p>Detailed content...</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #28a745;">3. Conclusion</h2>
                                <p>Conclusion content...</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>Reporter:</strong></p>
                                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'memo': {
                title: 'Internal Memo',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #6f42c1; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #6f42c1; text-align: center; font-size: 18px; font-weight: bold;">
                            📝 Internal Memo Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">INTERNAL MEMO</h1>
                            <div style="margin-bottom: 20px;">
                                <p><strong>To:</strong> Department/Person</p>
                                <p><strong>From:</strong> Your Name</p>
                                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                                <p><strong>Subject:</strong> Memo Subject</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p>Memo content...</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>Action Required:</strong></p>
                                <p>Please review and respond by [date].</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'newsletter': {
                title: 'Press Release',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #dc3545; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #dc3545; text-align: center; font-size: 18px; font-weight: bold;">
                            📰 Press Release Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">PRESS RELEASE</h1>
                            <div style="margin-bottom: 20px;">
                                <p><strong>FOR IMMEDIATE RELEASE</strong></p>
                                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                                <p><strong>Contact:</strong> Your Name, Company</p>
                                <p><strong>Phone:</strong> (555) 123-4567</p>
                                <p><strong>Email:</strong> contact@company.com</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #dc3545;">Headline</h2>
                                <p>Press release content...</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>About [Company Name]:</strong></p>
                                <p>Company description...</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'invoice': {
                title: 'Invoice',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #17a2b8; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #17a2b8; text-align: center; font-size: 18px; font-weight: bold;">
                            💰 Invoice Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">INVOICE</h1>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 30px;">
                                <div>
                                    <p><strong>From:</strong></p>
                                    <p>Your Company Name</p>
                                    <p>Address</p>
                                    <p>City, State ZIP</p>
                                </div>
                                <div>
                                    <p><strong>Invoice #:</strong> INV-001</p>
                                    <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                                    <p><strong>Due Date:</strong> [Due Date]</p>
                                </div>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p><strong>Bill To:</strong></p>
                                <p>Client Name</p>
                                <p>Client Address</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p><strong>Description:</strong> Service/Product Description</p>
                                <p><strong>Amount:</strong> $0.00</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>Total Amount Due:</strong> $0.00</p>
                            </div>
                        </div>
                    </div>
                `
            }
        };
        
        const template = templates[templateType];
        if (template) {
            // Ensure the editor is focused before inserting
            if (this.editor) {
                this.editor.focus();
            }
            
            // Use insertContent to insert at cursor position instead of replacing all content
            this.insertContent(template.content);
            
            // Update document title and mark as modified
            this.currentDocument.title = template.title;
            this.currentDocument.modified = true;
            
            this.showMessage(`${template.title} template inserted at cursor position`);
            
            // Close the template panel after insertion for better UX
            setTimeout(() => {
                this.showPage('insert');
            }, 500);
        } else {
            this.showMessage('Template does not exist');
        }
    }
    
    
    applySuperscript() {
        document.execCommand('superscript');
        this.showMessage('Superscript format applied');
    }
    
    applySubscript() {
        document.execCommand('subscript');
        this.showMessage('Subscript format applied');
    }
    
    setLineSpacing(spacing) {
        try {
            // Ensure the editor is focused
            this.editor.focus();
            
            // Get the current selection
            const selection = window.getSelection();
            
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                
                // Check if there's selected text
                if (!range.collapsed) {
                    // Apply line spacing to selected text
                    const selectedContent = range.extractContents();
                    const span = document.createElement('span');
                    span.style.setProperty('line-height', spacing, 'important');
                    span.appendChild(selectedContent);
                    range.insertNode(span);
                    
                    // Clear selection
                    selection.removeAllRanges();
                    
                    this.showMessage(`Line spacing ${spacing}x applied to selected text`);
                } else {
                    // No text selected, apply to current paragraph or entire document
                    const container = range.commonAncestorContainer;
                    const element = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
                    
                    // Find the closest paragraph or create one
                    let targetElement = element;
                    if (element && !element.closest('p, div, h1, h2, h3, h4, h5, h6')) {
                        // If not in a block element, find the containing paragraph
                        const paragraph = element.closest('p') || element.closest('div');
                        if (paragraph) {
                            targetElement = paragraph;
                        } else {
                            // Create a paragraph wrapper
                            const p = document.createElement('p');
                            p.style.setProperty('line-height', spacing, 'important');
                            range.insertNode(p);
                            range.selectNodeContents(p);
                            range.collapse(false);
                            selection.removeAllRanges();
                            selection.addRange(range);
                            this.showMessage(`Line spacing ${spacing}x applied to new paragraph`);
                            return;
                        }
                    }
                    
                    if (targetElement) {
                        targetElement.style.setProperty('line-height', spacing, 'important');
                        this.showMessage(`Line spacing ${spacing}x applied to paragraph`);
                    } else {
                        // Fallback: apply to entire editor
                        this.editor.style.setProperty('line-height', spacing, 'important');
                        this.showMessage(`Line spacing ${spacing}x applied to entire document`);
                    }
                }
            } else {
                // No selection, apply to entire editor
                this.editor.style.setProperty('line-height', spacing, 'important');
                this.showMessage(`Line spacing ${spacing}x applied to entire document`);
            }
            
            // Mark document as modified
            this.currentDocument.modified = true;
            this.updateStatus();
            
        } catch (error) {
            console.error('Error setting line spacing:', error);
            this.showMessage('Error applying line spacing', 'error');
        }
    }
    
    
    
    // Paragraph Settings Functions
    
    applySpaceBefore() {
        const spaceValue = document.getElementById('space-before').value;
        if (!spaceValue || spaceValue === '') {
            this.showMessage('Please enter a space before value', 'error');
            return;
        }
        
        const space = parseFloat(spaceValue);
        if (isNaN(space) || space < 0) {
            this.showMessage('Please enter a valid positive number', 'error');
            return;
        }
        
        this.applyParagraphSpacing('marginTop', space);
    }
    
    applySpaceAfter() {
        const spaceValue = document.getElementById('space-after').value;
        if (!spaceValue || spaceValue === '') {
            this.showMessage('Please enter a space after value', 'error');
            return;
        }
        
        const space = parseFloat(spaceValue);
        if (isNaN(space) || space < 0) {
            this.showMessage('Please enter a valid positive number', 'error');
            return;
        }
        
        this.applyParagraphSpacing('marginBottom', space);
    }
    
    applyParagraphSpacing(property, value) {
        try {
            this.editor.focus();
            const selection = window.getSelection();
            
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                
                if (!range.collapsed) {
                    // Apply to selected text
                    const selectedContent = range.extractContents();
                    const div = document.createElement('div');
                    div.style[property] = value + 'pt';
                    div.appendChild(selectedContent);
                    range.insertNode(div);
                    selection.removeAllRanges();
                    this.showMessage(`${property} ${value}pt applied to selected text`);
                } else {
                    // Apply to current paragraph
                    const container = range.commonAncestorContainer;
                    const element = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
                    const paragraph = element.closest('p') || element.closest('div');
                    
                    if (paragraph) {
                        paragraph.style[property] = value + 'pt';
                        this.showMessage(`${property} ${value}pt applied to paragraph`);
                    } else {
                        // Create new paragraph with spacing
                        const p = document.createElement('p');
                        p.style[property] = value + 'pt';
                        range.insertNode(p);
                        range.selectNodeContents(p);
                        range.collapse(false);
                        selection.removeAllRanges();
                        selection.addRange(range);
                        this.showMessage(`${property} ${value}pt applied to new paragraph`);
                    }
                }
            } else {
                // Apply to entire editor
                this.editor.style[property] = value + 'pt';
                this.showMessage(`${property} ${value}pt applied to entire document`);
            }
            
            this.currentDocument.modified = true;
            this.updateStatus();
        } catch (error) {
            console.error('Error applying paragraph spacing:', error);
            this.showMessage('Error applying paragraph spacing', 'error');
        }
    }
    
    
    openPageSetup() {
        this.showMessage('Page setup opened');
    }
    
    
    editHeader() {
        this.showMessage('Header editing mode activated');
    }
    
    editFooter() {
        this.showMessage('Footer editing mode activated');
    }
    
    showCharCount() {
        const charCount = this.editor.textContent.length;
        this.showMessage(`Character count: ${charCount}`);
    }
    
    
    
    
    // Check for shared document on page load
    checkForSharedDocument() {
        const urlParams = new URLSearchParams(window.location.search);
        const shareId = urlParams.get('share');
        
        if (shareId) {
            this.loadSharedDocument(shareId);
        }
    }
    
    // Load shared document content
    loadSharedDocument(shareId) {
        const shareData = localStorage.getItem(`miniword_share_${shareId}`);
        
        if (shareData) {
            try {
                const data = JSON.parse(shareData);
                
                // Check if share has expired
                if (data.expiration !== 'never') {
                    const expirationDate = new Date(data.created);
                    expirationDate.setDate(expirationDate.getDate() + parseInt(data.expiration));
                    
                    if (new Date() > expirationDate) {
                        this.showMessage('This share link has expired');
                        return;
                    }
                }
                
                // Load document content
                this.editor.innerHTML = data.documentContent;
                this.currentDocument = {
                    title: data.documentTitle,
                    content: data.documentContent
                };
                
                // Update document title
                document.title = `Shared: ${data.documentTitle}`;
                
                // Show share info
                this.showMessage(`Loading shared document: ${data.documentTitle}`);
                
                
                // Show share permissions info
                this.showSharePermissions(data);
                
            } catch (error) {
                this.showMessage('Error loading shared document');
                console.error('Error loading shared document:', error);
            }
            } else {
            this.showMessage('Share link not found or has been removed');
        }
    }
    
    // Show share permissions and info
    showSharePermissions(shareData) {
        const permissionInfo = document.createElement('div');
        permissionInfo.className = 'share-info-banner';
        permissionInfo.innerHTML = `
            <div class="share-info-content">
                <h4>📄 Shared Document</h4>
                <p><strong>Title:</strong> ${shareData.documentTitle}</p>
                <p><strong>Permission:</strong> ${shareData.permission}</p>
                <p><strong>Shared:</strong> ${new Date(shareData.created).toLocaleString()}</p>
                <button class="btn btn-sm" onclick="this.parentElement.parentElement.remove()">Close</button>
            </div>
        `;
        
        // Add to the top of the editor
        this.editor.parentNode.insertBefore(permissionInfo, this.editor);
    }
    
    // Share Document Functions
    generateShareLink() {
        const permission = 'view'; // Default to view only
        const expiration = 'never'; // Default to never expire
        const requirePassword = false; // Default to no password required
        
        // Get current document content
        const documentContent = this.editor.innerHTML;
        const documentTitle = this.currentDocument?.title || 'Untitled Document';
        
        // Generate unique share ID
        const shareId = 'share_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const baseUrl = window.location.origin + window.location.pathname;
        const shareUrl = `${baseUrl}?share=${shareId}`;
        
        // Create share data with document content
        const shareData = {
            id: shareId,
            url: shareUrl,
            permission: permission,
            expiration: expiration,
            requirePassword: requirePassword,
            created: new Date().toISOString(),
            documentTitle: documentTitle,
            documentContent: documentContent,
            lastModified: new Date().toISOString()
        };
        
        // Save share data to localStorage
        localStorage.setItem(`miniword_share_${shareId}`, JSON.stringify(shareData));
        
        // Also save to a general shares list
        const allShares = JSON.parse(localStorage.getItem('miniword_all_shares') || '[]');
        allShares.push(shareData);
        localStorage.setItem('miniword_all_shares', JSON.stringify(allShares));
        
        // Display the link
        const linkDisplay = document.getElementById('share-link-display');
        const linkInput = document.getElementById('generated-link');
        
        if (linkDisplay && linkInput) {
            linkInput.value = shareUrl;
            linkDisplay.style.display = 'block';
        }
        
        
        this.showMessage(`Share link generated successfully! Link: ${shareUrl}`);
    }
    
    copyShareLink() {
        const linkInput = document.getElementById('generated-link');
        if (linkInput && linkInput.value) {
            this.copyToClipboard('generated-link');
            this.showMessage('Share link copied to clipboard!');
        } else {
            this.showMessage('Please generate a share link first');
        }
    }
    
    
    shareToTwitter() {
        const shareUrl = document.getElementById('generated-link')?.value || window.location.href;
        const text = `Check out this document: ${this.currentDocument?.title || 'Untitled Document'}`;
        const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
        window.open(twitterUrl, '_blank');
        
        this.showMessage('Opening Twitter to share');
    }
    
    shareToFacebook() {
        const shareUrl = document.getElementById('generated-link')?.value || window.location.href;
        const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
        window.open(facebookUrl, '_blank');
        
        this.showMessage('Opening Facebook to share');
    }
    
    shareToLinkedIn() {
        const shareUrl = document.getElementById('generated-link')?.value || window.location.href;
        const title = this.currentDocument?.title || 'Untitled Document';
        const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(title)}`;
        window.open(linkedinUrl, '_blank');
        
        this.showMessage('Opening LinkedIn to share');
    }
    
    shareToWhatsApp() {
        const shareUrl = document.getElementById('generated-link')?.value || window.location.href;
        const text = `Check out this document: ${shareUrl}`;
        const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(text)}`;
        window.open(whatsappUrl, '_blank');
        
        this.showMessage('Opening WhatsApp to share');
    }
    
    
    copyToClipboard(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.select();
            element.setSelectionRange(0, 99999); // For mobile devices
            document.execCommand('copy');
            this.showMessage('Copied to clipboard!');
        }
    }
    
    
    async shareDocument() {
        try {
            // Generate share link
            const shareUrl = window.location.href;
            const documentContent = this.editor.innerHTML;
            const documentTitle = this.currentDocument.title || 'Untitled Document';
            
            // Create share data
            const shareData = {
                title: documentTitle,
                text: `View my document: ${documentTitle}`,
                url: shareUrl
            };
            
            // Try using Web Share API
            if (navigator.share) {
                await navigator.share(shareData);
                this.showMessage('Document shared successfully');
            } else {
                // Fallback to copy link
                await navigator.clipboard.writeText(shareUrl);
                this.showMessage('Share link copied to clipboard');
            }
        } catch (error) {
            // If sharing fails, generate download link
            this.generateShareLink();
        }
    }
    
    generateShareLink() {
        const documentContent = this.editor.innerHTML;
        const documentTitle = this.currentDocument.title || 'Untitled Document';
        
        // Create downloadable HTML file
        const htmlContent = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>${documentTitle}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .document-content { max-width: 800px; margin: 0 auto; }
    </style>
</head>
<body>
    <div class="document-content">
        <h1>${documentTitle}</h1>
        ${documentContent}
    </div>
</body>
</html>`;
        
        // Create download link
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${documentTitle}.html`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.showMessage('Document exported as HTML file');
    }
    
    // Generate QR code sharing
    generateQRCode() {
        const shareUrl = window.location.href;
        const qrCodeHTML = `
            <div class="qr-code-container" style="text-align: center; padding: 20px; border: 1px solid #ddd; margin: 20px 0;">
                <h3>Scan QR Code to Share Document</h3>
                <div class="qr-code" style="width: 200px; height: 200px; margin: 0 auto; background: #f0f0f0; display: flex; align-items: center; justify-content: center; border: 1px solid #ccc;">
                    <p>QR Code Placeholder</p>
                    <p style="font-size: 12px; color: #666;">${shareUrl}</p>
                </div>
                <p style="font-size: 12px; color: #666;">Share link: ${shareUrl}</p>
            </div>
        `;
        this.insertContent(qrCodeHTML);
        this.showMessage('QR code inserted into document');
    }
    
    // Submenu functions
    
    // Zoom functions
    zoomIn() {
        const zoomLevel = document.getElementById('zoom-in-level')?.value;
        const targetZoom = zoomLevel ? parseInt(zoomLevel) : this.getCurrentZoom() + 25;
        
        this.setZoom(targetZoom);
        this.showMessage(`Zoomed in to ${this.currentZoom}%`);
    }
    
    zoomOut() {
        const zoomLevel = document.getElementById('zoom-out-level')?.value;
        const targetZoom = zoomLevel ? parseInt(zoomLevel) : this.getCurrentZoom() - 25;
        
        this.setZoom(targetZoom);
        this.showMessage(`Zoomed out to ${this.currentZoom}%`);
    }
    
    setZoom(zoomLevel) {
        // Clamp zoom level between 25% and 500%
        zoomLevel = Math.max(25, Math.min(500, zoomLevel));
        
        // Store current zoom level
        this.currentZoom = zoomLevel;
        
        // Apply zoom to editor container
        const editorContainer = this.editor.parentElement;
        if (editorContainer) {
            editorContainer.style.transform = `scale(${zoomLevel / 100})`;
            editorContainer.style.transformOrigin = 'top left';
            editorContainer.style.transition = 'transform 0.2s ease';
            
            // Adjust container size to prevent overflow issues
            const scale = zoomLevel / 100;
            editorContainer.style.width = `${100 / scale}%`;
            editorContainer.style.height = `${100 / scale}%`;
        }
        
        // Update zoom level display if it exists
        this.updateZoomDisplay();
        
        // Store zoom level in localStorage for persistence
        localStorage.setItem('miniword-zoom', zoomLevel.toString());
    }
    
    getCurrentZoom() {
        return this.currentZoom || 100;
    }
    
    resetZoom() {
        this.setZoom(100);
        this.showMessage('Zoom reset to 100%');
    }
    
    updateZoomDisplay() {
        // Update any zoom level displays in the UI
        const zoomDisplays = document.querySelectorAll('.zoom-level-display');
        zoomDisplays.forEach(display => {
            display.textContent = `${this.currentZoom}%`;
        });
        
        // Update zoom level selects
        const zoomSelects = document.querySelectorAll('#zoom-in-level, #zoom-out-level');
        zoomSelects.forEach(select => {
            select.value = this.currentZoom;
        });
    }
    
    // Initialize zoom level from localStorage or default
    initializeZoom() {
        const savedZoom = localStorage.getItem('miniword-zoom');
        this.currentZoom = savedZoom ? parseInt(savedZoom) : 100;
        this.setZoom(this.currentZoom);
    }
    
    // Insert chart function
    insertChart() {
        const chartType = document.getElementById('chart-type').value;
        const chartTitle = document.getElementById('chart-title').value || 'Chart';
        const chartId = 'chart_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        let chartHTML = `
            <div class="inserted-chart-container" id="${chartId}_container" style="
                margin: 20px 0;
                padding: 15px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background: #f9f9f9;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
                clear: both;
                display: block;
            ">
                <h3 style="margin: 0 0 8px 0; color: #333; text-align: center; font-size: 14px; font-weight: bold;">${chartTitle}</h3>
                <div class="chart-placeholder" id="${chartId}" style="
                    background: #f0f0f0; 
                    padding: 20px; 
                    border: 2px dashed #ccc; 
                    border-radius: 3px;
                    text-align: center;
                    min-height: 150px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <p style="margin: 0 0 5px 0; font-size: 14px; color: #333;">${chartType.charAt(0).toUpperCase() + chartType.slice(1)} Chart</p>
                    <p style="margin: 0; color: #666; font-size: 11px;">Chart data will be displayed here</p>
                </div>
            </div>
        `;
        
        this.insertContent(chartHTML);
        this.showMessage(`${chartType} chart inserted`);
    }
    
    // Insert table function
    insertTable(rows = 3, cols = 3) {
        // Create a table with consistent cell widths and proper sizing
        let table = '<table style="border-collapse: collapse; width: 100%; margin: 10px 0; break-inside: avoid; page-break-inside: avoid; table-layout: fixed;">';
        for (let i = 0; i < rows; i++) {
            table += '<tr>';
            for (let j = 0; j < cols; j++) {
                // Calculate equal width for each cell
                const cellWidth = Math.floor(100 / cols);
                table += `<td style="padding: 8px; border: 1px solid #ccc; width: ${cellWidth}%; text-align: left; vertical-align: top; break-inside: avoid;">&nbsp;</td>`;
            }
            table += '</tr>';
        }
        table += '</table>';
        
        this.insertContent(table);
        this.showMessage(`${rows}×${cols} table inserted`);
    }
    
    // Insert inline table
    insertInlineTable(rows = 3, cols = 3) {
        // Create a smaller table
        let table = '<table style="border-collapse: collapse; margin: 5px 0; break-inside: avoid; page-break-inside: avoid; table-layout: fixed; max-width: 100%;">';
        for (let i = 0; i < rows; i++) {
            table += '<tr>';
            for (let j = 0; j < cols; j++) {
                // Calculate equal width for each cell
                const cellWidth = Math.floor(100 / cols);
                table += `<td style="padding: 6px; border: 1px solid #ccc; width: ${cellWidth}%; text-align: left; vertical-align: top; break-inside: avoid; font-size: 12px;">&nbsp;</td>`;
            }
            table += '</tr>';
        }
        table += '</table>';
        
        this.insertContent(table);
        this.showMessage(`${rows}×${cols} inline table inserted`);
    }
    
    // Split Cells functionality
    splitCells() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const cell = range.commonAncestorContainer.closest('td');
            if (cell) {
                const newCell = cell.cloneNode(true);
                newCell.innerHTML = '&nbsp;';
                cell.parentNode.insertBefore(newCell, cell.nextSibling);
                this.showMessage('Cell split');
            } else {
                this.showMessage('Please select cell to split');
            }
        } else {
            this.showMessage('Please select cell to split');
        }
    }
    
    // Merge Cells functionality
    mergeCells() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const cells = range.commonAncestorContainer.closest('table').querySelectorAll('td');
            if (cells.length > 1) {
                const firstCell = cells[0];
                const secondCell = cells[1];
                firstCell.innerHTML += secondCell.innerHTML;
                secondCell.remove();
                this.showMessage('Cells merged');
            } else {
                this.showMessage('Please select cells to merge');
            }
        } else {
            this.showMessage('Please select cells to merge');
        }
    }
    
    // Insert equation function
    insertEquation() {
        const equationType = document.getElementById('equation-type').value;
        const equationContent = document.getElementById('equation-content').value;
        
        if (!equationContent.trim()) {
            this.showMessage('Please enter equation content', 'error');
            return;
        }
        
        // Generate equation HTML based on type
        let equationHTML = '';
        
        switch (equationType) {
            case 'fraction':
                equationHTML = this.generateFractionEquation(equationContent);
                break;
            case 'root':
                equationHTML = this.generateRootEquation(equationContent);
                break;
            case 'power':
                equationHTML = this.generatePowerEquation(equationContent);
                break;
            case 'integral':
                equationHTML = this.generateIntegralEquation(equationContent);
                break;
            case 'sum':
                equationHTML = this.generateSummationEquation(equationContent);
                break;
            default:
                equationHTML = this.generateBasicEquation(equationContent);
        }
        
        this.insertContent(equationHTML);
        this.showMessage(`${equationType} equation inserted successfully`);
        
        // Clear the input
        document.getElementById('equation-content').value = '';
    }
    
    // Generate basic equation
    generateBasicEquation(content) {
        const equationId = 'equation_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        return `
            <div class="inserted-equation-container" id="${equationId}_container" style="
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #fafafa;
                text-align: center;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
            ">
                <div class="equation-content" id="${equationId}" style="
                    font-family: 'Times New Roman', 'Cambria Math', serif;
                    font-size: 20px;
                    color: #333;
                    line-height: 1.5;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    ${this.formatMathContent(content)}
                </div>
            </div>
        `;
    }
    
    // Generate fraction equation
    generateFractionEquation(content) {
        const equationId = 'equation_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const parts = content.split('/');
        const numerator = parts[0] || 'a';
        const denominator = parts[1] || 'b';
        
        return `
            <div class="inserted-equation-container" id="${equationId}_container" style="
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #fafafa;
                text-align: center;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
            ">
                <div class="equation-content" id="${equationId}" style="
                    font-family: 'Times New Roman', 'Cambria Math', serif;
                    font-size: 20px;
                    color: #333;
                    line-height: 1.5;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    <div style="display: inline-block; vertical-align: middle;">
                        <div style="border-bottom: 2px solid #333; padding: 0 10px; margin-bottom: 2px;">
                            ${this.formatMathContent(numerator)}
                        </div>
                        <div style="padding: 0 10px;">
                            ${this.formatMathContent(denominator)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Generate square root equation
    generateRootEquation(content) {
        const equationId = 'equation_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        return `
            <div class="inserted-equation-container" id="${equationId}_container" style="
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #fafafa;
                text-align: center;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
            ">
                <div class="equation-content" id="${equationId}" style="
                    font-family: 'Times New Roman', 'Cambria Math', serif;
                    font-size: 20px;
                    color: #333;
                    line-height: 1.5;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    <span style="font-size: 24px;">√</span><span style="text-decoration: overline; padding: 0 5px;">${this.formatMathContent(content)}</span>
                </div>
            </div>
        `;
    }
    
    // Generate power equation
    generatePowerEquation(content) {
        const equationId = 'equation_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const parts = content.split('^');
        const base = parts[0] || 'x';
        const exponent = parts[1] || '2';
        
        return `
            <div class="inserted-equation-container" id="${equationId}_container" style="
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #fafafa;
                text-align: center;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
            ">
                <div class="equation-content" id="${equationId}" style="
                    font-family: 'Times New Roman', 'Cambria Math', serif;
                    font-size: 20px;
                    color: #333;
                    line-height: 1.5;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    ${this.formatMathContent(base)}<sup style="font-size: 14px; vertical-align: super;">${this.formatMathContent(exponent)}</sup>
                </div>
            </div>
        `;
    }
    
    // Generate integral equation
    generateIntegralEquation(content) {
        const equationId = 'equation_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        return `
            <div class="inserted-equation-container" id="${equationId}_container" style="
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #fafafa;
                text-align: center;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
            ">
                <div class="equation-content" id="${equationId}" style="
                    font-family: 'Times New Roman', 'Cambria Math', serif;
                    font-size: 20px;
                    color: #333;
                    line-height: 1.5;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    <span style="font-size: 24px;">∫</span> ${this.formatMathContent(content)} dx
                </div>
            </div>
        `;
    }
    
    // Generate summation equation
    generateSummationEquation(content) {
        const equationId = 'equation_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        return `
            <div class="inserted-equation-container" id="${equationId}_container" style="
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #fafafa;
                text-align: center;
                page-break-inside: avoid;
                break-inside: avoid;
                max-width: 100%;
                box-sizing: border-box;
            ">
                <div class="equation-content" id="${equationId}" style="
                    font-family: 'Times New Roman', 'Cambria Math', serif;
                    font-size: 20px;
                    color: #333;
                    line-height: 1.5;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    <span style="font-size: 24px;">∑</span> ${this.formatMathContent(content)}
                </div>
            </div>
        `;
    }
    
    // Format mathematical content
    formatMathContent(content) {
        return content
            .replace(/\*/g, '×')
            .replace(/\//g, '÷')
            .replace(/\+/g, '+')
            .replace(/-/g, '−')
            .replace(/=/g, '=')
            .replace(/\(/g, '(')
            .replace(/\)/g, ')')
            .replace(/\[/g, '[')
            .replace(/\]/g, ']')
            .replace(/\{/g, '{')
            .replace(/\}/g, '}');
    }
    
    // Update equation preview
    updateEquationPreview() {
        const equationType = document.getElementById('equation-type').value;
        const equationContent = document.getElementById('equation-content').value;
        const previewElement = document.getElementById('equation-preview');
        
        if (!previewElement) return;
        
        if (!equationContent.trim()) {
            previewElement.innerHTML = 'Preview will appear here...';
            return;
        }
        
        let previewHTML = '';
        
        switch (equationType) {
            case 'fraction':
                const parts = equationContent.split('/');
                const numerator = parts[0] || 'a';
                const denominator = parts[1] || 'b';
                previewHTML = `
                    <div style="display: inline-block; vertical-align: middle;">
                        <div style="border-bottom: 2px solid #333; padding: 0 10px; margin-bottom: 2px;">
                            ${this.formatMathContent(numerator)}
                        </div>
                        <div style="padding: 0 10px;">
                            ${this.formatMathContent(denominator)}
                        </div>
                    </div>
                `;
                break;
            case 'root':
                previewHTML = `<span style="font-size: 24px;">√</span><span style="text-decoration: overline; padding: 0 5px;">${this.formatMathContent(equationContent)}</span>`;
                break;
            case 'power':
                const powerParts = equationContent.split('^');
                const base = powerParts[0] || 'x';
                const exponent = powerParts[1] || '2';
                previewHTML = `${this.formatMathContent(base)}<sup style="font-size: 14px; vertical-align: super;">${this.formatMathContent(exponent)}</sup>`;
                break;
            case 'integral':
                previewHTML = `<span style="font-size: 24px;">∫</span> ${this.formatMathContent(equationContent)} dx`;
                break;
            case 'sum':
                previewHTML = `<span style="font-size: 24px;">∑</span> ${this.formatMathContent(equationContent)}`;
                break;
            default:
                previewHTML = this.formatMathContent(equationContent);
        }
        
        previewElement.innerHTML = previewHTML;
    }
    
    // Insert image function
    insertImage() {
        const imageFile = document.getElementById('image-file').files[0];
        const imageSize = document.getElementById('image-size').value;
        
        if (!imageFile) {
            this.showMessage('Please select an image file', 'error');
            return;
        }
        
        // Check if it's actually an image file
        if (!imageFile.type.startsWith('image/')) {
            this.showMessage('Please select a valid image file', 'error');
            return;
        }
        
        const sizes = {
            'small': '200px',
            'medium': '400px',
            'large': '600px',
            'custom': '300px'
        };
        
        const width = sizes[imageSize] || '300px';
        
        // Use FileReader to convert file to data URL
        const reader = new FileReader();
        reader.onload = (e) => {
            // Create a properly styled image container that integrates with document flow
            const imageHTML = `
                <div class="inserted-image-container" style="
                    display: block;
                    margin: 15px auto;
                    text-align: center;
                    max-width: 100%;
                    box-sizing: border-box;
                    page-break-inside: avoid;
                    break-inside: avoid;
                ">
                    <img src="${e.target.result}" 
                         alt="Inserted Image" 
                         style="
                            width: ${width};
                            max-width: 100%;
                            height: auto;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            display: block;
                            margin: 0 auto;
                            box-sizing: border-box;
                        "
                        class="inserted-image">
                </div>
            `;
            this.insertContent(imageHTML);
            this.showMessage(`Image inserted: ${imageFile.name} (${imageSize} size)`);
            
            // Clear the file input
            document.getElementById('image-file').value = '';
        };
        
        reader.onerror = () => {
            this.showMessage('Error reading image file', 'error');
        };
        
        reader.readAsDataURL(imageFile);
    }
    
    // Insert link function
    insertLink() {
        const linkUrl = document.getElementById('link-url').value.trim();
        const linkText = document.getElementById('link-text').value.trim();
        
        if (!linkUrl) {
            this.showMessage('Please enter link URL', 'error');
            return;
        }
        
        // Ensure URL has proper protocol
        let finalUrl = linkUrl;
        if (!linkUrl.startsWith('http://') && !linkUrl.startsWith('https://') && !linkUrl.startsWith('mailto:')) {
            finalUrl = 'https://' + linkUrl;
        }
        
        const displayText = linkText || linkUrl;
        
        // Create a proper HTML anchor tag with all necessary attributes
        const linkHTML = `<a href="${finalUrl}" target="_blank" rel="noopener noreferrer" style="color: #0066cc; text-decoration: underline; cursor: pointer;">${displayText}</a>`;
        
        // Ensure the editor is focused before inserting
        if (this.editor) {
            this.editor.focus();
        }
        
        // Use insertContent to insert at cursor position
        this.insertContent(linkHTML);
        
        // Clear the input fields after successful insertion
        document.getElementById('link-url').value = '';
        document.getElementById('link-text').value = '';
        
        this.showMessage(`Link "${displayText}" inserted successfully`);
        
        // Close the link panel after insertion for better UX
        setTimeout(() => {
            this.showPage('insert');
        }, 500);
    }
    
    // Insert symbol function
    insertSymbol(symbol) {
        // Ensure the editor is focused before inserting
        if (this.editor) {
            this.editor.focus();
        }
        
        // Use the insertContent method which handles cursor positioning
        this.insertContent(symbol);
        
        // Provide user feedback
        this.showMessage(`Symbol "${symbol}" inserted at cursor position`);
        
        // Close the symbol panel after insertion for better UX
        setTimeout(() => {
            this.showPage('insert');
        }, 500);
    }
    
    // Insert section break function
    insertSectionBreak() {
        const sectionBreakHTML = `<div class="section-break" style="border-top: 2px solid #333; margin: 20px 0; text-align: center; color: #666; font-size: 12px;">Section Break</div>`;
        this.insertContent(sectionBreakHTML);
        this.showMessage('Section break inserted');
    }
    
    // Insert page break function
    insertPageBreak() {
        const pageBreakHTML = `
            <div class="page-break" style="
                page-break-before: always;
                break-before: page;
                border-top: 2px dashed #999;
                margin: 30px 0;
                text-align: center;
                color: #999;
                font-size: 12px;
                padding: 10px 0;
            ">
                <span style="background: white; padding: 0 10px;">Page Break</span>
            </div>
        `;
        this.insertContent(pageBreakHTML);
        this.showMessage('Page break inserted');
    }
    
    
    // Template Library functionality
    createFromTemplate(templateType) {
        const templates = {
            'letter': {
                title: 'Business Letter',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #0078d4; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #0078d4; text-align: center; font-size: 18px; font-weight: bold;">
                            📄 Business Letter Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <div style="text-align: right; margin-bottom: 30px;">
                                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p><strong>To:</strong></p>
                                <p>Company Name</p>
                                <p>Address</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p><strong>Dear Sir/Madam:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p>Body content...</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>Sincerely,</strong></p>
                                <p>Best regards!</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>From:</strong></p>
                                <p>Your Name</p>
                                <p>Your Position</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'report': {
                title: 'Report',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #28a745; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #28a745; text-align: center; font-size: 18px; font-weight: bold;">
                            📊 Report Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">Report Title</h1>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #28a745;">1. Overview</h2>
                                <p>Report overview content...</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #28a745;">2. Detailed Content</h2>
                                <p>Detailed content...</p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #28a745;">3. Conclusion</h2>
                                <p>Conclusion content...</p>
                            </div>
                            <div style="margin-top: 30px;">
                                <p><strong>Reporter:</strong></p>
                                <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                            </div>
                        </div>
                    </div>
                `
            },
            'resume': {
                title: 'Resume',
                content: `
                    <div class="inserted-template-container" style="
                        margin: 20px 0; padding: 20px; border: 2px solid #ffc107; border-radius: 8px;
                        background: #f8f9fa; page-break-inside: avoid; break-inside: avoid;
                        max-width: 100%; box-sizing: border-box; clear: both; display: block;
                    ">
                        <h3 style="margin: 0 0 15px 0; color: #ffc107; text-align: center; font-size: 18px; font-weight: bold;">
                            👤 Resume Template
                        </h3>
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; background: white; padding: 20px; border-radius: 6px;">
                            <h1 style="text-align: center; margin-bottom: 30px; color: #333;">Personal Resume</h1>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Personal Information</h2>
                                <p><strong>Name:</strong></p>
                                <p><strong>Phone:</strong></p>
                                <p><strong>Email:</strong></p>
                                <p><strong>Address:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Education Background</h2>
                                <p><strong>School Name:</strong></p>
                                <p><strong>Major:</strong></p>
                                <p><strong>Degree:</strong></p>
                                <p><strong>Time:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Work Experience</h2>
                                <p><strong>Company Name:</strong></p>
                                <p><strong>Position:</strong></p>
                                <p><strong>Time:</strong></p>
                                <p><strong>Job Description:</strong></p>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <h2 style="color: #ffc107;">Skills & Expertise</h2>
                                <p>Skill 1</p>
                                <p>Skill 2</p>
                                <p>Skill 3</p>
                            </div>
                        </div>
                    </div>
                `
            }
        };
        
        const template = templates[templateType];
        if (template) {
            // Ensure the editor is focused before inserting
            if (this.editor) {
                this.editor.focus();
            }
            
            // Use insertContent to insert at cursor position instead of replacing all content
            this.insertContent(template.content);
            
            // Update document title and mark as modified
            this.currentDocument.title = template.title;
            this.currentDocument.modified = true;
            
            this.showMessage(`${template.title} template inserted at cursor position`);
            
            // Close the template panel after insertion for better UX
            setTimeout(() => {
                this.showPage('insert');
            }, 500);
        } else {
            this.showMessage('Template does not exist');
        }
    }
    
    // Font color function
    fontColor() {
        const color = document.getElementById('font-color').value;
        
        // Check if there is selected text
        const selection = window.getSelection();
        const selectedText = selection.toString();
        
        // Debug information
        console.log('Selected text:', selectedText);
        console.log('Selection range count:', selection.rangeCount);
        console.log('Is collapsed:', selection.isCollapsed);
        
        if (selection.rangeCount > 0 && !selection.isCollapsed && selectedText.trim()) {
            // Has selected text, apply color
            try {
                // First try execCommand
                const success = document.execCommand('foreColor', false, color);
                if (!success) {
                    // If execCommand fails, use manual method
                    this.applyFontColorManually(color);
                } else {
                    this.showMessage(`Selected text "${selectedText}" color set to ${color}`);
                }
            } catch (error) {
                // If error occurs, use manual method
                this.applyFontColorManually(color);
            }
        } else {
            // No selected text, prompt user
            this.showMessage('Please select text to set color first (currently selected: "' + selectedText + '")');
        }
    }
    
    // Manually apply font color
    applyFontColorManually(color) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);
            
            // Create span element with color
            const span = document.createElement('span');
            span.style.color = color;
            
            // Extract selected content and wrap in span
            const contents = range.extractContents();
            span.appendChild(contents);
            
            // Insert colored content
            range.insertNode(span);
            
            // Clear selection
            selection.removeAllRanges();
            
            this.showMessage(`Selected text color set to ${color}`);
        }
    }
    
    // Apply color directly (called when clicking color square)
    applyColorDirect(color) {
        const selection = window.getSelection();
        const selectedText = selection.toString();
        
        console.log('Apply color directly:', color);
        console.log('Selected text:', selectedText);
        
        if (selection.rangeCount > 0 && !selection.isCollapsed && selectedText.trim()) {
            try {
                const success = document.execCommand('foreColor', false, color);
                if (!success) {
                    this.applyFontColorManually(color);
                } else {
                    this.showMessage(`Selected text "${selectedText}" color set to ${color}`);
                }
            } catch (error) {
                this.applyFontColorManually(color);
            }
        } else {
            this.showMessage('Please select text to set color first');
        }
    }
    
    // Apply font color to selected text
    applyFontColor(color) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);
            const span = document.createElement('span');
            span.style.color = color;
            span.appendChild(range.extractContents());
            range.insertNode(span);
            this.showMessage(`Text color set to ${color}`);
        } else {
            this.showMessage('Please select text to set color first');
        }
    }
    
    // Highlight display function
    applyHighlight() {
        const color = document.getElementById('highlight-color').value;
        
        // Check if there is selected text
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && !selection.isCollapsed) {
            // Has selected text, apply highlight
            try {
                // First try execCommand
                const success = document.execCommand('backColor', false, color);
                if (!success) {
                    // If execCommand fails, use manual method
                    this.applyHighlightManually(color);
                } else {
                    this.showMessage(`Selected text highlight color set to ${color}`);
                }
            } catch (error) {
                // If error occurs, use manual method
                this.applyHighlightManually(color);
            }
        } else {
            // No selected text, prompt user
            this.showMessage('Please select text to highlight first');
        }
    }
    
    // Apply highlight directly (called when clicking color square)
    applyHighlightDirect(color) {
        const selection = window.getSelection();
        const selectedText = selection.toString();
        
        console.log('Apply highlight directly:', color);
        console.log('Selected text:', selectedText);
        
        if (selection.rangeCount > 0 && !selection.isCollapsed && selectedText.trim()) {
            try {
                const success = document.execCommand('backColor', false, color);
                if (!success) {
                    this.applyHighlightManually(color);
                } else {
                    this.showMessage(`Selected text "${selectedText}" highlight color set to ${color}`);
                }
            } catch (error) {
                this.applyHighlightManually(color);
            }
        } else {
            this.showMessage('Please select text to highlight first');
        }
    }
    
    // Manually apply highlight
    applyHighlightManually(color) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);
            
            // Create span element with highlight
            const span = document.createElement('span');
            span.style.backgroundColor = color;
            
            // Extract selected content and wrap in span
            const contents = range.extractContents();
            span.appendChild(contents);
            
            // Insert highlighted content
            range.insertNode(span);
            
            // Clear selection
            selection.removeAllRanges();
            
            this.showMessage(`Selected text highlight color set to ${color}`);
        }
    }
    
    // Apply highlight to selected text
    applyHighlightToSelection(color) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);
            const span = document.createElement('span');
            span.style.backgroundColor = color;
            span.appendChild(range.extractContents());
            range.insertNode(span);
            this.showMessage(`Text highlight color set to ${color}`);
        } else {
            this.showMessage('Please select text to highlight first');
        }
    }
    
    
    // Page setup function
    // Page Orientation Functions
    
    applyPageOrientation() {
        try {
            const orientation = document.querySelector('input[name="page-orientation"]:checked').value;
            
            // Store current orientation for persistence
            this.currentDocument.pageOrientation = orientation;
            
            // Apply orientation to the editor with realistic page dimensions
            if (orientation === 'landscape') {
                // Landscape: wider than tall (like A4 rotated)
                this.editor.style.setProperty('width', '297mm', 'important');
                this.editor.style.setProperty('height', '210mm', 'important');
                this.editor.style.setProperty('max-width', '297mm', 'important');
                this.editor.style.setProperty('min-height', '210mm', 'important');
                this.editor.style.setProperty('transform', 'none', 'important');
                this.editor.style.setProperty('position', 'static', 'important');
                this.editor.style.setProperty('margin', '20px auto', 'important');
                this.editor.style.setProperty('padding', '20mm', 'important');
                this.editor.style.setProperty('box-sizing', 'border-box', 'important');
                
            } else {
                // Portrait: taller than wide (standard A4)
                this.editor.style.setProperty('width', '210mm', 'important');
                this.editor.style.setProperty('height', '297mm', 'important');
                this.editor.style.setProperty('max-width', '210mm', 'important');
                this.editor.style.setProperty('min-height', '297mm', 'important');
                this.editor.style.setProperty('transform', 'none', 'important');
                this.editor.style.setProperty('position', 'static', 'important');
                this.editor.style.setProperty('margin', '20px auto', 'important');
                this.editor.style.setProperty('padding', '20mm', 'important');
                this.editor.style.setProperty('box-sizing', 'border-box', 'important');
                
            }
            
            // Ensure proper page styling
            this.editor.style.setProperty('background-color', 'white', 'important');
            this.editor.style.setProperty('font-family', 'Arial, sans-serif', 'important');
            this.editor.style.setProperty('font-size', '12pt', 'important');
            this.editor.style.setProperty('line-height', '1.5', 'important');
            this.editor.style.setProperty('overflow-y', 'auto', 'important');
            
            this.showMessage(`Page orientation set to ${orientation} (${orientation === 'landscape' ? '297×210mm' : '210×297mm'})`);
            this.currentDocument.modified = true;
            this.updateStatus();
        } catch (error) {
            console.error('Error applying page orientation:', error);
            this.showMessage('Error applying page orientation', 'error');
        }
    }
    
    resetPageOrientation() {
        try {
            // Reset to portrait orientation
            document.querySelector('input[name="page-orientation"][value="portrait"]').checked = true;
            
            // Apply portrait styles (standard A4 dimensions)
            this.editor.style.setProperty('width', '210mm', 'important');
            this.editor.style.setProperty('height', '297mm', 'important');
            this.editor.style.setProperty('max-width', '210mm', 'important');
            this.editor.style.setProperty('min-height', '297mm', 'important');
            this.editor.style.setProperty('transform', 'none', 'important');
            this.editor.style.setProperty('position', 'static', 'important');
            this.editor.style.setProperty('margin', '20px auto', 'important');
            this.editor.style.setProperty('padding', '20mm', 'important');
            this.editor.style.setProperty('box-sizing', 'border-box', 'important');
            
            // Store orientation
            this.currentDocument.pageOrientation = 'portrait';
            
            this.showMessage('Page orientation reset to portrait (210×297mm)');
            this.currentDocument.modified = true;
            this.updateStatus();
        } catch (error) {
            console.error('Error resetting page orientation:', error);
            this.showMessage('Error resetting page orientation', 'error');
        }
    }
    
    // Initialize page orientation on document load
    initializePageOrientation() {
        try {
            // Set default orientation if none exists
            if (!this.currentDocument.pageOrientation) {
                this.currentDocument.pageOrientation = 'portrait';
            }
            
            // Apply the stored orientation
            const orientation = this.currentDocument.pageOrientation;
            
            if (orientation === 'landscape') {
                // Landscape: wider than tall (like A4 rotated)
                this.editor.style.setProperty('width', '297mm', 'important');
                this.editor.style.setProperty('height', '210mm', 'important');
                this.editor.style.setProperty('max-width', '297mm', 'important');
                this.editor.style.setProperty('min-height', '210mm', 'important');
                this.editor.style.setProperty('transform', 'none', 'important');
                this.editor.style.setProperty('position', 'static', 'important');
                this.editor.style.setProperty('margin', '20px auto', 'important');
                this.editor.style.setProperty('padding', '20mm', 'important');
                this.editor.style.setProperty('box-sizing', 'border-box', 'important');
                
            } else {
                // Portrait: taller than wide (standard A4)
                this.editor.style.setProperty('width', '210mm', 'important');
                this.editor.style.setProperty('height', '297mm', 'important');
                this.editor.style.setProperty('max-width', '210mm', 'important');
                this.editor.style.setProperty('min-height', '297mm', 'important');
                this.editor.style.setProperty('transform', 'none', 'important');
                this.editor.style.setProperty('position', 'static', 'important');
                this.editor.style.setProperty('margin', '20px auto', 'important');
                this.editor.style.setProperty('padding', '20mm', 'important');
                this.editor.style.setProperty('box-sizing', 'border-box', 'important');
            }
            
            // Ensure proper page styling
            this.editor.style.setProperty('background-color', 'white', 'important');
            this.editor.style.setProperty('font-family', 'Arial, sans-serif', 'important');
            this.editor.style.setProperty('font-size', '12pt', 'important');
            this.editor.style.setProperty('line-height', '1.5', 'important');
            this.editor.style.setProperty('overflow-y', 'auto', 'important');
            
        } catch (error) {
            console.error('Error initializing page orientation:', error);
        }
    }
    
    // Page Setup Functions (for Format section)
    
    applyPageSetup() {
        try {
            const orientation = 'portrait'; // Default to portrait since orientation is removed from Format section
            const pageSize = document.getElementById('page-size').value;
            const marginTop = parseFloat(document.getElementById('margin-top').value) || 2.54;
            const marginBottom = parseFloat(document.getElementById('margin-bottom').value) || 2.54;
            const marginLeft = parseFloat(document.getElementById('margin-left').value) || 3.18;
            const marginRight = parseFloat(document.getElementById('margin-right').value) || 3.18;
            
            // Define page sizes in mm (width x height)
            const pageSizes = {
                'A4': { width: 210, height: 297 },
                'A3': { width: 297, height: 420 },
                'Letter': { width: 216, height: 279 }, // 8.5" x 11" in mm
                'Legal': { width: 216, height: 356 },  // 8.5" x 14" in mm
                'A5': { width: 148, height: 210 },
                'B4': { width: 250, height: 353 }
            };
            
            let width, height;
            if (pageSizes[pageSize]) {
                width = pageSizes[pageSize].width;
                height = pageSizes[pageSize].height;
            } else {
                width = 210; // Default to A4
                height = 297;
            }
            
            // Swap dimensions for landscape orientation
            if (orientation === 'landscape') {
                [width, height] = [height, width];
            }
            
            // Apply page size with orientation
            this.editor.style.width = width + 'mm';
            this.editor.style.minHeight = height + 'mm';
            this.editor.style.maxWidth = width + 'mm';
            
            // Apply margins (convert cm to mm)
            this.editor.style.marginTop = (marginTop * 10) + 'mm';
            this.editor.style.marginBottom = (marginBottom * 10) + 'mm';
            this.editor.style.marginLeft = (marginLeft * 10) + 'mm';
            this.editor.style.marginRight = (marginRight * 10) + 'mm';
            
            // Add page styles
            this.editor.style.backgroundColor = 'white';
            this.editor.style.boxShadow = '0 0 15px rgba(0,0,0,0.2)';
            this.editor.style.padding = '15mm';
            this.editor.style.border = '1px solid #ccc';
            this.editor.style.borderRadius = '2px';
            this.editor.style.fontFamily = 'Arial, sans-serif';
            this.editor.style.fontSize = '12pt';
            this.editor.style.lineHeight = '1.5';
            
            // Store settings for persistence
            this.currentDocument.pageSettings = {
                orientation: orientation,
                size: pageSize,
                margins: {
                    top: marginTop,
                    bottom: marginBottom,
                    left: marginLeft,
                    right: marginRight
                }
            };
            
            this.showMessage(`Page setup applied: ${pageSize} ${orientation} with ${marginTop}cm margins`);
            this.currentDocument.modified = true;
            this.updateStatus();
        } catch (error) {
            console.error('Error applying page setup:', error);
            this.showMessage('Error applying page setup', 'error');
        }
    }
    
    resetPageSetup() {
        try {
            document.getElementById('page-size').value = 'A4';
            document.getElementById('margin-top').value = '2.54';
            document.getElementById('margin-bottom').value = '2.54';
            document.getElementById('margin-left').value = '3.18';
            document.getElementById('margin-right').value = '3.18';
            
            this.showMessage('Page setup reset to default');
        } catch (error) {
            console.error('Error resetting page setup:', error);
            this.showMessage('Error resetting page setup', 'error');
        }
    }
    
    setMarginPreset(preset) {
        try {
            const presets = {
                'normal': { top: 2.54, bottom: 2.54, left: 3.18, right: 3.18 },
                'narrow': { top: 1.27, bottom: 1.27, left: 1.27, right: 1.27 },
                'wide': { top: 3.81, bottom: 3.81, left: 5.08, right: 5.08 }
            };
            
            if (presets[preset]) {
                document.getElementById('margin-top').value = presets[preset].top;
                document.getElementById('margin-bottom').value = presets[preset].bottom;
                document.getElementById('margin-left').value = presets[preset].left;
                document.getElementById('margin-right').value = presets[preset].right;
                
                this.showMessage(`${preset.charAt(0).toUpperCase() + preset.slice(1)} margins applied`);
            }
        } catch (error) {
            console.error('Error setting margin preset:', error);
            this.showMessage('Error setting margin preset', 'error');
        }
    }
    
    // Header & Footer functionality
    editHeader() {
        const headerHTML = `<div class="header" style="border-bottom: 1px solid #ccc; padding: 10px; margin-bottom: 20px; text-align: center;">Header Content</div>`;
        this.editor.insertAdjacentHTML('afterbegin', headerHTML);
        this.showMessage('Header editing mode activated');
    }
    
    editFooter() {
        const footerHTML = `<div class="footer" style="border-top: 1px solid #ccc; padding: 10px; margin-top: 20px; text-align: center;">Footer Content</div>`;
        this.editor.insertAdjacentHTML('beforeend', footerHTML);
        this.showMessage('Footer editing mode activated');
    }
    
    // Comments System Implementation
    initializeComments() {
        // Add event listeners for text selection
        this.editor.addEventListener('mouseup', () => this.handleTextSelection());
        this.editor.addEventListener('keyup', () => this.handleTextSelection());
    }

    handleTextSelection() {
        const selection = window.getSelection();
        if (selection.toString().trim()) {
            this.selectedText = selection.toString().trim();
        }
    }

    addComment() {
        // Legacy function - redirect to inline comment
        this.addInlineComment();
    }

    addInlineComment() {
        const commentText = document.getElementById('comment-text')?.value;
        const commentAuthor = document.getElementById('comment-author')?.value || 'Reviewer';
        const commentPriority = document.getElementById('comment-priority')?.value || 'normal';
        
        if (!commentText || commentText.trim() === '') {
            this.showMessage('Please enter comment content');
            return;
        }

        // Check if text is selected
        const selection = window.getSelection();
        if (!selection.toString().trim()) {
            this.showMessage('Please select some text in the document first');
            return;
        }

        // Create comment object
        const comment = {
            id: ++this.commentId,
            text: commentText.trim(),
            author: commentAuthor,
            priority: commentPriority,
            timestamp: new Date(),
            resolved: false,
            replies: []
        };

        // Add to comments array
        this.documentComments.push(comment);

        // Create comment marker in document
        this.createInlineCommentMarker(comment);

        // Clear form
        this.clearCommentForm();

        this.showMessage(`Comment added by ${commentAuthor} - click the 💬 icon to view`);
    }

    createCommentMarker(comment) {
        // Legacy function - redirect to inline comment
        this.createInlineCommentMarker(comment);
    }

    createInlineCommentMarker(comment) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const commentSpan = document.createElement('span');
            commentSpan.className = 'document-comment inline-comment';
            commentSpan.setAttribute('data-comment-id', comment.id);
            commentSpan.setAttribute('data-priority', comment.priority);
            commentSpan.setAttribute('title', `Comment by ${comment.author}: ${comment.text}`);
            
            // Enhanced styling based on priority
            const priorityStyles = {
                'low': {
                    background: '#e3f2fd',
                    borderLeft: '3px solid #2196f3',
                    color: '#1565c0'
                },
                'normal': {
                    background: '#fff3e0',
                    borderLeft: '3px solid #ff9800',
                    color: '#e65100'
                },
                'high': {
                    background: '#fce4ec',
                    borderLeft: '3px solid #e91e63',
                    color: '#ad1457'
                },
                'urgent': {
                    background: '#ffebee',
                    borderLeft: '3px solid #f44336',
                    color: '#c62828'
                }
            };
            
            const style = priorityStyles[comment.priority] || priorityStyles['normal'];
            
            commentSpan.style.cssText = `
                background: ${style.background};
                border-left: ${style.borderLeft};
                color: ${style.color};
                padding: 3px 8px;
                border-radius: 4px;
                cursor: pointer;
                position: relative;
                display: inline-block;
                margin: 0 2px;
                font-size: 12px;
                font-weight: bold;
                transition: all 0.2s ease;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            `;
            
            // Add hover effect
            commentSpan.addEventListener('mouseenter', () => {
                commentSpan.style.transform = 'scale(1.05)';
                commentSpan.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)';
            });
            
            commentSpan.addEventListener('mouseleave', () => {
                commentSpan.style.transform = 'scale(1)';
                commentSpan.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
            });
            
            // Priority-based icon
            const priorityIcons = {
                'low': '💬',
                'normal': '💬',
                'high': '⚠️',
                'urgent': '🚨'
            };
            
            commentSpan.innerHTML = priorityIcons[comment.priority] || '💬';
            
            // Add click handler
            commentSpan.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showInlineCommentDetails(comment.id);
            });
            
            try {
                range.surroundContents(commentSpan);
            } catch (e) {
                // If surroundContents fails, insert at cursor position
                range.insertNode(commentSpan);
            }
        } else {
            // If no selection, insert at cursor position
            const style = priorityStyles[comment.priority] || priorityStyles['normal'];
            this.insertContent(`<span class="document-comment inline-comment" data-comment-id="${comment.id}" data-priority="${comment.priority}" title="Comment by ${comment.author}: ${comment.text}" style="background: ${style.background}; border-left: ${style.borderLeft}; color: ${style.color}; padding: 3px 8px; border-radius: 4px; cursor: pointer; display: inline-block; margin: 0 2px; font-size: 12px; font-weight: bold;">💬</span>`);
        }
    }

    showCommentDetails(commentId) {
        // Legacy function - redirect to inline comment details
        this.showInlineCommentDetails(commentId);
    }

    showInlineCommentDetails(commentId) {
        const comment = this.documentComments.find(c => c.id === commentId);
        if (!comment) return;

        const modal = document.createElement('div');
        modal.className = 'comment-modal';
        modal.innerHTML = `
            <div class="comment-modal-content inline-comment-modal">
                <div class="comment-modal-header">
                    <h3>💬 Inline Comment</h3>
                    <button class="close-btn" onclick="this.parentElement.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="comment-details">
                    <div class="comment-info">
                        <div class="info-row">
                            <span class="info-label">Author:</span>
                            <span class="info-value">${comment.author}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Priority:</span>
                            <span class="priority-badge priority-${comment.priority}">${comment.priority.toUpperCase()}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Date:</span>
                            <span class="info-value">${comment.timestamp.toLocaleString()}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Status:</span>
                            <span class="status-badge ${comment.resolved ? 'resolved' : 'active'}">${comment.resolved ? 'Resolved' : 'Active'}</span>
                        </div>
                    </div>
                    <div class="comment-text">
                        <div class="comment-label">Comment:</div>
                        <div class="comment-content">${comment.text}</div>
                    </div>
                    ${comment.replies.length > 0 ? `
                        <div class="comment-replies">
                            <div class="replies-label">Replies (${comment.replies.length}):</div>
                            ${comment.replies.map(reply => `
                                <div class="reply-item">
                                    <div class="reply-header">
                                        <strong>${reply.author}</strong>
                                        <small>${reply.timestamp.toLocaleString()}</small>
                                    </div>
                                    <div class="reply-content">${reply.text}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                <div class="comment-actions">
                    <button class="btn btn-primary" onclick="miniWord.replyToComment(${comment.id})">Reply</button>
                    <button class="btn btn-warning" onclick="miniWord.editComment(${comment.id})">Edit</button>
                    ${comment.resolved ? 
                        `<button class="btn btn-info" onclick="miniWord.unresolveComment(${comment.id})">Unresolve</button>` :
                        `<button class="btn btn-success" onclick="miniWord.resolveComment(${comment.id})">Resolve</button>`
                    }
                    <button class="btn btn-danger" onclick="miniWord.deleteComment(${comment.id})">Delete</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    updateCommentsList() {
        // This function is no longer needed for inline comments
        // Comments are now managed directly in the document
            return;
    }

    clearCommentForm() {
        try {
        const commentText = document.getElementById('comment-text');
        const commentAuthor = document.getElementById('comment-author');
        const commentPriority = document.getElementById('comment-priority');
        
            if (commentText) {
                commentText.value = '';
                commentText.focus();
            }
            if (commentAuthor) {
                commentAuthor.value = 'Reviewer';
            }
            if (commentPriority) {
                commentPriority.value = 'normal';
            }
            
            this.showMessage('Comment form cleared');
        } catch (error) {
            console.error('Error clearing comment form:', error);
            this.showMessage('Error clearing form');
        }
    }

    // Alternative clear function that can be called directly
    clearCommentFormDirect() {
        this.clearCommentForm();
    }

    editComment(commentId) {
        const comment = this.documentComments.find(c => c.id === commentId);
        if (!comment) return;

        const newText = prompt('Edit comment:', comment.text);
        if (newText && newText.trim() !== '') {
            comment.text = newText.trim();
            this.updateCommentsList();
            this.showMessage('Comment updated');
        }
    }

    resolveComment(commentId) {
        const comment = this.documentComments.find(c => c.id === commentId);
        if (comment) {
            comment.resolved = true;
            this.updateCommentsList();
            this.showMessage('Comment resolved');
        }
    }

    unresolveComment(commentId) {
        const comment = this.documentComments.find(c => c.id === commentId);
        if (comment) {
            comment.resolved = false;
            this.updateCommentsList();
            this.showMessage('Comment unresolved');
        }
    }

    deleteComment(commentId) {
        if (confirm('Are you sure you want to delete this comment?')) {
            this.documentComments = this.documentComments.filter(c => c.id !== commentId);
            
            // Remove comment marker from document
            const commentMarker = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (commentMarker) {
                commentMarker.remove();
            }
            
            this.updateCommentsList();
            this.showMessage('Comment deleted');
        }
    }

    replyToComment(commentId) {
        const comment = this.documentComments.find(c => c.id === commentId);
        if (!comment) return;

        const replyText = prompt('Enter your reply:');
        if (replyText && replyText.trim() !== '') {
            const reply = {
                text: replyText.trim(),
                author: this.commentAuthor,
                timestamp: new Date()
            };
            comment.replies.push(reply);
            this.updateCommentsList();
            this.showMessage('Reply added');
        }
    }

    showAllComments() {
        // Function removed - inline comments don't need sidebar management
        this.showMessage('Comments are now managed inline in the document');
    }

    resolveAllComments() {
        // Function removed - inline comments don't need bulk operations
        this.showMessage('Use individual comment actions in the document');
    }

    deleteAllComments() {
        // Function removed - inline comments don't need bulk operations
        this.showMessage('Use individual comment actions in the document');
    }
    
    // Numbered list function
    // Enhanced List Functionality
    
    // Bulleted List Methods
    createBulletedList() {
        const bulletStyle = document.getElementById('bullet-style')?.value || 'disc';
        const allowNested = document.getElementById('bullet-nested')?.checked || false;
        
        // Create bulleted list with custom style
        const listHTML = this.generateBulletedListHTML(bulletStyle, allowNested);
        this.insertContent(listHTML);
        this.showMessage(`Bulleted list created with ${bulletStyle} style`);
    }
    
    generateBulletedListHTML(style, nested = false) {
        const bulletChars = {
            'disc': '•',
            'circle': '○',
            'square': '■',
            'dash': '—',
            'arrow': '→',
            'star': '★',
            'check': '✓',
            'diamond': '♦'
        };
        
        const bullet = bulletChars[style] || '•';
        return `
            <ul class="bulleted-list" style="list-style-type: ${style}; margin-left: 20px;">
                <li>First item</li>
                <li>Second item</li>
                <li>Third item</li>
            </ul>
        `;
    }
    
    updateBulletPreview() {
        const style = document.getElementById('bullet-style')?.value || 'disc';
        const preview = document.getElementById('bullet-preview');
        if (!preview) return;
        
        const bulletChars = {
            'disc': '●',
            'circle': '○',
            'square': '■',
            'dash': '—',
            'arrow': '→',
            'star': '★',
            'check': '✓',
            'diamond': '♦'
        };
        
        const bullet = bulletChars[style] || '●';
        preview.innerHTML = `
            <div class="preview-item">${bullet} First item</div>
            <div class="preview-item">${bullet} Second item</div>
            <div class="preview-item">${bullet} Third item</div>
        `;
    }
    
    
    
    
    
    
    
    
    
    
    
    // Custom bullet
    insertCustomBullet(bulletType) {
        const bullets = {
                'disc': '•',
                'circle': '○',
                'square': '■',
                'arrow': '→',
                'star': '★',
            'check': '✓'
        };
        
        const bullet = bullets[bulletType] || '•';
        const bulletHTML = `<ul style="list-style-type: none; padding-left: 20px;"><li style="position: relative;"><span style="position: absolute; left: -20px;">${bullet}</span>Item content</li></ul>`;
        this.insertContent(bulletHTML);
        this.showMessage(`Custom bullet ${bullet} inserted`);
    }
    
    
    // Apply default font function from settings
    applyDefaultFont() {
        const fontFamily = document.getElementById('default-font-family').value;
        const fontSize = document.getElementById('default-font-size').value;
        
        if (!fontFamily || !fontSize) {
            this.showMessage('Please select both font family and font size');
            return;
        }
        
        console.log('Applying font:', fontFamily, 'size:', fontSize + 'px'); // Debug log
        
        // Get the font with proper fallbacks
        const finalFontFamily = this.applyFontWithFallback(fontFamily, fontSize);
        
        // Apply to the entire editor with !important to override any existing styles
        this.editor.style.setProperty('font-family', finalFontFamily, 'important');
        this.editor.style.setProperty('font-size', fontSize + 'px', 'important');
        
        // Apply to all existing elements in the editor
        const allElements = this.editor.querySelectorAll('*');
        allElements.forEach(element => {
            element.style.setProperty('font-family', finalFontFamily, 'important');
            element.style.setProperty('font-size', fontSize + 'px', 'important');
        });
        
        // Also apply to any text nodes by wrapping them in spans if needed
        this.applyFontToTextNodes(finalFontFamily, fontSize);
        
        // Force a re-render by temporarily changing and restoring a style
        const originalDisplay = this.editor.style.display;
        this.editor.style.display = 'none';
        this.editor.offsetHeight; // Trigger reflow
        this.editor.style.display = originalDisplay;
        
        // Add a CSS rule to ensure the font is applied globally to the editor
        this.addFontCSSRule(finalFontFamily, fontSize);
        
        // Save the settings to localStorage for persistence
        localStorage.setItem('miniword_default_font_family', fontFamily);
        localStorage.setItem('miniword_default_font_size', fontSize);
        
        this.showMessage(`Default font applied: ${fontFamily}, size ${fontSize}px`);
    }
    
    // Helper function to apply font to text nodes
    applyFontToTextNodes(fontFamily, fontSize) {
        const walker = document.createTreeWalker(
            this.editor,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        let textNode;
        while (textNode = walker.nextNode()) {
            if (textNode.textContent.trim()) {
                // Create a span wrapper for the text node
                const span = document.createElement('span');
                span.style.setProperty('font-family', fontFamily, 'important');
                span.style.setProperty('font-size', fontSize + 'px', 'important');
                
                // Replace the text node with the wrapped version
                textNode.parentNode.replaceChild(span, textNode);
                span.appendChild(textNode);
            }
        }
    }
    
    // Enhanced font application with fallbacks
    applyFontWithFallback(fontFamily, fontSize) {
        // Create a test element to check if font is available
        const testElement = document.createElement('span');
        testElement.style.fontFamily = fontFamily;
        testElement.textContent = 'Test';
        testElement.style.visibility = 'hidden';
        testElement.style.position = 'absolute';
        document.body.appendChild(testElement);
        
        const computedStyle = window.getComputedStyle(testElement);
        const actualFont = computedStyle.fontFamily;
        
        document.body.removeChild(testElement);
        
        console.log('Requested font:', fontFamily);
        console.log('Actual font applied:', actualFont);
        
        // If the font didn't apply correctly, try with fallbacks
        let finalFontFamily = fontFamily;
        if (!actualFont.includes(fontFamily)) {
            // Add fallbacks for specific fonts
            if (fontFamily === 'Times New Roman') {
                finalFontFamily = '"Times New Roman", Times, serif';
            } else if (fontFamily === 'Arial') {
                finalFontFamily = 'Arial, Helvetica, sans-serif';
            }
        }
        
        return finalFontFamily;
    }
    
    // Add CSS rule to ensure font is applied
    addFontCSSRule(fontFamily, fontSize) {
        // Remove any existing font rules
        const existingRule = document.getElementById('miniword-font-rule');
        if (existingRule) {
            existingRule.remove();
        }
        
        // Create a new style element with the font rule
        const style = document.createElement('style');
        style.id = 'miniword-font-rule';
        style.textContent = `
            #editor, #editor * {
                font-family: ${fontFamily} !important;
                font-size: ${fontSize}px !important;
            }
        `;
        document.head.appendChild(style);
        
        console.log('Added CSS rule for font:', fontFamily, 'size:', fontSize + 'px');
    }
    
    // Save all application settings
    saveSettings() {
        const fontFamily = document.getElementById('default-font-family').value;
        const fontSize = document.getElementById('default-font-size').value;
        
        // Save to localStorage
        const settings = {
            fontFamily: fontFamily,
            fontSize: fontSize,
            timestamp: new Date().toISOString()
        };
        
        localStorage.setItem('miniword_settings', JSON.stringify(settings));
        
        // Apply the settings immediately
        this.applyDefaultFont();
        
        this.showMessage('Settings saved successfully!');
    }
    
    // Load settings from localStorage
    loadSettings() {
        const settings = localStorage.getItem('miniword_settings');
        if (settings) {
            try {
                const parsedSettings = JSON.parse(settings);
                
                // Apply font settings
                if (parsedSettings.fontFamily) {
                    this.editor.style.fontFamily = parsedSettings.fontFamily;
                }
                if (parsedSettings.fontSize) {
                    this.editor.style.fontSize = parsedSettings.fontSize + 'px';
                }
                
                console.log('Settings loaded:', parsedSettings);
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
    }
    
    
    
    // Load current settings into the form
    loadCurrentSettings() {
        const settings = localStorage.getItem('miniword_settings');
        if (settings) {
            try {
                const parsedSettings = JSON.parse(settings);
                
                // Set font family
                const fontFamilySelect = document.getElementById('default-font-family');
                if (fontFamilySelect && parsedSettings.fontFamily) {
                    fontFamilySelect.value = parsedSettings.fontFamily;
                }
                
                // Set font size
                const fontSizeSelect = document.getElementById('default-font-size');
                if (fontSizeSelect && parsedSettings.fontSize) {
                    fontSizeSelect.value = parsedSettings.fontSize;
                }
                
                
                console.log('Current settings loaded into form');
            } catch (e) {
                console.error('Error loading current settings:', e);
            }
        }
    }
    
    
    // Help system functions
    showKeyboardShortcuts() {
        const shortcutsList = document.getElementById('shortcuts-list');
        if (shortcutsList) {
            shortcutsList.style.display = shortcutsList.style.display === 'none' ? 'block' : 'none';
        }
        this.showMessage('Keyboard shortcuts toggled');
    }
    
    showTutorial() {
        this.showMessage('Starting interactive tutorial...');
        // Create a simple tutorial sequence
        const tutorialSteps = [
            'Welcome to MiniWord! Let\'s start with the basics.',
            'Click on the text area to start typing.',
            'Use the toolbar buttons to format your text.',
            'Try the Tools section for advanced features.',
            'Use Help anytime for assistance!'
        ];
        
        let currentStep = 0;
        const showNextStep = () => {
            if (currentStep < tutorialSteps.length) {
                this.showMessage(`Tutorial Step ${currentStep + 1}: ${tutorialSteps[currentStep]}`);
                currentStep++;
                setTimeout(showNextStep, 3000);
            } else {
                this.showMessage('Tutorial completed! You\'re ready to use MiniWord.');
            }
        };
        
        showNextStep();
    }
    
    resetToDefaults() {
        if (confirm('Are you sure you want to reset all settings to defaults? This will clear your preferences.')) {
            // Clear localStorage settings
            localStorage.removeItem('miniword_settings');
            localStorage.removeItem('miniword_default_font_family');
            localStorage.removeItem('miniword_default_font_size');
            
            // Reset editor to default state
            this.editor.style.fontFamily = 'Arial';
            this.editor.style.fontSize = '14px';
            
            
            this.showMessage('Settings reset to defaults successfully!');
        }
    }
    
    exportHelp() {
        const helpContent = `
MiniWord Help Guide
==================

Keyboard Shortcuts:
- Ctrl+N: New Document
- Ctrl+O: Open Document  
- Ctrl+S: Save Document
- Ctrl+P: Print Document
- Ctrl+Z: Undo
- Ctrl+Y: Redo
- Ctrl+X: Cut
- Ctrl+C: Copy
- Ctrl+V: Paste
- Ctrl+F: Find
- Ctrl+H: Replace
- Ctrl+B: Bold
- Ctrl+I: Italic
- Ctrl+U: Underline

Features:
- Text formatting and styling
- Tables and charts
- Lists and bullets
- Comments and reviews
- Document statistics
- Auto-save functionality

For more help, use the interactive help system in the Help section.
        `;
        
        // Create and download the help file
        const blob = new Blob([helpContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'MiniWord_Help_Guide.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showMessage('Help guide exported successfully!');
    }
    
    searchHelp(query) {
        const resultsDiv = document.getElementById('help-results');
        if (!resultsDiv) return;
        
        if (query.length < 2) {
            resultsDiv.innerHTML = '';
            return;
        }
        
        const helpTopics = {
            'format': 'Text formatting options: Bold, Italic, Underline, Font size, Colors',
            'table': 'Table management: Insert tables, Edit cells, Format tables',
            'list': 'Lists: Create bulleted and numbered lists, Manage list items',
            'comment': 'Comments: Add inline comments, Review documents, Manage feedback',
            'save': 'Saving: Auto-save, Manual save, Export options',
            'print': 'Printing: Print document, Print preview, Page setup',
            'shortcut': 'Keyboard shortcuts: Use Ctrl+key combinations for quick actions',
            'tutorial': 'Tutorial: Interactive guide to learn MiniWord features',
            'settings': 'Settings: Configure application preferences and defaults'
        };
        
        const results = [];
        for (const [key, value] of Object.entries(helpTopics)) {
            if (key.includes(query.toLowerCase()) || value.toLowerCase().includes(query.toLowerCase())) {
                results.push(`<div class="help-result-item"><strong>${key.toUpperCase()}:</strong> ${value}</div>`);
            }
        }
        
        if (results.length > 0) {
            resultsDiv.innerHTML = results.join('');
        } else {
            resultsDiv.innerHTML = '<div class="help-result-item">No results found. Try different keywords.</div>';
        }
    }
    
    clearHelpSearch() {
        const searchInput = document.getElementById('help-search');
        const resultsDiv = document.getElementById('help-results');
        if (searchInput) searchInput.value = '';
        if (resultsDiv) resultsDiv.innerHTML = '';
    }
    
    showTip(tipType) {
        const tips = {
            'formatting': '💡 Formatting Tips:\n\n• Use Ctrl+B for bold, Ctrl+I for italic, Ctrl+U for underline\n• Change font size with the Format toolbar\n• Use highlight colors to emphasize text\n• Clear formatting with Ctrl+K',
            'tables': '📊 Table Management:\n\n• Insert tables from the Insert menu\n• Right-click on tables to edit properties\n• Use Tab to move between cells\n• Select rows/columns to format them',
            'lists': '📝 Lists and Bullets:\n\n• Use the Tools section for bulleted and numbered lists\n• Place cursor before text and click bullet/number buttons\n• Convert existing text to lists\n• Manage list items with the sidebar options',
            'comments': '💬 Comments and Reviews:\n\n• Select text and add comments from Tools section\n• Comments appear inline next to selected text\n• Use different priority levels for organization\n• Click comment icons to view/edit details'
        };
        
        const tip = tips[tipType] || 'Tip not found.';
        alert(tip);
    }
    
    toggleShortcuts() {
        const shortcutsList = document.getElementById('shortcuts-list');
        if (shortcutsList) {
            shortcutsList.style.display = shortcutsList.style.display === 'none' ? 'block' : 'none';
        }
    }
    
    // Enhanced spell check function
    spellCheck() {
        const text = this.editor.textContent;
        const words = text.split(/\s+/);
        const commonWords = [
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
            'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him',
            'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only',
            'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want',
            'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had', 'were', 'said', 'each', 'which', 'their',
            'China', 'Chinese', 'Document', 'Edit', 'Function', 'Application', 'Settings', 'Page', 'Format', 'Text', 'Content', 'Insert', 'Delete', 'Copy', 'Paste', 'Save', 'Open', 'New',
            'hello', 'world', 'computer', 'programming', 'software', 'development', 'technology', 'internet', 'website', 'email', 'password', 'username',
            'database', 'server', 'client', 'application', 'interface', 'system', 'network', 'security', 'information', 'data', 'file', 'folder',
            'document', 'text', 'content', 'format', 'style', 'design', 'layout', 'template', 'theme', 'color', 'font', 'size', 'bold', 'italic',
            'underline', 'strikethrough', 'subscript', 'superscript', 'alignment', 'margin', 'padding', 'border', 'background', 'foreground'
        ];
        
        let misspelledWords = [];
        words.forEach(word => {
            const cleanWord = word.toLowerCase().replace(/[^\w\u4e00-\u9fff]/g, '');
            // Check all words, including short ones, but skip very short words that are likely valid
            if (cleanWord.length > 0 && !commonWords.includes(cleanWord)) {
                // Enhanced spell check logic
                if (!this.isValidWord(cleanWord)) {
                    misspelledWords.push({
                        word: word,
                        cleanWord: cleanWord,
                        suggestions: this.getSuggestions(cleanWord)
                    });
                }
            }
        });
        
        if (misspelledWords.length > 0) {
            this.highlightMisspelledWords(misspelledWords);
            this.showSpellCheckResults(misspelledWords);
            this.showMessage(`Found ${misspelledWords.length} possible spelling errors`);
        } else {
            this.showMessage('Spell check completed, no errors found');
        }
    }
    
    isValidWord(word) {
        // Enhanced word validation logic - check if word is in dictionary
        const dictionary = [
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
            'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him',
            'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only',
            'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want',
            'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had', 'were', 'said', 'each', 'which', 'their',
            'hello', 'world', 'computer', 'programming', 'software', 'development', 'technology', 'internet', 'website', 'email', 'password', 'username',
            'database', 'server', 'client', 'application', 'interface', 'system', 'network', 'security', 'information', 'data', 'file', 'folder',
            'document', 'text', 'content', 'format', 'style', 'design', 'layout', 'template', 'theme', 'color', 'font', 'size', 'bold', 'italic',
            'underline', 'strikethrough', 'subscript', 'superscript', 'alignment', 'margin', 'padding', 'border', 'background', 'foreground',
            'welcome', 'miniword', 'click', 'toolbar', 'buttons', 'start', 'using', 'various', 'features', 'page', 'setup', 'margins', 'header',
            'footer', 'spell', 'check', 'comment', 'review', 'tools', 'insert', 'table', 'image', 'link', 'symbol', 'equation',
            'chart', 'graph', 'diagram', 'picture', 'photo', 'illustration', 'drawing', 'sketch', 'blueprint', 'plan', 'scheme', 'outline',
            'summary', 'abstract', 'overview', 'introduction', 'conclusion', 'analysis', 'research', 'study', 'investigation', 'examination',
            'evaluation', 'assessment', 'review', 'critique', 'commentary', 'opinion', 'viewpoint', 'perspective', 'standpoint', 'position'
        ];
        
        // Check if word is in dictionary
        if (dictionary.includes(word.toLowerCase())) {
            return true;
        }
        
        // Allow Chinese characters
        if (/^[\u4e00-\u9fff]+$/.test(word)) {
            return true;
        }
        
        // Allow pure numbers
        if (/^\d+$/.test(word)) {
            return true;
        }
        
        // Allow mixed alphanumeric (like "test123")
        if (/^[a-z]+\d+$/.test(word) || /^\d+[a-z]+$/.test(word)) {
            return true;
        }
        
        // Allow common abbreviations and acronyms
        if (word.length <= 3 && /^[A-Z]+$/.test(word)) {
            return true;
        }
        
        // Allow single letters that are common (a, i, o)
        if (word.length === 1 && /^[aio]$/.test(word)) {
            return true;
        }
        
        // If none of the above conditions are met, it's likely misspelled
        return false;
    }
    
    // Start spell check from the UI
    startSpellCheck() {
        this.showMessage('Starting spell check...');
        // Clear any existing spell check highlights first
        this.clearSpellCheckHighlights();
        setTimeout(() => {
            this.spellCheck();
        }, 500);
    }

    // Clear existing spell check highlights
    clearSpellCheckHighlights() {
        const highlightedWords = this.editor.querySelectorAll('.misspelled-word');
        highlightedWords.forEach(span => {
            const parent = span.parentNode;
            parent.replaceChild(document.createTextNode(span.textContent), span);
            parent.normalize();
        });
    }

    // Get spelling suggestions for a word
    getSuggestions(word) {
        const suggestions = [];
        const dictionary = [
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
            'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him',
            'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only',
            'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want',
            'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had', 'were', 'said', 'each', 'which', 'their',
            'hello', 'world', 'computer', 'programming', 'software', 'development', 'technology', 'internet', 'website', 'email', 'password', 'username',
            'database', 'server', 'client', 'application', 'interface', 'system', 'network', 'security', 'information', 'data', 'file', 'folder',
            'document', 'text', 'content', 'format', 'style', 'design', 'layout', 'template', 'theme', 'color', 'font', 'size', 'bold', 'italic',
            'underline', 'strikethrough', 'subscript', 'superscript', 'alignment', 'margin', 'padding', 'border', 'background', 'foreground',
            'welcome', 'miniword', 'click', 'toolbar', 'buttons', 'start', 'using', 'various', 'features', 'page', 'setup', 'margins', 'header',
            'footer', 'spell', 'check', 'comment', 'review', 'tools', 'insert', 'table', 'image', 'link', 'symbol', 'equation',
            'chart', 'graph', 'diagram', 'picture', 'photo', 'illustration', 'drawing', 'sketch', 'blueprint', 'plan', 'scheme', 'outline',
            'summary', 'abstract', 'overview', 'introduction', 'conclusion', 'analysis', 'research', 'study', 'investigation', 'examination',
            'evaluation', 'assessment', 'review', 'critique', 'commentary', 'opinion', 'viewpoint', 'perspective', 'standpoint', 'position'
        ];
        
        // Enhanced suggestion algorithm based on edit distance
        dictionary.forEach(dictWord => {
            if (this.calculateEditDistance(word, dictWord) <= 2) {
                suggestions.push(dictWord);
            }
        });
        
        // Add specific suggestions for common typos
        if (word === 't') {
            suggestions.push('to');
            suggestions.push('the');
        }
        if (word === 'teh') {
            suggestions.push('the');
        }
        if (word === 'adn') {
            suggestions.push('and');
        }
        
        // Sort by edit distance (closer matches first)
        suggestions.sort((a, b) => {
            const distA = this.calculateEditDistance(word, a);
            const distB = this.calculateEditDistance(word, b);
            return distA - distB;
        });
        
        return suggestions.slice(0, 5); // Return top 5 suggestions
    }

    // Calculate edit distance between two words
    calculateEditDistance(str1, str2) {
        const matrix = [];
        for (let i = 0; i <= str2.length; i++) {
            matrix[i] = [i];
        }
        for (let j = 0; j <= str1.length; j++) {
            matrix[0][j] = j;
        }
        for (let i = 1; i <= str2.length; i++) {
            for (let j = 1; j <= str1.length; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }
        return matrix[str2.length][str1.length];
    }

    // Show spell check results in the UI
    showSpellCheckResults(misspelledWords) {
        const resultsContainer = document.querySelector('.spelling-results');
        if (resultsContainer) {
            let html = '<h3>Spelling Errors Found:</h3>';
            misspelledWords.forEach((item, index) => {
                html += `
                    <div class="spelling-error-item" data-index="${index}">
                        <div class="error-word">
                            <strong>${item.word}</strong>
                            ${item.suggestions.length > 0 ? 
                                `<div class="suggestions">
                                    <span>Suggestions: </span>
                                    ${item.suggestions.map(suggestion => 
                                        `<button class="suggestion-btn" onclick="miniWord.replaceWord('${item.word}', '${suggestion}')">${suggestion}</button>`
                                    ).join(' ')}
                                </div>` : 
                                '<span class="no-suggestions">No suggestions available</span>'
                            }
                        </div>
                        <div class="error-actions">
                            <button class="btn btn-sm" onclick="miniWord.ignoreWord('${item.word}')">Ignore</button>
                            <button class="btn btn-sm" onclick="miniWord.addToDictionary('${item.word}')">Add to Dictionary</button>
                        </div>
                    </div>
                `;
            });
            resultsContainer.innerHTML = html;
        }
    }

    // Replace a word with a suggestion
    replaceWord(oldWord, newWord) {
        const regex = new RegExp(`\\b${oldWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
        this.editor.innerHTML = this.editor.innerHTML.replace(regex, newWord);
        this.showMessage(`Replaced "${oldWord}" with "${newWord}"`);
        this.refreshSpellCheckResults();
    }

    // Ignore a word (remove highlighting)
    ignoreWord(word) {
        const regex = new RegExp(`<span[^>]*>${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}</span>`, 'gi');
        this.editor.innerHTML = this.editor.innerHTML.replace(regex, word);
        this.showMessage(`Ignored "${word}"`);
        this.refreshSpellCheckResults();
    }

    // Add word to dictionary
    addToDictionary(word) {
        // In a real implementation, this would add to a persistent dictionary
        this.showMessage(`Added "${word}" to dictionary`);
        this.ignoreWord(word);
    }

    // Refresh spell check results display
    refreshSpellCheckResults() {
        setTimeout(() => {
            this.spellCheck();
        }, 100);
    }
    
    highlightMisspelledWords(words) {
        words.forEach(item => {
            const word = item.word || item;
            const regex = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            this.editor.innerHTML = this.editor.innerHTML.replace(regex, 
                `<span class="misspelled-word" style="background-color: #ffcccc; border-bottom: 1px wavy red; cursor: pointer;" 
                 title="Possible spelling error - Click for suggestions" 
                 onclick="miniWord.showWordSuggestions('${word}')">${word}</span>`);
        });
    }

    // Show suggestions for a specific word
    showWordSuggestions(word) {
        const suggestions = this.getSuggestions(word.toLowerCase());
        if (suggestions.length > 0) {
            const suggestionText = suggestions.join(', ');
            this.showMessage(`Suggestions for "${word}": ${suggestionText}`);
        } else {
            this.showMessage(`No suggestions found for "${word}"`);
        }
    }
    
    // Helper function to get the best insertion point
    getBestInsertionPoint() {
        const selection = window.getSelection();
        
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            
            // Check if cursor is within editor or page-content
            const isWithinEditor = this.editor.contains(range.commonAncestorContainer) || 
                                 this.editor === range.commonAncestorContainer;
            
            if (isWithinEditor) {
                return range;
            }
            
            // Check if cursor is within any page-content element
            const pageContentElements = this.editor.querySelectorAll('.page-content');
            for (let pageContent of pageContentElements) {
                if (pageContent.contains(range.commonAncestorContainer) || 
                    pageContent === range.commonAncestorContainer) {
                    return range;
                }
            }
        }
        
        // If no valid cursor position, try to find the best fallback
        if (this.paginationMode) {
            const pageContentElements = this.editor.querySelectorAll('.page-content');
            if (pageContentElements.length > 0) {
                const lastPageContent = pageContentElements[pageContentElements.length - 1];
                const range = document.createRange();
                range.selectNodeContents(lastPageContent);
                range.collapse(false);
                return range;
            }
        }
        
        // Final fallback - create range at end of editor
        const range = document.createRange();
        range.selectNodeContents(this.editor);
        range.collapse(false);
        return range;
    }
    
    // Insert content into editor
    insertContent(content) {
        console.log('insertContent called with:', content); // Debug log
        console.log('Editor element:', this.editor); // Debug log
        
        if (!this.editor) {
            console.error('Editor element not found');
            this.showMessage('Error: Editor not found', 'error');
            return;
        }
        
        try {
            // Focus the editor to ensure it's the active element
            this.editor.focus();
            
            // Get the best insertion point (cursor position or fallback)
            const range = this.getBestInsertionPoint();
            
            // Check if we're inserting a chart and if there's already a chart nearby
            const isChartInsertion = content.includes('inserted-chart-container');
            if (isChartInsertion) {
                // Add some spacing before the chart if needed
                const container = range.commonAncestorContainer;
                const element = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
                
                // Check if the previous element is also a chart container
                if (element && element.previousElementSibling && 
                    element.previousElementSibling.classList.contains('inserted-chart-container')) {
                    // Add a paragraph break for better separation
                    const spacer = document.createElement('p');
                    spacer.innerHTML = '&nbsp;';
                    spacer.style.margin = '10px 0';
                    spacer.style.height = '1px';
                    spacer.style.overflow = 'hidden';
                    range.insertNode(spacer);
                    range.collapse(false);
                }
            }
            
            // Insert content at the determined position
            range.deleteContents();
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            while (tempDiv.firstChild) {
                range.insertNode(tempDiv.firstChild);
            }
            
            // Move cursor to after the inserted content
            range.collapse(false);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            
            console.log('Content inserted at cursor position'); // Debug log
            
        } catch (error) {
            console.error('insertContent error:', error); // Debug log
            // Fallback: always use insertAdjacentHTML at the end of editor
            this.editor.insertAdjacentHTML('beforeend', content);
            console.log('Content inserted using fallback method'); // Debug log
        }
    }
    
    showMessage(message) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 1001;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    parseManualTableData(headers, data) {
        const headerArray = headers.split(',').map(h => h.trim());
        const lines = data.trim().split('\n');
        const parsedData = [headerArray]; // First row is headers
        
        lines.forEach(line => {
            if (line.trim()) {
                const values = line.split(',').map(val => val.trim());
                parsedData.push(values);
            }
        });
        
        return parsedData;
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
`;
document.head.appendChild(style);

// Initialize application
let miniWord;
document.addEventListener('DOMContentLoaded', () => {
    miniWord = new MiniWord();
    
    // Add global test function for debugging
    window.testTableInsert = function() {
        console.log('Testing table insert...');
        const testHTML = '<table border="1" style="border-collapse: collapse; width: 100%; margin: 16px 0;"><tr><td style="padding: 8px; border: 1px solid #ccc;">Test Cell</td></tr></table>';
        miniWord.editor.insertAdjacentHTML('beforeend', testHTML);
        console.log('Test table inserted');
    };
    
    // Screenshot automation utilities
    window.getButtonPosition = function(testId) {
        const element = document.querySelector(`[data-testid="${testId}"]`);
        if (!element) {
            console.error(`Button with testid "${testId}" not found`);
            return null;
        }
        
        const rect = element.getBoundingClientRect();
        return {
            testId: testId,
            x: rect.left,
            y: rect.top,
            width: rect.width,
            height: rect.height,
            right: rect.right,
            bottom: rect.bottom,
            centerX: rect.left + rect.width / 2,
            centerY: rect.top + rect.height / 2
        };
    };
    
    window.getAllButtonPositions = function() {
        const buttons = document.querySelectorAll('[data-testid]');
        const positions = {};
        
        buttons.forEach(button => {
            const testId = button.getAttribute('data-testid');
            const position = window.getButtonPosition(testId);
            if (position) {
                positions[testId] = position;
            }
        });
        
        return positions;
    };
    
    // Debug function to log all button positions
    window.logAllButtonPositions = function() {
        const positions = window.getAllButtonPositions();
        console.log('All Button Positions:', positions);
        return positions;
    };
    
    // Helper function for automation tools
    window.getButtonInfo = function(testId) {
        const element = document.querySelector(`[data-testid="${testId}"]`);
        if (!element) return null;
        
        const rect = element.getBoundingClientRect();
        return {
            testId: testId,
            ariaLabel: element.getAttribute('aria-label'),
            title: element.getAttribute('title'),
            dataPage: element.getAttribute('data-page'),
            dataGroup: element.getAttribute('data-group'),
            position: {
                x: rect.left,
                y: rect.top,
                width: rect.width,
                height: rect.height
            },
            isVisible: rect.width > 0 && rect.height > 0,
            isInViewport: rect.top >= 0 && rect.left >= 0 && 
                         rect.bottom <= window.innerHeight && 
                         rect.right <= window.innerWidth
        };
    };
    
    // Test function for screenshot automation
    window.testScreenshotAutomation = function() {
        console.log('=== Screenshot Automation Test ===');
        
        // Test individual button
        const newButton = window.getButtonInfo('btn-new');
        console.log('New Button Info:', newButton);
        
        // Test all buttons
        const allPositions = window.getAllButtonPositions();
        console.log('All Button Positions:', allPositions);
        
        // Test specific buttons
        const importantButtons = [
            'btn-new', 'btn-open', 'btn-save', 'btn-print',
            'btn-insert-image', 'btn-insert-table',
            'btn-zoom-in', 'btn-zoom-out', 'btn-bold', 'btn-italic'
        ];
        
        importantButtons.forEach(testId => {
            const info = window.getButtonInfo(testId);
            if (info) {
                console.log(`${testId}:`, info);
            } else {
                console.warn(`Button ${testId} not found`);
            }
        });
        
        return allPositions;
    };
    
    // Add another test function
    window.testSimpleInsert = function() {
        console.log('Testing simple insert...');
        miniWord.editor.insertAdjacentHTML('beforeend', '<p>Simple test paragraph</p>');
        console.log('Simple test inserted');
    };
});
