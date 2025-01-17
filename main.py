import os
import time
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from queue import Queue
import uuid
import threading

from prompts import search_assistant_system_prompt
from pinecones_utils_openai import query_openai_paragraphs
from openai_utils import get_chat_completion

app = Flask(__name__)
app.config['TIMEOUT'] = 120
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# Global job queue and results storage
job_queue = Queue()
job_results = {}

# Cache dictionary to store results with timestamps
query_cache = {}
CACHE_TIMEOUT = timedelta(minutes=30)

def get_cached_query_results(query, top_k):
    """Get cached results if they exist and haven't expired"""
    cache_key = f"{query}_{top_k}"
    if cache_key in query_cache:
        timestamp, results = query_cache[cache_key]
        if datetime.now() - timestamp < CACHE_TIMEOUT:
            print(f"[INFO] Cache hit for query: {query}")
            return results
    return None

def cache_query_results(query, top_k, results):
    """Cache the query results with current timestamp"""
    cache_key = f"{query}_{top_k}"
    query_cache[cache_key] = (datetime.now(), results)
    print(f"[INFO] Cached results for query: {query}")

def verify_response(quotes, original_paragraphs):
    """
    Verifies the GPT output by matching 'paragraph_text' to the metadata
    in 'original_paragraphs'. If found, it reconstructs a verified quote object
    using the original metadata. If not found, logs an unverified quote.
    """
    verified_quotes = []
    original_dict = {}

    # 1) Build dictionary of original paragraphs to support flexible matching
    for p in original_paragraphs:
        text = p['metadata']['paragraph_text']
        # Store both full text and normalized versions
        original_dict[text] = p['metadata']
        original_dict[text.strip()] = p['metadata']

        # Also store a version with punctuation stripped (optional)
        clean_text = ''.join(c for c in text if c.isalnum() or c.isspace()).strip()
        original_dict[clean_text] = p['metadata']

    # 2) Attempt to verify each returned quote
    for quote in quotes:
        quote_text = quote.get('paragraph_text', '')
        found = False

        if quote_text in original_dict:
            found = True
            original_meta = original_dict[quote_text]
        else:
            # Try normalized
            clean_quote = ''.join(c for c in quote_text if c.isalnum() or c.isspace()).strip()
            if clean_quote in original_dict:
                found = True
                original_meta = original_dict[clean_quote]

        if found:
            verified_quote = {
                'speaker': original_meta['speaker'],
                'role': original_meta['role'],
                'title': original_meta['title'],
                'youtube_link': original_meta['youtube_link'],
                'paragraph_deep_link': original_meta['paragraph_deep_link'],
                'paragraph_text': original_meta['paragraph_text'],
                'start_time': int(original_meta['start_time']),
                'end_time': int(original_meta['end_time'])
            }
            verified_quotes.append(verified_quote)
            print(f"✓ Verified quote: {verified_quote['paragraph_text'][:50]}...")
        else:
            print(f"✗ Unverified quote: {quote_text[:50]}...")

    return verified_quotes

def process_query(user_message):
    """Process a single query and return verified quotes"""
    top_k = 10  # Reduced from 15
    relevant_paragraphs = query_openai_paragraphs(query=user_message, top_k=top_k)
    if not relevant_paragraphs:
        raise Exception('No relevant paragraphs found')

    user_prompt = (
        "Relevant paragraphs with metadata:\n\n" +
        "\n\n".join([
            f"Speaker: {p['metadata'].get('speaker', '')}\n"
            f"Role: {p['metadata'].get('role', '')}\n"
            f"Title: {p['metadata'].get('title', '')}\n"
            f"Link: {p['metadata'].get('youtube_link', '')}\n"
            f"DeepLink: {p['metadata'].get('paragraph_deep_link', '')}\n"
            f"Text: {p['paragraph_text']}"
            for p in relevant_paragraphs
        ]) +
        f"\n\nUser question: {user_message}\n\n"
        "Return ONLY a raw JSON array with exact quotes and metadata - no markdown or code blocks."
    )

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response_text = get_chat_completion(
                system_prompt=search_assistant_system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                temperature=0.7,
                max_tokens=2000
            )
            quotes = json.loads(response_text)
            if not isinstance(quotes, list):
                raise ValueError("GPT output is not a JSON array")
            verified_quotes = verify_response(quotes, relevant_paragraphs)
            if not verified_quotes:
                raise Exception('No verified quotes found')
            return verified_quotes
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            time.sleep(1)
            continue

# Start background worker
def process_jobs():
    """Background worker to process jobs"""
    while True:
        job_id, user_message = job_queue.get()
        try:
            result = process_query(user_message)
            job_results[job_id] = {
                'status': 'complete', 
                'data': result,
                'query': user_message  # Store query for caching
            }
        except Exception as e:
            job_results[job_id] = {'status': 'error', 'error': str(e)}
        job_queue.task_done()

# Start the background worker thread
worker = threading.Thread(target=process_jobs, daemon=True)
worker.start()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def ask():
    """Submit a query to the job queue"""
    data = request.get_json()
    user_message = (data.get('question') or "").strip()

    if not user_message:
        return jsonify({'error': 'Question cannot be empty'}), 400

    print(f"\n[{datetime.now()}] Query: {user_message}")

    # Check cache first
    cached_results = get_cached_query_results(user_message, top_k=10)
    if cached_results:
        return jsonify({'response_text': cached_results})

    # Create new job with the query stored
    job_id = str(uuid.uuid4())
    job_results[job_id] = {
        'status': 'pending',
        'query': user_message  # Store the query with the job
    }
    job_queue.put((job_id, user_message))

    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
    """Check job status and return results if complete"""
    if job_id not in job_results:
        return jsonify({'error': 'Job not found'}), 404

    result = job_results[job_id]
    if result['status'] == 'complete':
        # Get the data and query
        data = result['data']
        user_message = result.get('query', '')
        if user_message:  # Only cache if we have the query
            cache_query_results(user_message, 10, data)
        # Clean up job data
        del job_results[job_id]
        return jsonify({'status': 'complete', 'response_text': data})
    elif result['status'] == 'error':
        error = result['error']
        del job_results[job_id]
        return jsonify({'status': 'error', 'error': error})
    else:
        return jsonify({'status': 'pending'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)