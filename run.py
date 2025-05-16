import feedparser
import json
import os
from tqdm import tqdm  # Import tqdm for the progress bar
import requests  # Import requests for making API requests
import datetime  # Ensure this import is at the top of your file

# Function to load the API key from the config file
def load_api_key(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config['Gemini_API_key']

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
    
    # Define the cutoff date
    cutoff_date = datetime.datetime(2025, 5, 10)

    for url in tqdm(feed_urls, desc="Fetching feeds", unit="feed"):
        print(f"Processing feed: {url}")  # Indicate which feed is being processed
        feed = feedparser.parse(url)
        new_entries = []  # List to hold new entries for this feed
        
        for entry in feed.entries[:limit_per_feed]:  # Pull up to 2 entries
            # Check for published date
            if 'published_parsed' in entry:
                published_date = datetime.datetime(*entry.published_parsed[:6])  # Convert to datetime object
            elif 'pubDate' in entry:
                published_date = datetime.datetime(*entry.pubDate_parsed[:6])  # Convert to datetime object
            else:
                continue  # Skip if no date is available
            
            # Check if the entry's published date is after the cutoff date
            if published_date < cutoff_date:
                continue  # Skip entries published before the cutoff date
            
            title = entry.title
            summary = entry.summary if 'summary' in entry else None
            new_entries.append({
                'title': title,
                'summary': summary,
                'link': entry.link  # Store the link for the last entry
            })

        summaries.extend(new_entries)  # Add new entries to the summaries list

    return summaries

# Function to call the Gemini API with the fetched summaries
def call_gemini_api(summaries, custom_prompt=""):
    api_key = load_api_key('config/config.json')  # Load the API key
    # api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"  # Use the specified endpoint
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"  # Use the specified endpoint

    # Prepare the data to send to the Gemini API
    input_text = "\n".join(
        [f"Title: {summary['title']}\nSummary: {summary['summary']}\nURL: {summary['link']}" for summary in summaries]
    )
    
    prompt_data = {
        "contents": [
            {
                "parts": [
                    {"text": custom_prompt},  # Use the custom prompt provided
                    {"text": input_text}
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Calculate lengths
    custom_prompt_length = len(custom_prompt)
    input_length = len(input_text)
    total_input_length = custom_prompt_length + input_length
    
    # Make the API request
    response = requests.post(api_url, json=prompt_data, headers=headers)
    
    if response.status_code == 200:
        # Extract the human-readable output from the response
        if 'candidates' in response.json() and len(response.json()['candidates']) > 0:
            output_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            output_length = len(output_text)
            
            # Calculate total length and percentage
            total_length = custom_prompt_length + input_length + output_length
            percentage_of_limit = (total_length / 4000000) * 100
            
            print(f"Custom Prompt Length: {custom_prompt_length} characters")
            print(f"Total Input Length: {total_input_length} characters")
            print(f"Output Length from Gemini: {output_length} characters")
            print(f"Total Length: {total_length} characters")
            print(f"Percentage of token limit (4M chars): {percentage_of_limit:.2f}%")
            
            return output_text
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
    # Read the custom prompt from the prompt-2.txt file
    with open("prompts/prompt-2.txt", 'r') as f:
        custom_prompt = f.read().strip()  # Read and strip any extra whitespace

    # custom_prompt = "I'm going to share a list of website post/article titles and their summaries. Your task is to create a concise, insightful overview of the topics covered. Group the articles by high-level category such as Health, Sports, Technology, Education, Marketing and so on. For each category: write a short executive summary (2–4 sentences) of what's being discussed in all the articles from that category, then include bullet points listing key themes, insights, data points, numbers, key takeaways or trends. Use numbers from articles if available and relevant. Convert to metric units: km, m, kg, etc. Avoid repeating ideas, and keep the output brief but information-rich. Summarize in easy to understand English. Include the URL (in parenthesis at the end of line) of the article for each bullet point summary only if the article is deemed important enough to include. Wish me a good read."

    # Call the Gemini API with the fetched summaries and the custom prompt
    gemini_response = call_gemini_api(summaries, custom_prompt)
    
    if gemini_response:
        # Print the human-readable output
        print("Gemini API Response:\n")
        print(gemini_response)  # Output the response in a readable format