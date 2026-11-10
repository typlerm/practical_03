"""Паттерни Singleton та Factory Method."""

import json
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime


class SingletonMeta(type):
    """Метаклас для реалізації патерну Singleton."""

    _instances: dict[type, object] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # Подвійна перевірка + lock — безпечно для багатопотокового коду
        if cls not in SingletonMeta._instances:
            with SingletonMeta._lock:
                if cls not in SingletonMeta._instances:
                    SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]


class LogFormatter(ABC):
    """Абстрактний базовий клас форматера логів."""

    @abstractmethod
    def format(self, level: str, message: str, timestamp: datetime) -> str:
        """Форматувати повідомлення логу."""


class PlainFormatter(LogFormatter):
    """Простий текстовий формат: [РІВЕНЬ] ЧАС - Повідомлення"""

    def format(self, level: str, message: str, timestamp: datetime) -> str:
        return f"[{level}] {timestamp:%Y-%m-%d %H:%M:%S} - {message}"


class JSONFormatter(LogFormatter):
    """JSON-формат: {"level": "...", "time": "...", "message": "..."}"""

    def format(self, level: str, message: str, timestamp: datetime) -> str:
        return json.dumps(
            {"level": level, "time": timestamp.isoformat(timespec="seconds"),
             "message": message},
            ensure_ascii=False,
        )


class ColorFormatter(LogFormatter):
    """Кольоровий формат для терміналу (ANSI-коди).

    DEBUG=сірий, INFO=зелений, WARNING=жовтий, ERROR=червоний.
    """
    COLORS = {
        "DEBUG": "\033[90m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
    }
    RESET = "\033[0m"

    def format(self, level: str, message: str, timestamp: datetime) -> str:
        color = self.COLORS.get(level, "")
        return f"{color}[{level}] {timestamp:%H:%M:%S} - {message}{self.RESET}"


class FormatterFactory:
    """Фабрика форматерів із підтримкою реєстрації нових типів."""

    _formatters: dict[str, type[LogFormatter]] = {
        "plain": PlainFormatter,
        "json": JSONFormatter,
        "color": ColorFormatter,
    }

    @classmethod
    def register(cls, name: str, formatter_cls: type[LogFormatter]):
        """Зареєструвати новий тип форматера (Open/Closed: без зміни фабрики)."""
        if not (isinstance(formatter_cls, type) and issubclass(formatter_cls, LogFormatter)):
            raise TypeError("formatter_cls має бути підкласом LogFormatter")
        cls._formatters[name] = formatter_cls

    @classmethod
    def create(cls, name: str) -> LogFormatter:
        """Створити форматер за іменем. Викинути ValueError, якщо невідомий."""
        try:
            return cls._formatters[name]()
        except KeyError:
            raise ValueError(
                f"Невідомий форматер '{name}'. Доступні: {', '.join(cls._formatters)}"
            ) from None

    @classmethod
    def available(cls) -> list[str]:
        """Повернути список доступних форматерів."""
        return list(cls._formatters)


class Logger(metaclass=SingletonMeta):
    """Логер із підтримкою рівнів та змінних форматерів."""

    LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}

    def __init__(self, formatter_name: str = "plain", min_level: str = "DEBUG"):
        if min_level not in self.LEVELS:
            raise ValueError(f"Невідомий рівень '{min_level}'")
        self._formatter = FormatterFactory.create(formatter_name)
        self._min_level = min_level
        self._log_history: list[str] = []

    def set_formatter(self, name: str):
        self._formatter = FormatterFactory.create(name)

    def log(self, level: str, message: str):
        level = level.upper()
        if level not in self.LEVELS:
            raise ValueError(f"Невідомий рівень '{level}'")
        if self.LEVELS[level] < self.LEVELS[self._min_level]:
            return
        line = self._formatter.format(level, message, datetime.now())
        print(line)
        self._log_history.append(line)

    def debug(self, msg: str):
        self.log("DEBUG", msg)

    def info(self, msg: str):
        self.log("INFO", msg)

    def warning(self, msg: str):
        self.log("WARNING", msg)

    def error(self, msg: str):
        self.log("ERROR", msg)

    def get_history(self) -> list[str]:
        return self._log_history[:]


class ShortFormatter(LogFormatter):
    """Новий форматер, доданий ззовні без зміни коду фабрики."""

    def format(self, level: str, message: str, timestamp: datetime) -> str:
        return f"{level[0]}: {message}"


def main():
    if os.name == "nt":
        os.system("")  # вмикає ANSI-кольори у консолі Windows

    logger1 = Logger("plain", "DEBUG")
    logger2 = Logger("json", "INFO")   # аргументи ігноруються — повертається той самий об'єкт
    print(f"Singleton: {logger1 is logger2}")  # True
    print(f"id: {id(logger1)} == {id(logger2)}\n")

    logger1.debug("Діагностика (plain)")
    logger1.info("Система запущена")
    logger1.warning("Мало пам'яті")
    logger1.error("Помилка з'єднання")

    print("\nЗмінюємо форматер на json:")
    logger1.set_formatter("json")
    logger1.debug("Діагностика")
    logger2.info("Повідомлення через logger2 (той самий об'єкт)")

    print("\nКольоровий форматер:")
    logger1.set_formatter("color")
    for lvl in ("DEBUG", "INFO", "WARNING", "ERROR"):
        logger1.log(lvl, f"рівень {lvl}")

    print("\nРеєстрація нового форматера без зміни фабрики:")
    FormatterFactory.register("short", ShortFormatter)
    logger1.set_formatter("short")
    logger1.info("Працює новий форматер")

    print("\nНевідомий форматер:")
    try:
        logger1.set_formatter("xml")
    except ValueError as e:
        print(f"  ValueError: {e}")

    print(f"\nФорматери: {FormatterFactory.available()}")
    print(f"Історія: {len(logger1.get_history())} записів")


if __name__ == "__main__":
    main()
