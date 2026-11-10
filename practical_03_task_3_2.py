"""Паттерни Observer, Strategy та архітектурний шаблон MVC."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable


# --- Observer ---

class EventEmitter:
    """Базовий клас для підтримки системи подій (Observer)."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}

    def on(self, event: str, callback: Callable):
        """Підписатися на подію."""
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable):
        """Відписатися від події."""
        listeners = self._listeners.get(event, [])
        if callback in listeners:
            listeners.remove(callback)

    def emit(self, event: str, *args, **kwargs):
        """Сповістити всіх слухачів про подію."""
        for callback in list(self._listeners.get(event, [])):
            callback(*args, **kwargs)


# --- Model ---

@dataclass
class Task:
    title: str
    priority: int  # 1 (найвищий) – 5 (найнижчий)
    deadline: datetime
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    task_id: int = 0  # стабільний номер завдання (задає модель)


# --- Strategy ---

class SortStrategy(ABC):
    """Абстрактна стратегія сортування завдань."""

    @abstractmethod
    def sort(self, tasks: list[Task]) -> list[Task]:
        ...


class SortByPriority(SortStrategy):
    """Сортування за пріоритетом (високий → низький)."""

    def sort(self, tasks: list[Task]) -> list[Task]:
        return sorted(tasks, key=lambda t: (t.priority, t.deadline))


class SortByDeadline(SortStrategy):
    """Сортування за терміном виконання (найближчий першим)."""

    def sort(self, tasks: list[Task]) -> list[Task]:
        return sorted(tasks, key=lambda t: t.deadline)


class SortByCreationDate(SortStrategy):
    """Сортування за датою створення (найновіші першими)."""

    def sort(self, tasks: list[Task]) -> list[Task]:
        # task_id — запасний ключ на випадок однакового часу створення
        return sorted(tasks, key=lambda t: (t.created_at, t.task_id), reverse=True)


class TaskModel(EventEmitter):
    """Model: дані та бізнес-логіка завдань.

    Параметр `index` у complete_task/remove_task — це номер завдання (колонка №),
    який не змінюється після видалення інших завдань.
    """

    def __init__(self):
        super().__init__()
        self._tasks: list[Task] = []
        self._next_id = 1

    def _find(self, task_id: int) -> Task:
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        raise ValueError(f"Завдання №{task_id} не знайдено")

    def add_task(self, title: str, priority: int, deadline: datetime):
        if not title.strip():
            raise ValueError("Назва завдання не може бути порожньою")
        if not 1 <= priority <= 5:
            raise ValueError("Пріоритет має бути в межах 1–5")
        task = Task(title.strip(), priority, deadline, task_id=self._next_id)
        self._next_id += 1
        self._tasks.append(task)
        self.emit("task_added", task)

    def complete_task(self, index: int):
        task = self._find(index)
        if task.completed:
            raise ValueError(f"Завдання №{index} уже виконане")
        task.completed = True
        self.emit("task_completed", task)

    def remove_task(self, index: int):
        task = self._find(index)
        self._tasks.remove(task)
        self.emit("task_removed", task)

    def get_tasks(self, include_completed: bool = True) -> list[Task]:
        if include_completed:
            return list(self._tasks)
        return [t for t in self._tasks if not t.completed]

    def get_statistics(self) -> dict:
        completed = sum(1 for t in self._tasks if t.completed)
        return {
            "total": len(self._tasks),
            "completed": completed,
            "active": len(self._tasks) - completed,
        }


# --- View ---

