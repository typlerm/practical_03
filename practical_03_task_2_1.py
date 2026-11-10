"""Декоратори функцій з параметрами."""

import functools
import time


def cache(max_size: int = 128, verbose: bool = False):
    """Декоратор кешування результатів функції (спрощений LRU-кеш).

    Args:
        max_size: максимальна кількість закешованих результатів.
        verbose: якщо True — друкувати "cache hit"/"cache miss" при кожному виклику.
    """
    def decorator(func):
        _cache = {}
        _call_order = []  # від найстарішого до найновішого використання
        stats = {"hits": 0, "misses": 0}

        @functools.wraps(func)
        def wrapper(*args):
            if args in _cache:
                stats["hits"] += 1
                _call_order.remove(args)   # LRU: оновлюємо "свіжість" запису
                _call_order.append(args)
                if verbose:
                    print(f"  [cache hit]  {func.__name__}{args}")
                return _cache[args]

            stats["misses"] += 1
            if verbose:
                print(f"  [cache miss] {func.__name__}{args}")
            result = func(*args)
            _cache[args] = result
            _call_order.append(args)
            if len(_cache) > max_size:
                oldest = _call_order.pop(0)
                del _cache[oldest]
            return result

        wrapper.cache_info = lambda: {
            "size": len(_cache), "max_size": max_size,
            "hits": stats["hits"], "misses": stats["misses"],
        }
        wrapper.cache_clear = lambda: (
            _cache.clear(), _call_order.clear(), stats.update(hits=0, misses=0)
        )
        return wrapper
    return decorator


def rate_limit(max_calls: int, period: float = 60.0):
    """Декоратор обмеження частоти викликів функції.

    Args:
        max_calls: максимальна кількість викликів за період.
        period: тривалість періоду в секундах.
    """
    def decorator(func):
        call_times: list[float] = []

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.monotonic()
            # Прибираємо записи, старші за period секунд
            while call_times and now - call_times[0] >= period:
                call_times.pop(0)
            if len(call_times) >= max_calls:
                wait = period - (now - call_times[0])
                raise RuntimeError(
                    f"Перевищено ліміт {max_calls} викликів за {period} с "
                    f"для '{func.__name__}'. Спробуйте через {wait:.1f} с"
                )
            call_times.append(now)
            return func(*args, **kwargs)

        return wrapper
    return decorator


def log(level: str = "INFO"):
    """Декоратор логування виклику функції з зазначенням рівня.

    Args:
        level: рівень логування (DEBUG, INFO, WARNING, ERROR).
    """
    level = level.upper()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            parts = [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
            print(f"[{level}] Виклик {func.__name__}({', '.join(parts)})")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                elapsed = time.perf_counter() - start
                print(f"[ERROR] {func.__name__} → {type(e).__name__}: {e} "
                      f"(час: {elapsed:.4f}с)")
                raise
            elapsed = time.perf_counter() - start
            print(f"[{level}] {func.__name__} → {result!r} (час: {elapsed:.4f}с)")
            return result

        return wrapper
    return decorator


@cache(max_size=64)
def fibonacci(n: int) -> int:
    """Обчислює n-е число Фібоначчі рекурсивно."""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


@cache(max_size=2, verbose=True)
def square(n: int) -> int:
    """Квадрат числа (демонстрація hit/miss та витіснення з кешу)."""
    return n * n


@rate_limit(max_calls=5, period=10.0)
def send_notification(message: str) -> str:
    """Імітує відправку сповіщення."""
    return f"Надіслано: {message}"


@log(level="DEBUG")
def divide(a: float, b: float) -> float:
    """Ділення з можливим ZeroDivisionError."""
    return a / b


def main():
    print("=== @cache ===")
    start = time.perf_counter()
    print(f"fibonacci(30) = {fibonacci(30)} ({time.perf_counter() - start:.5f}с)")
    print(f"cache_info: {fibonacci.cache_info()}")
    start = time.perf_counter()
    fibonacci(30)
    print(f"Повторний виклик: {time.perf_counter() - start:.7f}с (з кешу)")

    print("\nЛогування hit/miss та витіснення (max_size=2):")
    square(2); square(3); square(2)   # 2 -> hit
    square(4)                         # витісняє найстаріший (3)
    square(3)                         # знову miss
    print(f"cache_info: {square.cache_info()}")
    print(f"Метадані збережено: {fibonacci.__name__}, doc='{fibonacci.__doc__}'")

    print("\n=== @rate_limit (5 викликів за 10 с) ===")
    for i in range(1, 7):
        try:
            print(f"  {i}: {send_notification(f'повідомлення {i}')}")
        except RuntimeError as e:
            print(f"  {i}: RuntimeError: {e}")

    print("\n=== @log ===")
    divide(10, 3)
    try:
        divide(10, 0)
    except ZeroDivisionError:
        print("Помилку оброблено у main()")


if __name__ == "__main__":
    main()
