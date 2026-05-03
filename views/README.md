# Views Layer

Tkinter UI components with no business logic. Views handle user interface presentation and interaction, delegating all business operations to controllers.

## Purpose

The views layer is responsible for:
- Building and managing UI elements
- Handling user input events
- Displaying data from controllers
- Managing UI state
- Providing callback interfaces for controllers

**Key Principle**: Views never contain business logic or directly access models. They communicate exclusively through controller callbacks.

## Contents

### Core View Files

| File | Purpose | Tab |
|------|---------|-----|
| `base_tab.py` | Base class for all tabs | - |
| `main_window.py` | Main application window | - |
| `file_tab.py` | File summarization interface | File Summarizer |
| `youtube_summarizer_tab.py` | YouTube processing interface | YouTube Summarizer |
| `transcriber_tab.py` | Single file transcription interface | Transcriber |
| `bulk_summarizer_tab.py` | Bulk summarization interface | Bulk Summarizer |
| `bulk_transcriber_tab.py` | Bulk transcription interface | Bulk Transcriber |
| `translation_tab.py` | Translation interface | Translation |
| `video_subtitler_tab.py` | Video subtitling interface | Video Subtitler |
| `downloader_tab.py` | Video download interface | Downloader |

### Utility Components

| File | Purpose |
|------|---------|
| `context_menu.py` | Right-click context menus |
| `resizable_panes.py` | Resizable UI panels |

### Modular Packages

| Package | Purpose |
|--------|---------|
| `views/bulk_summarizer/` | Advanced bulk summarization UI |
| `views/bulk_transcriber/` | Advanced bulk transcription UI |

## BaseTab Contract

All tabs inherit from `BaseTab` and must implement:

```python
class CustomTab(BaseTab):
    def _setup_ui(self):
        """Build UI elements"""
        # Create widgets, layout, bindings
    
    def get_content(self):
        """Return current content for processing"""
        return self.text_area.get("1.0", tk.END)
    
    def clear_all(self):
        """Reset UI to initial state"""
        self.text_area.delete("1.0", tk.END)
        self.status_var.set("Ready")
```

## Architecture Pattern

Standard view-controller interaction:

1. **View Initialization**: Create UI elements
2. **Controller Binding**: Set controller as callback handler
3. **User Interaction**: View triggers controller methods
4. **Controller Processing**: Controller handles business logic
5. **View Updates**: Controller updates view through methods

```python
# In controller
self.view.set_busy(True)
self.view.update_status("Processing...")
self.view.display_result(result)
```

## Modular Package Structure

### views/bulk_summarizer/

Advanced bulk summarization interface with:
- File type selection
- Output format options
- Recursive scanning
- Progress tracking

**See**: [views/bulk_summarizer/README.md](bulk_summarizer/README.md)

### views/bulk_transcriber/

Advanced bulk transcription interface with:
- Media format selection
- Output format selection
- Recursive scanning
- Progress tracking

**See**: [views/bulk_transcriber/README.md](bulk_transcriber/README.md)

## UI Conventions

1. **Naming**: View names match their tab + "Tab" suffix
2. **Initialization**: Views receive parent notebook reference
3. **Callback Pattern**: Views expose callback properties for controllers
4. **State Management**: Views manage their own UI state
5. **Error Display**: Views show errors via controller callbacks

## Adding New Views

To add a new view:

1. **Create View Class**: Extend BaseTab in `views/`
2. **Implement Contract**: Add required methods
3. **Create in MainWindow**: Add to main window initialization
4. **Wire Controller**: Initialize controller in main.py
5. **Add to Notebook**: Register tab in main window

```python
# In main_window.py
self.new_tab = NewTab(self.notebook)
self.notebook.add(self.new_tab, text="New Feature")

# In main.py
new_controller = NewController(window.new_tab)
```

## Utility Components

### context_menu.py

Provides right-click context menus for:
- Text areas
- File lists
- Result displays

### resizable_panes.py

Implements resizable panel layouts using:
- Mouse drag handlers
- Minimum/maximum size constraints
- Persistence of sizes

## Testing Views

Test views by mocking tkinter:

```python
from unittest.mock import Mock
from views.file_tab import FileTab

# Mock tkinter components
mock_notebook = Mock()

# Create and test view
tab = FileTab(mock_notebook)
tab._setup_ui()

# Test content retrieval
content = tab.get_content()
assert content == ""

# Test clearing
tab.clear_all()
```

## Styling Conventions

1. **Theme Support**: Light/dark mode compatible
2. **Consistent Spacing**: Use consistent padding/margins
3. **Accessibility**: Ensure readable font sizes
4. **Responsive**: Handle window resizing gracefully
5. **Feedback**: Provide visual feedback for actions

## Performance Tips

1. **Lazy Loading**: Load heavy components on demand
2. **Background Updates**: Use controller threads for long operations
3. **Widget Reuse**: Reuse widgets instead of recreating
4. **Event Throttling**: Limit rapid UI updates
5. **Memory Management**: Clean up temporary resources