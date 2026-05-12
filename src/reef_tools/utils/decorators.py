"""Decorator utilities — timing, caching, and function wrappers."""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def timer(func: F) -> F:
    """Decorator that prints the execution time of a function.

    Args:
        func: The function to time.

    Returns:
        The wrapped function that prints elapsed time on each call.

    Example:
        >>> @timer
        ... def slow_add(a, b):
        ...     return a + b
        >>> result = slow_add(1, 2)
        slow_add took ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result

    return wrapper  # type: ignore[return-value]


def cache_result(func: F) -> F:
    """Decorator that caches the result of a function based on its arguments.

    Uses `functools.lru_cache` with a max size of 128 entries.
    Suitable for pure functions with hashable arguments.

    Args:
        func: The function whose results should be cached.

    Returns:
        The wrapped function with LRU caching.

    Example:
        >>> @cache_result
        ... def expensive(n):
        ...     return n * 2
        >>> expensive(5)  # computed
        10
        >>> expensive(5)  # cached
        10
    """

    @functools.wraps(func)
    @functools.lru_cache(maxsize=128)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
