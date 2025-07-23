"""Utility functions for handling callback configurations."""
import importlib
import warnings
import builtins
import sys
from typing import Any, Callable, Optional


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
    if isinstance(callback_spec, str):
        callback_spec = callback_spec.strip()
        if not callback_spec:
            return None

        # Handle module.function_name format (preferred)
        if '.' in callback_spec:
            module_path, function_name = callback_spec.rsplit('.', 1)
            try:
                # Special handling for 'conf' module - add source directory to path
                if module_path == 'conf' and app and hasattr(app, 'srcdir'):
                    srcdir = str(app.srcdir)
                    if srcdir not in sys.path:
                        sys.path.insert(0, srcdir)

                module = importlib.import_module(module_path)
                if hasattr(module, function_name):
                    return getattr(module, function_name)
                else:
                    raise AttributeError(f"Module '{module_path}' has no attribute '{function_name}'")
            except ImportError as e:
                raise ImportError(f"Cannot import module '{module_path}': {e}")

        # Handle function_name only - check built-ins first, then conf module
        else:
            function_name = callback_spec

            # Check built-ins first
            if hasattr(builtins, function_name):
                builtin_func = getattr(builtins, function_name)
                if callable(builtin_func):
                    return builtin_func

            # If not found in built-ins, try conf.function_name automatically
            if app and hasattr(app, 'srcdir'):
                try:
                    # Add source directory to path for conf module
                    srcdir = str(app.srcdir)
                    if srcdir not in sys.path:
                        sys.path.insert(0, srcdir)

                    # Try to import from conf module
                    conf_module = importlib.import_module('conf')
                    if hasattr(conf_module, function_name):
                        return getattr(conf_module, function_name)
                except ImportError:
                    pass

            # Function not found anywhere
            raise AttributeError(
                f"Function '{function_name}' not found in built-ins or conf.py. "
                f"Make sure the function is defined in conf.py or use 'module.function_name' format."
            )

    # Invalid specification type
    raise TypeError(f"Invalid callback specification type: {type(callback_spec)}. Expected callable or string.")


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
