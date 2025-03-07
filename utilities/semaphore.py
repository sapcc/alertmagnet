import logging
import time
import uuid

from threading import Thread, BoundedSemaphore

logger = logging.getLogger("alertmagnet")


class ThreadManager(object):
    def __init__(self, semaphore_count: int, delay: float):
        self.semaphore = BoundedSemaphore(semaphore_count)
        self.delay = delay
        self.threads: dict[str] = {}

    def add_thread(self, func) -> str:
        logger.debug("Adding thread: %s", func.__name__)
        thread_uuid = uuid.uuid4().hex
        self.threads[thread_uuid] = func

        return thread_uuid

    def wrapper_thread(self, func):
        with self.semaphore:
            func()

    def start_thread(self, thread_uuid: str = None) -> Thread:
        if not thread_uuid:
            return

        func = self.threads[thread_uuid]

        logger.debug("Starting thread: %s", func.__name__)
        thread = Thread(target=self.wrapper_thread, args=(func,))
        thread.start()

        # TODO pop the used thread uuids from the list

        return thread

    def execute_all_threads(self):
        logger.debug("Executing all threads")
        threads: list[Thread] = []
        for key in self.threads:
            thread = self.start_thread(thread_uuid=key)
            threads.append(thread)
            time.sleep(self.delay)

        for thread in threads:
            thread.join()
