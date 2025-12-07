"""
Transcriber Tab - UI for transcribe-anything integration

Responsibilities:
    - Display transcription interface
    - Allow local file or YouTube URL input
    - Show output SRT with copy-to-clipboard
    - Allow output file selection/deletion
    - Display transcription status and progress

Connects to TranscriberController for business logic.

Created: 2025-12-07 (v2.3)
Version: 2.3
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from views.base_tab import BaseTab


class TranscriberTab(BaseTab):
    """
    Transcriber tab UI for transcribe-anything integration.
    
    Features:
    - Local file or YouTube URL transcription
    - Device selection
    - SRT transcript display with copy button
    - Output file management
    - Progress tracking
    """
    
    def __init__(self, parent):
        """
        Initialize Transcriber tab.
        
        Args:
            parent: Parent widget (ttk.Notebook)
        """
        # Initialize variables BEFORE calling super().__init__()
        # because super().__init__() calls _setup_ui() which uses these
        self.mode_var = tk.StringVar(value="local")
        self.device_var = tk.StringVar(value="cuda")
        self.file_path_var = tk.StringVar()
        self.url_var = tk.StringVar()
        
        # Now call parent init (which calls _setup_ui())
        super().__init__(parent, "Transcriber")
        
        # Callbacks for controller (set after UI is created)
        self.on_file_selected = None
        self.on_transcribe_clicked = None
        self.on_copy_clicked = None
        self.on_clear_clicked = None
        
    def _setup_ui(self):
        """Setup transcriber tab UI"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Output expands
        
        # Mode selection
        self._setup_mode_section()
        
        # Input section (local file or YouTube URL)
        self._setup_input_section()
        
        # Device selection
        self._setup_device_section()
        
        # Output section
        self._setup_output_section()
        
        # Action bar
        self._setup_action_bar()
    
    def _setup_mode_section(self):
        """Setup mode selection (Local File / YouTube URL)"""
        mode_frame = ttk.LabelFrame(self, text="Mode Selection", padding="10")
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        mode_frame.columnconfigure(1, weight=1)
        
        ttk.Radiobutton(
            mode_frame,
            text="Local File",
            variable=self.mode_var,
            value="local",
            command=self._toggle_input_mode
        ).grid(row=0, column=0, sticky=tk.W, padx=10)
        
        ttk.Radiobutton(
            mode_frame,
            text="YouTube URL",
            variable=self.mode_var,
            value="youtube",
            command=self._toggle_input_mode
        ).grid(row=0, column=1, sticky=tk.W, padx=10)
    
    def _setup_input_section(self):
        """Setup input section (file browser or URL input)"""
        input_frame = ttk.LabelFrame(self, text="Input", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        input_frame.columnconfigure(1, weight=1)
        
        # Local file section
        self.local_frame = ttk.Frame(input_frame)
        self.local_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))
        self.local_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.local_frame, text="File:").grid(row=0, column=0, sticky=tk.W)
        self.file_entry = ttk.Entry(self.local_frame, textvariable=self.file_path_var)
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.browse_btn = ttk.Button(
            self.local_frame,
            text="Browse",
            command=self._browse_file
        )
        self.browse_btn.grid(row=0, column=2, padx=5)
        
        # YouTube URL section (hidden by default)
        self.youtube_frame = ttk.Frame(input_frame)
        # Don't grid it yet - will show/hide based on mode
        
        ttk.Label(self.youtube_frame, text="URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(self.youtube_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.youtube_frame.columnconfigure(1, weight=1)
    
    def _setup_device_section(self):
        """Setup device selection"""
        device_frame = ttk.LabelFrame(self, text="Device", padding="10")
        device_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        device_frame.columnconfigure(1, weight=1)
        
        devices = [
            ("CPU", "cpu"),
            ("CUDA (GPU)", "cuda"),
            ("Insane Mode", "insane"),
            ("MPS (Mac)", "mps")
        ]
        
        for i, (label, value) in enumerate(devices):
            ttk.Radiobutton(
                device_frame,
                text=label,
                variable=self.device_var,
                value=value
            ).grid(row=0, column=i, sticky=tk.W, padx=10)
    
    def _setup_output_section(self):
        """Setup output SRT display"""
        output_frame = ttk.LabelFrame(self, text="Transcript (SRT)", padding="10")
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(1, weight=1)
        
        # Copy button
        copy_frame = ttk.Frame(output_frame)
        copy_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        copy_frame.columnconfigure(0, weight=1)
        
        self.copy_btn = ttk.Button(
            copy_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_transcript
        )
        self.copy_btn.pack(side=tk.LEFT)
        
        self.copy_status = ttk.Label(copy_frame, text="")
        self.copy_status.pack(side=tk.LEFT, padx=10)
        
        # SRT display
        text_frame = ttk.Frame(output_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.transcript_text = tk.Text(
            text_frame,
            height=12,
            width=80,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.transcript_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.transcript_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.transcript_text.configure(yscrollcommand=scrollbar.set)
    
    def _setup_action_bar(self):
        """Setup action buttons"""
        action_frame = ttk.Frame(self)
        action_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        action_frame.columnconfigure(1, weight=1)
        
        self.transcribe_btn = ttk.Button(
            action_frame,
            text="🎬 Transcribe",
            command=self._transcribe_clicked,
            style="Accent.TButton" if hasattr(ttk.Style(), 'Accent.TButton') else ""
        )
        self.transcribe_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(
            action_frame,
            text="🗑️ Clear",
            command=self._clear_clicked
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Status indicator
        self.status_label = ttk.Label(action_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Loading indicator
        self.loading_label = ttk.Label(action_frame, text="")
        self.loading_label.pack(side=tk.LEFT, padx=5)
    
    def _toggle_input_mode(self):
        """Toggle between local file and YouTube URL input"""
        mode = self.mode_var.get()
        if mode == "local":
            self.local_frame.grid()
            self.youtube_frame.grid_remove()
        else:
            self.local_frame.grid_remove()
            self.youtube_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))
    
    def _browse_file(self):
        """Browse for local file"""
        supported_formats = [
            ("Media Files", "*.mp4 *.avi *.mov *.mkv *.mp3 *.wav *.flac *.m4a"),
            ("All Files", "*.*")
        ]
        file_path = filedialog.askopenfilename(
            title="Select media file",
            filetypes=supported_formats
        )
        if file_path:
            self.file_path_var.set(file_path)
            if self.on_file_selected:
                self.on_file_selected(file_path)
    
    def _transcribe_clicked(self):
        """Handle transcribe button click"""
        if self.on_transcribe_clicked:
            self.on_transcribe_clicked()
    
    def _copy_transcript(self):
        """Copy transcript to clipboard"""
        if self.on_copy_clicked:
            self.on_copy_clicked()
    
    def _clear_clicked(self):
        """Handle clear button click"""
        if self.on_clear_clicked:
            self.on_clear_clicked()
    
    # Public methods for controller
    
    def get_mode(self) -> str:
        """Get current mode (local or youtube)"""
        return self.mode_var.get()
    
    def get_file_path(self) -> str:
        """Get selected file path"""
        return self.file_path_var.get()
    
    def get_youtube_url(self) -> str:
        """Get YouTube URL"""
        return self.url_var.get()
    
    def get_device(self) -> str:
        """Get selected device"""
        return self.device_var.get()
    
    def set_transcript(self, content: str):
        """Set transcript text"""
        self.transcript_text.delete('1.0', tk.END)
        self.transcript_text.insert('1.0', content)
    
    def get_transcript(self) -> str:
        """Get current transcript"""
        return self.transcript_text.get('1.0', tk.END).rstrip()
    
    def set_status(self, message: str):
        """Set status message"""
        self.status_label.configure(text=message)
    
    def show_loading(self, show: bool = True):
        """Show/hide loading indicator"""
        if show:
            self.loading_label.configure(text="⏳ Transcribing...")
            self.transcribe_btn.configure(state="disabled")
        else:
            self.loading_label.configure(text="")
            self.transcribe_btn.configure(state="normal")
    
    def clear_all(self):
        """Clear all data"""
        self.file_path_var.set("")
        self.url_var.set("")
        self.transcript_text.delete('1.0', tk.END)
        self.set_status("Cleared")
        self.copy_status.configure(text="")
    
    def copy_to_clipboard(self) -> bool:
        """Copy transcript to clipboard"""
        try:
            content = self.get_transcript()
            if not content.strip():
                self.show_error("No transcript to copy")
                return False
            
            # Use tkinter's clipboard
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()  # Update clipboard
            
            self.copy_status.configure(text="✓ Copied!")
            return True
        except Exception as e:
            self.show_error(f"Failed to copy: {str(e)}")
            return False
    
    def get_content(self) -> str:
        """Get current content (transcript)"""
        return self.get_transcript()
