"""
JavascriptExecutor: Node.js executor
"""

import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from .base_executor import BaseExecutor
from ..config import Config


class JavascriptExecutor(BaseExecutor):
    """
    Executor for running JavaScript code with Node.js
    """
    
    def __init__(self):
        super().__init__()
        self.config = Config()
    
    def execute(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute JavaScript code with Node.js
        """
        if timeout is None:
            timeout = self.config.TIMEOUT_SECONDS
        
        # Create a temporary file to hold the JS code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute the JS code with Node.js
            result = subprocess.run(
                ["node", temp_file],
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
                "language": "javascript"
            }
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "language": "javascript"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": "Node.js is not installed or not in PATH",
                "language": "javascript"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "language": "javascript"
            }
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass  # Ignore errors when cleaning up
    
    def validate_syntax(self, code: str) -> bool:
        """
        Validate JavaScript code syntax by attempting to parse it
        """
        # Create a temporary file to check syntax
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            # Wrap code in a function to catch more syntax errors
            f.write("(function(){\n" + code + "\n})();")
            temp_file = f.name
        
        try:
            # Try to run the code with Node.js in check mode
            result = subprocess.run(
                ["node", "--check", temp_file],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    def get_environment_info(self) -> Dict[str, str]:
        """
        Get JavaScript/Node.js environment information
        """
        try:
            node_version = subprocess.check_output(["node", "--version"], text=True).strip()
        except:
            node_version = "Node.js not available"
        
        return {
            "node_version": node_version,
            "language": "javascript"
        }