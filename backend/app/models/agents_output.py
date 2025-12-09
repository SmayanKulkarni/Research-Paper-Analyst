from pydantic import BaseModel, Field
from typing import List, Optional

class ProofreadingIssue(BaseModel):
    issue_type: str = Field(..., description="Type of issue e.g., Grammar, Clarity, Tone, Passive Voice")
    original_text: str = Field(..., description="The segment of text containing the issue")
    suggestion: str = Field(..., description="The corrected or improved version")
    explanation: str = Field(..., description="Brief explanation of why this change is needed")

class ProofreadingOutput(BaseModel):
    executive_summary: str = Field(..., description="A 1-2 sentence summary of the paper's writing quality")
    issues: List[ProofreadingIssue]

class StructureCheck(BaseModel):
    section: str = Field(..., description="Section being analyzed (e.g., Abstract, Introduction, Methods)")
    status: str = Field(..., description="One of: 'Good', 'Needs Improvement', 'Missing'")
    feedback: str = Field(..., description="Specific feedback on this section")

class StructureOutput(BaseModel):
    adherence_to_imrad: bool = Field(..., description="Does it follow Introduction-Methods-Results-Discussion?")
    checks: List[StructureCheck]
    general_recommendations: str

class ConsistencyIssue(BaseModel):
    description: str = Field(..., description="Description of the inconsistency")
    conflicting_segments: List[str] = Field(..., description="The two or more text segments that contradict each other")
    severity: str = Field(..., description="High, Medium, or Low")

class ConsistencyOutput(BaseModel):
    consistency_score: int = Field(..., description="Score out of 10 (10 being perfectly consistent)")
    issues: List[ConsistencyIssue]

class CitationVerification(BaseModel):
    claim_text: str = Field(..., description="The claim made in the paper")
    citation_ref: str = Field(..., description="The citation identifier e.g., [1] or (Author, 2020)")
    verdict: str = Field(..., description="Supported, Unsupported, or Unverified")
    notes: str = Field(..., description="Reasoning for the verdict based on the tool output")

class CitationOutput(BaseModel):
    verifications: List[CitationVerification]
    general_comment: str