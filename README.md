# content-diet

![maintenance-status](https://img.shields.io/badge/maintenance-experimental-blue.svg)
<br>
![](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)

>Playing with AI to build a personal daily news channel — one smart summary a day from YouTube, X, websites and newsletters I follow, all powered by RSS.

### Idea

Throw all your sources (newsletters, people on X, YouTube channels, websites you read) to AI and get a nice, short summary.

### Why? 

There’s just too much content every day. Most of it is noise, and a lot becomes irrelevant within 24 hours. 

I found myself spending too much time reading across YouTube, X, newsletters, and websites — only to realize most of it didn’t stick or help me grow. I needed a smarter, faster way to catch the valuable stuff without falling into a daily time sink. Ideally it's gonna be a podcast, but for now - it's a written digest.

Think of it as putting your information consumption on a _diet_ — cutting out the junk content and keeping only the nutritious bits that actually matter.

## Release History

Check [TODO](https://github.com/vardecab/content-diet/blob/main/TODO) file for the full changelog and roadmap.
<!-- v4
- When summary is ready, upload it to Notion so it's accessible on mobile.

v3
- Just look at the newest entries in each feed since the last time script was run.

v2
- Updated Gemini API to 2.0 Flash from 1.5 Flash.
- Improved the prompt.
- Showing token limit.

v1
- Gemini now prepares an easier-to-read summary with clear grouping by topic.
- Gemini now prepares a summary from articles in the RSS feeds.
- Calling Gemini now works.
- Initial release: gets titles and summaries from RSS feeds. -->

## Acknowledgements

- Cursor
- Gemini API
- 3rd party Python libs:
    - [feedparser](https://github.com/kurtmckee/feedparser) to read RSS feeds
    - [tqdm](https://github.com/tqdm/tqdm) to show progress bars in the terminal
    - [requests](https://github.com/psf/requests) to access feeds and APIs
- Obsidian

## License

This project is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). No commercial use allowed without permission.

## Contributing

![](https://img.shields.io/github/issues/vardecab/content-diet)

If you found a bug or want to propose a feature, feel free to visit [the Issues page](https://github.com/vardecab/content-diet/issues).