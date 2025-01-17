import os
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

# Now we get the API key from environment variables
API_KEY = os.getenv("YOUTUBE_API_KEY")  # Must be set in .env as YOUTUBE_API_KEY

def format_timestamp(seconds):
    """Convert seconds to a formatted timestamp (MM:SS)."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02}"


def create_rtf_file_with_timestamps(transcript, video_id, output_dir):
    """
    Create an RTF file named "<video_id>.rtf" with timestamps.
    """
    rtf_filename = f"{video_id}.rtf"
    file_path = os.path.join(output_dir, rtf_filename)

    with open(file_path, "w", encoding="utf-8") as rtf_file:
        # Write an RTF header
        rtf_file.write(
            r"{\rtf1\ansi\ansicpg1252\cocoartf2761\n"
            r"{\fonttbl\f0\fswiss\fcharset0 Helvetica;}\n"
            r"{\colortbl;\red255\green255\blue255;}\n"
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


def fetch_and_save_transcripts(video_ids, output_dir):
    """
    Fetch transcripts for specific video IDs and save as RTF files.
    """
    os.makedirs(output_dir, exist_ok=True)

    for video_id in video_ids:
        # try:
        #     transcript = YouTubeTranscriptApi.get_transcript(video_id)
        #     rtf_file_path = create_rtf_file_with_timestamps(transcript, video_id, output_dir)
        #     print(f"Transcript saved: {rtf_file_path}")
        # except Exception as e:
        #     print(f"Error fetching transcript for video {video_id}: {e}")

        try:
            # Try fetching the transcript for 'en-US' language
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US', 'en'])
            rtf_file_path = create_rtf_file_with_timestamps(transcript, video_id, output_dir)
            print(f"Transcript saved: {rtf_file_path}")
        except Exception as e:
            print(f"Error fetching transcript for video {video_id}: {e}")


if __name__ == "__main__":
    # List of specific YouTube video IDs to process
    video_ids = ["AiP5Z9YgOVI"]
    output_dir = "youtube_transcripts_specific"

    # Fetch and save transcripts as RTF files
    fetch_and_save_transcripts(video_ids, output_dir)