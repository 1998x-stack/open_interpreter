from abc import ABC, abstractmethod
from typing import Dict, Any

from loguru import logger


class BaseInterpreter(ABC):
    """
    Abstract base class for all interpreters.
    Defines the common interface that all interpreters must implement.
    """
    
    def __init__(self, language: str, **kwargs):
        self.language = language
        self.active_block = None
        logger.info(f"Initializing {self.__class__.__name__} for language: {language}")

    @abstractmethod
    def execute(self, code: str) -> str:
        """
        Execute the given code and return the output.
        
        Args:
            code (str): The code to execute
            
        Returns:
            str: The output from code execution
        """
        pass

    @abstractmethod
    def validate_code(self, code: str) -> bool:
        """
        Validate the code before execution.
        
        Args:
            code (str): The code to validate
            
        Returns:
            bool: True if code is valid, False otherwise
        """
        pass

    def set_active_block(self, block):
        """Set the active block for displaying output."""
        self.active_block = block
        logger.debug(f"Active block set for {self.language} interpreter")


class BaseFactory(ABC):
    """
    Abstract base class for interpreter factories.
    """
    
    _interpreters: Dict[str, Any] = {}

    @classmethod
    @abstractmethod
    def create(cls, language: str, **kwargs):
        """
        Create an interpreter instance for the given language.
        
        Args:
            language (str): The programming language
            **kwargs: Additional arguments for interpreter creation
            
        Returns:
            BaseInterpreter: An interpreter instance for the language
        """
        pass

    @classmethod
    def register(cls, language: str, interpreter_class):
        """
        Register an interpreter class for a language.
        
        Args:
            language (str): The programming language
            interpreter_class: The interpreter class to register
        """
        cls._interpreters[language] = interpreter_class
        logger.info(f"Registered {interpreter_class.__name__} for language: {language}")

    @classmethod
    def get_registered_languages(cls):
        """
        Get all registered language interpreters.
        
        Returns:
            list: List of registered language names
        """
        return list(cls._interpreters.keys())