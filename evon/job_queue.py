from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import threading
import uuid

from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()


class SingleWorkerQueue:

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='job-worker')
        self._pending_jobs = set()
        self._lock = threading.Lock()

    def submit_job(self, func, *args, job_id=None, **kwargs):
        """
        Submit a job to the queue.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments for the function
            job_id: If provided, enables deduplication. If None, always runs.
        """
        # Generate unique ID if no job_id provided (no deduplication)
        if job_id is None:
            job_id = f"{func.__name__}-{uuid.uuid4().hex[:8]}"
            dedupe = False
        else:
            dedupe = True
            # Check for existing job if deduplication is enabled
            with self._lock:
                if job_id in self._pending_jobs:
                    logger.info(f"Job '{job_id}' already pending, skipping")
                    return None
                self._pending_jobs.add(job_id)

        def wrapped_job():
            try:
                logger.info(f"Starting job '{job_id}'")
                if dedupe:
                    with self._lock:
                        self._pending_jobs.discard(job_id)
                result = func(*args, **kwargs)
                logger.info(f"Completed job '{job_id}'")
                return result
            except Exception as e:
                logger.error(f"Job '{job_id}' failed: {e}")
                raise

        future = self._executor.submit(wrapped_job)
        return future

    def dedupe_job(self, job_id):
        """Decorator for automatic job queuing with deduplication"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.submit_job(func, *args, job_id=job_id, **kwargs)
            return wrapper
        return decorator

    def async_job(self, func):
        """Decorator for automatic job queuing, no deduplication"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.submit_job(func, *args, **kwargs)  # No job_id = no deduplication
        return wrapper


# Global instance
job_queue = SingleWorkerQueue()


# Convenience functions
def queue_job(func, *args, job_id=None, **kwargs):
    """
    Queue a job. Provide job_id for deduplication, omit for always-run.
    Jobs are run sequentially. Examples:

    # Deduped jobs (provide job_id)
    queue_job(firewall.init, job_id='firewall-init')  # Will add to queue
    queue_job(firewall.init, job_id='firewall-init')  # Won't add duplicate to queue if one is waiting but will add if one is running

    # Non-deduped jobs (no job_id)
    queue_job(firewall.apply_rule, rule1)  # will add to queue
    queue_job(firewall.apply_rule, rule2)  # will also add to queue, both will run sequentially
    """
    return job_queue.submit_job(func, *args, job_id=job_id, **kwargs)


def dedupe_job(job_id):
    """Decorator for job deduplication"""
    return job_queue.dedupe_job(job_id)


def async_job(func):
    """Decorator for non-deduped async jobs"""
    return job_queue.async_job(func)
