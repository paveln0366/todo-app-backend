from time import perf_counter

from sqlalchemy.orm import Session

from app.cache.cache import RedisCacheBackend
from app.core.config import get_settings
from app.repositories.task import TaskRepository
from app.schemas.task import TaskSchema, TaskCreateSchema, TaskUpdateSchema

settings = get_settings()


class TaskNotFound(Exception):
    """Задача не найдена в БД"""


class TaskService:
    def __init__(
            self,
            db: Session
    ) -> None:
        self.db = db
        self.task_repository = TaskRepository(db)
        self.cache = RedisCacheBackend(settings.redis_url, settings.cache_ttl_seconds)

    def list_tasks(self) -> list[TaskSchema]:
        start_time = perf_counter()
        # Шаг 1: проверить, есть ли данные  в Redis
        cached_tasks = self.cache.get(settings.cache_tasks_key)
        if cached_tasks is not None:
            print(f"Получение списка задач по кэшу заняло {perf_counter() - start_time}")
            return [TaskSchema.model_validate(task) for task in cached_tasks]

        tasks_orm = self.task_repository.get_all()  # Шаг 2: Идем в БД, если в кеше данных нет

        # Шаг 3: Сохранить в кеш, если данных в кеше нет
        task_read = [TaskSchema.model_validate(task) for task in tasks_orm]
        tasks_for_cache = [task.model_dump(mode="json") for task in task_read]
        self.cache.set(settings.cache_tasks_key, tasks_for_cache)

        print(f"Получение списка задач заняло {perf_counter() - start_time}")

        return task_read

    def create_task(self, task_create: TaskCreateSchema) -> TaskSchema:
        # Инвалидация кеша (чтобы он был актуальным)
        self.cache.delete(settings.cache_tasks_key)

        task_orm = self.task_repository.create(title=task_create.title)
        self.db.commit()
        return TaskSchema.model_validate(task_orm)

    def update_task(self, task_id: str, task_update: TaskUpdateSchema) -> TaskSchema:
        # Инвалидация кеша (чтобы он был актуальным)
        self.cache.delete(settings.cache_tasks_key)

        task_for_update = self.task_repository.get_by_id(task_id=task_id)
        if not task_for_update:
            raise TaskNotFound(f"Задача с {task_id} не найдена")
        if task_update.title is not None:
            task_for_update.title = task_update.title
        if task_update.completed is not None:
            task_for_update.completed = task_update.completed

        self.db.commit()
        return TaskSchema.model_validate(task_for_update)

    def delete_task(self, task_id: str) -> None:
        # Инвалидация кеша (чтобы он был актуальным)
        self.cache.delete(settings.cache_tasks_key)

        task_for_delete = self.task_repository.get_by_id(task_id=task_id)
        if not task_for_delete:
            raise TaskNotFound(f"Задача с {task_id} не найдена")
        self.task_repository.delete(task_for_delete)
        self.db.commit()
