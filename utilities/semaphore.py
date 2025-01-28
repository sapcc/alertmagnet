import time
import uuid

from threading import Thread, BoundedSemaphore


class ThreadManager(object):
    def __init__(self, semaphore_count: int):
        self.semaphore = BoundedSemaphore(semaphore_count)  # Consider using BoundedSemaphore
        self.threads: dict[str] = {}

    def add_thread(self, func) -> str:
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

        thread = Thread(target=self.wrapper_thread, args=(func,))
        thread.start()

        # self.threads.pop(thread_uuid)

        return thread

    def execute_all_threads(self):
        threads: list[Thread] = []
        for key in self.threads:
            thread = self.start_thread(thread_uuid=key)
            threads.append(thread)
            time.sleep(1)

        for thread in threads:
            thread.join()
