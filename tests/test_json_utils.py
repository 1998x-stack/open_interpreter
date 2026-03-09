"""
Unit tests for JSON utilities
"""

from src.open_interpreter.utils.json_utils import parse_partial_json, merge_deltas


def test_parse_complete_json():
    """Test parsing complete JSON"""
    json_str = '{"name": "John", "age": 30}'
    result = parse_partial_json(json_str)
    
    assert result == {"name": "John", "age": 30}


def test_parse_partial_json_with_trailing_comma():
    """Test parsing JSON with trailing comma"""
    json_str = '{"name": "John", "age": 30,}'
    result = parse_partial_json(json_str)
    
    assert result == {"name": "John", "age": 30}


def test_parse_partial_unclosed_object():
    """Test parsing JSON with unclosed object"""
    json_str = '{"name": "John", "age": 30'
    result = parse_partial_json(json_str)
    
    assert result == {"name": "John", "age": 30}


def test_parse_partial_nested_object():
    """Test parsing partial nested JSON object"""
    json_str = '{"user": {"name": "John"'
    result = parse_partial_json(json_str)
    
    # Should return the longest valid JSON prefix
    assert "user" in result
    assert isinstance(result["user"], dict)


def test_merge_deltas_basic():
    """Test basic delta merging"""
    original = {"name": "John", "age": 30}
    delta = {"age": 31, "city": "New York"}
    result = merge_deltas(original, delta)
    
    expected = {"name": "John", "age": 31, "city": "New York"}
    assert result == expected


def test_merge_deltas_nested():
    """Test merging nested deltas"""
    original = {
        "user": {
            "name": "John",
            "details": {
                "age": 30
            }
        },
        "active": True
    }
    
    delta = {
        "user": {
            "details": {
                "age": 31,
                "city": "New York"
            }
        },
        "active": False
    }
    
    result = merge_deltas(original, delta)
    
    expected = {
        "user": {
            "name": "John",
            "details": {
                "age": 31,
                "city": "New York"
            }
        },
        "active": False
    }
    
    assert result == expected


def test_merge_deltas_remove_key():
    """Test removing a key with None value"""
    original = {"name": "John", "age": 30, "city": "NYC"}
    delta = {"city": None}  # Should remove city
    result = merge_deltas(original, delta)
    
    expected = {"name": "John", "age": 30}
    assert result == expected


def test_merge_deltas_add_new_keys():
    """Test adding new keys during merge"""
    original = {"name": "John"}
    delta = {"age": 30, "city": "NYC"}
    result = merge_deltas(original, delta)
    
    expected = {"name": "John", "age": 30, "city": "NYC"}
    assert result == expected