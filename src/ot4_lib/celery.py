import loguru
import redis
from functools import wraps
from django.conf import settings
from celery import Task


def only_once(task_name, redis_client, lock_timeout=None):
    """
    Decorator to ensure a task is only run once at a time.
    :param task_name: The name of the task (unique key in Redis).
    :param redis_client: Redis client instance to use for locking.
    :param lock_timeout: Timeout in seconds for the Redis lock. Default is None (infinite).
    """

    def decorator(task_func):
        @wraps(task_func)
        def wrapper(*args, **kwargs):
            lock_name = f"lock:{task_name}"
            lock_acquired = redis_client.set(
                lock_name, "locked", nx=True, ex=lock_timeout
            )

            if not lock_acquired:
                print(f"Task {task_name} is already running, skipping...")
                return

            try:
                result = task_func(*args, **kwargs)
                return result
            finally:
                # Release the lock after task execution
                redis_client.delete(lock_name)

        return wrapper

    return decorator


class Once(Task):
    """
    This class ensures that a task runs only once at a time using a Redis lock mechanism.
    It initializes the Redis client with the URL specified in the Django settings (`CELERY_BROKER_URL`),
    and uses the `only_once` decorator to manage task concurrency.

    Example usage:

    @celery_app.task(base=Once)
    def my_periodic_task():
        print("Executing the task...")
        # Task logic here
    """

    def __call__(self, *args, **kwargs):
        # Get the Redis URL from Django settings
        redis_url = settings.CELERY_BROKER_URL
        redis_client = redis.StrictRedis.from_url(redis_url)

        task_name = self.name
        decorated_task = only_once(task_name, redis_client)(super(Once, self).__call__)
        return decorated_task(*args, **kwargs)

    @classmethod
    def release_all_locks(cls):
        """
        Releases all Redis locks created for Celery tasks.
        """
        redis_url = settings.CELERY_BROKER_URL
        redis_client = redis.StrictRedis.from_url(redis_url)

        # Find all keys that match the lock pattern
        lock_pattern = "lock:*"
        lock_keys = redis_client.keys(lock_pattern)

        # Delete all lock keys
        if lock_keys:
            redis_client.delete(*lock_keys)
            loguru.logger.debug(f"Released {len(lock_keys)} locks.")
        else:
            loguru.logger.debug("No locks to release.")
