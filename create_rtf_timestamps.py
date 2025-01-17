import os
import re
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()  

# Now we get the API key from environment variables
API_KEY = os.getenv("YOUTUBE_API_KEY")  # Must be set in .env as YOUTUBE_API_KEY

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def get_playlist_videos(api_key, playlist_id):
    """
    Fetch all video IDs and titles from a YouTube playlist.
    """
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)
    video_details = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,  # max allowed
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response["items"]:
            video_id = item["snippet"]["resourceId"]["videoId"]
            video_title = item["snippet"]["title"]
            video_details.append({"id": video_id, "title": video_title})

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return video_details


def format_timestamp(seconds):
    """Convert seconds to a formatted timestamp (MM:SS)."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02}"


def create_rtf_file_with_timestamps(transcript, video_id, video_title, output_dir):
    """
    Create an RTF file named "<video_id>.rtf" with timestamps.
    (We ignore the talk title to simplify matching in transcripts.py.)
    """
    # Just name the file using the YouTube ID
    rtf_filename = f"{video_id}.rtf"
    file_path = os.path.join(output_dir, rtf_filename)

    with open(file_path, "w", encoding="utf-8") as rtf_file:
        # Write an RTF header that’s compatible with your transcripts.
        rtf_file.write(
            r"{\rtf1\ansi\ansicpg1252\cocoartf2761\n"
            r"\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}\n"
            r"{\colortbl;\red255\green255\blue255;}\n"
            r"{\*\expandedcolortbl;;}\n"
            r"\margl1440\margr1440\vieww11520\viewh8400\viewkind0\n"
            r"\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0\n"
            r"\f0\fs24 \cf0 Transcript\n\n"
        )

        # Write transcript entries
        for entry in transcript:
            start_time = format_timestamp(entry["start"])
            text = entry["text"].replace("\n", "\\\n")  # RTF line breaks
            rtf_file.write(f"{start_time}\\\n{text}\\\n")

        rtf_file.write("}")

    return file_path
    

def fetch_transcripts_and_generate_rtf(api_key, playlist_id, output_dir):
    """
    Fetch transcripts for all videos in a single playlist
    and create RTF files named <video_id>_<title>.rtf,
    skipping videos with 'session' in the title.
    """
    os.makedirs(output_dir, exist_ok=True)
    videos = get_playlist_videos(api_key, playlist_id)

    for video in videos:
        video_id = video["id"]
        video_title = video["title"]

        # Skip if title contains 'session' (case-insensitive)
        if "session" in video_title.lower():
            print(f"Skipping combined session video: {video_title}")
            continue

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            rtf_file_path = create_rtf_file_with_timestamps(transcript, video_id, video_title, output_dir)
            print(f"Transcript saved: {rtf_file_path}")
        except Exception as e:
            print(f"Error fetching transcript for video {video_id} ({video_title}): {e}")


def fetch_transcripts_for_multiple_playlists(api_key, playlist_ids, output_base_dir):
    """
    Fetch transcripts for multiple playlists into separate subfolders.
    """
    for playlist_id in playlist_ids:
        print(f"Processing playlist: {playlist_id}")
        playlist_output_dir = os.path.join(output_base_dir, f"playlist_{playlist_id}")
        fetch_transcripts_and_generate_rtf(api_key, playlist_id, playlist_output_dir)
        print(f"Finished processing playlist: {playlist_id}\n")


if __name__ == "__main__":
    # Example usage:
    # Provide your playlist IDs
    playlist_ids = [
        "PLClOO0BdaFaMvqq1WnOY8ci5K_iytQ3yF",
        "PLClOO0BdaFaMZzuKzBXkLNAah9qnT-QSC",
        "PLClOO0BdaFaNrQxgVlLIN4uUmbWVid4q-",
        "PLClOO0BdaFaNXQBSQAiAkyQI923O8hAG3",
        "PLClOO0BdaFaPpMqgxNFENY0_iiPoEZi2h",
        "PLClOO0BdaFaPoU96UI_VoKHXxuTiN-Jnq",
        "PLClOO0BdaFaMY9nBNz_s4ZbYDyF2Xx5ja",
        "PLClOO0BdaFaN2iSB4m9nM4CXdKSMYHxLP",
        "PLClOO0BdaFaNZQ2xYdKz07gK08b7WTQzG",
        "PLClOO0BdaFaM9iItZGHRlax0GPpnoxZYQ",
        "PLClOO0BdaFaNnSB2F8pEjM5IJRF3rx1Rj",
        "PLClOO0BdaFaO56ApsIz_WBPAySrm5gZYD",
        "PLClOO0BdaFaPnyUuT8t_nIobLLpjaHTb9",
        "PLClOO0BdaFaMlORnNQByG5QdxMTaB6pF-",
    ]
    output_base_dir = "youtube_transcripts"

    # we assume .env has YOUTUBE_API_KEY=XXXXXXXX
    fetch_transcripts_for_multiple_playlists(API_KEY, playlist_ids, output_base_dir)