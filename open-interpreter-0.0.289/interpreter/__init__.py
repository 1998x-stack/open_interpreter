from .interpreter import Interpreter
import sys

# This is done so when users `import interpreter`,
# they get an instance of interpreter:

sys.modules["interpreter"] = Interpreter()


# Register default interpreters
try:
    from .factory import register_default_interpreters
    register_default_interpreters()
except ImportError:
    # If factory module is not available, continue without it
    pass
except Exception:
    # If registration fails, continue without it
    pass
# **This is a controversial thing to do,**
# because perhaps modules ought to behave like modules.

# But I think it saves a step, removes friction, and looks good.

#     ____                      ____      __                            __           
#    / __ \____  ___  ____     /  _/___  / /____  _________  ________  / /____  _____
#   / / / / __ \/ _ \/ __ \    / // __ \/ __/ _ \/ ___/ __ \/ ___/ _ \/ __/ _ \/ ___/
#  / /_/ / /_/ /  __/ / / /  _/ // / / / /_/  __/ /  / /_/ / /  /  __/ /_/  __/ /    
#  \____/ .___/\___/_/ /_/  /___/_/ /_/\__/\___/_/  / .___/_/   \___/\__/\___/_/     
#      /_/                                         /_/                               