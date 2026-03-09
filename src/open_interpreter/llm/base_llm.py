"""
Abstract base class BaseLLMClient
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM clients
    """
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM
        """
        pass
    
    @abstractmethod
    def stream_response(self, prompt: str, **kwargs):
        """
        Stream a response from the LLM
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model
        """
        pass