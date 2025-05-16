import feedparser
import json
import os
import time  # Import time module
from tqdm import tqdm  # Import tqdm for the progress bar
import requests  # Import requests for making API requests
# from progress.spinner import Spinner  # Import the Spinner class from progress

# Function to load the API key from the config file
def load_api_key(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config['Gemini_API_key'], config['Notion_secret']  # Return both keys

# Function to create a new page in Notion with a description
def create_notion_page_with_description(notion_token, database_id, title, description):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": description
                            }
                        }
                    ]
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("✅ Page created successfully with description.")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

# Function to load RSS feeds from a JSON file
def load_feeds(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    print("\nReading the JSON file with RSS feeds...")
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
def fetch_feeds(feed_urls, history_file='history.json', limit_per_feed=2):
    summaries = []
    new_entries_count = 0  # Initialize a counter for new entries
    
    # Read last entries from history.json
    last_entries = read_last_entries(history_file)

    # Initialize the progress bar with total number of feeds
    with tqdm(total=len(feed_urls), desc="Fetching feeds", unit="feed") as pbar:
        for url in feed_urls:
            print(f"Processing feed: {url}")  # Indicate which feed is being processed
            feed = feedparser.parse(url)
            new_entries = []  # List to hold new entries for this feed
            
            # Get the last seen entry for this feed
            last_seen_entry = last_entries.get(url, None)

            # Process up to limit_per_feed entries per feed
            entry_count = 0
            for entry in feed.entries:  # No limit on entries
                if last_seen_entry and entry.link == last_seen_entry:  # Check if the entry is the same as the last processed
                    print(f"No new updates for feed: {url}\n")  # Indicate no new updates
                    break  # Skip to the next feed
                
                if entry_count >= limit_per_feed:  # Stop after processing limit_per_feed entries
                    break
                
                title = entry.title
                summary = entry.summary if 'summary' in entry else None
                new_entries.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.link  # Store the link for the last entry
                })
                entry_count += 1  # Increment the entry count

            # Update the last seen entry for this feed with the topmost entry
            if feed.entries:  # Check if there are any entries
                last_entries[url] = feed.entries[0].link  # Update with the link of the topmost entry

            summaries.extend(new_entries)  # Add new entries to the summaries list
            new_entries_count += len(new_entries)  # Count new entries
            
            pbar.update(1)  # Increment the progress bar by 1 for each feed processed

    # Write the updated last entries back to history.json
    write_last_entries(history_file, last_entries)

    if new_entries_count == 0:
        print("\nThere are no new updates.")  # Indicate no new updates
        return  # Exit the function early if there are no new entries

    print(f"\nTotal new entries found: {new_entries_count}")  # Summarize new entries

    # Send summaries to Gemini API (this part is assumed to be here)
    # send_to_gemini_api(summaries)

    print("\nAll feeds have been fetched.")  # Indicate the end of the fetching process
    return summaries

# Function to call the Gemini API with the fetched summaries
def call_gemini_api(summaries, custom_prompt=""):
    api_key = load_api_key('config/config.json')[0]  # Load the API key
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
    start_time = time.time()  # Record the start time

    # Load API keys from the config file
    gemini_api_key, notion_token = load_api_key('config/config.json')  # Load both keys

    # Load feeds from the JSON file
    RSS_FEEDS = load_feeds('feeds.json')
    
    # Fetch summaries without checking history.json
    summaries = fetch_feeds(RSS_FEEDS)

    # Check if there are new entries before proceeding
    if not summaries:  # If summaries is empty, there are no new entries
        print("\nNo new entries to send to Gemini API. Exiting script.")
        exit()  # Exit the script early

    print()  # New line 
    
    # Prepare the custom prompt
    with open("prompts/prompt-2.txt", 'r') as f:
        custom_prompt = f.read().strip()  # Read and strip any extra whitespace

    # custom_prompt = "I'm going to share a list of website post/article titles and their summaries. Your task is to create a concise, insightful overview of the topics covered. Group the articles by high-level category such as Health, Sports, Technology, Education, Marketing and so on. For each category: write a short executive summary (2–4 sentences) of what's being discussed in all the articles from that category, then include bullet points listing key themes, insights, data points, numbers, key takeaways or trends. Use numbers from articles if available and relevant. Convert to metric units: km, m, kg, etc. Avoid repeating ideas, and keep the output brief but information-rich. Summarize in easy to understand English. Include the URL (in parenthesis at the end of line) of the article for each bullet point summary only if the article is deemed important enough to include. Wish me a good read."

    # Call the Gemini API with the fetched summaries and the custom prompt
    gemini_response = call_gemini_api(summaries, custom_prompt)
    
    if gemini_response:
        # Write the response to a markdown file with the current timestamp
        timestamp = time.strftime("%y%m%d-%H%M%S")  # Get the current timestamp
        output_file = f"summaries/summary-{timestamp}.md"  # Create the filename
        with open(output_file, 'w') as f:
            f.write(gemini_response)  # Write the response to the file
        print(f"\nResponse written to {output_file}")  # Confirm the file write

        # Load the summary from the markdown file
        if os.path.exists(output_file):  # Check if the file exists
            with open(output_file, 'r') as f:
                description = f.read()  # Read the content of the markdown file

            # Set the title as the name of the markdown file (without the extension)
            title = os.path.splitext(os.path.basename(output_file))[0]  # Get the filename without extension

            # Create a new page in Notion with the summary
            database_id = "1f5183e9c9f880d5a450e0cd861358d6"  # Replace with your Notion database ID
            create_notion_page_with_description(notion_token, database_id, title, description)
        else:
            print(f"❌ Summary file {output_file} does not exist.")

    end_time = time.time()  # Record the end time
    runtime = end_time - start_time  # Calculate the runtime

    # Display runtime in a user-friendly format
    if runtime < 60:
        print(f"\nScript runtime: {runtime:.2f} seconds")
    else:
        minutes = int(runtime // 60)
        seconds = runtime % 60
        print(f"\nScript runtime: {minutes} minutes and {seconds:.2f} seconds")