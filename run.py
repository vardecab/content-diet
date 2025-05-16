import feedparser
import json
import os
from tqdm import tqdm  # Import tqdm for the progress bar
import requests

def load_api_key(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data['Gemini_API_key']
# Function to load RSS feeds from a JSON file
def load_feeds(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    print("Reading the JSON file with RSS feeds...")
    print()  # New line 
    return data['feeds']

# Function to read the last processed entries from a JSON file
def read_last_entries(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error: history.json is not valid JSON. Initializing with empty data.")
                return {}  # Return an empty dictionary if JSON is invalid
    return {}

# Function to write the last processed entries to a JSON file
def write_last_entries(file_path, last_entries):
    with open(file_path, 'w') as f:
        json.dump(last_entries, f)

# Function to fetch and parse the feeds with a progress bar
def fetch_feeds(feed_urls, last_entries, limit_per_feed=2):
    summaries = []
    print("Fetching feeds...")
    
    for url in tqdm(feed_urls, desc="Fetching feeds", unit="feed"):
        feed = feedparser.parse(url)
        last_entry_id = last_entries.get(url)  # Get the last entry for this feed
        new_entries = []  # List to hold new entries for this feed
        for entry in feed.entries:
            # Check if the entry is new
            if last_entry_id and entry.link == last_entry_id:
                print("No new entries found for this feed.")
                break  # Exit if we reach the last processed entry
            new_entries.append(entry)  # Add new entry to the list

        # Limit to the specified number of new entries
        for entry in new_entries[:limit_per_feed]:
            title = entry.title
            summary = entry.summary if 'summary' in entry else None
            summaries.append({
                'title': title,
                'summary': summary,
                'link': entry.link  # Store the link for the last entry
            })

        # Update the last entry for this feed if there are new summaries
        if summaries:
            last_entries[url] = summaries[-1]['link']  # Update to the latest entry

    return summaries

def call_gemini_api(prompt):
    api_key = load_api_key('config/config.json')
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    # Gemini expects this structure
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        print(f"Error calling Gemini API: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Load feeds from the JSON file
    RSS_FEEDS = load_feeds('feeds.json')
    
    # Read the last processed entries
    last_entries = read_last_entries('history.json')
    
    # Fetch and print summaries
    summaries = fetch_feeds(RSS_FEEDS, last_entries)
    print()  # New line 
    for summary in summaries:
        print("-" * 40)  # Separator line for better readability
        print(f"Title: {summary['title']}")
        print(f"Summary: {summary['summary']}\n")

    # Write the updated last entries to the JSON file
    write_last_entries('history.json', last_entries)

    # Test the Gemini API with a simple prompt
    test_prompt = "hello Gemini"
    gemini_response = call_gemini_api(test_prompt)
    if gemini_response:
        print("Gemini API Response for test prompt:", gemini_response)