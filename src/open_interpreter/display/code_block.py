"""
CodeBlock: Code + Output panel
"""

from .base_block import BaseBlock
from ..utils.output_utils import truncate_output, fix_code_indentation
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


class CodeBlock(BaseBlock):
    """
    CodeBlock component for displaying code and its output
    """
    
    def __init__(self):
        super().__init__()
        self.console = Console()
    
    def display(self, code: str, output: str = "", language: str = "python", 
                sender: str = "assistant", **kwargs):
        """
        Display code and its output in a formatted panel
        """
        # Fix code indentation
        formatted_code = fix_code_indentation(code)
        
        # Create syntax-highlighted code panel
        syntax = Syntax(formatted_code, language, theme="monokai", 
                        line_numbers=True, word_wrap=True)
        
        # Truncate output if too long
        truncated_output = truncate_output(output, max_length=1000)
        
        # Create panel with code and output
        if output:
            content = f"[bold]{sender}[/bold]\n\n[bold]Code:[/bold]\n"
            content += syntax.plain + f"\n\n[bold]Output:[/bold]\n{truncated_output}"
        else:
            content = f"[bold]{sender}[/bold]\n\n[bold]Code:[/bold]\n"
            content += syntax.plain
        
        panel = Panel(content, title="Code Block", border_style="blue")
        self.console.print(panel)
    
    def update(self, content: str, **kwargs):
        """
        Update the displayed code block
        """
        # For now, just redisplay
        self.display(content, **kwargs)
    
    def clear(self):
        """
        Clear the code block display
        """
        self.console.clear()