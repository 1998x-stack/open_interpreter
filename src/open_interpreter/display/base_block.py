"""
Abstract base class BaseBlock
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseBlock(ABC):
    """
    Abstract base class for all display blocks
    """
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def display(self, content: Any, **kwargs):
        """
        Abstract method to display content
        """
        pass
    
    @abstractmethod
    def update(self, content: Any, **kwargs):
        """
        Abstract method to update displayed content
        """
        pass
    
    @abstractmethod
    def clear(self):
        """
        Abstract method to clear the display
        """
        pass