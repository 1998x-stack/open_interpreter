import subprocess
import platform
import os
from .base import BaseInterpreter
from loguru import logger


class ShellInterpreter(BaseInterpreter):
    """
    Interpreter for Shell command execution.
    """
    
    def __init__(self, language: str = "shell", **kwargs):
        super().__init__(language, **kwargs)
        self.debug_mode = kwargs.get('debug_mode', False)

    def execute(self, code: str) -> str:
        """
        Execute shell command and return the output.
        
        Args:
            code (str): Shell command to execute
            
        Returns:
            str: Output from the executed command
        """
        logger.info("Executing shell command")
        
        # Determine shell based on OS
        shell_cmd = 'cmd.exe' if platform.system() == 'Windows' else os.environ.get('SHELL', 'bash')
        
        try:
            # Execute the shell command
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
                
            logger.debug(f"Shell execution completed, output length: {len(output)}")
            return output
        except subprocess.TimeoutExpired:
            logger.error("Shell command execution timed out")
            return "ERROR: Command execution timed out after 30 seconds"
        except Exception as e:
            logger.error(f"Error executing shell command: {str(e)}")
            return f"ERROR: {str(e)}"

    def validate_code(self, code: str) -> bool:
        """
        Validate shell command (basic validation).
        
        Args:
            code (str): Shell command to validate
            
        Returns:
            bool: True if command appears valid, False otherwise
        """
        # Basic validation - check for empty code
        if not code.strip():
            logger.warning("Shell command validation failed: empty command")
            return False
        
        # Check for dangerous commands
        dangerous_patterns = ['rm -rf', 'sudo rm', 'format', 'del /s']
        for pattern in dangerous_patterns:
            if pattern in code.lower():
                logger.warning(f"Dangerous command detected: {pattern}")
                return False
                
        logger.debug("Shell command validation passed")
        return True