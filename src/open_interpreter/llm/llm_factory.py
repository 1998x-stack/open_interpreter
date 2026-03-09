"""
LLMFactory: Registration and creation of LLM clients
"""

from typing import Dict, Type
from .base_llm import BaseLLMClient
from .openai_client import OpenAIClient


class LLMFactory:
    """
    Factory class for creating LLM clients
    """
    
    _clients: Dict[str, Type[BaseLLMClient]] = {}
    
    @classmethod
    def register(cls, name: str, client_class: Type[BaseLLMClient]):
        """
        Register an LLM client class
        """
        cls._clients[name.lower()] = client_class
    
    @classmethod
    def create(cls, model_name: str, **kwargs) -> BaseLLMClient:
        """
        Create an instance of an LLM client based on model name
        """
        # Determine client type based on model name
        model_name_lower = model_name.lower()
        
        # Register default clients if not already registered
        cls._register_defaults()
        
        # Determine which client to use based on model name
        if any(provider in model_name_lower for provider in ['gpt-', 'openai']):
            client_class = cls._clients.get('openai', OpenAIClient)
        elif any(provider in model_name_lower for provider in ['claude']):
            # Would need ClaudeClient if implemented
            raise NotImplementedError(f"Claude models not implemented yet: {model_name}")
        elif any(provider in model_name_lower for provider in ['gemini', 'vertex']):
            # Would need GeminiClient if implemented
            raise NotImplementedError(f"Gemini models not implemented yet: {model_name}")
        else:
            # Default to OpenAI client for unknown models
            client_class = cls._clients.get('openai', OpenAIClient)
        
        # Get config values
        from ..config import Config
        config = Config()
        
        return client_class(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            model=model_name,
            **kwargs
        )
    
    @classmethod
    def _register_defaults(cls):
        """
        Register default LLM clients
        """
        if not cls._clients:
            cls.register("openai", OpenAIClient)


# Register default clients on module load
LLMFactory._register_defaults()