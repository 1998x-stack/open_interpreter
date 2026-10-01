import subprocess
from .base import BaseInterpreter
from loguru import logger


class JavaScriptInterpreter(BaseInterpreter):
    """
    Interpreter for JavaScript execution.
    """
    
    def __init__(self, language: str = "javascript", **kwargs):
        super().__init__(language, **kwargs)
        self.debug_mode = kwargs.get('debug_mode', False)

    def execute(self, code: str) -> str:
        """
        Execute JavaScript code and return the output.
        
        Args:
            code (str): JavaScript code to execute
            
        Returns:
            str: Output from the executed code
        """
        logger.info("Executing JavaScript code")
        
        try:
            # Execute JavaScript using Node.js
            result = subprocess.run(
                ['node', '-e', code],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
                
            logger.debug(f"JavaScript execution completed, output length: {len(output)}")
            return output
        except subprocess.TimeoutExpired:
            logger.error("JavaScript execution timed out")
            return "ERROR: Code execution timed out after 30 seconds"
        except FileNotFoundError:
            logger.error("Node.js is not installed or not in PATH")
            return "ERROR: Node.js is not installed or not accessible"
        except Exception as e:
            logger.error(f"Error executing JavaScript code: {str(e)}")
            return f"ERROR: {str(e)}"

    def validate_code(self, code: str) -> bool:
        """
        Basic validation for JavaScript code.
        
        Args:
            code (str): JavaScript code to validate
            
        Returns:
            bool: True if code appears valid, False otherwise
        """
        # Basic validation - check for empty code
        if not code.strip():
            logger.warning("JavaScript code validation failed: empty code")
            return False
        
        # Could add more sophisticated validation here
        logger.debug("JavaScript code validation passed")
        return True