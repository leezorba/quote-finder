import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import chardet
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import json
import os
import re
from typing import Dict, Tuple, List
import glob
from pathlib import Path

###############################
# Utility Functions
###############################

def extract_video_id(youtube_link: str) -> str:
    """
    Extracts the video ID from typical YouTube links, e.g.
    'https://www.youtube.com/watch?v=XXX' or 'https://youtu.be/XXX'.
    Returns an empty string if not found.
    """
    import re
    pattern = r"(?:v=|youtu\.be/)([\w-]+)"
    match = re.search(pattern, youtube_link)
    if match:
        return match.group(1)
    return ""

def sanitize_filename(name):
    """
    Sanitizes a string to be used as a valid filename by removing or replacing invalid characters.
    """
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized

def create_output_directory(directory_name='talks_json'):
    """
    Creates a directory for storing per-talk JSON files if it doesn't already exist.
    """
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)
        print(f"✅ Created directory '{directory_name}' for per-talk JSON files.")
    else:
        print(f"✅ Directory '{directory_name}' already exists.")
    return directory_name

def save_talk_to_json(talk_paragraphs, directory='talks_json', index=1):
    """
    Saves the data of a single talk to a separate JSON file.
    """
    if not talk_paragraphs:
        print(f"⚠️ No paragraphs to save for talk index {index}.")
        return

    # Use the title of the first paragraph for the filename
    title = talk_paragraphs[0].get('title', f"Talk_{index}")
    sanitized_title = sanitize_filename(title)
    filename = f"{index}_{sanitized_title}.json"
    filepath = os.path.join(directory, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as json_file:
            json.dump(talk_paragraphs, json_file, ensure_ascii=False, indent=4)
        print(f"✅ Saved talk data to '{filepath}'.")
    except Exception as e:
        print(f"❌ Error saving talk data to '{filepath}': {e}")

def clean_text(text):
    """
    Cleans up specific known encoding issues in the text.
    """
    if text is None:
        return "N/A"

    replacements = {
        'Â': ' ',
        'â': '"',
        'â': '"',
        'â': "'",
        'â': "'",
        'â¦': '...',
        'â': '–',
        'â': '—',
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text

def construct_deep_link(base_url, p_id):
    """
    Constructs a deep link URL for a specific paragraph.
    """
    parsed_url = urlparse(base_url)
    query = parse_qs(parsed_url.query)
    query['id'] = [p_id]
    new_query = urlencode(query, doseq=True)
    deep_link = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        f"{p_id}"
    ))
    return deep_link

