from threading import Thread
from queue import Queue
import time

job_queue = Queue()
job_results = {}

def process_jobs():
    """Process jobs from the queue and store results."""
    while True:
        try:
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
                print(f"Error processing job {job_id}: {str(e)}")
                job_results[job_id] = {
                    'status': 'error',
                    'error': str(e)
                }
            finally:
                job_queue.task_done()
        except Exception as e:
            print(f"Error in process_jobs: {str(e)}")
        time.sleep(0.1)  # Small delay to prevent CPU thrashing

def start_worker(process_func):
    """Start the background worker thread."""
    worker = Thread(target=process_jobs, daemon=True)
    worker.start()
    return worker