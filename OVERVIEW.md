# Open Interpreter Project Overview

This project implements an AI-powered interpreter that can execute code in multiple languages and interact with users through a rich terminal interface.

## Architecture

The project follows a modular architecture with several key components:

### Core Components
- `src/open_interpreter/interpreter.py`: Main orchestrator (Interpreter class)
- `src/open_interpreter/config.py`: Configuration center for env vars and global constants
- `src/open_interpreter/cli.py`: CLI entry point using argparse

### Terminal UI Layer (using Rich)
- `src/open_interpreter/display/`: Terminal UI components
  - `base_block.py`: Abstract base class BaseBlock
  - `code_block.py`: CodeBlock component for code and output panels
  - `message_block.py`: MessageBlock component for Markdown message panels

### Code Execution Layer (Pluggable Executors)
- `src/open_interpreter/execution/`: Code execution components
  - `base_executor.py`: Abstract base class BaseExecutor
  - `executor_factory.py`: ExecutorFactory for registration and creation
  - `python_executor.py`: Python subprocess executor
  - `shell_executor.py`: Shell/Bash executor
  - `javascript_executor.py`: Node.js executor

### LLM Client Layer (Pluggable)
- `src/open_interpreter/llm/`: LLM client components
  - `base_llm.py`: Abstract base class BaseLLMClient
  - `llm_factory.py`: LLMFactory for registration and creation
  - `openai_client.py`: OpenAI/compatible API client

### Utilities
- `src/open_interpreter/utils/`: General utilities
  - `json_utils.py`: JSON parsing utilities (parse_partial_json, merge_deltas)
  - `output_utils.py`: Output processing utilities (truncate_output, fix_code_indentation)

## Tasks
- `tasks/`: Example tasks that can be run directly
  - `task_01_fibonacci.py`: Math computation task (Fibonacci + performance analysis)
  - `task_02_data_analysis.py`: Data analysis task (CSV stats + visualization)
  - `task_03_file_ops.py`: File operations task (batch renaming + directory organization)

## Tests
- `tests/`: Unit tests using pytest