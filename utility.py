from typing import Any, List, Optional
from datetime import datetime
import logging
import io
import sys
import os

def is_number(value: Any) -> bool:
    return isinstance(value, (int, float))

def is_none(value: Any) -> bool:
    return value is None

def is_array(value: Any) -> bool:
    return isinstance(value, List)

def is_string(value: Any) -> bool:
    return isinstance(value, str)

def safe_get(record: list, index: int, default: str = "") -> str:
    """Safely get an item from a list at a given index"""
    try:
        return record[index] if index < len(record) else default
    except (IndexError, TypeError):
        return default

def parse_datetime(date_str: str) -> Optional[str]:
    """Parse ASTM datetime format (YYYYMMDDHHMMSS) to ISO format"""
    if not date_str or len(date_str) < 8:
        return None
    try:
        if len(date_str) == 8:
            dt = datetime.strptime(date_str, "%Y%m%d")
        elif len(date_str) == 14:
            dt = datetime.strptime(date_str, "%Y%m%d%H%M%S")
        else:
            return date_str
        return dt.isoformat()
    except ValueError:
        return date_str

def get_relative_path(file_path: str, base_path: str) -> str:
    relative_path = os.path.relpath(file_path, base_path)
    filename = os.path.basename(relative_path)
    return filename

def setup_logger(
    file_path: str,
    log_file: str,
    level: int = logging.INFO,
    format_string: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    console_output: bool = True,
    separate_levels: bool = True,
    base_path: str = None
) -> logging.Logger:
    """
    Setup a logger with file and optional console output.
    The logger's name will be the relative file name, like Dispatcher.py.

    Args:
        file_path: Absolute path of the source file (e.g. __file__)
        log_file: Base log file name
        level: Logging level
        format_string: Log format
        console_output: Whether to output to console
        separate_levels: Whether to create separate files for each level
        base_path: Base dir to trim off for logger name (default: current working directory)

    Returns:
        Configured logger
    """
    if base_path is None:
        base_path = os.getcwd()
    
    # Get the logger name from the relative file name
    logger_name = get_relative_path(file_path, base_path)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    formatter = logging.Formatter(format_string)
    
    if separate_levels:
        # Create separate files for each level
        levels = {
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'DEBUG': logging.DEBUG
        }
        
        for level_name, level_num in levels.items():
            level_file = log_file.replace('.log', f'_{level_name.lower()}.log')
            handler = logging.FileHandler(level_file, mode='a')
            handler.setLevel(level_num)
            handler.setFormatter(formatter)
            
            # Filter only specific level logs
            if level_name in ['INFO', 'WARNING']:
                handler.addFilter(lambda record, lvl=level_num: record.levelno == lvl)
            else:
                handler.addFilter(lambda record, lvl=level_num: record.levelno >= lvl)
            
            logger.addHandler(handler)
    else:
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def log_to_file(data, folder_path, filename):
    """
    Logs `data` to a file in the specified `folder_path`.
    If `filename` is not provided, it uses a timestamp-based default.
    """
    
    os.makedirs(folder_path, exist_ok=True)
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"log_{timestamp}.txt"

    file_path = os.path.join(folder_path, filename)

    with io.open(file_path, mode='a', encoding='utf-8') as file:
        file.write(data)
        if not data.endswith('\n'):
            file.write('\n')
    return file_path