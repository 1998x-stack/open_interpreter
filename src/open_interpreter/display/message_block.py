"""
MessageBlock: Markdown message panel
"""

from .base_block import BaseBlock
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class MessageBlock(BaseBlock):
    """
    MessageBlock component for displaying Markdown messages
    """
    
    def __init__(self):
        super().__init__()
        self.console = Console()
    
    def display(self, message: str, sender: str = "assistant", **kwargs):
        """
        Display a message in Markdown format
        """
        # Handle text that isn't Markdown properly
        if not self._looks_like_markdown(message):
            # Create simple text panel
            text_content = Text(message)
            panel = Panel(text_content, title=f"{sender} Message", 
                         border_style="green")
        else:
            # Process as Markdown
            markdown = Markdown(message)
            panel = Panel(markdown, title=f"{sender} Message", 
                         border_style="green")
        
        self.console.print(panel)
    
    def update(self, content: str, **kwargs):
        """
        Update the displayed message
        """
        # For now, just redisplay
        self.display(content, **kwargs)
    
    def clear(self):
        """
        Clear the message block display
        """
        self.console.clear()
    
    def _looks_like_markdown(self, text: str) -> bool:
        """
        Simple heuristic to determine if text looks like Markdown
        """
        markdown_indicators = [
            '# ', '## ', '### ',  # Headers
            '* ', '- ',  # Lists
            '**',  # Bold
            '*',  # Italic
            '`',  # Code
            '> ',  # Blockquotes
        ]
        
        return any(indicator in text for indicator in markdown_indicators)