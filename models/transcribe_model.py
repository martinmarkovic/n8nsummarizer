"""
Transcribe Model - Business logic for YouTube transcript fetching

Responsibilities:
    - Extract video ID from various YouTube URL formats
    - Download YouTube transcripts
    - Handle transcript parsing
    - Manage transcript errors and edge cases
    
REUSABLE by multiple controllers:
    - TranscribeController (YouTube Transcribe tab)
    - BulkController (future: bulk transcribe tab)
    - TranslationController (future: translation feature)

This is PURE business logic - NO UI dependencies.
Can be tested independently without GUI.
"""
from urllib.parse import urlparse, parse_qs
from utils.logger import logger


class TranscribeModel:
    """Handles YouTube transcript operations"""
    
    def __init__(self):
        """
        Initialize transcribe model.
        Checks if youtube-transcript-api is installed.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self.YouTubeTranscriptApi = YouTubeTranscriptApi
            logger.info("YouTubeTranscriptApi loaded successfully")
        except ImportError:
            logger.error("youtube-transcript-api not installed")
            self.YouTubeTranscriptApi = None
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Handles multiple URL formats:
        - https://www.youtube.com/watch?v=dQw4w9WgXcQ
        - https://youtu.be/dQw4w9WgXcQ
        - dQw4w9WgXcQ (raw video ID)
        
        Args:
            url (str): YouTube URL or video ID
            
        Returns:
            str: Video ID or None if invalid
            
        Example:
            >>> model = TranscribeModel()
            >>> vid_id = model.extract_video_id('https://youtu.be/dQw4w9WgXcQ')
            >>> print(vid_id)  # 'dQw4w9WgXcQ'
        """
        try:
            # Handle youtu.be short URLs
            if 'youtu.be' in url:
                # Remove query parameters and get video ID
                path = urlparse(url).path
                video_id = path.lstrip('/')
                if '?' in video_id:
                    video_id = video_id.split('?')[0]
                return video_id if video_id else None
            
            # Handle youtube.com full URLs
            if 'youtube.com' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get('v', [None])[0]
                return video_id
            
            # Assume it's already a video ID (11 characters)
            if len(url) == 11 and url.replace('_', '').replace('-', '').isalnum():
                return url
            
            logger.warning(f"Could not extract video ID from: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
            return None
    
    def get_transcript(self, video_url: str, languages: list = None) -> tuple[bool, str, str]:
        """
        Download YouTube transcript.
        
        Args:
            video_url (str): YouTube URL or video ID
            languages (list): List of language codes to try (e.g., ['en', 'es'])
                            Default: ['en'] (English only)
            
        Returns:
            tuple: (success: bool, transcript: str, error_msg: str or None)
            
        Example:
            >>> model = TranscribeModel()
            >>> success, transcript, error = model.get_transcript('dQw4w9WgXcQ')
            >>> if success:
            ...     print(f"Got {len(transcript)} characters of transcript")
        """
        if self.YouTubeTranscriptApi is None:
            error = "youtube-transcript-api not installed. Install with: pip install youtube-transcript-api"
            logger.error(error)
            return False, "", error
        
        if languages is None:
            languages = ['en']
        
        try:
            # Extract video ID
            video_id = self.extract_video_id(video_url)
            
            if not video_id:
                error = "Invalid YouTube URL or video ID"
                logger.error(error)
                return False, "", error
            
            logger.info(f"Fetching transcript for video: {video_id}")
            
            try:
                # Try to get transcript with specified languages
                transcript_data = self.YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=languages
                )
            except self.YouTubeTranscriptApi.NoTranscriptFound:
                # If no transcript in specified language, try to find any available
                logger.warning(f"No transcript found for languages {languages}, trying all available...")
                try:
                    # Get list of available transcripts
                    transcript_list = self.YouTubeTranscriptApi.list_transcripts(video_id)
                    
                    # Try to get the first available transcript
                    if transcript_list.auto_generated_transcripts:
                        transcript_data = transcript_list.auto_generated_transcripts[0].fetch()
                    elif transcript_list.manually_created_transcripts:
                        transcript_data = transcript_list.manually_created_transcripts[0].fetch()
                    else:
                        error = "No transcripts available for this video"
                        logger.error(error)
                        return False, "", error
                except Exception as e:
                    error = f"Could not find transcript: {str(e)}"
                    logger.error(error)
                    return False, "", error
            
            # Join transcript parts into single string
            full_transcript = ' '.join([item['text'] for item in transcript_data])
            
            if not full_transcript.strip():
                error = "Transcript is empty"
                logger.error(error)
                return False, "", error
            
            logger.info(f"Successfully fetched transcript ({len(full_transcript)} characters)")
            return True, full_transcript, None
        
        except Exception as e:
            error = f"Error fetching transcript: {str(e)}"
            logger.error(error)
            return False, "", error
    
    def get_video_metadata(self, video_url: str) -> dict:
        """
        Get basic metadata about the video (title, etc.).
        
        Args:
            video_url (str): YouTube URL or video ID
            
        Returns:
            dict: Metadata dictionary (currently just video_id)
                 {
                     'video_id': extracted video ID,
                     'title': video title (if available)
                 }
        """
        metadata = {}
        
        try:
            video_id = self.extract_video_id(video_url)
            if video_id:
                metadata['video_id'] = video_id
                # Could add title extraction here if needed (requires pytube or similar)
            return metadata
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
            return metadata
