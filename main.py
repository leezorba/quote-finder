# main.py

import os
import time
import datetime
import json
from flask import Flask, request, jsonify, render_template
from functools import lru_cache
from datetime import datetime, timedelta

from prompts import search_assistant_system_prompt
from pinecones_utils_openai import query_openai_paragraphs
from openai_utils import get_chat_completion

app = Flask(__name__)
app.config['TIMEOUT'] = 300  # Increased to 5 minutes
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# Cache dictionary to store results with timestamps
query_cache = {}
CACHE_TIMEOUT = timedelta(minutes=30)  # Cache expires after 30 minutes

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

@app.after_request
def after_request(response):
    response.headers["Proxy-Connection"] = "Keep-Alive"
    response.headers["Connection"] = "Keep-Alive"
    response.headers["Keep-Alive"] = "timeout=300, max=1000"
    response.headers['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def ask():
    """Handle the AJAX POST for searching."""
    data = request.get_json()
    user_message = (data.get('question') or "").strip()

    if not user_message:
        return jsonify({'error': 'Question cannot be empty'}), 400

    print(f"\n[{datetime.datetime.now()}] Query: {user_message}")
    print("Using single enhanced search mode (embed3)")

    # Check cache first
    cached_results = get_cached_query_results(user_message, top_k=15)
    if cached_results:
        return jsonify({'response_text': cached_results})

    # If not in cache, proceed with normal query
    try:
        top_k = 15  # You can adjust if you like
        relevant_paragraphs = query_openai_paragraphs(query=user_message, top_k=top_k)
        if not relevant_paragraphs:
            return jsonify({'error': 'No relevant paragraphs found'}), 404

        # 2) Build the user prompt for GPT
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

        # 3) Call GPT with up to 3 attempts if JSON is malformed
        max_attempts = 3
        quotes = None

        for attempt in range(max_attempts):
            try:
                response_text = get_chat_completion(
                    system_prompt=search_assistant_system_prompt,
                    user_prompt=user_prompt,
                    model="gpt-4o",
                    temperature=0.7,
                    max_tokens=2000
                )
                print(f"[INFO] GPT Response received (attempt {attempt+1})")
                print("Raw GPT response:", response_text)

                candidate_quotes = json.loads(response_text)
                if not isinstance(candidate_quotes, list):
                    raise ValueError("GPT output is not a JSON array")

                quotes = candidate_quotes
                break  # success, break out of the retry loop

            except (json.JSONDecodeError, ValueError) as e:
                print(f"[ERROR] GPT returned malformed JSON on attempt {attempt+1}: {str(e)}")
                if attempt == max_attempts - 1:
                    return jsonify({
                        'error': (
                            "Sorry! We encountered an error. Please refresh the page and try again. "
                            "If it continues failing, contact Hwa. "
                            f"Error code: mjson (Failed after {max_attempts} attempts)"
                        )
                    }), 500
                else:
                    time.sleep(1)
                    continue

        # 4) Verify quotes
        verified_quotes = verify_response(quotes, relevant_paragraphs)
        if not verified_quotes:
            return jsonify({'error': 'No verified quotes found'}), 404

        # Cache the results before returning
        cache_query_results(user_message, top_k, verified_quotes)
        return jsonify({'response_text': verified_quotes})

    except Exception as e:
        print("[ERROR] Request failed:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)