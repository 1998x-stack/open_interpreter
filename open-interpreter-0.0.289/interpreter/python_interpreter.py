import ast
import astor
import subprocess
import sys
import threading
import traceback
from .base import BaseInterpreter
from .utils import fix_code_indentation
from .code_interpreter import truncate_output
from loguru import logger


class PythonInterpreter(BaseInterpreter):
    """
    Interpreter for Python code execution.
    """
    
    def __init__(self, language: str = "python", **kwargs):
        super().__init__(language, **kwargs)
        self.proc = None
        self.debug_mode = kwargs.get('debug_mode', False)
        self.active_line = None
        self.output = ""

    def execute(self, code: str) -> str:
        """
        Execute Python code and return the output.
        
        Args:
            code (str): Python code to execute
            
        Returns:
            str: Output from the executed code
        """
        logger.info("Executing Python code")
        
        # Normalize code by parsing then unparsing it
        try:
            parsed_ast = ast.parse(code)
            normalized_code = astor.to_source(parsed_ast)
        except:
            # If normalization failed, use original code
            logger.warning("Code normalization failed, using original code")
            traceback_str = traceback.format_exc()
            logger.debug(f"Normalization error: {traceback_str}")
            normalized_code = code
        
        # Fix indentation
        normalized_code = fix_code_indentation(normalized_code)
        
        # Execute the code
        return self._execute_python_code(normalized_code)

    def _execute_python_code(self, code: str) -> str:
        """
        Execute Python code in a subprocess.
        
        Args:
            code (str): Normalized Python code to execute
            
        Returns:
            str: Output from the executed code
        """
        try:
            # Execute code using the system Python executable
            result = subprocess.run(
                [sys.executable, '-c', code],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
                
            # Truncate output if too long
            output = truncate_output(output)
            logger.debug(f"Python execution completed, output length: {len(output)}")
            
            return output
        except subprocess.TimeoutExpired:
            logger.error("Python code execution timed out")
            return "ERROR: Code execution timed out after 30 seconds"
        except Exception as e:
            logger.error(f"Error executing Python code: {str(e)}")
            return f"ERROR: {str(e)}"

    def validate_code(self, code: str) -> bool:
        """
        Validate Python code by attempting to parse it.
        
        Args:
            code (str): Python code to validate
            
        Returns:
            bool: True if code is valid Python, False otherwise
        """
        try:
            ast.parse(code)
            logger.debug("Python code validation passed")
            return True
        except SyntaxError as e:
            logger.warning(f"Python code validation failed: {str(e)}")
            return False
        except Exception as e:
            logger.warning(f"Python code validation error: {str(e)}")
            return False