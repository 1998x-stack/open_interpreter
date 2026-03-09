"""
PythonExecutor: Python subprocess executor
"""

import subprocess
import tempfile
import os
import sys
from typing import Dict, Any, Optional
from .base_executor import BaseExecutor
from ..config import Config


class PythonExecutor(BaseExecutor):
    """
    Executor for running Python code in a subprocess
    """
    
    def __init__(self):
        super().__init__()
        self.config = Config()
    
    def execute(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute Python code in a subprocess
        """
        if timeout is None:
            timeout = self.config.TIMEOUT_SECONDS
        
        # Create a temporary file to hold the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute the code in a subprocess
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Prepare result dictionary
            execution_result = {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "language": "python"
            }
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "language": "python"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "language": "python"
            }
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass  # Ignore errors when cleaning up
    
    def validate_syntax(self, code: str) -> bool:
        """
        Validate Python code syntax
        """
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def get_environment_info(self) -> Dict[str, str]:
        """
        Get Python environment information
        """
        return {
            "version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform
        }