"""
Output utilities: truncate_output, fix_code_indentation
"""

from typing import Optional


def truncate_output(output: str, max_length: int = 1000) -> str:
    """
    Truncate output if it exceeds max_length, adding indicator if truncated
    """
    if len(output) <= max_length:
        return output
    
    # Calculate how much to keep, accounting for the truncation indicator
    indicator = f"\n... (output truncated, showing first {max_length} characters)"
    available_length = max_length - len(indicator)
    
    if available_length <= 0:
        return indicator
    
    truncated = output[:available_length]
    return truncated + indicator


def fix_code_indentation(code: str) -> str:
    """
    Fix common code indentation issues
    """
    lines = code.split('\n')
    fixed_lines = []
    
    # Track the minimum indent level for the block
    min_indent = float('inf')
    non_empty_lines = [line for line in lines if line.strip()]
    
    for line in non_empty_lines:
        stripped = line.lstrip()
        if stripped:  # Skip completely empty lines for indent calculation
            indent = len(line) - len(stripped)
            min_indent = min(min_indent, indent)
    
    # Adjust all lines by removing the minimum indent
    for line in lines:
        if line.strip() and min_indent != float('inf'):
            # Remove the minimum indent from non-empty lines
            if len(line) >= min_indent:
                fixed_lines.append(line[min_indent:])
            else:
                fixed_lines.append(line)
        else:
            # Keep empty lines as they are
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def normalize_newlines(text: str) -> str:
    """
    Normalize different types of newlines to \n
    """
    return text.replace('\r\n', '\n').replace('\r', '\n')


def sanitize_output(output: str) -> str:
    """
    Sanitize output by removing potentially harmful content
    """
    # Remove ANSI escape codes (color codes, etc.)
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    sanitized = ansi_escape.sub('', output)
    
    return sanitized