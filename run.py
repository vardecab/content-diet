import feedparser
import json
import os
import time  # Import time module
from tqdm import tqdm  # Import tqdm for the progress bar
import requests  # Import requests for making API requests
# from progress.spinner import Spinner  # Import the Spinner class from progress
import shutil  # Import shutil for copying files

# Function to load the API key from the config file
def load_api_key(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config['Gemini_API_key'], config['Notion_secret']  # Return both keys

# Function to create a new page in Notion with a description
# def create_notion_page_with_description(notion_token, database_id, title, description):
#     url = "https://api.notion.com/v1/pages"
#     headers = {
#         "Authorization": f"Bearer {notion_token}",
#         "Content-Type": "application/json",
#         "Notion-Version": "2022-06-28"
#     }
#     data = {
#         "parent": {"database_id": database_id},
#         "properties": {
#             "Name": {
#                 "title": [
#                     {
#                         "text": {
#                             "content": title
#                         }
#                     }
#                 ]
#             }
#         },
#         "children": [
#             {
#                 "object": "block",
#                 "type": "paragraph",
#                 "paragraph": {
#                     "rich_text": [
#                         {
#                             "type": "text",
#                             "text": {
#                                 "content": description
#                             }
#                         }
#                     ]
#                 }
#             }
#         ]
#     }

#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200:
#         print("\n✅ Page created successfully with description.")
#     else:
#         print(f"\n❌ Failed: {response.status_code} - {response.text}")

# Function to load RSS feeds from a JSON file
def load_feeds(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    # print("\nReading the JSON file with RSS feeds...")
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
        json.dump(last_entries, f, indent=4) # Added indent for readability

# Function to fetch and parse the feeds with a progress bar
def fetch_feeds(feed_urls, history_file='history.json'):
    summaries = []
    new_entries_count = 0
    feed_stats = {url: 0 for url in feed_urls}
    
    last_entries = read_last_entries(history_file) # Read history
    updated_last_entries = last_entries.copy() # Create a copy to update

    print("\nFetching feeds from URLs...")
    for url in tqdm(feed_urls, desc="Processing feeds"):
        feed = feedparser.parse(url)
        
        # Get the link of the last processed entry for this feed
        last_processed_link = last_entries.get(url)
        
        first_new_entry_link = None # To store the link of the newest entry processed in this run

        entries_processed_for_feed = 0
        
        # Process entries from newest to oldest (feedparser usually provides them this way)
        for entry in feed.entries:
            # Stop if we encounter the last processed entry
            if last_processed_link and entry.link == last_processed_link:
                break

            # Only process up to 10 new entries per feed
            # if entries_processed_for_feed >= 10:
            #     break

            # This is a new entry
            summaries.append({
                'title': entry.title,
                'link': entry.link,
                'summary': entry.summary if hasattr(entry, 'summary') else None
            })
            new_entries_count += 1
            entries_processed_for_feed += 1

            # Record the link of the very first new entry encountered (which is the newest)
            if first_new_entry_link is None:
                first_new_entry_link = entry.link

        # Update the history for this feed with the link of the newest entry processed
        # Only update if new entries were found for this feed
        if first_new_entry_link:
            updated_last_entries[url] = first_new_entry_link

        feed_stats[url] = entries_processed_for_feed # Count new entries processed

    # Write the updated history back to the file
    write_last_entries(history_file, updated_last_entries)

    print(f"\nLoaded {new_entries_count} new entries")
    print("\nNew entries per feed:")
    for url, count in feed_stats.items():
        print(f"- {url}: {count} {'entries' if count != 1 else 'entry'}")

    if new_entries_count == 0:
        print("\nNo new entries found.")
        return []

    proceed = input(f"\nFound {new_entries_count} new entries. Proceed with Gemini API call? (y/n): ").strip().lower()
    if proceed != 'y':
        print("\nAborting Gemini API call as requested.")
        return []

    return summaries

# Function to call the Gemini API with the fetched summaries
def call_gemini_api(summaries, custom_prompt=""):
    api_key = load_api_key('api/config.json')[0]  # Load the API key
    # api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"  # Use the specified endpoint
    # api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"  # Use the specified endpoint
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"  # Use the specified endpoint

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
            
            print(f"Custom prompt length: {custom_prompt_length} characters")
            print(f"Total input length: {total_input_length} characters / 4,194,304 ({total_input_length / 4194304:.2%})")
            print(f"Output length from Gemini: {output_length} characters / 32,768 ({output_length / 32768:.2%})")
            # print(f"Total length: {total_length} characters")
            # print(f"Percentage of token limit (4M chars): {percentage_of_limit:.2f}%")
            
            return output_text
        else:
            print("No valid candidates returned.")
            return "No summary available."
    else:
        print(f"Error calling Gemini API: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    start_time = time.time()  # Record the start time

    # Load API keys from the new api folder
    gemini_api_key, _notion_token = load_api_key('api/config.json')

    # Load feeds from the separated JSON files
    # print("\nReading the JSON files with RSS feeds...")
    website_feeds = load_feeds('feeds/feeds-websites.json')
    print("Reading websites RSS feeds...")
    x_feeds = load_feeds('feeds/feeds-x.json')
    print("Reading X RSS feeds...")
    youtube_feeds = load_feeds('feeds/feeds-youtube.json')  # Load YouTube feeds
    print("Reading YouTube RSS feeds...")
    RSS_FEEDS = website_feeds + x_feeds + youtube_feeds  # Combine all feeds
    
    # Fetch summaries, now using history.json to filter
    summaries = fetch_feeds(RSS_FEEDS, history_file='feeds/history.json') # Pass history file path

    # Check if there are new entries before proceeding
    if not summaries:  # If summaries is empty, there are no new entries
        print("\nNo new entries to send to Gemini API. Exiting script.")
        exit()  # Exit the script early

    print()  # New line 
    
    # Prepare the custom prompt
    # with open("prompts/prompt-2.txt", 'r') as f:
    with open("prompts/prompt-6.txt", 'r') as f:
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
        destination_folder = "/Users/q/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vaultomix/content-diet/summaries"
        shutil.copy(output_file, destination_folder)
        print("File copied successfully to Obsidian.")
        
        # Notion integration
        # Load the summary from the markdown file
        # if os.path.exists(output_file):  # Check if the file exists
        #     with open(output_file, 'r') as f:
        #         description = f.read()  # Read the content of the markdown file

        #     # Set the title as the name of the markdown file (without the extension)
        #     title = os.path.splitext(os.path.basename(output_file))[0]  # Get the filename without extension

        #     # Create a new page in Notion with the summary
        #     database_id = "1f5183e9c9f880d5a450e0cd861358d6"  # Replace with your Notion database ID
        #     create_notion_page_with_description(notion_token, database_id, title, description)
        # else:
        #     print(f"❌ Summary file {output_file} does not exist.")
        

    end_time = time.time()  # Record the end time
    runtime = end_time - start_time  # Calculate the runtime

    # Display runtime in a user-friendly format
    if runtime < 60:
        print(f"\nScript runtime: {runtime:.2f} seconds")
    else:
        minutes = int(runtime // 60)
        seconds = runtime % 60
        print(f"\nScript runtime: {minutes} minutes and {seconds:.2f} seconds")