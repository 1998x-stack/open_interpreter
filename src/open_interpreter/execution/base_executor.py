"""
Abstract base class BaseExecutor
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseExecutor(ABC):
    """
    Abstract base class for all executors
    """
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def execute(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute code and return results
        """
        pass
    
    @abstractmethod
    def validate_syntax(self, code: str) -> bool:
        """
        Validate code syntax
        """
        pass
    
    @abstractmethod
    def get_environment_info(self) -> Dict[str, str]:
        """
        Get information about the execution environment
        """
        pass