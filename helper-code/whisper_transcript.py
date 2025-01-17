import os
import whisper

def format_timestamp(seconds):
    """
    Convert seconds to MM:SS format.
    """
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02}"

def transcribe_with_whisper(audio_path):
    """
    Transcribes the audio file using the Whisper model.
    """
    model = whisper.load_model("large")
    result = model.transcribe(audio_path, fp16=False)
    return result["segments"]  # Contains timestamps and text

def create_rtf_file_with_timestamps(transcript_segments, output_dir, video_id):
    """
    Create an RTF file in the desired format with timestamps.
    """
    rtf_filename = f"{video_id}.rtf"
    rtf_path = os.path.join(output_dir, rtf_filename)

    with open(rtf_path, "w", encoding="utf-8") as rtf_file:
        # RTF Header
        rtf_file.write(
            r"{\rtf1\ansi\ansicpg1252\cocoartf2761\n"
            r"{\fonttbl\f0\fswiss\fcharset0 Helvetica;}\n"
            r"{\colortbl;\red255\green255\blue255;}\n"
            r"\margl1440\margr1440\vieww11520\viewh8400\viewkind0\n"
            r"\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0\n"
            r"\f0\fs24 \cf0 Transcript\n\n"
        )

        # Write each transcript entry
        for segment in transcript_segments:
            start_time = format_timestamp(segment["start"])
            text = segment["text"].replace("\n", "\\\n")  # RTF line breaks
            rtf_file.write(f"{start_time}\\\n{text}\\\n")

        # Close RTF
        rtf_file.write("}")

    print(f"Transcript saved to {rtf_path}")
    return rtf_path

def main(local_audio_path, output_dir, video_id):
    """
    Main function to transcribe a local audio file and save the transcript in RTF format.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Transcribe Audio with Whisper
    print("Transcribing audio...")
    transcript_segments = transcribe_with_whisper(local_audio_path)

    # Step 2: Create RTF file
    create_rtf_file_with_timestamps(transcript_segments, output_dir, video_id)

if __name__ == "__main__":
    # Replace with your local audio file path and desired output directory
    local_audio_path = "vb9BkYmzPZc.m4a"  # Path to your downloaded MP3 file
    output_dir = "youtube_transcripts_specific"
    video_id = "vb9BkYmzPZc"  # Use the video ID for naming consistency
    main(local_audio_path, output_dir, video_id)