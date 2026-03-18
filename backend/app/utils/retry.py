"""
API call retry utilities.
Provides exponential backoff retry logic for LLM and external API calls.
"""

import time
import random
import functools
from typing import Callable, Any, Optional, Type, Tuple
from..utils.logger import get_logger

logger = get_logger('phoring.retry')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception],...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """Decorator for retrying a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        backoff_factor: Multiplier applied to delay after each attempt.
        jitter: Whether to add random jitter to the delay.
        exceptions: Exception types to catch and retry on.
        on_retry: Optional callback invoked on each retry (exception, attempt_number).

    Usage:
        @retry_with_backoff(max_retries=3)
        def call_llm_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise

                    current_delay = min(delay, max_delay)
                    if jitter:
                        current_delay = current_delay * (0.5 + random.random())

                    logger.warning(
                        f"Function {func.__name__} attempt {attempt + 1} failed: {str(e)}, "
                        f"retrying in {current_delay:.1f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt + 1)

                    time.sleep(current_delay)
                    delay *= backoff_factor

            raise last_exception

        return wrapper
    return decorator


