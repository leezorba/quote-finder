import os
import re
import json
import difflib
import striprtf.striprtf

###############################
# 1) Helper: Gather all RTF file paths from subfolders
###############################

def gather_all_rtf_files(base_dir: str):
    """
    Walk through `base_dir` (and all subdirectories) to find every .rtf file.
    Returns a dict mapping the rtf filename to its full path:
    """
    rtf_map = {}
    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            if filename.lower().endswith(".rtf"):
                full_path = os.path.join(root, filename)
                rtf_map[filename] = full_path
    return rtf_map


###############################
# 2) Parsing an RTF transcript
###############################

def parse_rtf_transcript(rtf_path: str):
    """
    Parse the RTF and return a list of (time_in_seconds, text_chunk).
    """
    with open(rtf_path, 'r', encoding='utf-8') as f:
        rtf_content = f.read()

    # Convert RTF to plain text
    raw_text = striprtf.striprtf.rtf_to_text(rtf_content)

    lines = raw_text.splitlines()
    transcript = []  # list of (time_in_seconds, text_chunk)

    for line in lines:
        line = line.strip()
        match = re.match(r"^(\d+):(\d{2})(.*)", line)
        if match:
            mins = int(match.group(1))
            secs = int(match.group(2))
            rest_text = match.group(3).strip()
            total_seconds = mins * 60 + secs
            transcript.append((total_seconds, rest_text))
        else:
            if transcript:
                last_time, last_text = transcript[-1]
                new_text = (last_text + " " + line).strip()
                transcript[-1] = (last_time, new_text)
    return transcript


###############################
# 3) Fuzzy alignment for paragraphs
###############################

def fuzzy_align_paragraph(paragraph_text: str, transcript_lines: list):
    """
    For a single paragraph, find the best matching line in transcript_lines.
    """
    best_ratio = 0.0
    best_idx = None

    for i, (timestamp, chunk_text) in enumerate(transcript_lines):
        ratio = difflib.SequenceMatcher(None, paragraph_text, chunk_text).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i

    if best_idx is None:
        return (0, 0)

    start_time = transcript_lines[best_idx][0]
    if best_idx < len(transcript_lines) - 1:
        end_time = transcript_lines[best_idx + 1][0]
    else:
        end_time = 1000
    return (start_time, end_time)


###############################
# 4) Main merge function
###############################

def merge_specific_timecodes_with_talks(talks_directory: str, transcripts_base_dir: str, specific_ids: list):
    """
    Merge timecodes for specific video IDs only.
    """
    # Gather all RTF files
    rtf_map = gather_all_rtf_files(transcripts_base_dir)
    print(f"[INFO] Found {len(rtf_map)} RTF files across all subfolders in '{transcripts_base_dir}'.")

    # Iterate through JSON files in the talks directory
    for file_name in os.listdir(talks_directory):
        if not file_name.endswith(".json") or "-time-codes.json" in file_name:
            continue

        json_path = os.path.join(talks_directory, file_name)
        with open(json_path, 'r', encoding='utf-8') as f:
            talk_data = json.load(f)

        if not talk_data:
            continue

        youtube_id = talk_data[0].get("youtube_id", "")
        if youtube_id not in specific_ids:
            continue  # Skip unrelated video IDs

        # Build the expected .rtf filename using the video ID
        rtf_filename = f"{youtube_id}.rtf"
        if rtf_filename not in rtf_map:
            print(f"[WARN] RTF file '{rtf_filename}' not found for video {youtube_id}. Skipping.")
            continue

        rtf_path = rtf_map[rtf_filename]
        # Parse the RTF
        transcript_lines = parse_rtf_transcript(rtf_path)
        if not transcript_lines:
            print(f"[WARN] No lines found in '{rtf_filename}'")
            continue

        # Fuzzy-match paragraphs
        for paragraph in talk_data:
            p_text = paragraph["paragraph_text"]
            start_sec, end_sec = fuzzy_align_paragraph(p_text, transcript_lines)
            paragraph["start_time"] = start_sec
            paragraph["end_time"] = end_sec

        # Overwrite the talk JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(talk_data, f, indent=4, ensure_ascii=False)

        print(f"[INFO] Updated timecodes for {file_name} => {rtf_filename}")


def main():
    # Directory paths
    talks_directory = "talks_json"
    transcripts_base_dir = "youtube_transcripts_specific"

    # List of specific video IDs to process
    specific_ids = ["AiP5Z9YgOVI", "C4m2bAGhzJY", "jBqtxDpoYnE", "vb9BkYmzPZc"]

    merge_specific_timecodes_with_talks(talks_directory, transcripts_base_dir, specific_ids)


if __name__ == "__main__":
    main()