def fetch_page(url):
    """
    Fetches the content of the given URL.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        detection = chardet.detect(response.content)
        encoding = detection['encoding']
        confidence = detection['confidence']

        if encoding and confidence > 0.5:
            response.encoding = encoding
            print(f"✅ Successfully fetched URL: {url} with encoding: {encoding} (Confidence: {confidence})")
        else:
            response.encoding = 'utf-8'
            print(f"⚠️ Encoding detection failed for URL: {url}. Falling back to 'utf-8'.")

        return response.content
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching URL {url}: {e}")
        return None

def extract_article_details(html):
    """
    Extracts the title, author, role, kicker, and paragraphs (with their unique IDs) 
    from the given HTML content.
    """
    soup = BeautifulSoup(html, 'lxml')

    article_data = {
        'title': "N/A",
        'author': "N/A",
        'role': "N/A",
        'kicker': "N/A",
        'paragraphs': []
    }

    # Title
    title_tag = soup.find('h1')
    if title_tag:
        article_data['title'] = title_tag.get_text(strip=True)
    else:
        print("⚠️ Title tag <h1> not found.")

    # Author
    author_tag = soup.find('p', class_='author-name')
    if author_tag:
        author_text = author_tag.get_text(strip=True)
        if author_text.lower().startswith('by '):
            author_text = author_text[3:]
        article_data['author'] = author_text
    else:
        print("⚠️ Author tag <p class='author-name'> not found.")

    # Role
    role_tag = soup.find('p', class_='author-role')
    if role_tag:
        article_data['role'] = role_tag.get_text(strip=True)
    else:
        print("⚠️ Role tag <p class='author-role'> not found.")

    # Kicker
    kicker_tag = soup.find('p', class_='kicker')
    if kicker_tag:
        article_data['kicker'] = kicker_tag.get_text(strip=True)
    else:
        print("⚠️ Kicker tag <p class='kicker'> not found.")

    # Paragraphs
    body_block = soup.find('div', class_='body-block')
    if body_block:
        paragraphs = body_block.find_all('p')
        for p in paragraphs:
            p_id = p.get('id', None)
            if not p_id:
                print("⚠️ Paragraph without an ID found.")
                continue
            paragraph_text = p.get_text(separator=' ', strip=True)
            article_data['paragraphs'].append((p_id, paragraph_text))
    else:
        print("⚠️ Body block <div class='body-block'> not found.")

    return article_data

def read_urls_from_excel(excel_file):
    """
    Reads URLs and YouTube links from the specified Excel file.
    """
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        if 'URL' not in df.columns or 'YouTube' not in df.columns:
            print(f"❌ 'URL' and/or 'YouTube' column not found in {excel_file}.")
            return []
        records = df[['URL', 'YouTube']].dropna(subset=['URL']).to_dict('records')
        print(f"✅ Successfully read {len(records)} URLs from {excel_file}.")
        return records
    except Exception as e:
        print(f"❌ Error reading Excel file {excel_file}: {e}")
        return []

def save_to_json(data_list, filename='extracted_data.json'):
    """
    Saves the extracted data to a flat JSON file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data_list, json_file, ensure_ascii=False, indent=4)
        print(f"✅ Data successfully saved to {filename}.")
    except Exception as e:
        print(f"❌ Error saving data to JSON file {filename}: {e}")

###############################
# Main Execution
###############################

def main():
    excel_file = '2018-2024-conf-talk-yt-links-pair.xlsx'
    flat_json_filename = 'extracted_data.json'
    talks_json_directory = create_output_directory('talks_json')

    records = read_urls_from_excel(excel_file)
    if not records:
        print("❌ No URLs to process. Exiting.")
        return

    json_data = []
    talk_counter = 1

    for idx, record in enumerate(records, 1):
        url = record['URL']
        youtube_link = record.get('YouTube', '')
        video_id = extract_video_id(youtube_link)  # get the ID

        print(f"🔍 Processing URL {idx}/{len(records)}: {url}")
        html_content = fetch_page(url)
        if html_content:
            article_details = extract_article_details(html_content)

            speaker = clean_text(article_details.get('author', 'N/A'))
            role = clean_text(article_details.get('role', 'N/A'))
            title = clean_text(article_details.get('title', 'N/A'))
            youtube = youtube_link if youtube_link else "N/A"

            talk_paragraphs = []
            paragraph_index = 1

            for p_id, para in article_details.get('paragraphs', []):
                deep_link = construct_deep_link(url, p_id)
                paragraph_text = clean_text(para)

                json_element = {
                    "speaker": speaker,
                    "role": role,
                    "title": title,
                    "youtube_link": youtube,
                    "youtube_id": video_id,
                    "paragraph_deep_link": deep_link,
                    "paragraph_text": paragraph_text,
                    "paragraph_index": paragraph_index,
                    "id": f"{talk_counter}-{paragraph_index}"
                }

                json_data.append(json_element)
                talk_paragraphs.append(json_element)
                paragraph_index += 1

            save_talk_to_json(talk_paragraphs, directory=talks_json_directory, index=talk_counter)
            talk_counter += 1
        else:
            print(f"⚠️ Skipping extraction for URL due to fetch failure: {url}\n")

        time.sleep(1)

    save_to_json(json_data, flat_json_filename)

if __name__ == "__main__":
    main()