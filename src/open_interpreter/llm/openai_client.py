"""
OpenAIClient: OpenAI/compatible API client
"""

import requests
from typing import Dict, Any, Generator
from .base_llm import BaseLLMClient
from ..config import Config


class OpenAIClient(BaseLLMClient):
    """
    OpenAI-compatible API client for generating responses
    """
    
    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        super().__init__(api_key, base_url, model)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from the OpenAI API
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            return f"Error communicating with LLM API: {str(e)}"
        except KeyError:
            return f"Unexpected response format from LLM API: {response.text}"
    
    def stream_response(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Stream a response from the OpenAI API
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "stream": True
        }
        
        try:
            with self.session.post(url, json=payload, stream=True) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data = line_str[6:]  # Remove 'data: ' prefix
                            if data != '[DONE]':
                                try:
                                    import json
                                    chunk = json.loads(data)
                                    content = chunk['choices'][0]['delta'].get('content', '')
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
        except requests.exceptions.RequestException as e:
            yield f"Error streaming from LLM API: {str(e)}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model
        """
        return {
            "model": self.model,
            "api_base": self.base_url,
            "provider": "OpenAI-compatible"
        }