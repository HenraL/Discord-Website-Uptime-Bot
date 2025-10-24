"""Package entrypoint for the Discord bot application.

Allows starting the program by calling the package directory with
``python -m`` or by running this module directly.
"""
import sys
try:
    from .code_logic import Main, program_globals
except ImportError:
    from code_logic import Main, program_globals

if __name__ == "__main__":
    DEBUG: bool = program_globals.HLP.check_input_args()
    MI = Main(debug=DEBUG)
    sys.exit(MI.main())
