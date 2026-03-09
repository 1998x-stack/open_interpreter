"""
CLI entry point using argparse
"""

import argparse
from .interpreter import Interpreter
from .config import Config


def main():
    parser = argparse.ArgumentParser(
        description="Open Interpreter - AI-powered code execution environment"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model to use (default: from config)"
    )
    
    parser.add_argument(
        "--executor",
        type=str,
        default="python",
        choices=["python", "shell", "javascript"],
        help="Code executor to use (default: python)"
    )
    
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        choices=["dark", "light"],
        help="Display theme (default: from config)"
    )
    
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Start interactive mode"
    )
    
    args = parser.parse_args()
    
    # Update config with CLI arguments
    config = Config()
    if args.model:
        config.MODEL = args.model
    if args.theme:
        config.THEME = args.theme
    
    # Create interpreter instance
    interpreter = Interpreter(config)
    
    if args.interactive:
        run_interactive(interpreter, args.executor)
    else:
        # If no interactive mode, show help
        parser.print_help()


def run_interactive(interpreter: Interpreter, executor_type: str):
    """Run the interpreter in interactive mode"""
    interpreter.switch_executor(executor_type)
    
    print(f"Starting interactive mode with {executor_type} executor...")
    print("Type 'exit' to quit\n")
    
    while True:
        try:
            user_input = input(">>> ")
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            if user_input.strip():
                response = interpreter.chat(user_input)
                print(response)
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()