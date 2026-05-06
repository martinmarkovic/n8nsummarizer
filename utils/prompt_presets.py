"""
Prompt Presets Module

Provides predefined prompt templates for different summarization use cases.
These presets are designed to work with LLM webhooks (LM Studio, Ollama, etc.)
and can be used to customize summarization behavior.

Usage:
    from utils.prompt_presets import PROMPT_PRESETS, DEFAULT_PROMPT_KEY, PRESET_NAMES
    
    # Get default prompt
    prompt = PROMPT_PRESETS[DEFAULT_PROMPT_KEY]
    
    # Get all preset names for UI dropdown
    preset_names = PRESET_NAMES
    
    # Get specific preset
    meeting_prompt = PROMPT_PRESETS["Meeting Notes"]
"""

# Prompt Presets Dictionary
# Keys are human-readable preset names, values are full prompt strings
PROMPT_PRESETS = {
    "General Summary": """
    Summarize the following content in a clear, concise manner. Focus on the main points, key information, and essential details. The summary should be comprehensive enough to understand the content without reading the original, but concise enough to be quickly digestible.
    
    Requirements:
    - Maintain the original meaning and context
    - Use bullet points or short paragraphs for readability
    - Keep the summary to approximately 20-30% of the original length
    - Preserve important names, dates, and specific details
    - Use professional, neutral language
    
    Content to summarize:
    {content}
    
    Summary:
    """,
    
    "Meeting Notes": """
    Extract key information from this meeting transcript or notes. Organize the information in a structured format.
    
    Required sections:
    1. Meeting Title/Topic:
    2. Date and Time:
    3. Participants:
    4. Key Decisions Made:
    5. Action Items (with owners and deadlines):
    6. Open Questions/Next Steps:
    7. Important Discussions or Debates:
    8. Any Deadlines or Milestones Mentioned:
    
    If any section has no content, write "None" or "Not applicable".
    
    Meeting content:
    {content}
    
    Structured meeting notes:
    """,
    
    "Technical Document": """
    Summarize this technical document focusing on key technical concepts, APIs, requirements, and implementation details. Use precise technical language and maintain accuracy.
    
    Structure your summary with these sections:
    1. Document Purpose/Overview:
    2. Key Technical Concepts:
    3. APIs/Interfaces (if applicable):
    4. Implementation Requirements:
    5. Dependencies/Prerequisites:
    6. Important Code Snippets or Configurations:
    7. Potential Issues or Considerations:
    8. Testing or Validation Requirements:
    
    Use markdown formatting for code blocks and maintain technical accuracy. Preserve all technical terms, variable names, and specific configurations.
    
    Technical content:
    {content}
    
    Technical summary:
    """,
    
    "Research / Article": """
    Create a structured summary of this research paper or article. Focus on the academic or analytical content.
    
    Required structure:
    1. Title and Authors:
    2. Main Research Question or Thesis:
    3. Methodology (if applicable):
    4. Key Findings or Arguments:
    5. Supporting Evidence or Data:
    6. Conclusions or Implications:
    7. Limitations or Counterarguments (if mentioned):
    8. References to Important Sources:
    
    For opinion pieces or editorials, adapt to focus on main argument, supporting points, and counterarguments.
    
    Research content:
    {content}
    
    Structured research summary:
    """,
    
    "Interview / Transcript": """
    Summarize this interview or conversation transcript, organizing by topics and identifying speakers where possible.
    
    Format your summary as follows:
    1. Interview/Conversation Title or Context:
    2. Participants (if identifiable):
    3. Date/Time (if available):
    4. Summary by Topic:
       - Topic 1: [Key points discussed, speaker attributions if possible]
       - Topic 2: [Key points discussed, speaker attributions if possible]
       - [Continue for all major topics]
    5. Notable Quotes (with speaker attribution if possible):
    6. Key Takeaways or Conclusions:
    7. Action Items or Follow-ups (if mentioned):
    
    If speakers cannot be identified, summarize by topic without attribution. Preserve the conversational flow and key insights.
    
    Interview content:
    {content}
    
    Structured interview summary:
    """
}

# Default prompt preset key
DEFAULT_PROMPT_KEY = "General Summary"

# List of preset names for UI dropdowns and selection
PRESET_NAMES = list(PROMPT_PRESETS.keys())


def get_prompt_preset(key: str) -> str:
    """
    Get a specific prompt preset by key.
    
    Args:
        key: The preset key (e.g., "General Summary", "Meeting Notes")
        
    Returns:
        The prompt string for the specified preset
        
    Raises:
        KeyError: If the key doesn't exist in PROMPT_PRESETS
    """
    return PROMPT_PRESETS[key]


def get_prompt_with_content(key: str, content: str) -> str:
    """
    Get a prompt preset with content inserted.
    
    Args:
        key: The preset key
        content: The content to be summarized
        
    Returns:
        The complete prompt with content inserted
    """
    prompt_template = PROMPT_PRESETS[key]
    return prompt_template.format(content=content)


def validate_prompt_key(key: str) -> bool:
    """
    Check if a prompt key exists in the presets.
    
    Args:
        key: The preset key to validate
        
    Returns:
        True if the key exists, False otherwise
    """
    return key in PROMPT_PRESETS