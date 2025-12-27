    def read_file(self, file_path: str) -> tuple[bool, str, str]:
        """
        Read file content with support for multiple formats and automatic encoding detection.
        Supports: .txt, .srt, .json, .docx, and text-based formats.
        
        v4.4.4: Auto-detect encoding (UTF-8, UTF-16, UTF-16-LE, UTF-16-BE, etc.)
        This fixes files that show half their actual size.
        
        Args:
            file_path (str): Path to file to read
            
        Returns:
            tuple: (success: bool, content: str, error_msg: str or None)
            
        Example:
            >>> model = FileModel()
            >>> success, content, error = model.read_file('test.txt')
            >>> if success:
            ...     print(f"Read {len(content)} characters")
        """
        # Validate file exists and is readable
        valid, error = validate_file(file_path)
        if not valid:
            logger.error(f"File validation failed: {error}")
            return False, "", error
        
        try:
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Handle different file types
            if ext == '.docx':
                content = self._read_docx(file_path)
            elif ext == '.json':
                content = self._read_json(file_path)
            elif ext == '.srt':
                content = self._read_srt(file_path)
            else:
                # Default: read as text with encoding detection
                content = self._read_text_with_encoding_detection(file_path)
            
            # Validate content is not empty
            valid, error = validate_content_not_empty(content)
            if not valid:
                logger.warning(f"File is empty: {file_path}")
                return False, "", error
            
            logger.info(f"Successfully read file: {file_path} ({ext})")
            return True, content, None
            
        except UnicodeDecodeError as e:
            error = f"File encoding error - try .txt format: {str(e)}"
            logger.error(error)
            return False, "", error
        except Exception as e:
            error = f"Error reading file: {str(e)}"
            logger.error(error)
            return False, "", error
    
    def _read_text_with_encoding_detection(self, file_path: str) -> str:
        """
        v4.4.4: Read text file with automatic encoding detection.
        
        Tries multiple encodings in order:
        1. UTF-8 (most common)
        2. UTF-16 (Windows, half the reported size)
        3. UTF-16-LE (Little Endian)
        4. UTF-16-BE (Big Endian)
        5. Latin-1 (fallback, can read any byte sequence)
        
        This fixes the issue where 181 KB files show as 78.7 KB!
        
        Args:
            file_path (str): Path to file
            
        Returns:
            str: File content
        """
        # List of encodings to try, in order of likelihood
        encodings_to_try = [
            'utf-8',
            'utf-8-sig',  # UTF-8 with BOM
            'utf-16',
            'utf-16-le',
            'utf-16-be',
            'cp1252',  # Windows Latin
            'iso-8859-1',  # Latin-1, accepts any byte sequence
        ]
        
        file_size = os.path.getsize(file_path)
        logger.debug(f"Reading {file_path} - File size: {file_size} bytes")
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                # Success! Log which encoding worked
                content_size = len(content)
                logger.debug(f"Successfully read with encoding '{encoding}': {content_size} characters")
                logger.debug(f"Size ratio: {file_size} bytes → {content_size} chars (ratio: {file_size/max(1,content_size):.2f})")
                
                # If UTF-16, check if we got roughly half the file size
                if encoding.startswith('utf-16') and file_size > content_size * 1.8:
                    logger.info(f"⚠️ Encoding '{encoding}': File was {file_size} bytes, content {content_size} chars")
                    logger.info(f"   This is expected for UTF-16 (uses 2+ bytes per character)")
                
                return content
            except (UnicodeDecodeError, UnicodeError, LookupError) as e:
                logger.debug(f"Encoding '{encoding}' failed: {str(e)[:100]}")
                continue
            except Exception as e:
                logger.debug(f"Unexpected error with '{encoding}': {str(e)[:100]}")
                continue
        
        # Fallback: If all else fails, read as Latin-1 (it accepts any byte sequence)
        logger.warning(f"Could not decode with standard encodings, using Latin-1 fallback")
        with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
            return f.read()
    
    def _read_docx(self, file_path: str) -> str: