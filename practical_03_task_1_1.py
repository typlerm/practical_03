"""Система плагінів з автоматичною реєстрацією через метаклас."""

import hashlib
import re
from abc import abstractmethod


class PluginMeta(type):
    """Метаклас для автоматичної реєстрації та валідації плагінів.

    Кожен клас, створений з цим метакласом, автоматично додається
    до реєстру, якщо він визначає обов'язкові атрибути.
    """

    _registry: dict[str, type] = {}
    REQUIRED_ATTRS = ("name", "version")

    def __new__(mcs, cls_name: str, bases: tuple, namespace: dict):
        # Базовий клас (без батьків) не реєструється і не валідується
        if bases:
            for attr in mcs.REQUIRED_ATTRS:
                if attr not in namespace:
                    raise TypeError(
                        f"Плагін '{cls_name}' не визначає обов'язковий "
                        f"атрибут '{attr}' (потрібні: {', '.join(mcs.REQUIRED_ATTRS)})"
                    )
            plugin_name = namespace["name"]
            if plugin_name in mcs._registry:
                raise ValueError(f"Плагін з іменем '{plugin_name}' уже зареєстровано")

        cls = super().__new__(mcs, cls_name, bases, namespace)

        if bases:
            mcs._registry[namespace["name"]] = cls
        return cls

    @classmethod
    def get_registry(mcs) -> dict[str, type]:
        """Повертає копію реєстру плагінів."""
        return dict(mcs._registry)

    @classmethod
    def create_plugin(mcs, plugin_name: str):
        """Фабричний метод: створює екземпляр плагіна за його name."""
        try:
            return mcs._registry[plugin_name]()
        except KeyError:
            available = ", ".join(mcs._registry) or "—"
            raise ValueError(
                f"Невідомий плагін '{plugin_name}'. Доступні: {available}"
            ) from None


class BasePlugin(metaclass=PluginMeta):
    """Базовий клас плагіна."""

    @abstractmethod
    def execute(self, data: str) -> str:
        """Обробити вхідні дані."""
        raise NotImplementedError


class UpperPlugin(BasePlugin):
    name = "upper"
    version = "1.0"

    def execute(self, data: str) -> str:
        return data.upper()


class ReversePlugin(BasePlugin):
    name = "reverse"
    version = "1.0"

    def execute(self, data: str) -> str:
        return data[::-1]


class CensorPlugin(BasePlugin):
    name = "censor"
    version = "1.1"

    def __init__(self, words=("світ",)):
        self.words = tuple(words)

    def execute(self, data: str) -> str:
        for word in self.words:
            data = re.sub(re.escape(word), "***", data, flags=re.IGNORECASE)
        return data


# Динамічне створення класу через type() у тризначній формі.
# Python сам визначить метаклас PluginMeta з BasePlugin і викличе його __new__.
def _hash_execute(self, data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


HashPlugin = type(
    "HashPlugin",
    (BasePlugin,),
    {"name": "hash", "version": "2.0", "execute": _hash_execute},
)


def main():
    print("Зареєстровані плагіни:")
    for name, cls in PluginMeta.get_registry().items():
        print(f"  {name} (v{cls.version}): {cls.__name__}")

    print(f"\nHashPlugin створено динамічно, метаклас: {type(HashPlugin).__name__}")

    print("\nВиконання через PluginMeta.create_plugin():")
    test_data = "Привіт Світ"
    for name in PluginMeta.get_registry():
        plugin = PluginMeta.create_plugin(name)
        print(f"  {name}: {plugin.execute(test_data)}")

    print("\nКлас без обов'язкових атрибутів:")
    try:
        class BrokenPlugin(BasePlugin):
            name = "broken"  # немає version

            def execute(self, data: str) -> str:
                return data
    except TypeError as e:
        print(f"  TypeError: {e}")
    print(f"  'broken' у реєстрі: {'broken' in PluginMeta.get_registry()}")

    print("\nНевідомий плагін:")
    try:
        PluginMeta.create_plugin("nope")
    except ValueError as e:
        print(f"  ValueError: {e}")


if __name__ == "__main__":
    main()
