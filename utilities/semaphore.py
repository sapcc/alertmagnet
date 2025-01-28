import uuid
from threading import Thread, BoundedSemaphore


class ThreadManager(object):
    def __init__(self, semaphore_count: int):
        self.semaphore = BoundedSemaphore(semaphore_count)  # Consider using BoundedSemaphore
        self.threads = {}

    def add_thread(self, func) -> str:
        thread_uuid = uuid.uuid4().hex
        self.threads[thread_uuid] = func
        return thread_uuid

    def wrapper_thread(self, func):
        with self.semaphore:
            func()

    def start_thread(self, thread_uuid: str = None):
        if not thread_uuid:
            return
        func = self.threads[thread_uuid]
        thread = Thread(target=self.wrapper_thread, args=(func,))
        thread.start()
        self.threads.pop(thread_uuid)

    def start_all_threads(self):
        for key in self.threads:
            self.start_thread(thread_uuid=key)
