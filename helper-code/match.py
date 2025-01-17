import os
import json
import unicodedata

# Function to clean text by normalizing Unicode characters
def clean_text(text):
    """Remove Unicode escapes and normalize text."""
    if text:
        return unicodedata.normalize("NFKC", text.encode("utf-8").decode("unicode_escape"))
    return text

# Folder containing JSON files
folder_path = "talks_json"

# List of YouTube video IDs to search for
video_ids_to_match = ["vb9BkYmzPZc", "AiP5Z9YgOVI", "jBqtxDpoYnE", "C4m2bAGhzJY"]

# Dictionary to store unique results
matching_summary = {}

# Iterate through all JSON files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        file_path = os.path.join(folder_path, filename)

        # Load the JSON file
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                talks = json.load(file)
                for talk in talks:
                    # If the talk's YouTube ID matches and it's not already added
                    youtube_id = talk.get("youtube_id")
                    if youtube_id in video_ids_to_match and youtube_id not in matching_summary:
                        matching_summary[youtube_id] = {
                            "title": clean_text(talk.get("title")),
                            "speaker": clean_text(talk.get("speaker")),
                            "paragraph_deep_link": clean_text(talk.get("paragraph_deep_link"))
                        }
            except json.JSONDecodeError as e:
                print(f"Error reading JSON from {file_path}: {e}")

# Output the matching summary
print("Matching Summary:")
for youtube_id, details in matching_summary.items():
    print(f"YouTube ID: {youtube_id}")
    print(f"  Title: {details['title']}")
    print(f"  Speaker: {details['speaker']}")
    print(f"  Paragraph Deep Link: {details['paragraph_deep_link']}")
    print()