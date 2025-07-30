import html
import re
import tiktoken

def escape_page_text(text: str) -> str:
    # Escape triple quotes, backticks, curly braces, and HTML-like tags
    text = text.replace("```", "'''")  # prevent markdown-style blocks
    text = text.replace("'''", "\\'\\'\\'")
    text = text.replace('"""', '\\"""')
    text = text.replace('{', '\\{').replace('}', '\\}')
    text = html.escape(text)  # escapes < > & etc.
    text = re.sub(r'[\\]', r'\\\\', text)  # escape backslashes
    return text


def count_tokens(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def split_content_by_commands(chapter, config) -> list[dict]:
    """
    Splits the chapter content into a series of segments based on commands.

    Each segment in the output will have the content, the voice_id, and the
    emotion that apply to it.

    Args:
        chapter (dict): A dictionary containing chapter details like 
                        'chapter_id', 'chapter_title', and 'content'.
        config (dict): A dictionary where keys are chapter_ids and values are
                       lists of command objects.

    Returns:
        list: A list of dictionaries, where each dictionary represents a
              segment with its content, voice_id, and emotion.
    """
    chapter_id = chapter.get("chapter_id")
    content = chapter.get("content", "")
    
    # Return early if there's no content or no configuration for this chapter
    if not content or not chapter_id or chapter_id not in config:
        return [{
            "content": content,
            "voice_id": None,
            "emotion": None
        }]

    commands = config[chapter_id] 
    
    # --- 1. Collect all unique split points ---
    # We start with 0 and the total length of the content.
    split_points = {0, len(content)}
    for command in commands:
        pos = command.get("content_position", {})
        start = pos.get("start")
        end = pos.get("end")
        if start is not None:
            split_points.add(start)
        if end is not None:
            split_points.add(end)
            
    # Sort the points to process the content chronologically
    sorted_points = sorted(list(filter(lambda p: p is not None and p <= len(content), split_points)))


    # --- 2. Create segments and assign commands ---
    result_segments = []
    
    # Iterate through the sorted points to create content segments
    for i in range(len(sorted_points) - 1):
        segment_start = sorted_points[i]
        segment_end = sorted_points[i+1]

        # Skip empty segments that might be created by adjacent split points
        if segment_start >= segment_end:
            continue

        segment_content = content[segment_start:segment_end]
        
        # Determine which commands apply to this specific segment
        applied_voice_id = None
        applied_emotion = None
        
        for command in commands:
            cmd_pos = command.get("content_position", {})
            cmd_start = cmd_pos.get("start")
            cmd_end = cmd_pos.get("end")
            
            # A command applies if the segment is fully contained within the command's range
            if cmd_start is not None and cmd_end is not None:
                if segment_start >= cmd_start and segment_end <= cmd_end:
                    command_type = command.get("command_type")
                    if command_type == "speaker_change":
                        applied_voice_id = command.get("voice_id")
                    elif command_type == "emotion_change":
                        applied_emotion = command.get("emotion")

        result_segments.append({
            "content": segment_content,
            "voice_id": applied_voice_id,
            "emotion": applied_emotion
        })
        
    return result_segments