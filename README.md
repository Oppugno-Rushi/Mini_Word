# MiniWord - Simulated Word Environment

This is a web-based simulated Word environment that integrates all PNG icon buttons, providing a Microsoft Word-like editing experience.

## Features

### File Operations
- **New Document** - Create blank document
- **Open Document** - Open local file or input content
- **Save Document** - Download as HTML format
- **Print Document** - Print current document
- **Close Document** - Close current document

### Edit Functions
- **Undo/Redo** - Support operation history
- **Cut/Copy/Paste** - Standard clipboard operations
- **Find/Replace** - Text search and replace functionality

### Text Formatting
- **Bold/Italic/Underline** - Basic text styles
- **Strikethrough/Superscript/Subscript** - Advanced text formatting
- **Font Color/Highlight** - Text color settings
- **Format Painter/Clear Formatting** - Format management

### Paragraph Formatting
- **Alignment** - Left, center, right, justify
- **Lists** - Bulleted and numbered lists
- **Indentation** - Increase/decrease paragraph indentation

### Insert Functions
- **Images** - Insert local or web images
- **Tables** - Create custom-sized tables
- **Links** - Insert hyperlinks
- **Equations** - Insert mathematical equations
- **Symbols** - Insert special symbols

### Layout Functions
- **Page Setup** - Set page size and margins
- **Header & Footer** - Page header and footer
- **Page Break** - Insert page break

### Review Functions
- **Spell Check** - Check document spelling
- **Comments** - Insert review comments

### View Functions
- **Zoom** - Zoom in/out view
- **Print Preview** - Preview print effect

## Usage

1. Open `index.html` file in browser
2. Start editing document content
3. Use toolbar buttons for formatting
4. Use keyboard shortcuts for efficiency

## Keyboard Shortcuts

| Function | Shortcut |
|------|--------|
| New Document | Ctrl+N |
| Open Document | Ctrl+O |
| Save Document | Ctrl+S |
| Print Document | Ctrl+P |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y |
| Cut | Ctrl+X |
| Copy | Ctrl+C |
| Paste | Ctrl+V |
| Find | Ctrl+F |
| Replace | Ctrl+H |
| Bold | Ctrl+B |
| Italic | Ctrl+I |
| Underline | Ctrl+U |

## File Structure

```
Mini_Word/
├── index.html              # Main page
├── styles.css              # Style file
├── script.js               # JavaScript functionality
├── button_manual.md        # Button manual
├── button_manifest.csv     # Button manifest
├── miniword_buttons_png/   # PNG icon folder
│   ├── file_new.png
│   ├── file_open.png
│   ├── file_save.png
│   └── ... (other icons)
└── README.md               # Documentation
```

## Technical Features

- **Responsive Design** - Adapt to different screen sizes
- **Modern UI** - Office-like interface design
- **Real-time Preview** - WYSIWYG editing
- **State Management** - Track document modification status
- **History** - Support undo/redo operations
- **Modal Dialogs** - User-friendly interaction

## Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Development Notes

This application is developed using pure HTML, CSS and JavaScript with no external dependencies. All icons come from the PNG files you provided, and functionality is fully implemented based on web standards.

## Notes

- Documents are saved in HTML format and can be opened in any modern browser
- Some advanced features (such as spell check) are demonstration features
- It is recommended to save documents regularly to avoid data loss
