import time
import functools
import inspect

def trace_method(func):
    """Decorator to trace a single function/method."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        
        # Format arguments for logging (truncate long strings/lists)
        args_repr = []
        for a in args[1:]: # Skip 'self'
            s = repr(a)
            args_repr.append(s if len(s) < 50 else s[:47] + "...")
        
        func_name = f"{func.__qualname__}"
        print(f"DEBUG: >>> ENTERing {func_name}({', '.join(args_repr)})")
        
        try:
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            print(f"DEBUG: <<< EXITing  {func_name} | {duration:.2f}ms")
            return result
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            print(f"DEBUG: !!! ERROR in {func_name} | {duration:.2f}ms | {type(e).__name__}: {e}")
            raise e
            
    return wrapper

def trace_class_methods(cls):
    """Class decorator to apply trace_method to all methods of a class."""
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        # Don't trace dunder methods except __init__
        if name.startswith("__") and name != "__init__":
            continue
        setattr(cls, name, trace_method(method))
    return cls
