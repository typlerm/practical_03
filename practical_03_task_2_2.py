"""Декоратори класів."""

import functools
import inspect


def auto_repr(cls):
    """Декоратор класу: додає __repr__ на основі __init__ параметрів.

    Використовується inspect.signature (а не __code__.co_varnames), бо він
    слідує за __wrapped__ і тому коректно працює разом з @frozen.
    """
    params = [
        name for name in inspect.signature(cls.__init__).parameters
        if name != "self"
    ]

    def __repr__(self):
        fields = ", ".join(f"{p}={getattr(self, p, '?')!r}" for p in params)
        return f"{type(self).__name__}({fields})"

    cls.__repr__ = __repr__
    return cls


def frozen(cls):
    """Декоратор класу: забороняє зміну атрибутів після __init__.

    Після ініціалізації будь-яка спроба змінити атрибут
    викликає AttributeError.
    """
    original_init = cls.__init__

    @functools.wraps(original_init)
    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise AttributeError(
                f"Не можна змінити '{name}': екземпляр {type(self).__name__} заморожений"
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if getattr(self, "_frozen", False):
            raise AttributeError(
                f"Не можна видалити '{name}': екземпляр {type(self).__name__} заморожений"
            )
        object.__delattr__(self, name)

    cls.__init__ = __init__
    cls.__setattr__ = __setattr__
    cls.__delattr__ = __delattr__
    return cls


def log_methods(cls):
    """Декоратор класу: логує виклики всіх публічних методів."""

    def make_wrapper(method_name, method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            parts = [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
            call = f"{cls.__name__}.{method_name}({', '.join(parts)})"
            try:
                result = method(self, *args, **kwargs)
            except Exception as e:
                print(f"[LOG] {call} → {type(e).__name__}: {e}")
                raise
            print(f"[LOG] {call} → {result!r}")
            return result
        return wrapper

    for name, attr in list(vars(cls).items()):
        if not name.startswith("_") and inspect.isfunction(attr):
            setattr(cls, name, make_wrapper(name, attr))
    return cls


@auto_repr
class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@frozen
class ImmutableConfig:
    def __init__(self, host: str, port: int, debug: bool = False):
        self.host = host
        self.port = port
        self.debug = debug


@log_methods
class MathService:
    def add(self, a: float, b: float) -> float:
        return a + b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Ділення на нуль")
        return a / b


# Комбінування всіх трьох декораторів на одному класі
@auto_repr
@frozen
@log_methods
class Account:
    def __init__(self, owner: str, balance: float):
        self.owner = owner
        self.balance = balance

    def with_bonus(self, percent: float) -> float:
        return self.balance * (1 + percent / 100)


def main():
    print("=== @auto_repr ===")
    p = Point(3.0, 4.0)
    print(repr(p))  # Point(x=3.0, y=4.0)
    print(f"Метод не зачеплено: distance_to = {p.distance_to(Point(0.0, 0.0))}")

    print("\n=== @frozen ===")
    cfg = ImmutableConfig("localhost", 8080, debug=True)
    print(f"Config: {cfg.host}:{cfg.port}")
    try:
        cfg.host = "remote"
    except AttributeError as e:
        print(f"Очікувана помилка: {e}")
    try:
        del cfg.port
    except AttributeError as e:
        print(f"Очікувана помилка: {e}")

    print("\n=== @log_methods ===")
    svc = MathService()
    svc.add(10, 20)
    svc.multiply(3, 7)
    try:
        svc.divide(10, 0)
    except ValueError:
        pass
    print(f"Метадані збережено: {MathService.add.__name__}")

    print("\n=== Комбінування @auto_repr + @frozen + @log_methods ===")
    acc = Account("Ірина", 1000.0)
    print(repr(acc))
    acc.with_bonus(5)
    try:
        acc.balance = 0
    except AttributeError as e:
        print(f"Очікувана помилка: {e}")


if __name__ == "__main__":
    main()
