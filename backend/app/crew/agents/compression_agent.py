from crewai import Agent
from app.services.llm_provider import get_crewai_compression_llm


# OPTIMIZATION: Use smaller, faster llama-3-8b for compression instead of 70b models
llm = get_crewai_compression_llm(temperature=0.3)


def create_compression_agent():
    return Agent(
        role="Document Compression Specialist",
        goal=(
            "Summarize and compress long research paper chunks without losing meaning. "
            "Produce compact, information-dense summaries that preserve important details."
        ),
        backstory=(
            "You specialize in condensing long academic texts into concise, accurate summaries. "
            "You never remove important content—only compress."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False
    )
