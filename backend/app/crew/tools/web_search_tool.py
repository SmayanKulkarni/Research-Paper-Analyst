from crewai.tools import tool
from groq import Groq
from app.config import get_settings

settings = get_settings()


def _get_groq_model_name(model: str) -> str:
    """Strip groq/ prefix for direct Groq SDK calls."""
    if model.startswith("groq/"):
        return model[5:]  # Remove "groq/" prefix
    return model


@tool("Web Search")
def web_search(query: str):
    """
    Perform a live web search using Groq's browser_search tool and return summarized results.
    Use this tool when you need to find current information from the web.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    # Use GPT-OSS model which supports browser_search tool
    # Only openai/gpt-oss-* models support the browser_search tool
    model = "openai/gpt-oss-20b"
    
    try:
        resp = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the browser_search tool to find information."},
                {"role": "user", "content": f"Search the web for: {query}"}
            ],
            model=model,
            temperature=0.7,
            max_completion_tokens=settings.MAX_COMPLETION_TOKENS,
            top_p=1,
            stream=False,
            stop=None,
            tool_choice="auto",  # Let model decide if it needs to search
            tools=[{"type": "browser_search"}],
        )
        content = resp.choices[0].message.content
        return content if content else "No results found."
    except Exception as e:
        # Fall back to just using the model without browser_search
        resp = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ],
            model=model,
            temperature=0.7,
            max_completion_tokens=settings.MAX_COMPLETION_TOKENS,
        )
        content = resp.choices[0].message.content
        return content if content else "No results found."

