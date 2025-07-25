"""Utility functions for handling callback configurations."""
import importlib
import warnings
import builtins
import sys
from typing import Any, Callable, Optional


def _add_srcdir_to_path(app) -> Optional[str]:
    """Add source directory to Python path if available."""
    if not (app and hasattr(app, 'srcdir')):
        return None

    srcdir = str(app.srcdir)
    if srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    return srcdir


def _resolve_module_function(module_path: str, function_name: str, app=None) -> Callable:
    """Resolve function from module.function_name format."""
    # Special handling for 'conf' module - add source directory to path
    if module_path == 'conf':
        _add_srcdir_to_path(app)

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Cannot import module '{module_path}': {e}")

    if not hasattr(module, function_name):
        raise AttributeError(f"Module '{module_path}' has no attribute '{function_name}'")

    return getattr(module, function_name)


def _get_builtin_function(function_name: str) -> Optional[Callable]:
    """Get function from builtins if it exists and is callable."""
    if not hasattr(builtins, function_name):
        return None

    builtin_func = getattr(builtins, function_name)
    return builtin_func if callable(builtin_func) else None


def _get_conf_function(function_name: str, app=None) -> Optional[Callable]:
    """Get function from conf module if available."""
    if not _add_srcdir_to_path(app):
        return None

    try:
        conf_module = importlib.import_module('conf')
        return getattr(conf_module, function_name) if hasattr(conf_module, function_name) else None
    except ImportError:
        return None


def _resolve_bare_function(function_name: str, app=None) -> Callable:
    """Resolve function from bare function name (check built-ins, then conf)."""
    # Check built-ins first
    builtin_func = _get_builtin_function(function_name)
    if builtin_func is not None:
        return builtin_func

    # Try conf module
    conf_func = _get_conf_function(function_name, app)
    if conf_func is not None:
        return conf_func

    # Function not found anywhere
    raise AttributeError(
        f"Function '{function_name}' not found in built-ins or conf.py. "
        f"Make sure the function is defined in conf.py or use 'module.function_name' format."
    )


def get_callback_function(callback_spec: Any, app=None) -> Optional[Callable]:
    """
    Convert a callback specification to a callable function.

    Args:
        callback_spec: Function specification - can be:
            - A callable function (backward compatibility)
            - A string with module.function_name format
            - A string with just function_name (searches built-ins, then conf.function_name)
        app: Sphinx application object (optional, for context)

    Returns:
        Callable function or None if not found

    Raises:
        ImportError: If the specified module cannot be imported
        AttributeError: If the specified function doesn't exist in the module
    """
    if callback_spec is None:
        return None

    # Handle direct function objects (backward compatibility)
    if callable(callback_spec):
        warnings.warn(
            "Using function objects in configuration is deprecated. "
            "Use string specifications instead (e.g., 'function_name')",
            DeprecationWarning,
            stacklevel=2
        )
        return callback_spec

    # Handle string specifications
    if not isinstance(callback_spec, str):
        raise TypeError(f"Invalid callback specification type: {type(callback_spec)}. Expected callable or string.")

    callback_spec = callback_spec.strip()
    if not callback_spec:
        return None

    # Handle module.function_name format (preferred)
    if '.' in callback_spec:
        module_path, function_name = callback_spec.rsplit('.', 1)
        return _resolve_module_function(module_path, function_name, app)

    # Handle function_name only
    return _resolve_bare_function(callback_spec, app)


def call_callback_function(callback_spec: Any, *args, app=None, **kwargs) -> Any:
    """
    Call a callback function with the given arguments.

    Args:
        callback_spec: Function specification (same as get_callback_function)
        *args: Positional arguments to pass to the callback
        app: Sphinx application object (optional)
        **kwargs: Keyword arguments to pass to the callback

    Returns:
        The return value of the callback function

    Raises:
        ImportError: If the specified module cannot be imported
        AttributeError: If the specified function doesn't exist
        TypeError: If callback_spec is not a valid type
    """
    callback_func = get_callback_function(callback_spec, app)
    if callback_func is None:
        return None
    return callback_func(*args, **kwargs)
