from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import threading

from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()


class SingleWorkerQueue:

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='job-worker')
        self._pending_jobs = set()
        self._lock = threading.Lock()

    def submit_job(self, job_id, func, *args, **kwargs):
        """Submit a job if not already pending"""
        with self._lock:
            if job_id in self._pending_jobs:
                logger.info(f"Job '{job_id}' already pending, skipping")
                return None
            self._pending_jobs.add(job_id)

        def wrapped_job():
            try:
                logger.info(f"Starting job '{job_id}'")
                result = func(*args, **kwargs)
                logger.info(f"Completed job '{job_id}'")
                return result
            except Exception as e:
                logger.error(f"Job '{job_id}' failed: {e}")
                raise
            finally:
                with self._lock:
                    self._pending_jobs.discard(job_id)

        future = self._executor.submit(wrapped_job)
        return future

    def dedupe_job(self, job_id):
        """Decorator for automatic job deduplication"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.submit_job(job_id, func, *args, **kwargs)
            return wrapper
        return decorator


# Global instance
job_queue = SingleWorkerQueue()


# Convenience functions
def queue_job(job_id, func, *args, **kwargs):
    """Queue a job with deduplication"""
    return job_queue.submit_job(job_id, func, *args, **kwargs)


def dedupe_job(job_id):
    """Decorator for job deduplication"""
    return job_queue.dedupe_job(job_id)
