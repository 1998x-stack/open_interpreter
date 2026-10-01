import subprocess
import platform
from .base import BaseInterpreter
from loguru import logger


class AppleScriptInterpreter(BaseInterpreter):
    """
    Interpreter for AppleScript execution (macOS only).
    """
    
    def __init__(self, language: str = "applescript", **kwargs):
        super().__init__(language, **kwargs)
        self.debug_mode = kwargs.get('debug_mode', False)

    def execute(self, code: str) -> str:
        """
        Execute AppleScript code and return the output.
        
        Args:
            code (str): AppleScript code to execute
            
        Returns:
            str: Output from the executed code
        """
        logger.info("Executing AppleScript code")
        
        # Check if running on macOS
        if platform.system() != 'Darwin':
            logger.warning("AppleScript is only available on macOS")
            return "ERROR: AppleScript is only available on macOS"
        
        try:
            # Execute AppleScript using osascript
            result = subprocess.run(
                ['osascript', '-e', code],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
                
            logger.debug(f"AppleScript execution completed, output length: {len(output)}")
            return output
        except subprocess.TimeoutExpired:
            logger.error("AppleScript execution timed out")
            return "ERROR: Code execution timed out after 30 seconds"
        except FileNotFoundError:
            logger.error("osascript is not available on this system")
            return "ERROR: AppleScript is not available on this system"
        except Exception as e:
            logger.error(f"Error executing AppleScript: {str(e)}")
            return f"ERROR: {str(e)}"

    def validate_code(self, code: str) -> bool:
        """
        Basic validation for AppleScript code.
        
        Args:
            code (str): AppleScript code to validate
            
        Returns:
            bool: True if code appears valid, False otherwise
        """
        # Basic validation - check for empty code
        if not code.strip():
            logger.warning("AppleScript validation failed: empty code")
            return False
        
        # Could add more sophisticated validation here
        logger.debug("AppleScript validation passed")
        return True