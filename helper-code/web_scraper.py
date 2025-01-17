import requests
from bs4 import BeautifulSoup
import csv

# Function to extract talk links from a single URL
def extract_talk_links(url):
    response = requests.get(url)
    response.raise_for_status()  # Ensure the request was successful
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract all talk links in the order they appear
    talk_links = []
    for link in soup.find_all('a', href=True):
        if '/study/general-conference/' in link['href'] and '?lang=eng' in link['href']:
            full_url = f"https://www.churchofjesuschrist.org{link['href']}"
            talk_links.append(full_url)

    return talk_links

# List of URLs to scrape
urls = [
    "https://www.churchofjesuschrist.org/study/general-conference/2024/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2024/04?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2023/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2023/04?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2022/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2022/04?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2021/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2021/04?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2020/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2020/04?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2019/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2019/04?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2018/10?lang=eng",
    "https://www.churchofjesuschrist.org/study/general-conference/2018/04?lang=eng",
]

# Collect all extracted links
all_links = []

for url in urls:
    try:
        print(f"Fetching talks from: {url}")
        links = extract_talk_links(url)
        all_links.extend(links)  # Add links in the order they appear
    except Exception as e:
        print(f"Error processing {url}: {e}")

# Remove duplicates while maintaining order
unique_links = list(dict.fromkeys(all_links))

# Save to CSV file
output_file = "talk_links_ordered.csv"
with open(output_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Talk URL"])  # Header
    for link in unique_links:
        writer.writerow([link])

print(f"Saved {len(unique_links)} unique talk links to {output_file}")