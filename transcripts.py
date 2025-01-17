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
       e.g. {
          "abc123_someTitle.rtf": "/absolute/path/youtube_transcripts/playlist_abc/abc123_someTitle.rtf",
          ...
       }
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
    Each line is expected to begin with 'MM:SS' (e.g. '0:00').
    The rest of the line is treated as text for that timestamp.

    If a line doesn't start with a time, it's appended 
    to the previous chunk's text.
    """
    with open(rtf_path, 'r', encoding='utf-8') as f:
        rtf_content = f.read()

    # Convert RTF to plain text
    raw_text = striprtf.striprtf.rtf_to_text(rtf_content)

    lines = raw_text.splitlines()
    transcript = []  # list of (time_in_seconds, text_chunk)

    for line in lines:
        line = line.strip()
        # Attempt to match something like "0:00" or "12:35"
        match = re.match(r"^(\d+):(\d{2})(.*)", line)
        if match:
            mins = int(match.group(1))
            secs = int(match.group(2))
            rest_text = match.group(3).strip()
            total_seconds = mins * 60 + secs
            transcript.append((total_seconds, rest_text))
        else:
            # Continuation of the previous line's text if no new timestamp
            if transcript:
                last_time, last_text = transcript[-1]
                new_text = (last_text + " " + line).strip()
                transcript[-1] = (last_time, new_text)
            else:
                pass  # If there's no prior entry, skip or handle differently

    return transcript


###############################
# 3) Fuzzy alignment for paragraphs (optional)
###############################

def fuzzy_align_paragraph(paragraph_text: str, transcript_lines: list):
    """
    For a single paragraph, find the best matching line in transcript_lines 
    using difflib to measure text similarity.

    transcript_lines: [(time_in_seconds, text_chunk), ...]
    
    Returns (start_time, end_time).
      start_time = matched line's time_in_seconds
      end_time   = next line's time_in_seconds (or 1000 if last line).
    """
    best_ratio = 0.0
    best_idx = None

    for i, (timestamp, chunk_text) in enumerate(transcript_lines):
        ratio = difflib.SequenceMatcher(None, paragraph_text, chunk_text).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i

    if best_idx is None:
        return (0, 0)  # fallback if no match

    start_time = transcript_lines[best_idx][0]
    if best_idx < len(transcript_lines) - 1:
        end_time = transcript_lines[best_idx + 1][0]
    else:
        end_time = 1000
    return (start_time, end_time)


###############################
# 4) Main merge function
###############################

def merge_timecodes_with_talks(talks_directory: str, transcripts_base_dir: str):
    """
    1. Gather RTF files from all subfolders in transcripts_base_dir.
    2. For each talk JSON in talks_directory, read 'youtube_id' only (ignore talk title).
       Build the expected rtf_filename = "<youtube_id>.rtf".
    3. If that filename is in rtf_map, parse & fuzzy-match each paragraph 
       for start/end times. Overwrite the JSON with updated times.
    """
    # Step A: Gather all RTF files
    rtf_map = gather_all_rtf_files(transcripts_base_dir)
    print(f"[INFO] Found {len(rtf_map)} RTF files across all subfolders in '{transcripts_base_dir}'.")

    # Step B: Go through all talk JSON files
    for file_name in os.listdir(talks_directory):
        if not file_name.endswith(".json") or "-time-codes.json" in file_name:
            continue

        json_path = os.path.join(talks_directory, file_name)
        with open(json_path, 'r', encoding='utf-8') as f:
            talk_data = json.load(f)

        if not talk_data:
            continue

        # We assume all paragraphs share the same youtube_id
        youtube_id = talk_data[0].get("youtube_id", "")
        if not youtube_id:
            print(f"[WARN] No youtube_id found in {file_name}. Skipping.")
            continue

        # Build the expected .rtf filename using ONLY the video ID
        rtf_filename = f"{youtube_id}.rtf"
        if rtf_filename not in rtf_map:
            print(f"[WARN] RTF file '{rtf_filename}' not found in any subfolder. Skipping.")
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
    # Example usage:
    talks_directory = "talks_json"
    transcripts_base_dir = "youtube_transcripts"  # We will walk ALL subfolders under this

    merge_timecodes_with_talks(talks_directory, transcripts_base_dir)

if __name__ == "__main__":
    main()