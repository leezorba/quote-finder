from pytube import Playlist
import csv

# Function to extract video links from a playlist
def extract_youtube_links(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        print(f"Fetching videos from playlist: {playlist.title}")
        video_links = list(playlist.video_urls)  # Get all video URLs in the playlist
        return playlist.title, video_links
    except Exception as e:
        print(f"Error processing playlist {playlist_url}: {e}")
        return None, []

# List of playlist URLs
playlist_urls = [
    "https://www.youtube.com/watch?v=9t8zdkO9abE&list=PLClOO0BdaFaMvqq1WnOY8ci5K_iytQ3yF",
    "https://www.youtube.com/watch?v=nD8gGZzHZ7Y&list=PLClOO0BdaFaMZzuKzBXkLNAah9qnT-QSC",
    "https://www.youtube.com/watch?v=zzx6GYH95zw&list=PLClOO0BdaFaNrQxgVlLIN4uUmbWVid4q-",
    "https://www.youtube.com/watch?v=vXqR-96h75g&list=PLClOO0BdaFaNXQBSQAiAkyQI923O8hAG3",
    "https://www.youtube.com/watch?v=k17s5HhlpIk&list=PLClOO0BdaFaPpMqgxNFENY0_iiPoEZi2h",
    "https://www.youtube.com/watch?v=8YQgH8tkzEA&list=PLClOO0BdaFaPoU96UI_VoKHXxuTiN-Jnq",
    "https://www.youtube.com/watch?v=XDT9_CRnWpo&list=PLClOO0BdaFaMY9nBNz_s4ZbYDyF2Xx5ja",
    "https://www.youtube.com/watch?v=Qt2jW5JBtwI&list=PLClOO0BdaFaN2iSB4m9nM4CXdKSMYHxLP",
    "https://www.youtube.com/watch?v=gsgTiPYMYe8&list=PLClOO0BdaFaNZQ2xYdKz07gK08b7WTQzG",
    "https://www.youtube.com/watch?v=E8Cvrfv0SVQ&list=PLClOO0BdaFaM9iItZGHRlax0GPpnoxZYQ",
    "https://www.youtube.com/watch?v=lP4h309SCUM&list=PLClOO0BdaFaNnSB2F8pEjM5IJRF3rx1Rj",
    "https://www.youtube.com/watch?v=m9Toqz6aJs8&list=PLClOO0BdaFaO56ApsIz_WBPAySrm5gZYD",
    "https://www.youtube.com/watch?v=sVtZVmveELI&list=PLClOO0BdaFaPnyUuT8t_nIobLLpjaHTb9",
    "https://www.youtube.com/watch?v=R3t_llxrIGM&list=PLClOO0BdaFaMlORnNQByG5QdxMTaB6pF-",
]

# File to save all links
output_file = "youtube_video_links.csv"

# Extract and save video links to CSV
with open(output_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Playlist Title", "Video URL"])  # Header row

    for playlist_url in playlist_urls:
        playlist_title, video_links = extract_youtube_links(playlist_url)
        if video_links:
            for link in video_links:
                writer.writerow([playlist_title, link])  # Write playlist title and video URL

print(f"Extracted video links from {len(playlist_urls)} playlists.")
print(f"Links saved to {output_file}")