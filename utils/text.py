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