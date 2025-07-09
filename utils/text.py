import html
import re

def escape_page_text(text: str) -> str:
    # Escape triple quotes, backticks, curly braces, and HTML-like tags
    text = text.replace("```", "'''")  # prevent markdown-style blocks
    text = text.replace("'''", "\\'\\'\\'")
    text = text.replace('"""', '\\"""')
    text = text.replace('{', '\\{').replace('}', '\\}')
    text = html.escape(text)  # escapes < > & etc.
    text = re.sub(r'[\\]', r'\\\\', text)  # escape backslashes
    return text
