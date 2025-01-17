import os
import json

def merge_paragraphs_for_bigger_chunks(paragraphs, max_tokens=200):
    """
    'paragraphs' is a list of dicts, each having at least "paragraph_text", 
    "start_time", and "end_time".
    
    Merges consecutive paragraphs until we reach ~max_tokens worth of text 
    (in this example, tokens ~ words). Returns a new list of merged chunk dicts.
    """
    big_chunks = []
    current_chunk_text = []
    current_start_time = None
    current_end_time = None
    current_word_count = 0

    for p in paragraphs:
        text = p["paragraph_text"]
        words = text.split()
        word_count = len(words)

        # If adding this paragraph would exceed max_tokens, flush the current chunk
        if current_chunk_text and (current_word_count + word_count > max_tokens):
            # Save the chunk
            merged_text = " ".join(current_chunk_text)
            big_chunks.append({
                "speaker": p["speaker"],  # or from the first chunk
                "role": p["role"],
                "title": p["title"],
                "youtube_link": p["youtube_link"],
                "paragraph_deep_link": p["paragraph_deep_link"], 
                "paragraph_text": merged_text,
                "start_time": current_start_time,
                "end_time": current_end_time
            })
            # Reset
            current_chunk_text = []
            current_word_count = 0
            current_start_time = None
            current_end_time = None

        # Start building a chunk if not started
        if current_start_time is None:
            current_start_time = p["start_time"]
        # Always update the end_time to the latest
        current_end_time = p["end_time"]

        current_chunk_text.append(text)
        current_word_count += word_count

    # Flush the last chunk
    if current_chunk_text:
        merged_text = " ".join(current_chunk_text)
        big_chunks.append({
            "speaker": paragraphs[-1]["speaker"],
            "role": paragraphs[-1]["role"],
            "title": paragraphs[-1]["title"],
            "youtube_link": paragraphs[-1]["youtube_link"],
            "paragraph_deep_link": paragraphs[-1]["paragraph_deep_link"],
            "paragraph_text": merged_text,
            "start_time": current_start_time,
            "end_time": current_end_time
        })

    return big_chunks


if __name__ == "__main__":
    input_folder = "talks_json"
    output_folder = "talks_json_bigger"
    max_tokens = 200  # Adjust as desired

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created folder '{output_folder}' for bigger-chunks JSON.")

    # Loop through all JSON files in talks_json
    for file_name in os.listdir(input_folder):
        if not file_name.endswith(".json"):
            continue

        input_path = os.path.join(input_folder, file_name)
        with open(input_path, "r", encoding="utf-8") as f:
            paragraphs = json.load(f)

        if not paragraphs:
            print(f"Skipping empty file: {file_name}")
            continue

        # Merge paragraphs for bigger chunks
        big_chunks = merge_paragraphs_for_bigger_chunks(paragraphs, max_tokens=max_tokens)

        # Write out to the new folder
        output_path = os.path.join(output_folder, file_name)
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(big_chunks, out_f, ensure_ascii=False, indent=4)

        print(f"✅ {file_name} => {len(big_chunks)} bigger-chunks written to {output_path}")