# EPITECH PROJECT, 2022
# Desktop_pet (Workspace)
# File description:
# __init__.py

from .sql_manager import SQL
from .sql_injection import SQLInjection

__all__ = [
    "SQLInjection",
    "SQL"
]
