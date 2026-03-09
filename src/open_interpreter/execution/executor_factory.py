"""
ExecutorFactory: Registration and creation of executors
"""

from typing import Dict, Type
from .base_executor import BaseExecutor
from .python_executor import PythonExecutor
from .shell_executor import ShellExecutor
from .javascript_executor import JavascriptExecutor


class ExecutorFactory:
    """
    Factory class for creating executors
    """
    
    _executors: Dict[str, Type[BaseExecutor]] = {}
    
    @classmethod
    def register(cls, name: str, executor_class: Type[BaseExecutor]):
        """
        Register an executor class
        """
        cls._executors[name.lower()] = executor_class
    
    @classmethod
    def create(cls, name: str) -> BaseExecutor:
        """
        Create an instance of an executor
        """
        name = name.lower()
        if name not in cls._executors:
            # Auto-register default executors if not already registered
            cls._register_defaults()
            
            if name not in cls._executors:
                raise ValueError(f"Unknown executor type: {name}")
        
        return cls._executors[name]()
    
    @classmethod
    def _register_defaults(cls):
        """
        Register default executors
        """
        if not cls._executors:
            cls.register("python", PythonExecutor)
            cls.register("shell", ShellExecutor)
            cls.register("bash", ShellExecutor)  # alias
            cls.register("javascript", JavascriptExecutor)
            cls.register("js", JavascriptExecutor)  # alias


# Register default executors on module load
ExecutorFactory._register_defaults()