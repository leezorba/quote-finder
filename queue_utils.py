from threading import Thread
from queue import Queue
import time

job_queue = Queue()
job_results = {}

def process_jobs():
    while True:
        job_id, query = job_queue.get()
        try:
            from main import process_query
            result = process_query(query)
            job_results[job_id] = {
                'status': 'complete',
                'data': result,
                'query': query
            }
        except Exception as e:
            job_results[job_id] = {
                'status': 'error',
                'error': str(e)
            }
        finally:
            job_queue.task_done()
            time.sleep(0.1)

def start_worker(process_func):
    worker = Thread(target=process_jobs, daemon=True)
    worker.start()