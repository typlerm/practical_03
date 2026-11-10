"""Типізовані дескриптори та __init_subclass__ для системи конфігурації."""


class ValidatedField:
    """Дескриптор із валідацією типу та діапазону значень.

    Використовує __set_name__ для автоматичного визначення імені атрибута.
    """

    def __init__(self, expected_type: type, min_value=None, max_value=None):
        self.expected_type = expected_type
        self.min_value = min_value
        self.max_value = max_value

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        try:
            return getattr(obj, self.private_name)
        except AttributeError:
            raise AttributeError(
                f"Поле '{self.public_name}' ще не ініціалізоване"
            ) from None

    def __set__(self, obj, value):
        # bool є підкласом int, тому для int-полів відхиляємо його явно
        is_bad_bool = isinstance(value, bool) and self.expected_type is not bool
        if is_bad_bool or not isinstance(value, self.expected_type):
            raise TypeError(
                f"Поле '{self.public_name}' очікує {self.expected_type.__name__}, "
                f"отримано {type(value).__name__}: {value!r}"
            )
        if self.min_value is not None and value < self.min_value:
            raise ValueError(
                f"Поле '{self.public_name}': значення {value} менше за мінімум "
                f"{self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValueError(
                f"Поле '{self.public_name}': значення {value} більше за максимум "
                f"{self.max_value}"
            )
        setattr(obj, self.private_name, value)


class ConfigSection:
    """Базовий клас секції конфігурації з автоматичною реєстрацією."""

    _sections: dict[str, type] = {}

    def __init_subclass__(cls, section_name: str = "", **kwargs):
        super().__init_subclass__(**kwargs)
        name = section_name or cls.__name__.lower()
        if name in ConfigSection._sections:
            raise ValueError(f"Секція '{name}' уже зареєстрована")
        ConfigSection._sections[name] = cls

    @classmethod
    def get_section(cls, name: str):
        """Повертає клас секції за іменем."""
        try:
            return ConfigSection._sections[name]
        except KeyError:
            raise KeyError(f"Секцію '{name}' не знайдено") from None

    @classmethod
    def list_sections(cls) -> list[str]:
        """Повертає список усіх зареєстрованих секцій."""
        return list(ConfigSection._sections)


class DatabaseConfig(ConfigSection, section_name="database"):
    host = ValidatedField(str)
    port = ValidatedField(int, min_value=1, max_value=65535)
    max_connections = ValidatedField(int, min_value=1, max_value=1000)

    def __init__(self, host: str, port: int, max_connections: int):
        self.host = host
        self.port = port
        self.max_connections = max_connections

    def __repr__(self):
        return (f"DatabaseConfig(host={self.host!r}, port={self.port}, "
                f"max_connections={self.max_connections})")


class LoggingConfig(ConfigSection, section_name="logging"):
    level = ValidatedField(str)
    max_file_size_mb = ValidatedField(int, min_value=1, max_value=1024)

    def __init__(self, level: str, max_file_size_mb: int):
        self.level = level
        self.max_file_size_mb = max_file_size_mb

    def __repr__(self):
        return (f"LoggingConfig(level={self.level!r}, "
                f"max_file_size_mb={self.max_file_size_mb})")


def main():
    print(f"Зареєстровані секції: {ConfigSection.list_sections()}")
    print(f"get_section('logging') -> {ConfigSection.get_section('logging').__name__}")

    db = DatabaseConfig("localhost", 5432, 100)
    log_cfg = LoggingConfig("INFO", 50)
    print(db)
    print(log_cfg)

    print("\nВалідація типу:")
    try:
        db.port = "abc"
    except TypeError as e:
        print(f"  TypeError: {e}")

    print("Валідація діапазону:")
    try:
        db.port = 70000
    except ValueError as e:
        print(f"  ValueError: {e}")
    try:
        db.max_connections = 0
    except ValueError as e:
        print(f"  ValueError: {e}")

    print("Некоректне значення в конструкторі:")
    try:
        LoggingConfig("DEBUG", 5000)
    except ValueError as e:
        print(f"  ValueError: {e}")

    print(f"\nПісля невдалих спроб значення не змінились: {db}")


if __name__ == "__main__":
    main()
