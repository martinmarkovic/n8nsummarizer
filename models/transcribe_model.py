"""
Transcribe Model v2.7 - Business logic for transcribe-anything wrapper

Responsibilities:
    - Call transcribe-anything CLI for local files and YouTube URLs
    - Extract YouTube video titles for output naming
    - Manage output files (SRT, TXT, etc.)
    - Handle user-selected file formats
    - Delete unwanted formats
    - Handle device selection (CPU, CUDA, Insane, MPS)
    - Return SRT transcript for processing
    - Cleanup temporary files
    - Load ANY available format if preferred not available
    - Handle Unicode filenames (Japanese, Korean, etc.)
    - Sanitize output filenames for Windows filesystem

Reusable by:
    - TranscriberTab (primary)
    - FileTab (secondary - transcribe files first)
    - Future tabs (bulk transcriber, translation, etc.)

Version: 2.7
Updated: 2026-01-06
Fixed: Output file path handling and error logging
"""
import subprocess
import tempfile
import shutil
import re
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from utils.logger import logger


class TranscribeModel:
    """
    Handles transcription using transcribe-anything CLI tool.
    
    Supports:
    - Local media files (mp4, avi, mkv, mp3, wav, etc.)
    - YouTube videos and playlists
    - Multiple device types (CPU, CUDA, Insane Mode, MPS)
    - User-selected output formats
    - Unicode filenames (Japanese, Korean, Chinese, Cyrillic, etc.)
    - Automatic filename sanitization for Windows filesystem
    
    Output handling:
    - Generates multiple formats (.txt, .srt, .vtt, .json, .tsv)
    - Keeps only user-selected formats
    - Deletes unwanted formats automatically
    - Loads ANY available format for display (fallback strategy)
    - Returns transcript content for processing
    - Cleans up temporary files
    - Sanitizes output filenames to work on all filesystems
    """
    
    def __init__(self, transcribe_path: str = None):
        """
        Initialize TranscribeModel.
        
        Args:
            transcribe_path: Path to transcribe-anything directory
                           If None, assumes 'transcribe-anything' in PATH
        """
        self.transcribe_path = transcribe_path or "F:\\Python scripts\\Transcribe anything"
        self.supported_formats = {
            # Video
            '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv', '.webm', '.mpg', '.mpeg',
            '.m4v', '.3gp', '.ogv', '.ts', '.vob', '.asf', '.rm', '.rmvb', '.divx',
            '.xvid', '.f4v',
            # Audio
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.au'
        }
        logger.info("TranscribeModel initialized (transcribe-anything wrapper v2.7 - Unicode + filename sanitization)")
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for Windows filesystem.
        
        Removes/replaces problematic characters:
        - < > : " / \\ | ? *  (Windows reserved)
        - Trims excessive whitespace
        - Handles Unicode by converting problematic chars to underscore
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        # Replace Windows-forbidden characters
        forbidden = r'[<>:"/\|?*]'
        sanitized = re.sub(forbidden, '_', filename)
        
        # Replace multiple underscores with single
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove trailing dots and spaces (Windows doesn't allow)
        sanitized = sanitized.rstrip('. ')
        
        # Limit length to 200 chars (safe for most filesystems)
        if len(sanitized) > 200:
            # Keep extension, trim middle
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            name = name[:190]
            sanitized = f"{name}.{ext}" if ext else name
        
        return sanitized
    
    def transcribe_file(
        self,
        file_path: str,
        device: str = "cuda",
        output_dir: Optional[str] = None,
        keep_formats: List[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict]]:
        """
        Transcribe a local media file.
        
        Args:
            file_path: Path to local media file (supports Unicode filenames)
            device: "cpu", "cuda", "insane", or "mps"
            output_dir: Where to save transcripts (None = same as input file)
            keep_formats: File formats to keep ['.txt', '.srt']
                         Other formats deleted after transcription
        
        Returns:
            Tuple: (success, srt_content, error_msg, metadata_dict)
            - success: bool
            - srt_content: str (transcript content) or None
            - error_msg: str or None
            - metadata: dict with info like file_name, base_name, etc.
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return False, None, f"File not found: {file_path}", None
            
            if file_path.suffix.lower() not in self.supported_formats:
                return False, None, f"Unsupported format: {file_path.suffix}", None
            
            if keep_formats is None:
                keep_formats = ['.txt', '.srt']
            
            if output_dir is None:
                output_dir = file_path.parent
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # v2.7: Sanitize base_name for filesystem compatibility
            base_name = self._sanitize_filename(file_path.stem)
            logger.info(f"Original filename: {file_path.stem}")
            logger.info(f"Sanitized filename: {base_name}")
            
            # Use temp directory for transcription
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Run transcribe-anything
                success, error = self._run_transcribe(
                    input_path=str(file_path),
                    output_dir=str(temp_path),
                    device=device
                )
                
                if not success:
                    return False, None, error, None
                
                # Move and manage output files
                transcript_content, metadata = self._process_outputs(
                    temp_path=temp_path,
                    output_dir=output_dir,
                    base_name=base_name,
                    keep_formats=keep_formats,
                    source_type="file"
                )
                
                if transcript_content is None:
                    return False, None, "No transcript generated", None
                
                logger.info(f"Successfully transcribed: {file_path.name}")
                return True, transcript_content, None, metadata
        
        except Exception as e:
            error = f"Error transcribing file: {str(e)}"
            logger.error(error, exc_info=True)
            return False, None, error, None
    
    def transcribe_youtube(
        self,
        youtube_url: str,
        device: str = "cuda",
        output_dir: Optional[str] = None,
        keep_formats: List[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict]]:
        """
        Transcribe a YouTube video.
        
        Args:
            youtube_url: YouTube video URL (youtube.com or youtu.be)
            device: "cpu", "cuda", "insane", or "mps"
            output_dir: Where to save transcripts
                       If None, uses ~/Documents/Transcribe Anything
            keep_formats: File formats to keep ['.txt', '.srt']
        
        Returns:
            Tuple: (success, srt_content, error_msg, metadata_dict)
        """
        try:
            if not self.validate_youtube_url(youtube_url):
                return False, None, "Invalid YouTube URL", None
            
            if keep_formats is None:
                keep_formats = ['.txt', '.srt']
            
            if output_dir is None:
                output_dir = Path.home() / "Documents" / "Transcribe Anything"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Try to get video title for naming
            base_name = self._get_youtube_title(youtube_url)
            if not base_name:
                # Fallback to video ID
                video_id = self._extract_youtube_id(youtube_url)
                base_name = video_id if video_id else "youtube_video"
            
            # v2.7: Sanitize base_name
            base_name = self._sanitize_filename(base_name)
            
            logger.info(f"Transcribing YouTube video: {base_name}")
            
            # Use temp directory for transcription
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Run transcribe-anything
                success, error = self._run_transcribe(
                    input_path=youtube_url,
                    output_dir=str(temp_path),
                    device=device
                )
                
                if not success:
                    return False, None, error, None
                
                # Move and manage output files
                transcript_content, metadata = self._process_outputs(
                    temp_path=temp_path,
                    output_dir=output_dir,
                    base_name=base_name,
                    keep_formats=keep_formats,
                    source_type="youtube",
                    url=youtube_url
                )
                
                if transcript_content is None:
                    return False, None, "No transcript generated", None
                
                logger.info(f"Successfully transcribed YouTube video: {base_name}")
                return True, transcript_content, None, metadata
        
        except Exception as e:
            error = f"Error transcribing YouTube: {str(e)}"
            logger.error(error, exc_info=True)
            return False, None, error, None
    
    def _run_transcribe(
        self,
        input_path: str,
        output_dir: str,
        device: str = "cuda"
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute transcribe-anything CLI command.
        
        v2.6: Handle Unicode filenames by:
        - Using UTF-8 encoding environment variable
        - Passing arguments as list (not shell string)
        - Setting proper encoding for subprocess
        
        v2.7: Better error message logging
        
        Returns:
            Tuple: (success, error_msg)
        """
        try:
            # Build command as list (safer for Unicode handling)
            cmd = [
                'transcribe-anything',
                input_path,
                '--device', device,
                '--output_dir', output_dir
            ]
            
            logger.info(f"Running: {' '.join(cmd[:2])} ... --device {device}")
            logger.debug(f"Full command: {' '.join(cmd)}")
            
            # Set up environment to handle Unicode
            env = os.environ.copy()
            # Force UTF-8 encoding for subprocess
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
            
            # Execute command with proper encoding
            # Use shell=False when passing list (more secure, handles Unicode better)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes
                env=env,
                encoding='utf-8',  # Explicitly set UTF-8 encoding
                errors='replace'   # Replace encoding errors instead of failing
            )
            
            if result.returncode != 0:
                # Extract meaningful error from stderr/stdout
                error_output = result.stderr or result.stdout
                
                # v2.6: Handle Unicode encoding errors gracefully
                if 'UnicodeEncodeError' in error_output or 'charmap' in error_output:
                    error = f"Unicode filename error: filename contains characters not supported by system encoding. Try renaming file to ASCII characters only."
                    logger.error(f"Transcription failed with Unicode error for: {input_path}")
                    logger.error(f"Details: {error_output[:200]}")
                    return False, error
                
                # v2.7: Log full error for debugging
                logger.error(f"Transcription process returned non-zero exit code: {result.returncode}")
                logger.error(f"STDERR: {error_output[:500]}")
                logger.error(f"STDOUT: {result.stdout[:500] if result.stdout else '(empty)'}")
                
                # Truncate for user display (just show first meaningful part)
                display_error = error_output.split('\n')[0] if error_output else "Unknown error"
                error = f"Transcription failed: {display_error}"
                return False, error
            
            logger.debug(f"Transcription succeeded, stdout: {result.stdout[:100]}")
            return True, None
        
        except subprocess.TimeoutExpired:
            error = "Transcription timeout (30 minutes exceeded)"
            logger.error(error)
            return False, error
        except Exception as e:
            error = f"Error running transcribe-anything: {str(e)}"
            logger.error(error, exc_info=True)
            return False, error
    
    def _process_outputs(
        self,
        temp_path: Path,
        output_dir: Path,
        base_name: str,
        keep_formats: List[str],
        source_type: str = "file",
        url: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Process transcription output files.
        
        - Moves kept formats to output_dir
        - Deletes unwanted formats
        - Returns transcript content (loads ANY available format)
        - Generates metadata
        - v2.7: Better error handling for file operations
        
        Returns:
            Tuple: (transcript_content_str, metadata_dict)
        """
        try:
            transcript_content = None
            files_created = []
            format_loaded = None
            metadata = {
                'base_name': base_name,
                'source_type': source_type,
                'url': url,
                'output_dir': str(output_dir),
                'files_kept': [],
                'files_deleted': [],
                'format_loaded': None
            }
            
            # Expected output files from transcribe-anything
            output_extensions = ['.txt', '.srt', '.vtt', '.json', '.tsv']
            
            # Priority order for loading transcript (if preferred format not available)
            load_priority = ['.srt', '.txt', '.vtt', '.json', '.tsv']
            
            logger.info(f"Processing outputs from temp dir: {temp_path}")
            logger.info(f"Files found in temp dir: {list(temp_path.glob('*'))}")
            
            # Find and process output files
            for temp_file in temp_path.iterdir():
                if not temp_file.is_file():
                    continue
                
                logger.debug(f"Found temp file: {temp_file.name}")
                
                # Check if it's an output file
                if not (temp_file.name.startswith('out.') or temp_file.suffix in output_extensions):
                    logger.debug(f"Skipping non-output file: {temp_file.name}")
                    continue
                
                # Determine final filename
                if temp_file.name.startswith('out.'):
                    new_name = temp_file.name.replace('out.', f'{base_name}.')
                else:
                    new_name = f"{base_name}{temp_file.suffix}"
                
                final_path = output_dir / new_name
                ext = temp_file.suffix.lower()
                
                logger.debug(f"Processing {temp_file.name} -> {new_name} (keep={ext in keep_formats})")
                
                # Check if we should keep this format
                if ext in keep_formats:
                    try:
                        # v2.7: Better error handling for file copy
                        logger.info(f"Copying to output: {final_path}")
                        shutil.copy2(temp_file, final_path)
                        files_created.append(new_name)
                        metadata['files_kept'].append(new_name)
                        
                        # Try to load content (use priority order)
                        if transcript_content is None or ext in load_priority[: load_priority.index(ext) + 1]:
                            with open(final_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip():
                                    transcript_content = content
                                    format_loaded = ext
                                    logger.info(f"Loaded transcript from: {ext} ({len(content)} chars)")
                        
                        logger.info(f"Created: {new_name}")
                    except Exception as e:
                        logger.error(f"Failed to copy {temp_file.name} to {final_path}: {str(e)}", exc_info=True)
                        # v2.7: Don't fail completely - try to load from temp anyway
                        try:
                            with open(temp_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip() and transcript_content is None:
                                    transcript_content = content
                                    format_loaded = ext
                                    logger.warning(f"Loaded transcript from temp location instead (copy failed): {ext}")
                        except Exception as e2:
                            logger.error(f"Also failed to load from temp: {str(e2)}")
                else:
                    # Delete unwanted format
                    try:
                        temp_file.unlink()
                        metadata['files_deleted'].append(new_name)
                        logger.info(f"Deleted unwanted format: {new_name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {temp_file.name}: {str(e)}")
            
            # If no transcript loaded from kept formats, try to load ANY available format
            if transcript_content is None:
                logger.info("No transcript in kept formats, trying fallback...")
                for temp_file in temp_path.iterdir():
                    if not temp_file.is_file():
                        continue
                    ext = temp_file.suffix.lower()
                    if ext in output_extensions:
                        try:
                            logger.info(f"Trying fallback format: {ext}")
                            with open(temp_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip():
                                    transcript_content = content
                                    format_loaded = ext
                                    logger.info(f"Loaded transcript from fallback format: {ext} ({len(content)} chars)")
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to load {temp_file}: {str(e)}")
            
            metadata['format_loaded'] = format_loaded
            
            logger.info(f"Output processing complete: {len(files_created)} files created, loaded from {format_loaded}")
            return transcript_content, metadata
        
        except Exception as e:
            logger.error(f"Error processing outputs: {str(e)}", exc_info=True)
            return None, None
    
    def _get_youtube_title(self, url: str) -> Optional[str]:
        """
        Fetch YouTube video title for output naming.
        
        Returns:
            Sanitized title or None
        """
        try:
            # Try yt-dlp first
            try:
                from yt_dlp import YoutubeDL
                ydl_opts = {'quiet': True, 'no_warnings': True}
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title')
                    if title:
                        # Sanitize for filesystem
                        title = re.sub(r'[\\/*?:"<>|]', "_", title)
                        if len(title) > 200:
                            title = title[:200]
                        return title
            except ImportError:
                # Fallback to youtube-dl
                try:
                    import youtube_dl
                    ydl_opts = {'quiet': True, 'no_warnings': True}
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title')
                        if title:
                            title = re.sub(r'[\\/*?:"<>|]', "_", title)
                            if len(title) > 200:
                                title = title[:200]
                            return title
                except ImportError:
                    logger.warning("Neither yt-dlp nor youtube-dl available")
        except Exception as e:
            logger.warning(f"Could not fetch YouTube title: {str(e)}")
        
        return None
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL.
        
        Handles:
        - youtube.com/watch?v=ID
        - youtu.be/ID
        - youtube.com/embed/ID
        - youtube.com/v/ID
        """
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([^&\?/]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def validate_youtube_url(url: str) -> bool:
        """
        Validate if URL is a YouTube URL.
        
        Args:
            url: URL string to validate
        
        Returns:
            bool
        """
        youtube_patterns = [
            "youtube.com/watch",
            "youtu.be/",
            "youtube.com/embed/",
            "youtube.com/v/",
        ]
        return any(pattern in url.lower() for pattern in youtube_patterns)
    
    def get_supported_formats(self) -> set:
        """
        Get set of supported media formats.
        """
        return self.supported_formats
