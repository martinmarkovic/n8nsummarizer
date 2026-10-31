"""
VideoSubtitlerController - Phase 1
Wires VideoSubtitlerTab UI to existing transcription models.
Runs download + transcription in a single daemon thread.
"""
import threading
import shutil
import tkinter as tk
import re
from pathlib import Path
from tkinter import filedialog
from models.transcribe_model import TranscribeModel
from models.translation_model import TranslationModel
from models.transcription.youtube import get_youtube_title
from models.video_subtitler_model import VideoSubtitlerModel, TEMP_DIR, TRANSCRIBE_OUT_DIR
from utils.logger import logger
from utils.video_utils import (
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
        self.tab.translate_btn.configure(state=tk.DISABLED)
        
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
            self.tab.after(0, lambda: self.tab.translate_btn.configure(state=tk.NORMAL))
    
    @staticmethod
    def _ass_timestamp(delta) -> str:
        """Render an SRT timedelta in ASS's H:MM:SS.CC timestamp format."""
        total_centiseconds = max(0, round(delta.total_seconds() * 100))
        hours, remainder = divmod(total_centiseconds, 360000)
        minutes, remainder = divmod(remainder, 6000)
        seconds, centiseconds = divmod(remainder, 100)
        return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"

    @staticmethod
    def _ass_text(text: str) -> str:
        """Escape SRT content for an ASS dialogue line."""
        return (
            (text or "").replace("\\", "\\\\").replace("{", "\\{")
            .replace("}", "\\}").replace("\r\n", "\n")
            .replace("\r", "\n").replace("\n", "\\N")
        )

    def _probe_video_dimensions(self, ffprobe_exe: str, input_video: Path, flags: int):
        """Return input video dimensions, or a sensible HD fallback."""
        import subprocess
        try:
            result = subprocess.run(
                [
                    ffprobe_exe, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=p=0:s=x", str(input_video),
                ],
                capture_output=True, text=True, timeout=30, creationflags=flags,
            )
            if result.returncode == 0:
                width, height = (int(part) for part in result.stdout.strip().split("x", 1))
                if width > 0 and height > 0:
                    return width, height
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            logger.warning("Could not inspect video dimensions; using HD subtitle layout")
        return 1280, 720

    def _write_advanced_ass(self, srt_path: Path, style: dict, dimensions: tuple, dark_bg: bool, opacity: float) -> Path:
        """Convert the chosen SRT into an explicit, video-sized ASS script.

        SRT does not declare a layout resolution. Writing ASS ourselves avoids
        FFmpeg's build-dependent implicit conversion and makes Advanced font
        size predictable relative to the actual video height.
        """
        import srt

        width, height = dimensions
        # Font value 16 is the documented normal setting: 3% of video height.
        # The UI range remains 10..32, and ScaleX/Y are only shape adjustments.
        ui_font_size = int(style.get("font_size", 16))
        font_size = max(18, round(height * 0.03 * ui_font_size / 16))
        border_style = 4 if dark_bg else 1
        back_colour = (
            f"&H{format(int((1.0 - opacity) * 255), '02X')}000000"
            if dark_bg else "&HFF000000"
        )
        ass_path = srt_path.with_name("video_advanced.ass")
        style_line = (
            "Style: Default,Arial,{font_size},{primary},&H000000FF,{outline},{back},"
            "{bold},{italic},0,0,{scale_x},{scale_y},0,0,{border_style},{outline_size},"
            "{shadow},{alignment},20,20,{margin},1"
        ).format(
            font_size=font_size,
            primary=style.get("primary_colour", "&H00FFFFFF"),
            outline=style.get("outline_colour", "&H00000000"),
            back=back_colour,
            bold=-1 if style.get("bold") else 0,
            italic=-1 if style.get("italic") else 0,
            scale_x=int(style.get("scale_x", 100)),
            scale_y=int(style.get("scale_y", 100)),
            border_style=border_style,
            outline_size=int(style.get("outline", 1)),
            shadow=int(style.get("shadow", 0)),
            alignment=int(style.get("alignment", 2)),
            margin=int(style.get("margin_v", 20)),
        )
        try:
            subtitles = list(srt.parse(srt_path.read_text(encoding="utf-8")))
        except Exception as exc:
            raise ValueError(f"Advanced burn needs valid SRT timing: {exc}") from exc
        if not subtitles:
            raise ValueError("Advanced burn needs at least one SRT subtitle entry.")

        lines = [
            "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}",
            f"PlayResY: {height}", "ScaledBorderAndShadow: yes", "WrapStyle: 0", "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            style_line, "", "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        for subtitle in subtitles:
            lines.append(
                "Dialogue: 0,{start},{end},Default,,0,0,0,,{text}".format(
                    start=self._ass_timestamp(subtitle.start),
                    end=self._ass_timestamp(subtitle.end),
                    text=self._ass_text(subtitle.content),
                )
            )
        ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Generated Advanced ASS layout %sx%s with font size %s", width, height, font_size)
        return ass_path

    def on_burn(self):
        """Handle burn request from view."""
        # Disable burn button during processing
        self.tab.burn_btn.configure(state=tk.DISABLED)
        
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
                # Make sure the temp dir exists (the user may have deleted it)
                srt_file.parent.mkdir(parents=True, exist_ok=True)
                srt_file.write_text(ui_content, encoding="utf-8")
            except Exception as write_err:
                self.tab.after(0, lambda e=write_err: self.tab.show_error(f"Could not write subtitle file: {e}"))
                return
            
            # Resolve the input video to burn onto.
            #
            # Priority:
            #   1. Local-file mode  -> the exact file the user selected on disk
            #      (e.g. a video on their Desktop). We never touch temp_subtitler.
            #   2. URL / online mode -> the video we downloaded/processed
            #      (self.input_video_path), which lives in temp_subtitler.
            #   3. Fallback         -> scan temp_subtitler for a video.* file.
            VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}
            input_video = None

            try:
                input_mode = self.tab.get_input_mode()
            except Exception:
                input_mode = None

            if input_mode == "local":
                local_sel = self.tab.get_local_file_path()
                if local_sel and Path(local_sel).is_file():
                    input_video = Path(local_sel)
                    logger.info("Burn: using user-selected local video: %s", input_video)
                else:
                    self.tab.after(0, lambda: self.tab.show_error(
                        "No local video selected. Choose a file with the 'Local File' "
                        "browse button before burning."
                    ))
                    return
            else:
                # URL / online source — use the downloaded/processed video in temp.
                if self.input_video_path and Path(self.input_video_path).is_file():
                    input_video = Path(self.input_video_path)
                else:
                    # Fallback: scan temp folder for a video.* file (deterministic order)
                    try:
                        candidates = sorted(
                            f for f in TEMP_DIR.iterdir()
                            if f.is_file() and f.stem == "video" and f.suffix.lower() in VIDEO_EXTENSIONS
                        )
                    except FileNotFoundError:
                        candidates = []
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
            
            # Build FFmpeg command with forward slashes for Windows compatibility.
            # Also escape the drive-letter colon so the subtitles filtergraph parser
            # doesn't treat it as an option separator (e.g. C:/x -> C\:/x).
            srt_path_fixed = str(srt_file).replace("\\", "/").replace(":", "\\:")

            subtitle_filter = f"subtitles={srt_path_fixed}"

            import subprocess
            import os

            # Resolve FFmpeg / ffprobe from Settings or the process PATH.
            ffmpeg_exe = os.getenv("FFMPEG_PATH", "").strip()
            if not (ffmpeg_exe and os.path.isfile(ffmpeg_exe)):
                ffmpeg_exe = "ffmpeg"
            if ffmpeg_exe != "ffmpeg":
                probe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
                candidate = os.path.join(os.path.dirname(ffmpeg_exe), probe_name)
                ffprobe_exe = candidate if os.path.isfile(candidate) else "ffprobe"
            else:
                ffprobe_exe = "ffprobe"
            _NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            
            # Check if dark background is enabled
            use_dark_bg = self.tab.get_dark_bg()
            opacity = self.tab.get_bg_opacity()

            # Remember current selections as the new "last pick"
            self._save_burn_prefs()

            # Burn mode: "simple" (minimal, known-good command — default) or
            # "advanced" (full style panel with font/colour/scale/etc.).
            try:
                burn_mode = self.tab.get_burn_mode()
            except AttributeError:
                burn_mode = "simple"

            if burn_mode == "advanced":
                # Advanced mode writes a complete ASS script with explicit
                # PlayRes matching the source video. Unlike force_style on a
                # raw SRT, this has deterministic font/layout behaviour across
                # FFmpeg/libass builds and does not use original_size.
                try:
                    style = self.tab.get_subtitle_style()
                    dimensions = self._probe_video_dimensions(
                        ffprobe_exe, input_video, _NO_WINDOW
                    )
                    ass_path = self._write_advanced_ass(
                        srt_file, style, dimensions, use_dark_bg, opacity
                    )
                    ass_path_fixed = str(ass_path).replace("\\", "/").replace(":", "\\:")
                    vf_filter = f"subtitles={ass_path_fixed}"
                except Exception as exc:
                    logger.error("Could not prepare Advanced ASS subtitles: %s", exc)
                    self.tab.after(0, lambda e=exc: self.tab.show_error(
                        f"Advanced subtitle setup failed: {e}"
                    ))
                    return
            else:
                # --- Simple (default): the original minimal command ---
                # Lets libass use its own sensible defaults for font/size/colour.
                # The only options are the optional dark background box.
                if use_dark_bg:
                    alpha_hex = format(int((1.0 - opacity) * 255), '02X')
                    back_colour = f"&H{alpha_hex}000000"
                    force_style = (
                        f"BackColour={back_colour},BorderStyle=4,"
                        f"Outline=0,Shadow=0,MarginV=20"
                    )
                    vf_filter = f"{subtitle_filter}:force_style='{force_style}'"
                else:
                    vf_filter = subtitle_filter

            logger.info("Burn mode: %s | vf: %s", burn_mode, vf_filter)

            # -nostdin: never read stdin (a common cause of "frozen" ffmpeg when
            #           launched from a GUI process).
            # -progress pipe:1 -nostats: emit machine-readable progress on stdout
            #           (newline-delimited key=value), which is far more reliable to
            #           parse than the \r-updated stats line on stderr.
            cmd = [
                ffmpeg_exe, "-y", "-hide_banner", "-nostdin",
                "-i", str(input_video),
                "-vf", vf_filter,
                "-c:a", "copy",
                "-progress", "pipe:1", "-nostats",
                str(output_path)
            ]

            logger.info("Burning subtitles. FFmpeg command: %s", " ".join(cmd))

            self.tab.after(0, lambda: self.tab.update_ffmpeg_status("🔄 Starting FFmpeg..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "FFmpeg: Starting"))

            # First get total duration using ffprobe (for progress %)
            duration_cmd = [
                ffprobe_exe, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(input_video)
            ]

            total_duration = 0
            try:
                duration_result = subprocess.run(
                    duration_cmd, capture_output=True, text=True, timeout=30,
                    creationflags=_NO_WINDOW,
                )
                if duration_result.returncode == 0:
                    total_duration = float(duration_result.stdout.strip() or 0)
            except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as probe_err:
                logger.warning("ffprobe duration lookup failed: %s", probe_err)
                total_duration = 0

            # Launch FFmpeg. Catch a missing executable explicitly so the user gets
            # a clear message instead of a silent failure.
            try:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=_NO_WINDOW,
                )
            except FileNotFoundError:
                logger.error("FFmpeg executable not found: %s", ffmpeg_exe)
                self.tab.after(0, lambda: self.tab.show_error(
                    "FFmpeg was not found. Install FFmpeg and add it to PATH, or set its "
                    "path in Settings → Paths (FFmpeg)."
                ))
                return

            # Do not claim a font-cache build without evidence. Some FFmpeg
            # builds may initialize libass/fonts on first use, but others do
            # not; stderr below reports a cache message only if FFmpeg emits it.
            self.tab.after(0, lambda: self.tab.update_ffmpeg_status(
                "🔄 FFmpeg rendering subtitles…"
            ))

            # Drain stderr on a background thread so the pipe can never fill up and
            # deadlock ffmpeg. Keep successful libass/fontconfig diagnostics too:
            # they are required to diagnose a provider repeatedly rebuilding cache.
            stderr_chunks = []
            font_cache_reported = False

            def _drain_stderr():
                nonlocal font_cache_reported
                try:
                    for line in process.stderr:
                        stderr_chunks.append(line)
                        lowered = line.lower()
                        if "libass" in lowered or "fontconfig" in lowered:
                            logger.info("FFmpeg subtitle diagnostic: %s", line.rstrip())
                        if "cache" in lowered and not font_cache_reported:
                            font_cache_reported = True
                            self.tab.after(0, lambda: self.tab.update_ffmpeg_status(
                                "🔄 FFmpeg is preparing its font cache…"
                            ))
                except Exception:
                    pass

            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

            # Parse machine-readable progress from stdout (-progress pipe:1).
            # Lines look like:  out_time=00:00:04.050000  /  progress=continue|end
            last_pct = -1.0
            for raw in process.stdout:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("out_time=") and total_duration > 0:
                    m = re.search(r"out_time=([0-9:.]+)", line)
                    if m:
                        parts = m.group(1).split(":")
                        if len(parts) == 3:
                            try:
                                h, mm, ss = map(float, parts)
                            except ValueError:
                                continue
                            elapsed = h * 3600 + mm * 60 + ss
                            percent = max(0.0, min(100.0, (elapsed / total_duration) * 100))
                            # Throttle UI updates to whole-tenths changes
                            if percent - last_pct >= 0.1:
                                last_pct = percent
                                self.tab.after(
                                    0,
                                    lambda p=percent: self.tab.update_progress(p, f"FFmpeg: {p:.1f}%"),
                                )
                elif line == "progress=end":
                    break

            returncode = process.wait()
            stderr_thread.join(timeout=5)
            full_err = "".join(stderr_chunks)

            if returncode == 0:
                logger.info("FFmpeg burn completed successfully: %s", output_path)
                self.tab.after(0, lambda: self.tab.update_ffmpeg_status("✅ Done! Subtitles burned."))
                self.tab.after(0, lambda: self.tab.enable_open_btn())
                self.tab.after(0, lambda: self.tab.update_progress(100, "Burn complete."))
            else:
                logger.error(
                    "FFmpeg burn failed (exit %s).\nCommand: %s\nSTDERR tail:\n%s",
                    returncode, " ".join(cmd), full_err[-2000:],
                )
                error_msg = full_err[-800:].strip() or f"exit code {returncode} (no output)"
                self.tab.after(0, lambda m=error_msg: self.tab.show_error(f"FFmpeg failed: {m}"))
                self.tab.after(0, lambda: self.tab.update_ffmpeg_status("❌ FFmpeg failed."))
                
        except Exception as e:
            logger.error(f"VideoSubtitler FFmpeg error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.show_error(f"FFmpeg error: {e}"))
            
        finally:
            # Re-enable burn button
            self.tab.after(0, lambda: self.tab.burn_btn.configure(state=tk.NORMAL))
    

    
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
        "burn_mode": ("SUBTITLE_BURN_MODE", str),
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
        provider, model, url = (provider or "").strip(), (model or "").strip(), (url or "").strip()
        if not (provider and model and url):
            logger.debug(
                "Ignoring incomplete Translation LLM configuration for Video "
                "Subtitler: provider=%r, model=%r, url=%r", provider, model, url
            )
            return

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