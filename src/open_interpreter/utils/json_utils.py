"""
JSON utilities: parse_partial_json, merge_deltas
"""

import json
import re
from typing import Dict, Any, Union


def parse_partial_json(json_str: str) -> Union[Dict[str, Any], None]:
    """
    Parse a potentially incomplete JSON string by attempting to fix common issues
    """
    # Try to parse the JSON as-is first
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # If that fails, try to fix common issues
    
    # Remove trailing commas before closing braces/brackets
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Try to close unclosed objects and arrays
    # Count opening and closing brackets
    open_count = json_str.count('{') + json_str.count('[')
    close_count = json_str.count('}') + json_str.count(']')
    
    # Close any unclosed brackets
    while close_count < open_count:
        if json_str.rstrip().endswith(','):
            json_str = json_str.rstrip(',') + '}'
        elif json_str.rstrip().endswith(':'):
            json_str = json_str.rstrip(':') + '"}'
        elif json_str.rstrip().endswith('"') or json_str.rstrip().endswith("'"):
            json_str += '}'
        else:
            json_str += '}'
        close_count += 1
    
    # Try to parse again
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # If still failing, try more aggressive truncation
        # Find the longest valid JSON prefix
        for i in range(len(json_str), 0, -1):
            try:
                partial = json_str[:i]
                # Add closing brackets if needed
                open_count = partial.count('{') + partial.count('[')
                close_count = partial.count('}') + partial.count(']')
                
                while close_count < open_count:
                    partial += '}'
                    close_count += 1
                
                return json.loads(partial)
            except json.JSONDecodeError:
                continue
        
        return None


def merge_deltas(original: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge a delta (partial update) into the original dictionary
    """
    result = original.copy()
    
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            # Recursively merge nested dictionaries
            result[key] = merge_deltas(result[key], value)
        elif value is None and key in result:
            # Remove key if value is None
            del result[key]
        else:
            # Update or add the key-value pair
            result[key] = value
    
    return result