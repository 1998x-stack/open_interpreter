# Open Interpreter

Quick start guide for the Open Interpreter project.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Run the interpreter
python -m src.open_interpreter.cli --help

# Run example tasks
python tasks/task_01_fibonacci.py
python tasks/task_02_data_analysis.py
python tasks/task_03_file_ops.py
```

## Features

- Multi-language code execution (Python, Shell, JavaScript)
- Rich terminal UI with code and message blocks
- Pluggable LLM client support
- Interactive command-line interface
- Built-in utility functions for JSON and output processing

## Development

See `OVERVIEW.md` for architectural details and contribution guidelines.