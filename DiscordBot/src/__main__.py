"""Package entrypoint for the Discord bot application.

Allows starting the program by calling the package directory with
``python -m`` or by running this module directly.
"""
try:
    from .code_logic import start_wrapper
except ImportError:
    from code_logic import start_wrapper

if __name__ == "__main__":
    start_wrapper()
