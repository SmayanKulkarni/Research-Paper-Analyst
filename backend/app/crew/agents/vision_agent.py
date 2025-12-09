from crewai import Agent
from app.crew.tools.vision_tool import vision_tool
from app.services.llm_provider import get_crewai_vision_llm
from app.config import get_settings


def create_vision_agent():
    settings = get_settings()
    # Vision agent uses its dedicated vision model
    llm = get_crewai_vision_llm(model=settings.CREW_VISION_MODEL, temperature=0.1)
    
    return Agent(
        role="Scientific Image Reviewer",
        backstory=(
            "You analyze figures efficiently. One tool call per image, no retries."
            "Assume the figures are labelled in the pdf and go on only what is seen in the image."
            "Analyze the image thoroughly but concisely and try to find logical flaw only if extremely evident."
        ),
        goal="Analyze figures using vision tool. Call tool ONCE per image, then finish."
             " Have a proper concise summary of the image analysis in the final report, if images are blurry or unclear ignore them fully as they might mistakes from image extraction.",
        llm=llm,
        tools=[vision_tool],
        verbose=True,
        max_iter=2,  # Limited iterations
        max_retry_limit=0,  # No retries
    )