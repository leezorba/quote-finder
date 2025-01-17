import os
import time
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from queue_utils import start_worker, job_queue, job_results
from pinecones_utils_openai import query_openai_paragraphs
from openai_utils import get_chat_completion
from prompts import search_assistant_system_prompt

app = Flask(__name__)
app.config['TIMEOUT'] = 300  # Increased timeout for long queries
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# Cache dictionary to store results with timestamps
query_cache = {}
CACHE_TIMEOUT = timedelta(minutes=30)

def get_cached_query_results(query, top_k):
    """Retrieve cached results if they exist and haven't expired."""
    cache_key = f"{query}_{top_k}"
    if cache_key in query_cache:
        timestamp, results = query_cache[cache_key]
        if datetime.now() - timestamp < CACHE_TIMEOUT:
            print(f"[INFO] Cache hit for query: {query}")
            return results
    return None

def cache_query_results(query, top_k, results):
    """Cache the query results with a timestamp."""
    cache_key = f"{query}_{top_k}"
    query_cache[cache_key] = (datetime.now(), results)
    print(f"[INFO] Cached results for query: {query}")

def verify_response(quotes, original_paragraphs):
    """Verify GPT output by matching paragraph text to metadata."""
    verified_quotes = []
    original_dict = {}

    # Build a dictionary of original paragraphs for matching
    for p in original_paragraphs:
        text = p['metadata']['paragraph_text']
        original_dict[text.strip()] = p['metadata']
        clean_text = ''.join(c for c in text if c.isalnum() or c.isspace()).strip()
        original_dict[clean_text] = p['metadata']

    for quote in quotes:
        quote_text = quote.get('paragraph_text', '').strip()
        clean_quote = ''.join(c for c in quote_text if c.isalnum() or c.isspace()).strip()
        original_meta = original_dict.get(quote_text) or original_dict.get(clean_quote)

        if original_meta:
            verified_quotes.append({
                'speaker': original_meta['speaker'],
                'role': original_meta['role'],
                'title': original_meta['title'],
                'youtube_link': original_meta['youtube_link'],
                'paragraph_deep_link': original_meta['paragraph_deep_link'],
                'paragraph_text': original_meta['paragraph_text'],
                'start_time': int(original_meta['start_time']),
                'end_time': int(original_meta['end_time']),
            })
            print(f"✓ Verified quote: {quote_text[:50]}...")
        else:
            print(f"✗ Unverified quote: {quote_text[:50]}...")

    return verified_quotes

def process_query(user_message):
    """Process a single query and return verified quotes."""
    top_k = 10
    retries = 3

    for attempt in range(retries):
        try:
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
            if verified_quotes:
                return verified_quotes
        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def ask():
    """Submit a query to the job queue."""
    data = request.get_json()
    user_message = (data.get('question') or "").strip()

    if not user_message:
        return jsonify({'error': 'Question cannot be empty'}), 400

    print(f"\n[{datetime.now()}] Query: {user_message}")

    # Check cache first
    cached_results = get_cached_query_results(user_message, top_k=10)
    if cached_results:
        return jsonify({'response_text': cached_results})

    job_id = str(uuid.uuid4())
    job_results[job_id] = {'status': 'pending'}
    job_queue.put((job_id, user_message))

    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
    """Check the status of a job and return results if complete."""
    if job_id not in job_results:
        return jsonify({'error': 'Job not found'}), 404

    result = job_results[job_id]
    if result['status'] == 'complete':
        # Cache the completed result
        cache_query_results(result.get('query', ''), 10, result['data'])
        return jsonify({'status': 'complete', 'response_text': result['data']})
    elif result['status'] == 'error':
        return jsonify({'status': 'error', 'error': result['error']})
    return jsonify({'status': 'pending'})

if __name__ == '__main__':
    # Start the background worker thread
    start_worker(process_query)

    # Run the Flask app
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)