"""
Main orchestrator - Interpreter class
"""

from typing import Dict, Any, Optional
from .config import Config
from .llm.llm_factory import LLMFactory
from .execution.executor_factory import ExecutorFactory
from .display.code_block import CodeBlock
from .display.message_block import MessageBlock


class Interpreter:
    """
    Main interpreter class that orchestrates LLM communication, 
    code execution, and display management.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.config.validate()
        
        # Initialize components
        self.llm = LLMFactory.create(self.config.MODEL)
        self.executor = ExecutorFactory.create("python")  # default executor
        
        # Display components
        self.message_block = MessageBlock()
        self.code_block = CodeBlock()
    
    def chat(self, user_input: str) -> str:
        """
        Main chat method - handles user input and returns response
        """
        # Show user message
        self.message_block.display(user_input, sender="user")
        
        # Get response from LLM
        llm_response = self._get_llm_response(user_input)
        
        # Process the response (could contain code to execute)
        processed_response = self._process_response(llm_response)
        
        return processed_response
    
    def _get_llm_response(self, user_input: str) -> str:
        """
        Get response from the LLM
        """
        # This is a simplified implementation
        # In reality, this would involve a conversation with the LLM
        return self.llm.generate_response(user_input)
    
    def _process_response(self, response: str) -> str:
        """
        Process the LLM response, potentially executing code
        """
        # Placeholder implementation - in a real scenario, 
        # this would parse the response for executable code blocks
        return response
    
    def switch_executor(self, executor_type: str):
        """
        Switch to a different code executor
        """
        self.executor = ExecutorFactory.create(executor_type)
    
    def run_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Execute code in the specified language
        """
        executor = ExecutorFactory.create(language)
        return executor.execute(code)