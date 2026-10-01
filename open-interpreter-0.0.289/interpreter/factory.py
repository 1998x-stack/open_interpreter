from typing import Dict, Type
from .base import BaseInterpreter, BaseFactory
from .code_interpreter import CodeInterpreter
from loguru import logger


class InterpreterFactory(BaseFactory):
    """
    Factory class to create interpreter instances.
    """
    
    @classmethod
    def create(cls, language: str, **kwargs) -> BaseInterpreter:
        """
        Create an interpreter instance for the given language.
        
        Args:
            language (str): The programming language
            **kwargs: Additional arguments for interpreter creation
            
        Returns:
            BaseInterpreter: An interpreter instance for the language
        """
        if language not in cls._interpreters:
            # Default to CodeInterpreter for backward compatibility
            logger.warning(f"Language {language} not registered, falling back to CodeInterpreter")
            debug_mode = kwargs.get('debug_mode', False)
            # Create CodeInterpreter with the proper interface
            ci = CodeInterpreter(language, debug_mode=debug_mode)
            return ci
        interpreter_class = cls._interpreters[language]
        logger.info(f"Creating interpreter for language: {language}")
        return interpreter_class(language, **kwargs)


def register_default_interpreters():
    """
    Register default interpreters for supported languages.
    This maintains backward compatibility with the original implementation.
    """
    try:
        from .python_interpreter import PythonInterpreter
        from .shell_interpreter import ShellInterpreter
        from .javascript_interpreter import JavaScriptInterpreter
        from .applescript_interpreter import AppleScriptInterpreter
        
        # Register specific interpreters
        InterpreterFactory.register('python', PythonInterpreter)
        InterpreterFactory.register('shell', ShellInterpreter)
        InterpreterFactory.register('javascript', JavaScriptInterpreter)
        InterpreterFactory.register('applescript', AppleScriptInterpreter)
        
        logger.info("Registered specific interpreters for all supported languages")
    except ImportError:
        # If individual interpreters are not available, use the base CodeInterpreter
        # This maintains backward compatibility
        from .code_interpreter import CodeInterpreter
        InterpreterFactory.register('python', CodeInterpreter)
        InterpreterFactory.register('shell', CodeInterpreter)
        InterpreterFactory.register('javascript', CodeInterpreter)
        InterpreterFactory.register('applescript', CodeInterpreter)
        
        logger.info("Using CodeInterpreter as fallback for all languages")