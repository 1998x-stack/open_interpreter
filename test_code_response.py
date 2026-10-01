"""
Test script to see what the LLM returns when prompted for code
"""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from src.open_interpreter import Interpreter

def test_code_generation():
    print("Testing LLM code generation...")

    interp = Interpreter()
    interp.auto_run = True

    # Simple prompt to generate code
    message = "Write a simple Python function to calculate the sum of first 10 Fibonacci numbers, and then execute it to show the result."

    print(f"Sending message: {message}")
    messages = interp.chat(message, return_messages=True)

    print("\nMessages received:")
    for i, msg in enumerate(messages):
        print(f"Message {i}: {msg}")

if __name__ == "__main__":
    test_code_generation()