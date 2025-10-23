""" File in charge of allowing the users to start the program by calling the folder with python.
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
