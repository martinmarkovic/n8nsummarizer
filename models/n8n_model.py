    def extract_summary(self, response_data) -> str:
        """
        Extract summary from n8n response.
        Tries multiple common keys: summary, summarization, result, output, text, content
        
        v4.4.2: Also handles None responses gracefully
        v4.4.3: Returns None for truly empty responses (to be filtered)
        v4.4.4: DEBUG LOGGING - Log full response and extraction process
        
        Args:
            response_data: Response from n8n (dict, str, etc.)
            
        Returns:
            str: Extracted summary or stringified response. None if truly empty.
        """
        # v4.4.4 DEBUG: Log the FULL response first
        logger.debug(f"\n{'='*70}")
        logger.debug(f"EXTRACT_SUMMARY - Full N8N Response:")
        logger.debug(f"Response type: {type(response_data).__name__}")
        
        if isinstance(response_data, dict):
            logger.debug(f"Response keys: {list(response_data.keys())}")
            logger.debug(f"Response content (JSON):")
            for key, value in response_data.items():
                value_type = type(value).__name__
                if isinstance(value, str):
                    value_preview = value[:100] if len(value) > 100 else value
                    logger.debug(f"  {key}: ({value_type}) {value_preview}")
                elif isinstance(value, (dict, list)):
                    logger.debug(f"  {key}: ({value_type}) {len(str(value))} chars")
                else:
                    logger.debug(f"  {key}: ({value_type}) {value}")
        elif isinstance(response_data, str):
            preview = response_data[:200] if len(response_data) > 200 else response_data
            logger.debug(f"Response content (String): {preview}")
        else:
            logger.debug(f"Response content: {response_data}")
        
        logger.debug(f"{'='*70}\n")
        
        # Original extraction logic
        if response_data is None:
            logger.debug("Result: Response is None")
            return None
        
        if isinstance(response_data, str):
            # Check if it's an empty string
            if response_data.strip() == "":
                logger.debug("Result: Response is empty string")
                return None
            logger.debug(f"Result: Returning string response ({len(response_data)} chars)")
            return response_data
        
        if isinstance(response_data, dict):
            # Try common keys first
            common_keys = ['summary', 'summarization', 'result', 'output', 'text', 'content']
            logger.debug(f"Checking for common keys: {common_keys}")
            
            for key in common_keys:
                if key in response_data:
                    value = response_data[key]
                    logger.debug(f"Found key '{key}' with type {type(value).__name__}")
                    
                    if isinstance(value, str):
                        if value.strip():
                            logger.debug(f"Result: Extracted from key '{key}' ({len(value)} chars)")
                            return value
                        else:
                            logger.debug(f"  Key '{key}' is empty string, continuing")
                    elif isinstance(value, dict):
                        logger.debug(f"Result: Found dict in key '{key}', returning as JSON")
                        return json.dumps(value, indent=2)
                    else:
                        str_value = str(value)
                        logger.debug(f"Result: Found {type(value).__name__} in key '{key}', stringified ({len(str_value)} chars)")
                        return str_value
            
            # If no common keys, check if dict is empty
            if not response_data:
                logger.debug("Result: Response dict is empty")
                return None
            
            # Return pretty-printed JSON if not empty
            json_str = json.dumps(response_data, indent=2)
            logger.debug(f"Result: No common keys found, returning full dict as JSON ({len(json_str)} chars)")
            return json_str
        
        # For other types, stringify
        str_response = str(response_data)
        if str_response.strip():
            logger.debug(f"Result: Stringified {type(response_data).__name__} ({len(str_response)} chars)")
            return str_response
        else:
            logger.debug(f"Result: Response is empty after stringification")
            return None