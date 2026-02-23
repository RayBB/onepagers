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

## LLM Provider Configuration

This project uses LiteLLM to easily switch between different LLM providers. Set `LITELLM_MODEL` environment variable to switch providers.

### API Keys

LiteLLM automatically picks up API keys from environment variables. Set the key for your provider:

| Provider | Env Variable |
|----------|-------------|
| Z.AI (direct) | `ZAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Gemini | `GEMINI_API_KEY` |

### Provider Examples

**Z.AI (Direct Subscription)**
```bash
LITELLM_MODEL=zai/glm-4.7
LITELLM_MODEL=openrouter/z-ai/glm-4.5-air:free
LITELLM_MODEL=gemini/gemini-3-pro-preview
```

