"""
ShellExecutor: Shell/Bash executor
"""

import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from .base_executor import BaseExecutor
from ..config import Config


class ShellExecutor(BaseExecutor):
    """
    Executor for running shell/bash commands
    """
    
    def __init__(self):
        super().__init__()
        self.config = Config()
    
    def execute(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute shell commands
        """
        if timeout is None:
            timeout = self.config.TIMEOUT_SECONDS
        
        try:
            # Execute the shell command
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable='/bin/bash'  # Use bash for broader compatibility
            )
            
            # Prepare result dictionary
            execution_result = {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "language": "shell"
            }
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "language": "shell"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "language": "shell"
            }
    
    def validate_syntax(self, code: str) -> bool:
        """
        Validate shell command syntax (basic validation)
        """
        # Basic check: ensure the command isn't empty
        return len(code.strip()) > 0
    
    def get_environment_info(self) -> Dict[str, str]:
        """
        Get shell environment information
        """
        import platform
        return {
            "shell": os.environ.get("SHELL", "/bin/sh"),
            "platform": platform.system(),
            "user": os.environ.get("USER", ""),
            "home_directory": os.environ.get("HOME", "")
        }