class TaskView:
    """View: відображення даних у консолі."""

    def show_tasks(self, tasks: list[Task], title: str = "Завдання"):
        print(f"\n=== {title} ===")
        if not tasks:
            print("  (список порожній)")
            return
        header = f"{'№':<3} {'Назва':<28} {'Пріоритет':<10} {'Дедлайн':<17} {'Статус':<10}"
        print(header)
        print("-" * len(header))
        for t in tasks:
            name = t.title if len(t.title) <= 27 else t.title[:26] + "…"
            status = "Виконано" if t.completed else "Активне"
            print(f"{t.task_id:<3} {name:<28} {t.priority:<10} "
                  f"{t.deadline:%Y-%m-%d %H:%M}  {status:<10}")

    def show_message(self, message: str):
        print(f"[INFO] {message}")

    def show_statistics(self, stats: dict):
        print("\n=== Статистика ===")
        print(f"  Всього:   {stats['total']}")
        print(f"  Виконано: {stats['completed']}")
        print(f"  Активних: {stats['active']}")


# --- Controller ---

class TaskController:
    """Controller: координація Model та View з підтримкою Strategy."""

    def __init__(self, model: TaskModel, view: TaskView):
        self._model = model
        self._view = view
        self._sort_strategy: SortStrategy = SortByPriority()

        # Observer: контролер підписується на події моделі
        self._model.on("task_added", self._on_task_added)
        self._model.on("task_completed", self._on_task_completed)
        self._model.on("task_removed", self._on_task_removed)

    def _on_task_added(self, task: Task):
        self._view.show_message(f"Додано завдання №{task.task_id}: «{task.title}»")

    def _on_task_completed(self, task: Task):
        self._view.show_message(f"Виконано завдання №{task.task_id}: «{task.title}»")

    def _on_task_removed(self, task: Task):
        self._view.show_message(f"Видалено завдання №{task.task_id}: «{task.title}»")

    def set_sort_strategy(self, strategy: SortStrategy):
        """Змінити стратегію сортування (Strategy)."""
        self._sort_strategy = strategy

    def add_task(self, title: str, priority: int, deadline: datetime):
        self._model.add_task(title, priority, deadline)

    def complete_task(self, index: int):
        self._model.complete_task(index)

    def remove_task(self, index: int):
        self._model.remove_task(index)

    def show_all(self):
        tasks = self._model.get_tasks()
        sorted_tasks = self._sort_strategy.sort(tasks)
        strategy = type(self._sort_strategy).__name__
        self._view.show_tasks(sorted_tasks, title=f"Усі завдання ({strategy})")

    def show_active(self):
        tasks = self._model.get_tasks(include_completed=False)
        sorted_tasks = self._sort_strategy.sort(tasks)
        self._view.show_tasks(sorted_tasks, title="Активні завдання")

    def show_stats(self):
        self._view.show_statistics(self._model.get_statistics())


def main():
    model = TaskModel()
    view = TaskView()
    ctrl = TaskController(model, view)

    now = datetime.now()
    ctrl.add_task("Підготувати звіт з ПР №3", 1, now + timedelta(days=2))
    ctrl.add_task("Купити продукти", 4, now + timedelta(days=1))
    ctrl.add_task("Написати тести", 2, now + timedelta(days=5))
    ctrl.add_task("Записатися до лікаря", 3, now + timedelta(hours=10))
    ctrl.add_task("Прочитати лекцію 3", 5, now + timedelta(days=3))

    ctrl.show_all()  # за замовчуванням SortByPriority

    ctrl.set_sort_strategy(SortByDeadline())
    ctrl.show_all()

    ctrl.set_sort_strategy(SortByCreationDate())
    ctrl.show_all()

    ctrl.complete_task(1)
    ctrl.show_active()

    ctrl.remove_task(2)

    print("\nПомилка при повторному виконанні:")
    try:
        ctrl.complete_task(1)
    except ValueError as e:
        print(f"  ValueError: {e}")

    ctrl.show_stats()

    # Відписка від події (off): після цього повідомлення про додавання не показуються
    model.off("task_added", ctrl._on_task_added)
    ctrl.add_task("Без сповіщення", 3, now + timedelta(days=7))
    print("\n(після off() повідомлення про додавання не з'явилося)")
    ctrl.show_stats()


if __name__ == "__main__":
    main()
