"""
Transcriber Tab v2.4 - Enhanced UI with Output Options

Responsibilities:
    - Display transcription interface
    - Allow local file or YouTube URL input
    - Show output SRT with copy-to-clipboard
    - Output location selection (original vs custom)
    - Export buttons for individual formats
    - File format selection via checkboxes

Connects to TranscriberController for business logic.

Created: 2025-12-07 (v2.3)
Enhanced: 2025-12-07 (v2.4 - Layout and output options)
Version: 2.4
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
    - Output location selection
    - Export buttons for individual formats
    - File format checkboxes
    - Proper window resizing
    """
    
    def __init__(self, parent):
        """
        Initialize Transcriber tab.
        
        Args:
            parent: Parent widget (ttk.Notebook)
        """
        # Initialize variables BEFORE calling super().__init__()
        self.mode_var = tk.StringVar(value="local")
        self.device_var = tk.StringVar(value="cuda")
        self.file_path_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.output_location_var = tk.StringVar(value="original")  # original or custom
        self.output_custom_path_var = tk.StringVar()
        
        # Output format checkboxes
        self.keep_txt_var = tk.BooleanVar(value=True)
        self.keep_srt_var = tk.BooleanVar(value=True)
        self.keep_vtt_var = tk.BooleanVar(value=False)
        self.keep_json_var = tk.BooleanVar(value=False)
        self.keep_tsv_var = tk.BooleanVar(value=False)
        
        # Now call parent init (which calls _setup_ui())
        super().__init__(parent, "Transcriber")
        
        # Callbacks for controller (set after UI is created)
        self.on_file_selected = None
        self.on_transcribe_clicked = None
        self.on_copy_clicked = None
        self.on_export_txt_clicked = None
        self.on_export_srt_clicked = None
        self.on_clear_clicked = None
        
    def _setup_ui(self):
        """Setup transcriber tab UI with proper resizing"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)  # Transcript area expands
        
        row = 0
        
        # Mode selection
        self._setup_mode_section()
        row += 1
        
        # Input section (no pady between this and mode)
        self._setup_input_section()
        row += 1
        
        # Device selection (reduced pady)
        self._setup_device_section()
        row += 1
        
        # Output location selection
        self._setup_output_location_section()
        row += 1
        
        # Output format checkboxes
        self._setup_format_selection_section()
        row += 1
        
        # Output SRT display (this expands)
        self._setup_output_section()
        row += 1
        
        # Action bar
        self._setup_action_bar()
    
    def _setup_mode_section(self):
        """Setup mode selection (Local File / YouTube URL)"""
        mode_frame = ttk.LabelFrame(self, text="Mode Selection", padding="10")
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=(10, 0))
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
        # NO pady between Mode and Input (they're grouped)
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 0))
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
        ttk.Label(self.youtube_frame, text="URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(self.youtube_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.youtube_frame.columnconfigure(1, weight=1)
    
    def _setup_device_section(self):
        """Setup device selection (reduced padding)"""
        device_frame = ttk.LabelFrame(self, text="Device", padding="10")
        # Reduced pady below input
        device_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=(5, 0))
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
    
    def _setup_output_location_section(self):
        """Setup output location selection"""
        output_loc_frame = ttk.LabelFrame(self, text="Output Location", padding="10")
        output_loc_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=(5, 0))
        output_loc_frame.columnconfigure(1, weight=1)
        
        ttk.Radiobutton(
            output_loc_frame,
            text="Original Location",
            variable=self.output_location_var,
            value="original",
            command=self._toggle_output_location
        ).grid(row=0, column=0, sticky=tk.W, padx=10)
        
        ttk.Radiobutton(
            output_loc_frame,
            text="Custom Destination",
            variable=self.output_location_var,
            value="custom",
            command=self._toggle_output_location
        ).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # Custom path selection (initially hidden)
        self.custom_path_frame = ttk.Frame(output_loc_frame)
        self.custom_path_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.custom_path_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.custom_path_frame, text="Path:").grid(row=0, column=0, sticky=tk.W, padx=10)
        self.custom_path_entry = ttk.Entry(self.custom_path_frame, textvariable=self.output_custom_path_var)
        self.custom_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.browse_output_btn = ttk.Button(
            self.custom_path_frame,
            text="Browse",
            command=self._browse_output_folder
        )
        self.browse_output_btn.grid(row=0, column=2, padx=5)
        self.custom_path_frame.grid_remove()  # Hide initially
    
    def _setup_format_selection_section(self):
        """Setup file format selection checkboxes"""
        format_frame = ttk.LabelFrame(self, text="Output Formats", padding="10")
        format_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=(5, 0))
        format_frame.columnconfigure(2, weight=1)
        
        ttk.Checkbutton(
            format_frame,
            text=".txt",
            variable=self.keep_txt_var
        ).grid(row=0, column=0, sticky=tk.W, padx=10)
        
        ttk.Checkbutton(
            format_frame,
            text=".srt",
            variable=self.keep_srt_var
        ).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Checkbutton(
            format_frame,
            text=".vtt",
            variable=self.keep_vtt_var
        ).grid(row=0, column=2, sticky=tk.W, padx=10)
        
        ttk.Checkbutton(
            format_frame,
            text=".json",
            variable=self.keep_json_var
        ).grid(row=0, column=3, sticky=tk.W, padx=10)
        
        ttk.Checkbutton(
            format_frame,
            text=".tsv",
            variable=self.keep_tsv_var
        ).grid(row=0, column=4, sticky=tk.W, padx=10)
    
    def _setup_output_section(self):
        """Setup output SRT display (expandable)"""
        output_frame = ttk.LabelFrame(self, text="Transcript (SRT)", padding="10")
        # This frame should expand with window
        output_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(5, 0))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(2, weight=1)  # Text area expands
        
        # Copy and export buttons
        button_frame = ttk.Frame(output_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        button_frame.columnconfigure(3, weight=1)
        
        self.copy_btn = ttk.Button(
            button_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_transcript
        )
        self.copy_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_txt_btn = ttk.Button(
            button_frame,
            text="💾 Export .txt",
            command=self._export_txt
        )
        self.export_txt_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_srt_btn = ttk.Button(
            button_frame,
            text="💾 Export .srt",
            command=self._export_srt
        )
        self.export_srt_btn.pack(side=tk.LEFT, padx=5)
        
        self.copy_status = ttk.Label(button_frame, text="")
        self.copy_status.pack(side=tk.LEFT, padx=10)
        
        # SRT display (PROPER RESIZING)
        text_frame = ttk.Frame(output_frame)
        text_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)  # Text widget expands
        
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
        action_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        action_frame.columnconfigure(1, weight=1)
        
        self.transcribe_btn = ttk.Button(
            action_frame,
            text="🎬 Transcribe",
            command=self._transcribe_clicked
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
    
    def _toggle_output_location(self):
        """Toggle custom output location field"""
        if self.output_location_var.get() == "custom":
            self.custom_path_frame.grid()
        else:
            self.custom_path_frame.grid_remove()
    
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
    
    def _browse_output_folder(self):
        """Browse for custom output folder"""
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_custom_path_var.set(folder)
    
    def _transcribe_clicked(self):
        """Handle transcribe button click"""
        if self.on_transcribe_clicked:
            self.on_transcribe_clicked()
    
    def _copy_transcript(self):
        """Copy transcript to clipboard"""
        if self.on_copy_clicked:
            self.on_copy_clicked()
    
    def _export_txt(self):
        """Export transcript as .txt"""
        if self.on_export_txt_clicked:
            self.on_export_txt_clicked()
    
    def _export_srt(self):
        """Export transcript as .srt"""
        if self.on_export_srt_clicked:
            self.on_export_srt_clicked()
    
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
    
    def get_output_location(self) -> str:
        """Get output location choice (original or custom)"""
        return self.output_location_var.get()
    
    def get_output_path(self) -> str:
        """Get custom output path"""
        return self.output_custom_path_var.get()
    
    def get_keep_formats(self) -> list:
        """Get list of formats to keep"""
        formats = []
        if self.keep_txt_var.get():
            formats.append('.txt')
        if self.keep_srt_var.get():
            formats.append('.srt')
        if self.keep_vtt_var.get():
            formats.append('.vtt')
        if self.keep_json_var.get():
            formats.append('.json')
        if self.keep_tsv_var.get():
            formats.append('.tsv')
        return formats
    
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
            
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()
            
            self.copy_status.configure(text="✓ Copied!")
            return True
        except Exception as e:
            self.show_error(f"Failed to copy: {str(e)}")
            return False
    
    def get_content(self) -> str:
        """Get current content (transcript)"""
        return self.get_transcript()
