"""
Transcribe Model - Business logic for transcribe-anything wrapper

Responsibilities:
    - Call transcribe-anything CLI for local files and YouTube URLs
    - Extract YouTube video titles for output naming
    - Manage output files (SRT, TXT, etc.)
    - Handle device selection (CPU, CUDA, Insane, MPS)
    - Return SRT transcript for n8n processing

Reusable by:
    - TranscriberTab (primary)
    - FileTab (secondary - transcribe files first)
    - Future tabs (bulk transcriber, translation, etc.)
"""
import subprocess
import tempfile
import shutil
import re
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
    
    Output handling:
    - Generates .txt and .srt by default
    - Optional: .json, .vtt, .tsv
    - Returns SRT content for processing
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
        logger.info("TranscribeModel initialized (transcribe-anything wrapper)")
    
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
            file_path: Path to local media file
            device: "cpu", "cuda", "insane", or "mps"
            output_dir: Where to save transcripts (None = same as input file)
            keep_formats: File formats to keep ['.txt', '.srt']
                         Other formats deleted after transcription
        
        Returns:
            Tuple: (success, srt_content, error_msg, metadata_dict)
            - success: bool
            - srt_content: str (SRT transcript content) or None
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
            base_name = file_path.stem
            
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
                srt_content, metadata = self._process_outputs(
                    temp_path=temp_path,
                    output_dir=output_dir,
                    base_name=base_name,
                    keep_formats=keep_formats,
                    source_type="file"
                )
                
                if srt_content is None:
                    return False, None, "No SRT transcript generated", None
                
                logger.info(f"Successfully transcribed: {file_path.name}")
                return True, srt_content, None, metadata
        
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
                srt_content, metadata = self._process_outputs(
                    temp_path=temp_path,
                    output_dir=output_dir,
                    base_name=base_name,
                    keep_formats=keep_formats,
                    source_type="youtube",
                    url=youtube_url
                )
                
                if srt_content is None:
                    return False, None, "No SRT transcript generated", None
                
                logger.info(f"Successfully transcribed YouTube video: {base_name}")
                return True, srt_content, None, metadata
        
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
        
        Returns:
            Tuple: (success, error_msg)
        """
        try:
            # Build command
            cmd = [
                'transcribe-anything',
                f'"{input_path}"',
                f'--device {device}',
                f'--output_dir "{output_dir}"'
            ]
            
            # Alternative: Use batch file on Windows (if direct command fails)
            cmd_str = ' '.join(cmd)
            
            logger.info(f"Running: {cmd_str}")
            
            # Execute command
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )
            
            if result.returncode != 0:
                error = f"Transcription failed: {result.stderr or result.stdout}"
                logger.error(error)
                return False, error
            
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
        - Returns SRT content
        - Generates metadata
        
        Returns:
            Tuple: (srt_content_str, metadata_dict)
        """
        try:
            srt_content = None
            files_created = []
            metadata = {
                'base_name': base_name,
                'source_type': source_type,
                'url': url,
                'output_dir': str(output_dir),
                'files_kept': [],
                'files_deleted': []
            }
            
            # Expected output files from transcribe-anything
            output_extensions = ['.txt', '.srt', '.vtt', '.json', '.tsv']
            
            # Find and process output files
            for temp_file in temp_path.iterdir():
                if not temp_file.is_file():
                    continue
                
                # Check if it's an output file
                if not (temp_file.name.startswith('out.') or temp_file.suffix in output_extensions):
                    continue
                
                # Determine final filename
                if temp_file.name.startswith('out.'):
                    new_name = temp_file.name.replace('out.', f'{base_name}.')
                else:
                    new_name = f"{base_name}{temp_file.suffix}"
                
                final_path = output_dir / new_name
                ext = temp_file.suffix.lower()
                
                # Check if we should keep this format
                if ext in keep_formats:
                    try:
                        shutil.copy2(temp_file, final_path)
                        files_created.append(new_name)
                        metadata['files_kept'].append(new_name)
                        
                        # Read SRT content if this is the SRT file
                        if ext == '.srt':
                            with open(final_path, 'r', encoding='utf-8') as f:
                                srt_content = f.read()
                        
                        logger.info(f"Created: {new_name}")
                    except Exception as e:
                        logger.warning(f"Failed to copy {temp_file.name}: {str(e)}")
                else:
                    # Delete unwanted format
                    try:
                        temp_file.unlink()
                        metadata['files_deleted'].append(new_name)
                        logger.info(f"Deleted unwanted format: {new_name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {temp_file.name}: {str(e)}")
            
            logger.info(f"Output processing complete: {len(files_created)} files created")
            return srt_content, metadata
        
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
