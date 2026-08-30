"""
VideoSubtitlerController - Phase 1
Wires VideoSubtitlerTab UI to existing transcription models.
Runs download + transcription in a single daemon thread.
"""
import threading
import shutil
import yt_dlp
import tkinter as tk
import re
from pathlib import Path
from tkinter import filedialog
from models.transcribe_model import TranscribeModel
from models.translation_model import TranslationModel
from models.transcription.youtube import get_youtube_title
from models.video_subtitler_model import VideoSubtitlerModel, TEMP_DIR, TRANSCRIBE_OUT_DIR
from utils.settings_manager import SettingsManager
from utils.logger import logger
from utils.video_utils import (
    download_progress_hook,
    model_progress_callback,
    create_download_progress_wrapper,
    run_translation_sync
)


# TEMP_DIR and utility functions are now in VideoSubtitlerModel


class VideoSubtitlerController:
    def __init__(self, tab, settings_manager=None, translation_controller=None):
        self.tab = tab
        self.settings = settings_manager
        self.translation_controller = translation_controller
        self.transcribe_model = TranscribeModel()
        self.translation_model = TranslationModel()
        self.video_subtitler_model = VideoSubtitlerModel()
        self._thread = None
        self.srt_path = None
        self.translated_srt_path = None
        self.output_video_path = None
        self.input_video_path = None  # Exact video just processed/downloaded (source of truth for burn)
        self._output_dir = None
        self._original_video_title = None
        
        # LLM configuration for translation (inherited from Translation tab)
        self._translation_provider = None
        self._translation_model_name = None
        self._translation_webhook_url = None
        
        # Load saved output directory
        if self.settings:
            saved_dir = self.settings.get("SUBTITLER_OUTPUT_DIR", "")
            if saved_dir:
                self._output_dir = Path(saved_dir)
                tab.output_dir_var.set(saved_dir)

        tab.set_controller(self)

        # Restore last-used subtitle style/burn preferences from settings
        self._load_burn_prefs()
        
        # Create callback for video utils (instance method to avoid scope issues)
        self.tab_progress_callback = lambda percent, message: self.tab.after(0, lambda p=percent, m=message: self.tab.update_progress(p, m))
        
        # Create callback dictionary for translation sync (instance method to avoid scope issues)
        def create_translation_callbacks(self):
            """Create callbacks dictionary for run_translation_sync"""
            return {
                'after': lambda delay, func: self.tab.after(delay, func),
                'display_translated_srt': lambda translated: self.tab.display_translated_srt(translated),
                'update_status': lambda status: self.tab.update_status(status),
                'enable_burn_btn': lambda: self.tab.enable_burn_btn()
            }
        self.create_translation_callbacks = create_translation_callbacks.__get__(self, self.__class__)
        
        logger.info("VideoSubtitlerController initialized")

    def _refresh_translation_llm_config(self):
        """Refresh translation LLM config from TranslationController.
        
        Fetches current settings from TranslationController and applies them
        to ensure Video Subtitler uses the same config as Translation tab.
        """
        if self.translation_controller:
            provider, model, url = self.translation_controller.get_current_llm_config()
            self.set_translation_llm_config(provider, model, url)
            logger.info(f"Refreshed translation config from TranslationController: {provider}/{model} @ {url}")
        else:
            logger.warning("No TranslationController attached; using cached/fallback translation config")

    def on_start(self):
        if self._thread and self._thread.is_alive():
            self.tab.show_error("Already running. Please wait.")
            return
        
        # Check output directory
        output_dir = self.settings.get("SUBTITLER_OUTPUT_DIR", "") if self.settings else ""
        if not output_dir or not Path(output_dir).is_dir():
            chosen = filedialog.askdirectory(title="Select output folder for subtitled video")
            if not chosen:
                return  # User cancelled — abort everything
            if self.settings:
                self.settings.set("SUBTITLER_OUTPUT_DIR", chosen)
            output_dir = chosen
        self._output_dir = Path(output_dir)
        
        input_mode = self.tab.get_input_mode()
        
        if input_mode == "url":
            url = self.tab.get_url()
            if not url:
                self.tab.show_error("Please enter a video URL.")
                return
            self.tab.set_busy(True)
            self._thread = threading.Thread(
                target=self._run_url, args=(url,), daemon=True
            )
        else:
            file_path = self.tab.get_local_file_path()
            if not file_path:
                self.tab.show_error("Please select a local video file.")
                return
            self.tab.set_busy(True)
            self._thread = threading.Thread(
                target=self._run_local, args=(file_path,), daemon=True
            )
        
        self._thread.start()
    
    def _run_auto_url(self, url):
        """Run complete pipeline for URL input: Download → Transcribe → Translate → Burn."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("⬇ Downloading video..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Downloading..."))
            
            # Extract video title first
            self._original_video_title = get_youtube_title(url) or 'video'
            
            # Use model to handle download and processing with correct callback
            download_progress_wrapper = create_download_progress_wrapper(
                lambda p, s, e: model_progress_callback(p, s, e, tab_callback=self.tab_progress_callback)
            )
            video_path = self.video_subtitler_model.download_and_process_video(url, download_progress_wrapper)
            
            self.tab.after(0, lambda: self.tab.update_progress(100, "Download complete."))

            # Run transcription
            self._run_transcription(str(video_path))

            # Refresh LLM config from TranslationController if available
            if self.translation_controller:
                self._refresh_translation_llm_config()

            # Set up LLM configuration for translation
            provider = self._translation_provider or "lmstudio"
            model = self._translation_model_name or "local-model"
            url = self._translation_webhook_url or "http://127.0.0.1:1234/v1/completions"
            if self._translation_provider:
                logger.info(f"Auto pipeline: using inherited LLM: {provider}/{model}")
            else:
                logger.warning("Auto pipeline: using default LLM config - no inherited settings")
            self.translation_model.set_current_file_path(str(self.srt_path))
            self.translation_model.set_llm_settings(provider, url, model)

            # Run translation
            ok = run_translation_sync(
                self.translation_model, 
                self.srt_path, 
                self.tab.get_target_language(),
                self.create_translation_callbacks()
            )
            if ok:
                self._run_ffmpeg()
            
        except Exception as e:
            logger.error(f"VideoSubtitler Auto URL error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))
    
    def _run_auto_local(self, file_path):
        """Run complete pipeline for local file: Copy → Transcribe → Translate → Burn."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("📁 Processing local file..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Processing..."))
            
            # Use model to handle local file processing
            source_path = Path(file_path)
            video_path = self.video_subtitler_model.process_local_video_file(
                source_path, 
                lambda p, s=0, e=0, m=None: model_progress_callback(p, s, e, m, tab_callback=self.tab_progress_callback)
            )
            
            # Run transcription
            self._run_transcription(str(video_path))

            # Refresh LLM config from TranslationController if available
            if self.translation_controller:
                self._refresh_translation_llm_config()

            # Set up LLM configuration for translation
            provider = self._translation_provider or "lmstudio"
            model = self._translation_model_name or "local-model"
            url = self._translation_webhook_url or "http://127.0.0.1:1234/v1/completions"
            if self._translation_provider:
                logger.info(f"Auto pipeline: using inherited LLM: {provider}/{model}")
            else:
                logger.warning("Auto pipeline: using default LLM config - no inherited settings")
            self.translation_model.set_current_file_path(str(self.srt_path))
            self.translation_model.set_llm_settings(provider, url, model)
            
            # Run translation
            ok = run_translation_sync(
                self.translation_model, 
                self.srt_path, 
                self.tab.get_target_language(),
                self.create_translation_callbacks()
            )
            if ok:
                self._run_ffmpeg()
            
        except Exception as e:
            logger.error(f"VideoSubtitler Auto Local error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))

    def _run_url(self, url):
        """Process URL-based video using VideoSubtitlerModel."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("⬇ Downloading video..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Downloading..."))
            
             # Use model to handle download and processing with correct callback
            download_progress_wrapper = create_download_progress_wrapper(
                lambda p, s, e: model_progress_callback(p, s, e, tab_callback=self.tab_progress_callback)
            )
            video_path = self.video_subtitler_model.download_and_process_video(url, download_progress_wrapper)
            
            self.tab.after(0, lambda: self.tab.update_progress(100, "Download complete."))
            
            # Run transcription (video file remains in temp directory for other steps)
            self._run_transcription(str(video_path))
            
        except Exception as e:
            logger.error(f"VideoSubtitler URL error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))



    def _run_local(self, file_path):
        """Process local video file using VideoSubtitlerModel."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("📁 Processing local file..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Processing..."))
            
            # Use model to handle local file processing
            source_path = Path(file_path)
            video_path = self.video_subtitler_model.process_local_video_file(
                source_path, 
                lambda p, s=0, e=0, m=None: model_progress_callback(p, s, e, m, tab_callback=self.tab_progress_callback)
            )
            
            # Run transcription (video file remains in temp directory for other steps)
            self._run_transcription(str(video_path))
            
        except Exception as e:
            logger.error(f"VideoSubtitler Local File error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))

    def _run_transcription(self, video_path):
        """Run transcription on prepared video file."""
        try:
            # Remember the exact video we're working on so the burn step uses THIS
            # file, not whatever happens to match "video.*" in the temp folder.
            self.input_video_path = Path(video_path)

            self.tab.after(0, lambda: self.tab.update_status("🎙 Transcribing..."))

            # Ensure output directory exists and is clean
            TRANSCRIBE_OUT_DIR.mkdir(parents=True, exist_ok=True)
            for f in TRANSCRIBE_OUT_DIR.iterdir():
                if f.is_file():
                    f.unlink()

            # Call transcribe_file with separate output directory
            success, srt_content, error_msg, metadata = self.transcribe_model.transcribe_file(
                file_path=video_path,
                device="cuda",
                output_dir=str(TRANSCRIBE_OUT_DIR),
                keep_formats=[".srt"]
            )
            
            if not success:
                raise Exception(error_msg)
            
            # Copy SRT file from output directory to main temp directory
            srt_source = TRANSCRIBE_OUT_DIR / "video.srt"
            if srt_source.exists():
                shutil.copy2(srt_source, TEMP_DIR / "video.srt")
            
            # Store SRT path for Phase 2 use
            self.srt_path = TEMP_DIR / "video.srt"
            
            # Display SRT content
            self.tab.after(0, lambda t=srt_content: self.tab.display_srt(t))
            self.tab.after(0, lambda: self.tab.enable_translate_btn())  # Enable translation
            self.tab.after(0, lambda: self.tab.update_progress(100, "Done."))
            self.tab.after(0, lambda: self.tab.update_status(
                f"✅ Done. SRT saved to: {self.srt_path}"
            ))
            
        except Exception as e:
            logger.error(f"VideoSubtitler Transcription error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            raise
    
    def on_translate(self):
        """Handle translation request from view."""
        # Disable translate button during translation
        self.tab.translate_btn.config(state=tk.DISABLED)
        
        # Run translation in background thread
        translation_thread = threading.Thread(target=self._run_translation, daemon=True)
        translation_thread.start()
    
    def _run_translation(self):
        """Run translation in background thread."""
        try:
            # Get target language and SRT content
            lang = self.tab.get_target_language()
            srt_text = self.srt_path.read_text(encoding="utf-8")
            
            # Set file path so TranslationModel detects SRT mode
            self.translation_model.set_current_file_path(str(self.srt_path))
            
            # Refresh LLM config from TranslationController if available
            if self.translation_controller:
                self._refresh_translation_llm_config()

            # Use stored LLM config if available, otherwise fall back to defaults
            provider = self._translation_provider or "lmstudio"
            model = self._translation_model_name or "local-model"
            url = self._translation_webhook_url or "http://127.0.0.1:1234/v1/completions"
            
            # Log what we're using
            if self._translation_provider:
                logger.info(f"Using inherited LLM config for translation: provider={provider}, model={model}")
            else:
                logger.warning("Using default LLM config - check if real values were passed from controller")
            
            # Set LLM settings on translation model
            self.translation_model.set_llm_settings(provider, url, model)
            
            # Translate the SRT
            success, translated, error = self.translation_model.translate_srt(srt_text, lang)
            
            if success:
                # Display translated SRT and save to file
                self.tab.after(0, lambda t=translated: self.tab.display_translated_srt(t))
                
                # Save translated SRT file
                self.translated_srt_path = TEMP_DIR / "video_translated.srt"
                self.translated_srt_path.write_text(translated, encoding="utf-8")
                
                self.tab.after(0, lambda: self.tab.update_status(
                    f"✅ Translation complete. Saved to: {self.translated_srt_path}"
                ))
                self.tab.after(0, lambda: self.tab.enable_burn_btn())  # Enable burn button
            else:
                self.tab.after(0, lambda e=error: self.tab.show_error(f"Translation failed: {e}"))
                
        except Exception as e:
            logger.error(f"VideoSubtitler Translation error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.show_error(f"Translation error: {e}"))
            
        finally:
            # Re-enable translate button
            self.tab.after(0, lambda: self.tab.translate_btn.config(state=tk.NORMAL))
    
    def on_burn(self):
        """Handle burn request from view."""
        # Disable burn button during processing
        self.tab.burn_btn.config(state=tk.DISABLED)
        
        # Run FFmpeg in background thread
        ffmpeg_thread = threading.Thread(target=self._run_ffmpeg, daemon=True)
        ffmpeg_thread.start()
    
    def _run_ffmpeg(self):
        """Run FFmpeg subtitle burning in background thread."""
        try:
            # Determine subtitle file
            source = self.tab.get_subtitle_source()
            srt_file = TEMP_DIR / ("video_translated.srt" if source == "translated" else "video.srt")
            
            # Always use the UI field as source of truth — write it to disk before burning.
            # This ensures manual edits or pastes override whatever the backend last wrote.
            if source == "translated":
                ui_content = self.tab.get_translated_srt()
            else:
                ui_content = self.tab.get_content().strip()

            if not ui_content:
                self.tab.after(0, lambda: self.tab.show_error("No subtitle content found. Please paste or generate subtitles first."))
                return

            try:
                srt_file.write_text(ui_content, encoding="utf-8")
            except Exception as write_err:
                self.tab.after(0, lambda e=write_err: self.tab.show_error(f"Could not write subtitle file: {e}"))
                return
            
            # Resolve the input video. Prefer the exact file we just processed/downloaded
            # so we never burn onto a stale leftover from a previous session.
            VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}
            input_video = None
            if self.input_video_path and Path(self.input_video_path).is_file():
                input_video = Path(self.input_video_path)
            else:
                # Fallback: scan temp folder for a video.* file (deterministic order)
                candidates = sorted(
                    f for f in TEMP_DIR.iterdir()
                    if f.is_file() and f.stem == "video" and f.suffix.lower() in VIDEO_EXTENSIONS
                )
                input_video = candidates[0] if candidates else None

            if not input_video:
                self.tab.after(0, lambda: self.tab.show_error(
                    "No video file found. Please process or download a video before burning."
                ))
                return
            
            # Set output path
            use_original_name = self.tab.get_use_original_name()
            title = self._original_video_title or 'video_output'
            if use_original_name:
                output_filename = f"{title}_subtitled.mp4"
            else:
                output_filename = "video_subtitled.mp4"
            output_path = self._output_dir / output_filename
            self.output_video_path = output_path
            
            # Build FFmpeg command with forward slashes for Windows compatibility
            srt_path_fixed = str(srt_file).replace("\\", "/")
            
            # Check if dark background is enabled
            use_dark_bg = self.tab.get_dark_bg()
            opacity = self.tab.get_bg_opacity()

            # Gather user-selected subtitle style options (with safe fallbacks)
            try:
                style = self.tab.get_subtitle_style()
            except AttributeError:
                style = {}

            # Remember these selections as the new "last pick"
            self._save_burn_prefs()

            style_parts = [
                f"FontSize={style.get('font_size', 24)}",
                f"PrimaryColour={style.get('primary_colour', '&H00FFFFFF')}",
                f"OutlineColour={style.get('outline_colour', '&H00000000')}",
                f"Bold={-1 if style.get('bold') else 0}",
                f"Italic={-1 if style.get('italic') else 0}",
                f"Alignment={style.get('alignment', 2)}",
                f"MarginV={style.get('margin_v', 20)}",
                f"ScaleX={style.get('scale_x', 100)}",
                f"ScaleY={style.get('scale_y', 100)}",
                f"Shadow={style.get('shadow', 0)}",
            ]

            if use_dark_bg:
                # Opaque box behind text. BackColour is &HAABBGGRR — AA is alpha
                # (00 = fully opaque, FF = fully transparent).
                alpha_hex = format(int((1.0 - opacity) * 255), '02X')
                back_colour = f"&H{alpha_hex}000000"
                style_parts.append(f"BackColour={back_colour}")
                style_parts.append("BorderStyle=4")  # opaque box
                # For box style, Outline controls box padding
                style_parts.append(f"Outline={style.get('outline', 2)}")
            else:
                style_parts.append("BorderStyle=1")  # outline + shadow
                style_parts.append(f"Outline={style.get('outline', 2)}")

            force_style = ",".join(style_parts)
            vf_filter = f"subtitles={srt_path_fixed}:force_style='{force_style}'"
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_video),
                "-vf", vf_filter,
                "-c:a", "copy",
                str(output_path)
            ]
            
            self.tab.after(0, lambda: self.tab.update_ffmpeg_status("🔄 Starting FFmpeg..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "FFmpeg: Starting"))
            
            # Run FFmpeg with progress parsing
            import subprocess
            
            # First get total duration using ffprobe
            duration_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(input_video)
            ]
            
            try:
                duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
                total_duration = float(duration_result.stdout.strip()) if duration_result.returncode == 0 else 0
            except (subprocess.TimeoutExpired, ValueError):
                total_duration = 0
            
            # Run FFmpeg and parse progress
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                # Parse time progress from FFmpeg output
                if "time=" in line:
                    time_match = re.search(r"time=([0-9:.]+)", line)
                    if time_match:
                        time_str = time_match.group(1)
                        # Convert HH:MM:SS.ms to seconds
                        time_parts = time_str.split(":")
                        if len(time_parts) == 3:
                            hours, minutes, seconds = map(float, time_parts)
                            elapsed_seconds = hours * 3600 + minutes * 60 + seconds
                            
                            if total_duration > 0:
                                percent = (elapsed_seconds / total_duration) * 100
                                self.tab.after(0, lambda p=percent: self.tab.update_progress(p, f"FFmpeg: {p:.1f}%"))
            
            returncode = process.wait()
            
            if returncode == 0:
                self.tab.after(0, lambda: self.tab.update_ffmpeg_status("✅ Done! Subtitles burned."))
                self.tab.after(0, lambda: self.tab.enable_open_btn())
                self.tab.after(0, lambda: self.tab.update_progress(100, "Burn complete."))
            else:
                # Get last 500 chars of stderr for error message
                stderr_output = process.stderr.read() if process.stderr else ""
                error_msg = stderr_output[-500:] if len(stderr_output) > 500 else stderr_output
                self.tab.after(0, lambda: self.tab.show_error(f"FFmpeg failed: {error_msg}"))
                
        except Exception as e:
            logger.error(f"VideoSubtitler FFmpeg error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.show_error(f"FFmpeg error: {e}"))
            
        finally:
            # Re-enable burn button
            self.tab.after(0, lambda: self.tab.burn_btn.config(state=tk.NORMAL))
    

    
    def set_output_dir(self, path: str):
        """Set output directory and save to settings."""
        if self.settings:
            self.settings.set("SUBTITLER_OUTPUT_DIR", path)
        self._output_dir = Path(path)

    # --- Subtitle style / burn preferences persistence (.env via SettingsManager) ---
    _BURN_PREF_KEYS = {
        # pref_key: (env_key, type)
        "font_size": ("SUBTITLE_FONT_SIZE", int),
        "bold": ("SUBTITLE_BOLD", bool),
        "italic": ("SUBTITLE_ITALIC", bool),
        "text_color": ("SUBTITLE_TEXT_COLOR", str),
        "outline_color": ("SUBTITLE_OUTLINE_COLOR", str),
        "outline_width": ("SUBTITLE_OUTLINE_WIDTH", int),
        "shadow": ("SUBTITLE_SHADOW", int),
        "v_align": ("SUBTITLE_V_ALIGN", str),
        "h_align": ("SUBTITLE_H_ALIGN", str),
        "margin_v": ("SUBTITLE_MARGIN_V", int),
        "scale_x": ("SUBTITLE_SCALE_X", int),
        "scale_y": ("SUBTITLE_SCALE_Y", int),
        "dark_bg": ("SUBTITLE_DARK_BG", bool),
        "bg_opacity": ("SUBTITLE_BG_OPACITY", float),
    }

    def _load_burn_prefs(self):
        """Load saved subtitle style prefs from settings and apply to the tab."""
        if not self.settings:
            return
        prefs = {}
        for pref_key, (env_key, typ) in self._BURN_PREF_KEYS.items():
            raw = self.settings.get(env_key, "")
            if raw == "":
                continue  # Not saved yet — keep the in-code default
            try:
                if typ is bool:
                    prefs[pref_key] = str(raw).strip().lower() in ("1", "true", "yes")
                elif typ is int:
                    prefs[pref_key] = int(float(raw))
                elif typ is float:
                    prefs[pref_key] = float(raw)
                else:
                    prefs[pref_key] = str(raw)
            except (ValueError, TypeError):
                continue
        if prefs:
            try:
                self.tab.apply_burn_prefs(prefs)
            except Exception as e:
                logger.debug(f"Could not apply saved burn prefs: {e}")

    def _save_burn_prefs(self):
        """Persist the current subtitle style prefs to settings (.env)."""
        if not self.settings:
            return
        try:
            prefs = self.tab.get_burn_prefs()
        except Exception:
            return
        for pref_key, (env_key, typ) in self._BURN_PREF_KEYS.items():
            if pref_key not in prefs:
                continue
            value = prefs[pref_key]
            if typ is bool:
                value = "1" if value else "0"
            self.settings.set(env_key, str(value))

    def set_translation_llm_config(self, provider, model, url):
        """Set LLM configuration for translation from Translation tab.
        
        Args:
            provider: LLM provider (e.g., 'lmstudio', 'ollama-local')
            model: Model name to use
            url: Base URL for the LLM provider
        """
        self._translation_provider = provider
        self._translation_model_name = model
        self._translation_webhook_url = url
        logger.info(f"VideoSubtitlerController: Set translation LLM config - provider={provider}, model={model}, url={url}")
        
        # Update UI label to show current LLM config
        if hasattr(self.tab, 'update_translation_llm_label'):
            self.tab.update_translation_llm_label(provider, model)
    
    def on_auto(self):
        """Handle auto pipeline request."""
        if self._thread and self._thread.is_alive():
            self.tab.show_error("Already running. Please wait.")
            return
        
        # Check output directory
        output_dir = self.settings.get("SUBTITLER_OUTPUT_DIR", "") if self.settings else ""
        if not output_dir or not Path(output_dir).is_dir():
            chosen = filedialog.askdirectory(title="Select output folder")
            if not chosen:
                return
            if self.settings:
                self.settings.set("SUBTITLER_OUTPUT_DIR", chosen)
            self._output_dir = Path(chosen)
        
        input_mode = self.tab.get_input_mode()
        if input_mode == "url":
            url = self.tab.get_url()
            if not url:
                self.tab.show_error("Please enter a video URL.")
                return
            self.tab.set_busy(True)
            self._thread = threading.Thread(
                target=self._run_auto_url, args=(url,), daemon=True
            )
        else:
            file_path = self.tab.get_local_file_path()
            if not file_path:
                self.tab.show_error("Please select a local video file.")
                return
            self.tab.set_busy(True)
            self._thread = threading.Thread(
                target=self._run_auto_local, args=(file_path,), daemon=True
            )
        self._thread.start()