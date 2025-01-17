from queue import Queue
import threading

# Global job queue and results storage
job_queue = Queue()
job_results = {}

def process_jobs(process_query):
    """
    Background worker to process jobs.
    Dynamically receives the `process_query` function to avoid circular imports.
    """
    while True:
        job_id, user_message = job_queue.get()
        try:
            result = process_query(user_message)
            job_results[job_id] = {'status': 'complete', 'data': result}
        except Exception as e:
            job_results[job_id] = {'status': 'error', 'error': str(e)}
        finally:
            job_queue.task_done()

def start_worker(process_query):
    """
    Start the background worker thread with the provided `process_query` function.
    """
    worker = threading.Thread(target=process_jobs, args=(process_query,), daemon=True)
    worker.start()