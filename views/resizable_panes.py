"""
Resizable Panes Widget

Provides a draggable separator between two panes, allowing users to manually
adjust the width of each pane by dragging the separator with the mouse.
"""

import tkinter as tk
from tkinter import ttk


class ResizablePanes(ttk.Frame):
    """
    A frame with two resizable panes separated by a draggable separator.

    Usage:
        panes = ResizablePanes(parent)
        panes.pack(fill=tk.BOTH, expand=True)

        # Add content to left and right panes
        left_frame = panes.left_pane
        right_frame = panes.right_pane

        # Customize separator appearance
        panes.separator_width = 4
        panes.separator_color = "#666666"
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize resizable panes.

        Args:
            parent: Parent widget
            **kwargs: Additional frame arguments
        """
        super().__init__(parent, **kwargs)

        # Configuration
        self.separator_width = 4
        self.separator_color = "#666666"
        self.separator_hover_color = "#888888"
        self.min_pane_width = 100

        # Create panes and separator
        self._create_widgets()
        self._setup_layout()
        self._bind_events()

        # Initial position (50% split)
        self._separator_position = 0.5

    def _create_widgets(self):
        """Create the pane frames and separator."""
        # Left pane
        self.left_pane = ttk.Frame(self)
        self.left_pane.configure(relief=tk.FLAT)

        # Right pane
        self.right_pane = ttk.Frame(self)
        self.right_pane.configure(relief=tk.FLAT)

        # Separator (vertical line that can be dragged)
        self.separator = tk.Frame(
            self, bg=self.separator_color, width=self.separator_width
        )
        self.separator.configure(cursor="sb_h_double_arrow")

    def _setup_layout(self):
        """Setup grid layout for panes and separator."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(1, weight=0)  # Separator doesn't expand
        self.rowconfigure(0, weight=1)

        # Position widgets
        self.left_pane.grid(row=0, column=0, sticky="nsew")
        self.separator.grid(row=0, column=1, sticky="ns")
        self.right_pane.grid(row=0, column=2, sticky="nsew")

        # Set initial separator position
        self.update_separator_position(0.5)

    def _bind_events(self):
        """Bind mouse events for dragging the separator."""
        # Binding to separator frame
        self.separator.bind("<ButtonPress-1>", self._on_drag_start)
        self.separator.bind("<B1-Motion>", self._on_drag_motion)
        self.separator.bind("<ButtonRelease-1>", self._on_drag_end)

        # Also bind to panes for better UX
        self.left_pane.bind("<B1-Motion>", self._on_drag_motion)
        self.right_pane.bind("<B1-Motion>", self._on_drag_motion)

    def _on_drag_start(self, event):
        """Handle start of drag operation."""
        self._drag_start_x = event.x_root
        self._initial_position = self._separator_position

        # Change separator color to indicate active state
        self.separator.configure(bg=self.separator_hover_color)

    def _on_drag_motion(self, event):
        """Handle separator dragging."""
        if not hasattr(self, "_drag_start_x"):
            return

        # Calculate new position based on mouse movement
        delta_x = event.x_root - self._drag_start_x
        window_width = self.winfo_width()

        if window_width <= 0:
            return

        # Calculate new position (0.0 to 1.0)
        pixel_delta = delta_x
        new_position = self._initial_position + (pixel_delta / window_width)

        # Constrain to valid range
        new_position = max(0.1, min(0.9, new_position))

        # Update separator position
        self.update_separator_position(new_position)

    def _on_drag_end(self, event):
        """Handle end of drag operation."""
        # Reset separator color
        self.separator.configure(bg=self.separator_color)

        # Clean up drag state
        if hasattr(self, "_drag_start_x"):
            del self._drag_start_x
        if hasattr(self, "_initial_position"):
            del self._initial_position

    def update_separator_position(self, position):
        """
        Update the separator position.

        Args:
            position: Position as fraction of total width (0.0 to 1.0)
        """
        self._separator_position = position

        # Calculate pixel position
        window_width = self.winfo_width()
        if window_width <= 0:
            return

        separator_x = int(window_width * position)

        # Update grid weights to achieve the desired split
        # Note: Grid weights must be integers, so we use a ratio
        # If position is 0.5, use equal weights (1:1)
        # If position is 0.75, use weights (3:1)
        # If position is 0.25, use weights (1:3)
        if position < 0.01:
            left_weight, right_weight = 1, 99
        elif position > 0.99:
            left_weight, right_weight = 99, 1
        else:
            # Calculate integer weights that approximate the ratio
            left_weight = int(position * 100)
            right_weight = 100 - left_weight

        self.columnconfigure(0, weight=left_weight)
        self.columnconfigure(2, weight=right_weight)

        # Store the position for reference
        self._current_position = position

    def get_separator_position(self):
        """
        Get the current separator position.

        Returns:
            float: Position as fraction of total width (0.0 to 1.0)
        """
        return getattr(self, "_current_position", 0.5)

    def set_separator_position(self, position):
        """
        Set the separator position.

        Args:
            position: Position as fraction of total width (0.0 to 1.0)
        """
        self.update_separator_position(position)
