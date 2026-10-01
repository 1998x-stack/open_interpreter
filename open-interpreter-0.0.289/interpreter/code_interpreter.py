import subprocess
import threading
import traceback
import platform
import time
import ast
import astor
import sys
import os

from loguru import logger

# Mapping of languages to their start and print commands
language_map = {
  "python": {
    # Python is run from this interpreter with sys.executable
    # in interactive, quiet, and unbuffered mode
    "start_cmd": sys.executable + " -i -q -u",
    "print_cmd": 'print("{}")'
  },
  "shell": {
    # On Windows, the shell start command is `cmd.exe`
    # On Unix, it should be the SHELL environment variable (defaults to 'bash' if not set)
    "start_cmd": 'cmd.exe' if platform.system() == 'Windows' else os.environ.get('SHELL', 'bash'),
    "print_cmd": 'echo "{}"'
  },
  "javascript": {
    "start_cmd": "node -i",
    "print_cmd": 'console.log("{}")'
  },
  "applescript": {
    "start_cmd": "osascript",
    "print_cmd": 'log "{}"'
  }
}

# Get forbidden_commands (disabled)
"""
with open("interpreter/forbidden_commands.json", "r") as f:
  forbidden_commands = json.load(f)
"""


from .base import BaseInterpreter

class CodeInterpreter(BaseInterpreter):
  def __init__(self, language, debug_mode=None, **kwargs):
    super().__init__(language, **kwargs)
    self.language = language
    self.proc = None
    self.active_line = None
    # Handle both old interface (positional) and new interface (keyword)
    if debug_mode is None:
      debug_mode = kwargs.get('debug_mode', False)
    self.debug_mode = debug_mode
    logger.info(f"Initialized CodeInterpreter for language: {language}")

  def start_process(self):
    logger.debug(f"Starting process for language: {self.language}")
    # Get the start_cmd for the selected language
    start_cmd = language_map[self.language]["start_cmd"]

    # Use the appropriate start_cmd to execute the code
    self.proc = subprocess.Popen(start_cmd.split(),
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 text=True)

    # Start watching ^ its `stdout` and `stderr` streams
    threading.Thread(target=self.save_and_display_stream,
                     args=(self.proc.stdout, ),
                     daemon=True).start()
    threading.Thread(target=self.save_and_display_stream,
                     args=(self.proc.stderr, ),
                     daemon=True).start()

  def update_active_block(self):
      """
      This will also truncate the output,
      which we need to do every time we update the active block.
      """
      # Strip then truncate the output if necessary
      self.output = truncate_output(self.output)
  
      # Display it
      self.active_block.active_line = self.active_line
      self.active_block.output = self.output
      self.active_block.refresh()

  def run(self):
    logger.info(f"Running code in {self.language}")
    """
    Executes code.
    """

    # Get code to execute
    self.code = self.active_block.code

    # Check for forbidden commands (disabled)
    """
    for line in self.code.split("\n"):
      if line in forbidden_commands:
        message = f"This code contains a forbidden command: {line}"
        message += "\n\nPlease contact the Open Interpreter team if this is an error."
        self.active_block.output = message
        return message
    """

    # Start the subprocess if it hasn't been started
    try:
      if not self.proc:
        self.start_process()
    except:
      # Sometimes start_process will fail!
      # Like if they don't have `node` installed or something.
      
      traceback_string = traceback.format_exc()
      self.output = traceback_string
      self.update_active_block()

      # Before you return, wait for the display to catch up?
      # (I'm not sure why this works)
      time.sleep(0.1)

      return self.output

    # Reset output
    self.output = ""

    # Use the print_cmd for the selected language
    self.print_cmd = language_map[self.language]["print_cmd"]
    code = self.code

    # Add print commands that tell us what the active line is
    code = self.add_active_line_prints(code)

    # If it's Python, we also need to normalize
    # and fix indentation (so it works with `python -i`)
    if self.language == "python":

      # Normalize code by parsing then unparsing it
      try:
        parsed_ast = ast.parse(code)
        code = astor.to_source(parsed_ast)
      except:
        # If this failed, it means the code didn't compile
        # This traceback will be our output.
        
        traceback_string = traceback.format_exc()
        self.output = traceback_string
        self.update_active_block()

        # Before you return, wait for the display to catch up?
        # (I'm not sure why this works)
        time.sleep(0.1)

        return self.output
        
      code = fix_code_indentation(code)

    # Remove any whitespace lines, as this will break indented blocks
    code_lines = code.split("\n")
    code_lines = [c for c in code_lines if c.strip() != ""]
    code = "\n".join(code_lines)

    # Add end command (we'll be listening for this so we know when it ends)
    code += "\n\n" + self.print_cmd.format('END_OF_EXECUTION') + "\n"

    # Debug and logging
    if self.debug_mode:
      logger.debug("Running code:")
      logger.debug(code)
      print("Running code:")
      print(code)
      print("---")
    else:
      logger.debug(f"Executing {len(code.split(chr(10)))} lines of {self.language} code")

    # Reset self.done so we can .wait() for it
    self.done = threading.Event()
    self.done.clear()

    # Write code to stdin of the process
    try:
      self.proc.stdin.write(code)
      self.proc.stdin.flush()
    except BrokenPipeError:
      # It can just.. break sometimes? Let's fix this better in the future
      # For now, just try again
      self.start_process()
      self.run()
      return

    # Wait until execution completes
    self.done.wait()

    # Before you return, wait for the display to catch up?
    # (I'm not sure why this works)
    time.sleep(0.1)

    # Return code output
    return self.output


  def execute(self, code: str) -> str:
    """
    Execute the given code and return the output.
    This method implements the abstract method from BaseInterpreter.
    """
    # Store the code in the active block temporarily
    if self.active_block:
      original_code = getattr(self.active_block, 'code', None)
      self.active_block.code = code
      
      # Execute using the existing run method
      try:
        result = self.run()
      finally:
        # Restore original code if it existed
        if original_code is not None:
          self.active_block.code = original_code
        elif hasattr(self.active_block, 'code'):
          delattr(self.active_block, 'code')
      
      return result
    else:
      # If no active block, execute directly using subprocess
      logger.warning("No active block set, executing code directly")
      return self._execute_directly(code)

  def _execute_directly(self, code: str) -> str:
    """Execute code directly without active block."""
    import subprocess
    import sys
    
    # Get the appropriate start command based on language
    start_cmd = language_map[self.language]['start_cmd']
    
    # For Python, execute the code directly
    if self.language == 'python':
      try:
        result = subprocess.run([sys.executable, '-c', code], 
                                capture_output=True, text=True, timeout=30)
        output = result.stdout
        if result.stderr:
          output += f"\nSTDERR: {result.stderr}"
        return output
      except subprocess.TimeoutExpired:
        return "ERROR: Code execution timed out"
      except Exception as e:
        return f"ERROR: {str(e)}"
    else:
      # For other languages, use the start command
      try:
        parts = start_cmd.split()
        if self.language == 'shell':
          # For shell, execute the code as a command
          result = subprocess.run(code, shell=True, 
                                  capture_output=True, text=True, timeout=30)
        else:
          # For others like javascript, applescript, create appropriate execution
          if self.language == 'javascript':
            result = subprocess.run(['node', '-e', code], 
                                    capture_output=True, text=True, timeout=30)
          elif self.language == 'applescript':
            result = subprocess.run(['osascript', '-e', code], 
                                    capture_output=True, text=True, timeout=30)
          else:
            # Default: try to execute as shell command
            result = subprocess.run(code, shell=True, 
                                    capture_output=True, text=True, timeout=30)
        
        output = result.stdout
        if result.stderr:
          output += f"\nSTDERR: {result.stderr}"
        return output
      except Exception as e:
        return f"ERROR: {str(e)}"

  def validate_code(self, code: str) -> bool:
    """
    Validate the code before execution.
    This method implements the abstract method from BaseInterpreter.
    """
    # Basic validation - check if code is not empty
    if not code or not code.strip():
        logger.warning("Code validation failed: empty code")
        return False
    
    # Check for dangerous patterns (basic check)
    dangerous_patterns = ["rm -rf", "sudo rm", "format", "del /s"]
    for pattern in dangerous_patterns:
        if pattern in code.lower():
            logger.warning(f"Dangerous command detected: {pattern}")
            return False
            
    logger.debug("Code validation passed")
    return True
  def add_active_line_prints(self, code):
    """
    This function takes a code snippet and adds print statements before each line,
    indicating the active line number during execution. The print statements respect
    the indentation of the original code, using the indentation of the next non-blank line.

    Note: This doesn't work on shell if:
    1) Any line starts with whitespace and
    2) Sometimes, doesn't even work for regular loops with newlines between lines
    We return in those cases.
    3) It really struggles with multiline stuff, so I've disabled that (but we really should fix and restore).

    In python it doesn't work if:
    1) Try/Except clause
    2) Triple quote multiline strings
    """

    # Split the original code into lines
    code_lines = code.strip().split('\n')

    # If it's shell, check for breaking cases
    if self.language == "shell":
      if len(code_lines) > 1:
        return code
      if "for" in code or "do" in code or "done" in code:
        return code
      for line in code_lines:
        if line.startswith(" "):
          return code

    # If it's Python, check for breaking cases
    if self.language == "python":
      if "try" in code or "except" in code or "'''" in code or "'''" in code or "[\n" in code or "{\n" in code:
        return code

    # Initialize an empty list to hold the modified lines of code
    modified_code_lines = []

    # Iterate over each line in the original code
    for i, line in enumerate(code_lines):
      # Initialize a variable to hold the leading whitespace of the next non-empty line
      leading_whitespace = ""

      # Iterate over the remaining lines to find the leading whitespace of the next non-empty line
      for next_line in code_lines[i:]:
        if next_line.strip():
          leading_whitespace = next_line[:len(next_line) -
                                         len(next_line.lstrip())]
          break

      # Format the print command with the current line number, using the found leading whitespace
      print_line = self.print_cmd.format(f"ACTIVE_LINE:{i+1}")
      print_line = leading_whitespace + print_line

      # Add the print command and the original line to the modified lines
      modified_code_lines.append(print_line)
      modified_code_lines.append(line)

    # Join the modified lines with newlines and return the result
    code = "\n".join(modified_code_lines)
    return code

  def save_and_display_stream(self, stream):
    # Handle each line of output
    for line in iter(stream.readline, ''):

      if self.debug_mode:
        logger.debug("Received output line:")
        logger.debug(line)
        print("Recieved output line:")
        print(line)
        print("---")
      else:
        logger.debug(f"Output line: {line}")
      
      line = line.strip()

      # Check if it's a message we added (like ACTIVE_LINE)
      # Or if we should save it to self.output
      if line.startswith("ACTIVE_LINE:"):
        self.active_line = int(line.split(":")[1])
      elif line == "END_OF_EXECUTION":
        self.done.set()
        self.active_line = None
      elif "KeyboardInterrupt" in line:
        raise KeyboardInterrupt
      else:
        self.output += "\n" + line
        self.output = self.output.strip()

      self.update_active_block()

def fix_code_indentation(code):
  lines = code.split("\n")
  fixed_lines = []
  was_indented = False
  for line in lines:
    current_indent = len(line) - len(line.lstrip())
    if current_indent == 0 and was_indented:
      fixed_lines.append('')  # Add an empty line after an indented block
    fixed_lines.append(line)
    was_indented = current_indent > 0

  return "\n".join(fixed_lines)


def truncate_output(data):

  # In the future, this will come from a config file
  max_output_chars = 2000

  message = f'Output truncated. Showing the last {max_output_chars} characters.\n\n'

  # Remove previous truncation message if it exists
  if data.startswith(message):
    data = data[len(message):]

  # If data exceeds max length, truncate it and add message
  if len(data) > max_output_chars:
    data = message + data[-max_output_chars:]

  return data
