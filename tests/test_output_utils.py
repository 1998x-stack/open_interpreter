"""
Unit tests for output utilities
"""

from src.open_interpreter.utils.output_utils import (
    truncate_output, 
    fix_code_indentation,
    normalize_newlines,
    sanitize_output
)


def test_truncate_output_within_limit():
    """Test that outputs within the limit are unchanged"""
    text = "Short text"
    result = truncate_output(text, max_length=20)
    
    assert result == "Short text"


def test_truncate_output_exceeds_limit():
    """Test that outputs exceeding the limit are truncated"""
    long_text = "This is a very long text that exceeds the character limit we set"
    result = truncate_output(long_text, max_length=20)
    
    # Should contain the truncation indicator
    assert "... (output truncated" in result
    # Should be exactly the max length
    assert len(result) <= 20


def test_fix_code_indentation_consistent():
    """Test fixing consistently indented code"""
    indented_code = """    def hello():
        print("Hello")
        if True:
            print("World")"""
    
    expected = """def hello():
    print("Hello")
    if True:
        print("World")"""
    
    result = fix_code_indentation(indented_code)
    assert result == expected


def test_fix_code_indentation_mixed():
    """Test fixing mixed indentation"""
    mixed_code = """def test():
      x = 1
    y = 2
      if x:
        print(y)"""
    
    # The function should adjust indentation based on the minimum indent
    result = fix_code_indentation(mixed_code)
    lines = result.split('\n')
    
    # Verify that the first meaningful line has no indent
    assert lines[0] == "def test():"
    

def test_normalize_newlines():
    """Test normalizing different newline formats"""
    text_with_different_newlines = "Line 1\r\nLine 2\rLine 3\nLine 4"
    result = normalize_newlines(text_with_different_newlines)
    
    # All newlines should be converted to \n
    assert "\r\n" not in result
    assert "\r" not in result
    assert result.count('\n') == 3  # 3 newlines separating 4 lines


def test_sanitize_output_removes_ansi_codes():
    """Test sanitizing output by removing ANSI color codes"""
    text_with_colors = "This is \x1b[31mred\x1b[0m text"
    result = sanitize_output(text_with_colors)
    
    # Color codes should be removed
    assert "\x1b[31m" not in result
    assert "\x1b[0m" not in result
    assert result == "This is red text"


def test_sanitize_output_preserves_normal_text():
    """Test that normal text is preserved during sanitization"""
    normal_text = "This is normal text without any special codes"
    result = sanitize_output(normal_text)
    
    assert result == normal_text