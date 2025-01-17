from queue import Queue
import threading

# Global job queue and results storage
job_queue = Queue()
job_results = {}

def process_jobs():
    """Background worker to process jobs"""
    while True:
        job_id, user_message = job_queue.get()
        try:
            # Actual processing will be imported from main.py
            from main import process_query
            result = process_query(user_message)
            job_results[job_id] = {'status': 'complete', 'data': result}
        except Exception as e:
            job_results[job_id] = {'status': 'error', 'error': str(e)}
        job_queue.task_done()

# Start background worker
worker = threading.Thread(target=process_jobs, daemon=True)
worker.start()