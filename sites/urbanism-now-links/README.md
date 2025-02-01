We collect a lot of links for Urbanism now.
It's kind of a pain to copy the titles and dates and categorize them.
We should focus more on writing a good summary of them.
However, that other information is important.

So what I'd like to do is create a simple webpage where we can paste a url and then have a new item created in the notion database with all the information extracted in the page.

A few main components here:
- Notion
    - Get database schema
    - Create row
- Fetch the page
    - Also we should support uploading screenshots or copy/pasting text for the future.
- Convert it to MD for the LLM
- Upload to LLM
- A UI to make this easy


I'm going to use Python because it's more common for data science.

`uv run main.py` to have it run through and update rows without AI summaries!
