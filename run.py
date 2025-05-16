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
def fetch_feeds(feed_urls, limit_per_feed=2):
    summaries = []
    print("Fetching feeds...")
    
    for url in tqdm(feed_urls, desc="Fetching feeds", unit="feed"):
        print(f"Processing feed: {url}")  # Indicate which feed is being processed
        feed = feedparser.parse(url)
        new_entries = []  # List to hold new entries for this feed
        
        for entry in feed.entries[:limit_per_feed]:  # Pull up to 2 entries
            title = entry.title
            summary = entry.summary if 'summary' in entry else None
            new_entries.append({
                'title': title,
                'summary': summary,
                'link': entry.link  # Store the link for the last entry
            })

        summaries.extend(new_entries)  # Add new entries to the summaries list

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
                    # {"text": "I need a summary of the following webpage content:"},
                    {"text": "\n".join(
                        [f"Title: {summary['title']}\nSummary: {summary['summary']}" for summary in summaries]
                    )},
                    # {"text": "Don't use Markdown for formatting. No text in bold or italics."},
                    # {"text": "Be brief and to the point but try to not skip the numbers."},
                    # {"text": "Use bullet points (-) for easy scanning if possible."},
                    # {"text": "Avoid repetition."},
                    # {"text": "Summarize in Polish."},
                    # {"text": "Convert numbers to metric units such as km, m, cm, kg."}
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
        # Extract the human-readable output from the response
        if 'candidates' in response.json() and len(response.json()['candidates']) > 0:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            print("No valid candidates returned.")
            return "No summary available."
    else:
        print(f"Error calling Gemini API: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Load feeds from the JSON file
    RSS_FEEDS = load_feeds('feeds.json')
    
    # Fetch summaries without checking history.json
    summaries = fetch_feeds(RSS_FEEDS, limit_per_feed=2)
    print()  # New line 

    # Prepare the custom prompt
    custom_prompt = "I'm gonna share a list of website post/articles' titles and summaries. I want you to prepare a summary of topics covered in these articles. I want you to group them by topic, eg. Health/Sport/Technology/Education/IT/Marketing and then under each topic group you can put an executive summary kind of text explaining what's being discussed. If there are many articles for any given group you can rank them. Don't use Markdown in formatting, don't use any formatting. Summarize in English. Avoid repetition. Convert numbers to metrics units such as km, m, cm."

    # Call the Gemini API with the fetched summaries and the custom prompt
    gemini_response = call_gemini_api(summaries, custom_prompt)
    
    if gemini_response:
        # Print the human-readable output
        print("Gemini API Response:\n")
        print(gemini_response)  # Output the response in a readable format