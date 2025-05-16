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

def call_gemini_api(summaries, custom_prompt=""):
    api_key = load_api_key('config/config.json')  # Load the API key
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"  # Use the specified endpoint

    # Prepare the data to send to the Gemini API
    prompt_data = {
        "contents": [
            {
                "parts": [
                    {"text": custom_prompt},  # Use the custom prompt provided
                    {"text": "\n".join(
                        [f"Title: {summary['title']}\nSummary: {summary['summary']}" for summary in summaries]
                    )},
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Make the API request
    response = requests.post(api_url, json=prompt_data, headers=headers)
    
    if response.status_code == 200:
        return response.json()  # Return the response from the API
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

    # Specify your custom prompt here
    custom_prompt = "I'm gonna share a list of website post/articles' titles and summaries. I want you to prepare a summary of topics covered in these articles. I want you to group them by topic, eg. Health/Sport/Technology/Education/IT/Marketing and then under each topic group you can put an executive summary kind of text explaining what's being discussed. If there are many articles for any given group you can rank them. Don't use Markdown in formatting, don't use any formatting. Summarize in English. Avoid repetition. Convert numbers to metrics units such as km, m, cm."  # <-- Add your prompt message here
    # Call the Gemini API with the fetched summaries and the custom prompt
    gemini_response = call_gemini_api(summaries, custom_prompt)
    if gemini_response:
        print("Gemini API Response:", gemini_response)