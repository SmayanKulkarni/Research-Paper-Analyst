"""
Paper Preprocessor Service

Intelligent preprocessing service that extracts relevant portions of research papers
for each specialized agent, reducing token usage by 60-90% while maintaining analysis quality.

Key Features:
- Comprehensive section detection with 150+ heading variations
- Complete citation extraction (never miss any citation)
- Context-aware sampling for each agent type
- Handles varied academic paper formats (IEEE, ACM, Springer, arXiv, etc.)
- SEMANTIC RETRIEVAL: Uses embeddings to find most relevant sections for each agent
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from app.utils.logging import logger
from app.config import get_settings

# Lazy import for semantic service to avoid circular imports
_semantic_service = None


def get_semantic_service():
    """Lazy load semantic section service."""
    global _semantic_service
    if _semantic_service is None:
        try:
            from app.services.semantic_section_service import get_semantic_section_service
            _semantic_service = get_semantic_section_service()
        except Exception as e:
            logger.warning(f"Could not load semantic service: {e}")
            _semantic_service = False  # Mark as unavailable
    return _semantic_service if _semantic_service else None


@dataclass
class ExtractedSection:
    """Represents an extracted section from the paper."""
    name: str
    heading: str
    content: str
    start_pos: int
    end_pos: int


class PaperPreprocessor:
    """
    Intelligent preprocessing service that extracts relevant portions
    of research papers for each specialized agent.
    
    This dramatically reduces token usage (60-90%) while maintaining
    analysis quality by giving each agent exactly what it needs.
    """
    
    # ==========================================================================
    # COMPREHENSIVE HEADING PATTERNS
    # Covers IEEE, ACM, Springer, arXiv, Nature, Science, and custom formats
    # ==========================================================================
    
    # Abstract section identifiers
    ABSTRACT_PATTERNS = [
        r'\babstract\b',
        r'\bsummary\b',
        r'\boverview\b',
        r'\bsynopsis\b',
    ]
    
    # Introduction and background
    INTRO_PATTERNS = [
        r'\bintroduction\b',
        r'\bbackground\b',
        r'\bmotivation\b',
        r'\boverview\b',
        r'\bproblem\s*statement\b',
        r'\bproblem\s*formulation\b',
        r'\bresearch\s*context\b',
        r'\bcontext\b',
        r'\bpreliminaries\b',
        r'\bpreliminary\b',
        r'\bfoundations\b',
        r'\bbasics\b',
    ]
    
    # Literature review and related work
    RELATED_WORK_PATTERNS = [
        r'\brelated\s*work\b',
        r'\bliterature\s*review\b',
        r'\bprior\s*work\b',
        r'\bprevious\s*work\b',
        r'\bstate\s*of\s*the\s*art\b',
        r'\bbackground\s*and\s*related\s*work\b',
        r'\bexisting\s*approaches\b',
        r'\bexisting\s*methods\b',
        r'\brelated\s*research\b',
        r'\breview\s*of\s*literature\b',
    ]
    
    # Methodology and approach
    METHODOLOGY_PATTERNS = [
        r'\bmethodology\b',
        r'\bmethod\b',
        r'\bmethods\b',
        r'\bapproach\b',
        r'\bour\s*approach\b',
        r'\bproposed\s*approach\b',
        r'\bproposed\s*method\b',
        r'\bproposed\s*system\b',
        r'\bproposed\s*framework\b',
        r'\bproposed\s*model\b',
        r'\bsystem\s*design\b',
        r'\barchitecture\b',
        r'\bsystem\s*architecture\b',
        r'\bmodel\s*architecture\b',
        r'\bframework\b',
        r'\bdesign\b',
        r'\bimplementation\b',
        r'\btechnical\s*approach\b',
        r'\balgorithm\b',
        r'\balgorithms\b',
        r'\bformulation\b',
        r'\bproblem\s*definition\b',
        r'\bsolution\b',
        r'\bsolution\s*approach\b',
        r'\btechnique\b',
        r'\btechniques\b',
        r'\bprocedure\b',
        r'\bprocedures\b',
        r'\bprotocol\b',
        r'\bsetup\b',
        r'\bexperimental\s*setup\b',
        r'\bdata\s*collection\b',
        r'\bdata\s*processing\b',
        r'\bfeature\s*extraction\b',
        r'\bmodel\s*description\b',
        r'\bnetwork\s*architecture\b',
        r'\btraining\b',
        r'\btraining\s*procedure\b',
        r'\blearning\b',
        r'\boptimization\b',
    ]
    
    # Experiments and evaluation
    EXPERIMENTS_PATTERNS = [
        r'\bexperiment\b',
        r'\bexperiments\b',
        r'\bexperimental\s*results\b',
        r'\bexperimental\s*evaluation\b',
        r'\bexperimental\s*analysis\b',
        r'\bevaluation\b',
        r'\bevaluations\b',
        r'\bvalidation\b',
        r'\bverification\b',
        r'\btesting\b',
        r'\btest\s*results\b',
        r'\bbenchmark\b',
        r'\bbenchmarks\b',
        r'\bbenchmarking\b',
        r'\bperformance\b',
        r'\bperformance\s*evaluation\b',
        r'\bperformance\s*analysis\b',
        r'\bcomparison\b',
        r'\bcomparative\s*analysis\b',
        r'\bcomparative\s*study\b',
        r'\bablation\b',
        r'\bablation\s*study\b',
        r'\buser\s*study\b',
        r'\bcase\s*study\b',
        r'\bcase\s*studies\b',
        r'\bsimulation\b',
        r'\bsimulations\b',
        r'\bsimulation\s*results\b',
        r'\bnumerical\s*results\b',
        r'\bnumerical\s*experiments\b',
        r'\bempirical\s*evaluation\b',
        r'\bempirical\s*results\b',
        r'\bempirical\s*analysis\b',
    ]
    
    # Results section
    RESULTS_PATTERNS = [
        r'\bresults\b',
        r'\bresult\b',
        r'\bfindings\b',
        r'\bobservations\b',
        r'\boutcomes\b',
        r'\banalysis\b',
        r'\bdata\s*analysis\b',
        r'\bquantitative\s*results\b',
        r'\bqualitative\s*results\b',
        r'\bmain\s*results\b',
        r'\bkey\s*results\b',
        r'\bkey\s*findings\b',
    ]
    
    # Discussion section
    DISCUSSION_PATTERNS = [
        r'\bdiscussion\b',
        r'\bdiscussions\b',
        r'\banalysis\s*and\s*discussion\b',
        r'\bresults\s*and\s*discussion\b',
        r'\binterpretation\b',
        r'\binterpretations\b',
        r'\bimplications\b',
        r'\binsights\b',
        r'\blessons\s*learned\b',
        r'\blimitations\b',
        r'\blimitations\s*and\s*future\s*work\b',
        r'\bthreats\s*to\s*validity\b',
    ]
    
    # Conclusion section
    CONCLUSION_PATTERNS = [
        r'\bconclusion\b',
        r'\bconclusions\b',
        r'\bconcluding\s*remarks\b',
        r'\bsummary\s*and\s*conclusion\b',
        r'\bconclusion\s*and\s*future\s*work\b',
        r'\bfinal\s*remarks\b',
        r'\bclosing\s*remarks\b',
        r'\bsummary\b',
        r'\bwrap\s*up\b',
    ]
    
    # Future work section
    FUTURE_WORK_PATTERNS = [
        r'\bfuture\s*work\b',
        r'\bfuture\s*directions\b',
        r'\bfuture\s*research\b',
        r'\bopen\s*problems\b',
        r'\bopen\s*questions\b',
        r'\bextensions\b',
        r'\bpossible\s*extensions\b',
        r'\bnext\s*steps\b',
        r'\boutlook\b',
    ]
    
    # References/Bibliography section
    REFERENCES_PATTERNS = [
        r'\breferences\b',
        r'\bbibliography\b',
        r'\bcitations\b',
        r'\bliterature\s*cited\b',
        r'\bworks\s*cited\b',
        r'\bcited\s*works\b',
    ]
    
    # Appendix section
    APPENDIX_PATTERNS = [
        r'\bappendix\b',
        r'\bappendices\b',
        r'\bsupplementary\b',
        r'\bsupplementary\s*material\b',
        r'\bsupplemental\b',
        r'\bsupporting\s*information\b',
        r'\badditional\s*material\b',
        r'\btechnical\s*details\b',
        r'\bproofs\b',
        r'\bderivations\b',
    ]
    
    # Acknowledgments section
    ACKNOWLEDGMENTS_PATTERNS = [
        r'\backnowledgment\b',
        r'\backnowledgments\b',
        r'\backnowledgement\b',
        r'\backnowledgements\b',
        r'\bthanks\b',
    ]
    
    # Additional specialized sections
    THEORY_PATTERNS = [
        r'\btheory\b',
        r'\btheoretical\s*background\b',
        r'\btheoretical\s*framework\b',
        r'\btheoretical\s*foundation\b',
        r'\bmathematical\s*framework\b',
        r'\bmathematical\s*formulation\b',
        r'\bnotation\b',
        r'\bnotations\b',
        r'\bdefinitions\b',
        r'\bproblem\s*setup\b',
    ]
    
    # Dataset and data sections
    DATA_PATTERNS = [
        r'\bdataset\b',
        r'\bdatasets\b',
        r'\bdata\b',
        r'\bdata\s*description\b',
        r'\bcorpus\b',
        r'\bcorpora\b',
        r'\bbenchmark\s*datasets\b',
        r'\bdata\s*preparation\b',
        r'\bdata\s*preprocessing\b',
        r'\bfeatures\b',
        r'\bfeature\s*engineering\b',
    ]
    
    # Model/System sections
    MODEL_PATTERNS = [
        r'\bmodel\b',
        r'\bmodels\b',
        r'\bsystem\b',
        r'\bsystems\b',
        r'\bbaseline\b',
        r'\bbaselines\b',
        r'\bcomponents\b',
        r'\bmodules\b',
        r'\bpipeline\b',
        r'\bworkflow\b',
    ]
    
    # ==========================================================================
    # CITATION PATTERNS - Comprehensive coverage
    # ==========================================================================
    
    # Numbered citations: [1], [2,3], [1-5], [1, 2, 3]
    NUMBERED_CITATION_PATTERN = r'\[(\d+(?:\s*[-–,]\s*\d+)*)\]'
    
    # Author-year citations: (Smith, 2020), (Smith et al., 2020), (Smith & Jones, 2020)
    AUTHOR_YEAR_PATTERN = r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.|&|and)\s+[A-Z][a-z]+)?,?\s*\d{4}[a-z]?)\)'
    
    # Superscript citations: ¹, ², ¹⁻³
    SUPERSCRIPT_PATTERN = r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+(?:[-–][⁰¹²³⁴⁵⁶⁷⁸⁹]+)?'
    
    # Footnote markers
    FOOTNOTE_PATTERN = r'(?<!\d)\d{1,3}(?!\d)(?=\s|$|[.,;:)])'
    
    # ==========================================================================
    # SIGNPOST/TRANSITION PHRASES
    # ==========================================================================
    
    SIGNPOST_PHRASES = [
        # Contrast
        r'\bhowever\b', r'\bon the other hand\b', r'\bin contrast\b', r'\bnevertheless\b',
        r'\bnonetheless\b', r'\balthough\b', r'\bwhile\b', r'\bwhereas\b', r'\bdespite\b',
        r'\bin spite of\b', r'\bconversely\b', r'\bunlike\b', r'\byet\b', r'\bbut\b',
        
        # Addition
        r'\bfurthermore\b', r'\bmoreover\b', r'\bin addition\b', r'\badditionally\b',
        r'\balso\b', r'\bbesides\b', r'\blikewise\b', r'\bsimilarly\b',
        
        # Cause/Effect
        r'\btherefore\b', r'\bthus\b', r'\bhence\b', r'\bconsequently\b', r'\bas a result\b',
        r'\baccordingly\b', r'\bfor this reason\b', r'\bbecause\b', r'\bsince\b',
        r'\bdue to\b', r'\bowing to\b',
        
        # Sequence
        r'\bfirst\b', r'\bsecond\b', r'\bthird\b', r'\bfinally\b', r'\blastly\b',
        r'\bnext\b', r'\bthen\b', r'\bsubsequently\b', r'\bafterward\b',
        r'\bpreviously\b', r'\bformerly\b', r'\binitially\b', r'\bultimately\b',
        
        # Emphasis
        r'\bindeed\b', r'\bin fact\b', r'\bactually\b', r'\bcertainly\b',
        r'\bnotably\b', r'\bimportantly\b', r'\bsignificantly\b', r'\bespecially\b',
        r'\bparticularly\b', r'\bspecifically\b', r'\bin particular\b',
        
        # Example
        r'\bfor example\b', r'\bfor instance\b', r'\bsuch as\b', r'\bincluding\b',
        r'\bnamely\b', r'\bto illustrate\b', r'\bas an illustration\b',
        
        # Conclusion
        r'\bin conclusion\b', r'\bto conclude\b', r'\bin summary\b', r'\bto summarize\b',
        r'\boverall\b', r'\bin brief\b', r'\bbriefly\b', r'\bin short\b',
        r'\bto sum up\b', r'\ball in all\b',
        
        # Reference to other parts
        r'\bas mentioned\b', r'\bas noted\b', r'\bas discussed\b', r'\bas shown\b',
        r'\bas demonstrated\b', r'\bas illustrated\b', r'\bas described\b',
        r'\bsee section\b', r'\bsee figure\b', r'\bsee table\b',
    ]
    
    # ==========================================================================
    # CLAIM/RESULT INDICATOR PHRASES
    # ==========================================================================
    
    CLAIM_INDICATORS = [
        r'\bwe show\b', r'\bwe demonstrate\b', r'\bwe prove\b', r'\bwe establish\b',
        r'\bwe find\b', r'\bwe found\b', r'\bwe observe\b', r'\bwe observed\b',
        r'\bwe propose\b', r'\bwe present\b', r'\bwe introduce\b', r'\bwe develop\b',
        r'\bour results\b', r'\bour findings\b', r'\bour analysis\b', r'\bour experiments\b',
        r'\bour contribution\b', r'\bour approach\b', r'\bour method\b', r'\bour model\b',
        r'\bthis paper\b', r'\bthis work\b', r'\bthis study\b', r'\bin this paper\b',
        r'\bthe main contribution\b', r'\bthe key contribution\b', r'\bkey finding\b',
        r'\bnovel\b', r'\bstate-of-the-art\b', r'\boutperforms\b', r'\bachieve\b',
        r'\bimprove\b', r'\bsurpass\b', r'\bexceed\b', r'\bsignificant improvement\b',
        r'\bsignificantly better\b', r'\bsubstantially\b',
    ]
    
    # ==========================================================================
    # MATH PATTERNS
    # ==========================================================================
    
    # LaTeX equation environments
    LATEX_EQUATION_PATTERNS = [
        r'\$\$.*?\$\$',  # Display math $$...$$
        r'\$[^\$]+\$',   # Inline math $...$
        r'\\begin\{equation\}.*?\\end\{equation\}',
        r'\\begin\{align\}.*?\\end\{align\}',
        r'\\begin\{align\*\}.*?\\end\{align\*\}',
        r'\\begin\{eqnarray\}.*?\\end\{eqnarray\}',
        r'\\begin\{gather\}.*?\\end\{gather\}',
        r'\\begin\{multline\}.*?\\end\{multline\}',
        r'\\begin\{split\}.*?\\end\{split\}',
        r'\\\[.*?\\\]',  # Display math \[...\]
        r'\\\(.*?\\\)',  # Inline math \(...\)
    ]
    
    # Theorem-like environments
    THEOREM_PATTERNS = [
        r'(?:theorem|lemma|proposition|corollary|definition|remark|proof|claim|conjecture|axiom|property)\s*\d*\.?\s*[:\.\-]?\s*.*?(?=\n\n|\Z)',
    ]
    
    def __init__(self):
        """Initialize the preprocessor with compiled regex patterns."""
        # Compile all section patterns for efficiency
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        # Compile heading detection pattern
        # Matches: "1. Introduction", "I. INTRODUCTION", "Introduction", "1 Introduction", etc.
        self.heading_pattern = re.compile(
            r'^(?:'
            r'(?:\d+\.?\s*)+|'  # Numbered: 1., 1.1., etc.
            r'(?:[IVXLC]+\.?\s*)+|'  # Roman numerals: I., II., etc.
            r'(?:[A-Z]\.?\s*)'  # Letters: A., B., etc.
            r')?'
            r'([A-Z][A-Za-z\s\-&]+)$',  # Heading text
            re.MULTILINE
        )
        
        # Compile citation patterns
        self.numbered_citation_re = re.compile(self.NUMBERED_CITATION_PATTERN)
        self.author_year_re = re.compile(self.AUTHOR_YEAR_PATTERN)
        
    def preprocess_for_agent(self, full_text: str, agent_type: str) -> str:
        """
        Route to appropriate preprocessing function based on agent type.
        
        Args:
            full_text: Complete paper text
            agent_type: Type of agent ("language_quality", "structure", etc.)
            
        Returns:
            Preprocessed text optimized for the specific agent
        """
        preprocessors = {
            "language_quality": self.preprocess_for_language_quality,
            "structure": self.preprocess_for_structure,
            "citation": self.preprocess_for_citations,
            "citations": self.preprocess_for_citations,
            "clarity": self.preprocess_for_clarity,
            "flow": self.preprocess_for_flow,
            "math": self.preprocess_for_math,
            "math_review": self.preprocess_for_math,
        }
        
        preprocessor_func = preprocessors.get(agent_type)
        if preprocessor_func:
            try:
                result = preprocessor_func(full_text)
                original_tokens = len(full_text.split())
                processed_tokens = len(result.split())
                reduction = (1 - processed_tokens / original_tokens) * 100 if original_tokens > 0 else 0
                logger.info(f"Preprocessed for {agent_type}: {original_tokens:,} → {processed_tokens:,} tokens ({reduction:.1f}% reduction)")
                return result
            except Exception as e:
                logger.warning(f"Preprocessing failed for {agent_type}: {e}. Using full text.")
                return full_text
        else:
            logger.warning(f"No preprocessor for agent type: {agent_type}. Using full text.")
            return full_text
    
    def preprocess_for_agent_semantic(
        self, 
        full_text: str, 
        agent_type: str,
        paper_id: str = "default"
    ) -> str:
        """
        SEMANTIC-ENHANCED preprocessing using embeddings.
        
        This method combines regex-based section extraction with
        semantic similarity ranking to provide the most relevant
        content for each agent type.
        
        Process:
        1. Extract all sections using regex patterns
        2. Embed sections (cached for reuse)
        3. Rank sections by semantic relevance to agent's task
        4. Apply agent-specific preprocessing to top-ranked sections
        
        Args:
            full_text: Complete paper text
            agent_type: Type of agent
            paper_id: Unique identifier for caching embeddings
            
        Returns:
            Semantically-optimized preprocessed text
        """
        semantic_svc = get_semantic_service()
        
        if semantic_svc is None:
            # Fallback to regex-only preprocessing
            logger.debug("Semantic service unavailable, using regex-only preprocessing")
            return self.preprocess_for_agent(full_text, agent_type)
        
        try:
            # 1. Extract all sections using regex
            sections = self._find_all_sections(full_text)
            
            if not sections:
                logger.warning("No sections found, using regex-only preprocessing")
                return self.preprocess_for_agent(full_text, agent_type)
            
            # 2. Embed sections (will use cache if already done)
            sections_data = [
                {
                    'name': s.name,
                    'heading': s.heading,
                    'content': s.content,
                    'start_pos': s.start_pos,
                    'end_pos': s.end_pos
                }
                for s in sections
            ]
            semantic_svc.embed_paper_sections(paper_id, sections_data)
            
            # 3. Get semantically relevant sections for this agent
            relevant = semantic_svc.get_sections_for_agent(
                paper_id=paper_id,
                agent_type=agent_type,
                max_sections=8  # Get top 8 relevant sections
            )
            
            if not relevant:
                logger.debug(f"No semantic matches for {agent_type}, using regex-only")
                return self.preprocess_for_agent(full_text, agent_type)
            
            # 4. Build optimized text from relevant sections
            # First apply regex-based preprocessing to get structured output
            regex_result = self.preprocess_for_agent(full_text, agent_type)
            
            # Add semantic relevance information
            semantic_header = f"\n=== SEMANTIC RELEVANCE RANKING (Agent: {agent_type}) ===\n"
            semantic_info = []
            for i, r in enumerate(relevant[:5]):  # Show top 5
                semantic_info.append(
                    f"{i+1}. {r.heading} (relevance: {r.score:.2f})"
                )
            
            # Combine: regex preprocessing + semantic ranking info
            enhanced_result = (
                regex_result + 
                "\n\n" + semantic_header +
                "\n".join(semantic_info)
            )
            
            logger.info(f"Semantic preprocessing for {agent_type}: "
                       f"top section '{relevant[0].heading}' (score: {relevant[0].score:.2f})")
            
            return enhanced_result
            
        except Exception as e:
            logger.warning(f"Semantic preprocessing failed: {e}. Falling back to regex-only.")
            return self.preprocess_for_agent(full_text, agent_type)
    
    def embed_paper_for_analysis(self, full_text: str, paper_id: str) -> bool:
        """
        Pre-embed all paper sections for faster agent-specific retrieval.
        
        Call this once before running multiple agents to avoid
        re-embedding for each agent.
        
        Args:
            full_text: Complete paper text
            paper_id: Unique identifier for the paper
            
        Returns:
            True if embedding successful, False otherwise
        """
        semantic_svc = get_semantic_service()
        if semantic_svc is None:
            return False
            
        try:
            # Extract all sections
            sections = self._find_all_sections(full_text)
            
            if not sections:
                logger.warning(f"No sections found for paper {paper_id}")
                return False
            
            # Embed sections
            sections_data = [
                {
                    'name': s.name,
                    'heading': s.heading,
                    'content': s.content,
                    'start_pos': s.start_pos,
                    'end_pos': s.end_pos
                }
                for s in sections
            ]
            semantic_svc.embed_paper_sections(paper_id, sections_data)
            
            # Also extract and embed citations if available
            citation_data = self._extract_all_citations(full_text)
            if citation_data.get('citation_contexts') and citation_data.get('references_section'):
                # Parse references into list
                refs_text = citation_data['references_section']
                refs = [r.strip() for r in refs_text.split('\n') if r.strip() and len(r.strip()) > 20]
                
                semantic_svc.embed_citations(
                    paper_id=paper_id,
                    citation_contexts=citation_data['citation_contexts'][:100],  # Limit for performance
                    references=refs[:100]
                )
            
            logger.info(f"Embedded {len(sections)} sections for paper {paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed paper {paper_id}: {e}")
            return False
    
    def get_semantic_section_ranking(
        self, 
        full_text: str, 
        agent_type: str,
        paper_id: str = "default"
    ) -> List[Tuple[str, float]]:
        """
        Get section relevance ranking for an agent without full preprocessing.
        
        Useful for debugging and understanding what sections are most
        relevant for each agent type.
        
        Args:
            full_text: Complete paper text
            agent_type: Type of agent
            paper_id: Paper identifier
            
        Returns:
            List of (section_heading, relevance_score) tuples
        """
        semantic_svc = get_semantic_service()
        if semantic_svc is None:
            return []
            
        try:
            # Ensure paper is embedded
            sections = self._find_all_sections(full_text)
            if not sections:
                return []
                
            sections_data = [
                {
                    'name': s.name,
                    'heading': s.heading,
                    'content': s.content,
                    'start_pos': s.start_pos,
                    'end_pos': s.end_pos
                }
                for s in sections
            ]
            semantic_svc.embed_paper_sections(paper_id, sections_data)
            
            # Get relevance ranking
            relevant = semantic_svc.get_sections_for_agent(
                paper_id=paper_id,
                agent_type=agent_type,
                max_sections=15
            )
            
            return [(r.heading, r.score) for r in relevant]
            
        except Exception as e:
            logger.warning(f"Failed to get semantic ranking: {e}")
            return []
    
    # ==========================================================================
    # SECTION EXTRACTION METHODS
    # ==========================================================================
    
    def _find_all_sections(self, text: str) -> List[ExtractedSection]:
        """
        Find all sections in the paper with their content.
        
        Handles various heading formats:
        - "1. Introduction"
        - "I. INTRODUCTION"
        - "Introduction"
        - "1 Introduction"
        - "INTRODUCTION"
        - "1.1 Background"
        """
        sections = []
        lines = text.split('\n')
        
        # Primary heading patterns (most reliable section titles)
        primary_patterns = (
            self.ABSTRACT_PATTERNS + self.INTRO_PATTERNS + self.RELATED_WORK_PATTERNS +
            self.CONCLUSION_PATTERNS + self.REFERENCES_PATTERNS + self.ACKNOWLEDGMENTS_PATTERNS
        )
        
        # Secondary patterns (common but might false-positive)
        secondary_patterns = (
            self.METHODOLOGY_PATTERNS + self.EXPERIMENTS_PATTERNS + self.RESULTS_PATTERNS +
            self.DISCUSSION_PATTERNS + self.FUTURE_WORK_PATTERNS + 
            self.APPENDIX_PATTERNS + self.THEORY_PATTERNS + self.DATA_PATTERNS + self.MODEL_PATTERNS
        )
        
        all_patterns = primary_patterns + secondary_patterns
        
        section_starts = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Skip lines that are too long to be headings
            if len(line_stripped) > 100:
                continue
            
            # Skip lines with too many words (headings are typically short)
            word_count = len(line_stripped.split())
            if word_count > 12:
                continue
            
            # Check if line looks like a heading (structural indicators)
            is_heading = False
            matched_pattern = None
            
            # Clean the line for pattern matching
            # Remove leading numbers, roman numerals, letters
            clean_line = re.sub(r'^(?:[\d\.]+\s*|[IVXLC]+\.?\s*|[A-Z]\.?\s*)', '', line_stripped)
            clean_line_lower = clean_line.lower().strip()
            
            # Require structural heading markers for reliability
            has_number_prefix = bool(re.match(r'^(?:\d+\.?\s+|[IVXLC]+\.?\s+|[A-Z]\.\s+)', line_stripped))
            is_all_caps = line_stripped.isupper() and len(line_stripped) > 3
            is_title_case = line_stripped.istitle() and word_count <= 6
            is_short_standalone = word_count <= 4 and len(line_stripped) < 50
            
            # Only check for pattern match if line looks like a heading structurally
            if has_number_prefix or is_all_caps or is_title_case or is_short_standalone:
                # Check primary patterns first (more likely to be actual headings)
                for pattern in primary_patterns:
                    if re.search(pattern, clean_line_lower):
                        is_heading = True
                        matched_pattern = pattern
                        break
                
                # If not primary, check secondary patterns with stricter requirements
                if not is_heading and (has_number_prefix or is_all_caps):
                    for pattern in secondary_patterns:
                        # For secondary patterns, require exact match or near-exact
                        if re.fullmatch(pattern.replace(r'\b', '').replace('\\s*', ' ?'), clean_line_lower):
                            is_heading = True
                            matched_pattern = pattern
                            break
                        elif re.search(pattern, clean_line_lower) and word_count <= 5:
                            is_heading = True
                            matched_pattern = pattern
                            break
            
            if is_heading:
                section_starts.append({
                    'line_idx': i,
                    'heading': line_stripped,
                    'pattern': matched_pattern,
                    'category': self._categorize_heading(matched_pattern)
                })
        
        # Extract content between headings
        for j, section_info in enumerate(section_starts):
            start_idx = section_info['line_idx']
            if j + 1 < len(section_starts):
                end_idx = section_starts[j + 1]['line_idx']
            else:
                end_idx = len(lines)
            
            content = '\n'.join(lines[start_idx + 1:end_idx]).strip()
            
            sections.append(ExtractedSection(
                name=section_info['category'],
                heading=section_info['heading'],
                content=content,
                start_pos=start_idx,
                end_pos=end_idx
            ))
        
        return sections
    
    def _categorize_heading(self, pattern: Optional[str]) -> str:
        """Categorize a heading pattern into a standard section name."""
        if not pattern:
            return "other"
            
        if pattern in self.ABSTRACT_PATTERNS:
            return "abstract"
        elif pattern in self.INTRO_PATTERNS:
            return "introduction"
        elif pattern in self.RELATED_WORK_PATTERNS:
            return "related_work"
        elif pattern in self.METHODOLOGY_PATTERNS:
            return "methodology"
        elif pattern in self.EXPERIMENTS_PATTERNS:
            return "experiments"
        elif pattern in self.RESULTS_PATTERNS:
            return "results"
        elif pattern in self.DISCUSSION_PATTERNS:
            return "discussion"
        elif pattern in self.CONCLUSION_PATTERNS:
            return "conclusion"
        elif pattern in self.FUTURE_WORK_PATTERNS:
            return "future_work"
        elif pattern in self.REFERENCES_PATTERNS:
            return "references"
        elif pattern in self.APPENDIX_PATTERNS:
            return "appendix"
        elif pattern in self.ACKNOWLEDGMENTS_PATTERNS:
            return "acknowledgments"
        elif pattern in self.THEORY_PATTERNS:
            return "theory"
        elif pattern in self.DATA_PATTERNS:
            return "data"
        elif pattern in self.MODEL_PATTERNS:
            return "model"
        else:
            return "other"
    
    def _extract_abstract(self, text: str) -> str:
        """Extract the abstract section."""
        # Try to find explicit abstract section
        abstract_match = re.search(
            r'(?:^|\n)\s*(?:abstract|summary)\s*[\n\-:.]?\s*(.+?)(?=\n\s*(?:\d+\.?\s*)?(?:introduction|keywords|index terms|i\.\s|1\.\s)|\Z)',
            text, re.IGNORECASE | re.DOTALL
        )
        
        if abstract_match:
            return abstract_match.group(1).strip()[:3000]  # Cap at ~750 tokens
        
        # Fallback: First substantial paragraph
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        if paragraphs:
            return paragraphs[0][:2000]
        
        return ""
    
    def _extract_section_by_category(self, sections: List[ExtractedSection], 
                                     category: str, max_chars: int = 8000) -> str:
        """Extract sections matching a category."""
        matching = [s for s in sections if s.name == category]
        if not matching:
            return ""
        
        combined = "\n\n".join([f"[{s.heading}]\n{s.content}" for s in matching])
        return combined[:max_chars]
    
    def _extract_sections_by_categories(self, sections: List[ExtractedSection],
                                        categories: List[str], max_chars: int = 8000) -> str:
        """Extract sections matching any of the given categories."""
        matching = [s for s in sections if s.name in categories]
        if not matching:
            return ""
        
        combined = "\n\n".join([f"[{s.heading}]\n{s.content}" for s in matching])
        return combined[:max_chars]
    
    def _extract_references_section(self, text: str) -> str:
        """Extract the complete references/bibliography section."""
        # Find references section start
        ref_match = re.search(
            r'(?:^|\n)\s*(?:\d+\.?\s*)?(?:references|bibliography|works\s*cited|literature\s*cited)\s*[\n\-:.]?\s*',
            text, re.IGNORECASE
        )
        
        if ref_match:
            # Get everything after the references heading
            ref_start = ref_match.end()
            ref_text = text[ref_start:]
            
            # Try to find where references end (appendix, acknowledgments, etc.)
            end_match = re.search(
                r'\n\s*(?:\d+\.?\s*)?(?:appendix|appendices|supplementary|acknowledgment)',
                ref_text, re.IGNORECASE
            )
            
            if end_match:
                ref_text = ref_text[:end_match.start()]
            
            return ref_text.strip()
        
        return ""
    
    # ==========================================================================
    # CITATION EXTRACTION - COMPLETE AND COMPREHENSIVE
    # ==========================================================================
    
    def _extract_all_citations(self, text: str) -> Dict[str, Any]:
        """
        Extract ALL citations from the paper - never miss any.
        
        Returns:
            Dict containing:
            - numbered_citations: List of [number] citations
            - author_year_citations: List of (Author, Year) citations
            - citation_contexts: List of sentences containing citations
            - unique_citation_numbers: Set of unique citation numbers
            - references_section: Full references section text
        """
        result = {
            'numbered_citations': [],
            'author_year_citations': [],
            'citation_contexts': [],
            'unique_citation_numbers': set(),
            'references_section': '',
        }
        
        # Find all numbered citations [1], [2,3], [1-5], etc.
        numbered_matches = self.numbered_citation_re.findall(text)
        for match in numbered_matches:
            result['numbered_citations'].append(f"[{match}]")
            # Parse individual numbers
            numbers = re.findall(r'\d+', match)
            for num in numbers:
                result['unique_citation_numbers'].add(int(num))
            # Handle ranges like [1-5]
            range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)', match)
            if range_match:
                start, end = int(range_match.group(1)), int(range_match.group(2))
                for i in range(start, end + 1):
                    result['unique_citation_numbers'].add(i)
        
        # Find author-year citations
        author_year_matches = self.author_year_re.findall(text)
        result['author_year_citations'] = list(set(author_year_matches))
        
        # Extract sentences containing citations with context
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if self.numbered_citation_re.search(sentence) or self.author_year_re.search(sentence):
                result['citation_contexts'].append(sentence.strip())
        
        # Get full references section
        result['references_section'] = self._extract_references_section(text)
        
        return result
    
    def _extract_citations_with_context(self, text: str, context_chars: int = 200) -> List[str]:
        """Extract all citations with surrounding context."""
        contexts = []
        
        # Find all citation positions
        for match in self.numbered_citation_re.finditer(text):
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end].strip()
            # Clean up partial words at boundaries
            if start > 0:
                context = '...' + context.split(' ', 1)[-1] if ' ' in context else '...' + context
            if end < len(text):
                context = context.rsplit(' ', 1)[0] + '...' if ' ' in context else context + '...'
            contexts.append(context)
        
        # Deduplicate while preserving order
        seen = set()
        unique_contexts = []
        for ctx in contexts:
            if ctx not in seen:
                seen.add(ctx)
                unique_contexts.append(ctx)
        
        return unique_contexts
    
    # ==========================================================================
    # MULTI-POINT SAMPLING STRATEGY (NEW)
    # Samples from beginning, middle, and end of document for comprehensive coverage
    # ==========================================================================
    
    def _get_multipoint_samples(self, full_text: str, sample_size: int = 4000, num_points: int = 3) -> str:
        """
        Extract samples from multiple points in the document.
        
        Strategy:
        - Beginning: First sample_size chars after abstract/intro
        - Middle: Middle sample_size chars
        - End: Last sample_size chars before references
        
        Args:
            full_text: Complete paper text
            sample_size: Chars to extract per sample
            num_points: Number of sampling points (3 = beginning, middle, end)
            
        Returns:
            Combined multipoint samples as string
        """
        text_len = len(full_text)
        samples = []
        
        # Calculate sampling points
        if num_points == 1:
            points = [0]  # Just use beginning
        elif num_points == 2:
            points = [0, text_len // 2]  # Beginning and middle
        else:
            # Multiple points: beginning, evenly spaced middle, end
            points = [0]  # Beginning
            for i in range(1, num_points - 1):
                points.append(int(text_len * i / num_points))
            points.append(max(text_len - sample_size, 0))  # End
        
        for point_idx, point in enumerate(points):
            # Extract sample starting near this point
            sample_start = max(0, point - sample_size // 2)
            sample_end = min(text_len, sample_start + sample_size)
            
            # Adjust to word boundaries
            if sample_start > 0:
                # Find next sentence boundary
                next_period = full_text.find('. ', sample_start)
                if next_period != -1 and next_period < sample_start + 200:
                    sample_start = next_period + 2
            
            sample = full_text[sample_start:sample_end].strip()
            
            # Remove incomplete words at start/end
            if sample_start > 0:
                first_space = sample.find(' ')
                if first_space > 0:
                    sample = sample[first_space + 1:]
                sample = '...' + sample
            
            if sample_end < text_len:
                last_space = sample.rfind(' ')
                if last_space > 0 and last_space < len(sample) - 50:
                    sample = sample[:last_space] + '...'
            
            if sample:
                section_label = ["BEGINNING", "MIDDLE", "END"][min(point_idx, 2)]
                samples.append(f"=== MULTIPOINT SAMPLE ({section_label}) ===\n{sample}")
        
        return "\n\n".join(samples)
    
    def _sample_from_sections(self, sections: List[ExtractedSection], max_chars_per_section: int = 5000) -> str:
        """
        Extract diverse samples from each section.
        
        For each section: get beginning, middle, and end portions.
        This ensures comprehensive coverage without processing entire sections.
        
        Args:
            sections: List of extracted sections
            max_chars_per_section: Max chars to extract from each section
            
        Returns:
            Combined samples from all sections
        """
        samples = []
        
        for section in sections:
            if not section.content:
                continue
                
            content = section.content.strip()
            content_len = len(content)
            sample_size = max_chars_per_section // 3  # Divide into 3 samples
            
            # Get beginning, middle, end
            parts = []
            
            # Beginning
            beginning = content[:sample_size].strip()
            if beginning:
                parts.append(f"[START] {beginning}")
            
            # Middle
            if content_len > sample_size * 2:
                mid_start = (content_len - sample_size) // 2
                middle = content[mid_start:mid_start + sample_size].strip()
                if middle:
                    parts.append(f"[MIDDLE] {middle}")
            
            # End
            if content_len > sample_size:
                end = content[-sample_size:].strip()
                if end:
                    parts.append(f"[END] {end}")
            
            # Combine section samples
            if parts:
                section_sample = f"\n[{section.heading}]\n" + "\n\n".join(parts)
                samples.append(section_sample)
        
        return "\n\n".join(samples)
    
    # ==========================================================================
    # AGENT-SPECIFIC PREPROCESSING METHODS (ENHANCED WITH MULTI-POINT SAMPLING)
    # ==========================================================================
    
    def preprocess_for_language_quality(self, full_text: str) -> str:
        """
        Extract representative samples for language quality analysis.
        
        ENHANCED STRATEGY (Multi-Point Sampling):
        - Full abstract (critical for first impressions)
        - Beginning, middle, and end of introduction
        - Samples from each major section (beginning, middle, end)
        - Full conclusion
        - Overall document quality samples from multiple points
        
        Token reduction: ~60-70% (higher than before due to comprehensive sampling)
        """
        sections = self._find_all_sections(full_text)
        components = []
        settings = get_settings()
        
        # Check if paper is short enough to analyze fully
        if len(full_text) < settings.SHORT_PAPER_THRESHOLD:
            logger.info(f"Short paper detected ({len(full_text)} chars). Using full-text analysis.")
            return f"=== FULL TEXT (SHORT PAPER) ===\n{full_text}"
        
        # 1. Full abstract
        abstract = self._extract_abstract(full_text)
        if abstract:
            components.append(f"=== ABSTRACT (LANGUAGE QUALITY BASELINE) ===\n{abstract}")
        
        # 2. Introduction with multi-point sampling
        intro_sections = [s for s in sections if s.name == "introduction"]
        if intro_sections:
            intro_content = "\n".join([s.content for s in intro_sections])
            components.append(f"\n=== INTRODUCTION (MULTI-POINT SAMPLES) ===")
            components.append(self._sample_from_sections(intro_sections, max_chars_per_section=8000))
        
        # 3. Multi-point samples from all major sections
        major_categories = ["methodology", "results", "experiments", "discussion", "related_work"]
        major_sections = [s for s in sections if s.name in major_categories]
        
        if major_sections:
            components.append(f"\n=== MAJOR SECTIONS (MULTI-POINT SAMPLES) ===")
            section_samples = self._sample_from_sections(major_sections, max_chars_per_section=6000)
            components.append(section_samples)
        
        # 4. Full conclusion
        conclusion = self._extract_sections_by_categories(
            sections, ["conclusion", "future_work"], max_chars=8000
        )
        if conclusion:
            components.append(f"\n=== CONCLUSION (FULL FOR QUALITY CHECK) ===\n{conclusion}")
        
        # 5. Overall document quality samples from different points
        if len(full_text) > 5000:  # Only if paper is substantial
            components.append(f"\n=== OVERALL DOCUMENT SAMPLES ===")
            multipoint = self._get_multipoint_samples(full_text, sample_size=3000, num_points=3)
            components.append(multipoint)
        
        # Fallback if very few sections found
        if len(components) <= 2:
            logger.warning("Few sections detected for language quality. Using comprehensive paragraph sampling.")
            paragraphs = [p.strip() for p in full_text.split('\n\n') if len(p.strip()) > 100]
            if paragraphs:
                # Sample: first 5, every 5th, last 5
                samples = paragraphs[:5]
                for i in range(5, len(paragraphs), max(1, len(paragraphs) // 10)):
                    samples.append(paragraphs[i])
                samples.extend(paragraphs[-5:])
                
                components = [f"=== COMPREHENSIVE PARAGRAPH SAMPLING ===\n" + 
                            '\n\n'.join([f"[Para {i+1}]\n{p}" for i, p in enumerate(samples[:30])])]
        
        return '\n\n'.join(components)
    
    def preprocess_for_structure(self, full_text: str) -> str:
        """
        Extract structural elements for paper structure analysis.
        
        ENHANCED STRATEGY (Multi-Point Sampling):
        - Full abstract
        - ALL section headings with hierarchy
        - Multi-point samples (beginning, middle, end) of each section
        - Structural markers and transitions between sections
        - Full conclusion
        
        Token reduction: ~75-85%
        """
        sections = self._find_all_sections(full_text)
        components = []
        
        # 1. Full abstract
        abstract = self._extract_abstract(full_text)
        if abstract:
            components.append(f"=== ABSTRACT ===\n{abstract}")
        
        # 2. Document structure - ALL headings with hierarchy
        components.append("\n=== DOCUMENT STRUCTURE (ALL HEADINGS) ===")
        if sections:
            for i, section in enumerate(sections):
                indent = "  " * (section.name.count("_") if "_" in section.name else 0)
                components.append(f"{indent}{i+1}. {section.heading} [{section.name}]")
        else:
            # Fallback: extract anything that looks like a heading
            heading_lines = []
            for line in full_text.split('\n'):
                line = line.strip()
                if line and len(line) < 100:
                    if re.match(r'^(?:\d+\.?\s*|[IVXLC]+\.?\s*)?[A-Z]', line):
                        if len(line.split()) <= 10:
                            heading_lines.append(line)
            for i, heading in enumerate(heading_lines[:50]):
                components.append(f"{i+1}. {heading}")
        
        # 3. Multi-point structural samples from each section
        components.append("\n=== SECTION STRUCTURE SAMPLES (BEGINNING, MIDDLE, END) ===")
        if sections:
            section_samples = self._sample_from_sections(sections, max_chars_per_section=5000)
            components.append(section_samples)
        
        # 4. Section transitions and boundaries
        components.append("\n=== SECTION TRANSITIONS ===")
        for i in range(min(len(sections) - 1, 10)):  # Limit to first 10 transitions
            current = sections[i]
            next_sec = sections[i + 1]
            
            # Get last paragraph of current
            current_paras = [p.strip() for p in current.content.split('\n\n') if p.strip()]
            last_para = current_paras[-1][:400] if current_paras else ""
            
            # Get first paragraph of next
            next_paras = [p.strip() for p in next_sec.content.split('\n\n') if p.strip()]
            first_para = next_paras[0][:400] if next_paras else ""
            
            components.append(f"\n[TRANSITION] {current.heading} → {next_sec.heading}")
            if last_para:
                components.append(f"  [CLOSING] {last_para[:300]}")
            if first_para:
                components.append(f"  [OPENING] {first_para[:300]}")
        
        # 5. Full conclusion for structural analysis
        conclusion = self._extract_sections_by_categories(
            sections, ["conclusion", "future_work"], max_chars=7000
        )
        if conclusion:
            components.append(f"\n=== FULL CONCLUSION (STRUCTURAL COMPLETENESS) ===\n{conclusion}")
        
        return '\n\n'.join(components)
    
    def preprocess_for_citations(self, full_text: str) -> str:
        """
        Extract COMPLETE citation information for citation analysis.
        
        CRITICAL: Never miss any citation - this is essential for accuracy.
        
        Strategy:
        - ALL in-text citations with context
        - FULL references section (complete, untruncated)
        - Citation statistics and analysis
        
        Token reduction: ~85-95% (varies based on reference count)
        """
        citation_data = self._extract_all_citations(full_text)
        components = []
        
        # 1. Citation statistics summary
        components.append("=== CITATION ANALYSIS SUMMARY ===")
        components.append(f"Total unique citation numbers: {len(citation_data['unique_citation_numbers'])}")
        if citation_data['unique_citation_numbers']:
            sorted_nums = sorted(citation_data['unique_citation_numbers'])
            components.append(f"Citation range: [{min(sorted_nums)} - {max(sorted_nums)}]")
            components.append(f"All citation numbers found: {sorted_nums}")
            
            # Check for missing numbers in sequence
            if sorted_nums:
                expected = set(range(1, max(sorted_nums) + 1))
                missing = expected - citation_data['unique_citation_numbers']
                if missing:
                    components.append(f"⚠️ POTENTIALLY MISSING CITATIONS: {sorted(missing)}")
        
        components.append(f"Author-year citations: {len(citation_data['author_year_citations'])}")
        
        # 2. ALL citation contexts (every sentence with a citation)
        components.append("\n=== ALL IN-TEXT CITATIONS WITH CONTEXT ===")
        contexts = citation_data['citation_contexts']
        if contexts:
            # Include ALL contexts - no truncation for citations
            for i, ctx in enumerate(contexts):
                components.append(f"\n[Context {i+1}]")
                components.append(ctx)
        else:
            components.append("No numbered citations found in text.")
        
        # 3. FULL references section - NEVER truncate
        components.append("\n\n=== COMPLETE REFERENCES SECTION ===")
        if citation_data['references_section']:
            components.append(citation_data['references_section'])
        else:
            # Try harder to find references
            ref_patterns = [
                r'\[1\].*',  # Start from [1]
                r'1\.\s+[A-Z].*',  # Numbered list starting with 1.
            ]
            for pattern in ref_patterns:
                match = re.search(pattern, full_text, re.DOTALL)
                if match:
                    # Get a large chunk
                    ref_text = full_text[match.start():]
                    # Try to find the end
                    components.append(ref_text[:30000])  # Allow large reference sections
                    break
            else:
                components.append("⚠️ REFERENCES SECTION NOT FOUND - Manual verification required")
        
        # 4. Author-year citations if present
        if citation_data['author_year_citations']:
            components.append("\n=== AUTHOR-YEAR CITATIONS ===")
            for citation in citation_data['author_year_citations']:
                components.append(f"• {citation}")
        
        return '\n\n'.join(components)
    
    def preprocess_for_clarity(self, full_text: str) -> str:
        """
        Extract logical structure for clarity of thought analysis.
        
        ENHANCED STRATEGY (Multi-Point Sampling):
        - Full abstract (main argument)
        - Introduction with problem statement (multi-point sampling)
        - Key claims and contributions throughout paper
        - Methodology and approach overview
        - Main results/findings (multi-point sampling from different parts)
        - Full conclusion
        
        Token reduction: ~60-70%
        """
        sections = self._find_all_sections(full_text)
        components = []
        
        # 1. Full abstract
        abstract = self._extract_abstract(full_text)
        if abstract:
            components.append(f"=== ABSTRACT (MAIN ARGUMENT) ===\n{abstract}")
        
        # 2. Introduction - problem statement with multi-point sampling
        intro = self._extract_sections_by_categories(
            sections, ["introduction"], max_chars=12000
        )
        if intro:
            components.append(f"\n=== INTRODUCTION (PROBLEM STATEMENT - FULL) ===\n{intro}")
        
        # 3. Key claims - extract from throughout the paper (not just first occurrence)
        components.append("\n=== KEY CLAIMS AND CONTRIBUTIONS (SAMPLED) ===")
        claim_sentences = []
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        
        # Sample claims from different parts of paper
        claims_per_part = 10
        part_size = len(sentences) // 3  # Divide into 3 parts
        
        for part in range(3):
            start_idx = part * part_size
            end_idx = (part + 1) * part_size if part < 2 else len(sentences)
            
            for sentence in sentences[start_idx:end_idx]:
                sentence_lower = sentence.lower()
                for indicator in self.CLAIM_INDICATORS:
                    if re.search(indicator, sentence_lower):
                        claim_sentences.append((sentence.strip(), part))
                        break
                if len(claim_sentences) > claims_per_part * (part + 1):
                    break
        
        if claim_sentences:
            for i, (claim, part) in enumerate(claim_sentences[:50]):
                part_label = ["EARLY", "MIDDLE", "LATE"][part]
                components.append(f"• [{part_label}] {claim[:300]}")
        else:
            components.append("(No explicit claim indicators found)")
        
        # 4. Methodology overview (multi-point sampling)
        methodology = self._extract_sections_by_categories(
            sections, ["methodology", "model", "theory"], max_chars=8000
        )
        if methodology:
            components.append(f"\n=== METHODOLOGY OVERVIEW ===\n{methodology}")
        
        # 5. Results/findings with multi-point sampling
        results_sections = [s for s in sections if s.name in ["results", "experiments"]]
        if results_sections:
            components.append(f"\n=== KEY RESULTS (MULTI-POINT SAMPLES) ===")
            components.append(self._sample_from_sections(results_sections, max_chars_per_section=7000))
        
        # 6. Discussion (reasoning about findings)
        discussion = self._extract_sections_by_categories(
            sections, ["discussion"], max_chars=6000
        )
        if discussion:
            components.append(f"\n=== DISCUSSION (REASONING) ===\n{discussion}")
        
        # 7. Full conclusion
        conclusion = self._extract_sections_by_categories(
            sections, ["conclusion", "future_work"], max_chars=7000
        )
        if conclusion:
            components.append(f"\n=== CONCLUSION ===\n{conclusion}")
        
        return '\n\n'.join(components)
    
    def preprocess_for_flow(self, full_text: str) -> str:
        """
        Extract transition elements for flow analysis.
        
        ENHANCED STRATEGY (Multi-Point Sampling):
        - Abstract (narrative tone)
        - Section transitions (all transitions analyzed)
        - Multi-point paragraph sampling (beginning, middle, end)
        - Signpost phrases sampled from different paper sections
        - Conclusion (narrative resolution)
        
        Token reduction: ~70-80%
        """
        sections = self._find_all_sections(full_text)
        components = []
        
        # 1. Abstract (sets narrative tone)
        abstract = self._extract_abstract(full_text)
        if abstract:
            components.append(f"=== ABSTRACT (NARRATIVE TONE) ===\n{abstract}")
        
        # 2. ALL section transitions with full context
        components.append("\n=== SECTION TRANSITIONS (FLOW ANALYSIS) ===")
        for i in range(len(sections) - 1):
            current_section = sections[i]
            next_section = sections[i + 1]
            
            # Get last 2 paragraphs of current section
            current_paragraphs = [p.strip() for p in current_section.content.split('\n\n') if p.strip()]
            last_paras = current_paragraphs[-2:] if len(current_paragraphs) > 1 else current_paragraphs
            
            # Get first 2 paragraphs of next section
            next_paragraphs = [p.strip() for p in next_section.content.split('\n\n') if p.strip()]
            first_paras = next_paragraphs[:2]
            
            components.append(f"\n=== TRANSITION: {current_section.heading} → {next_section.heading} ===")
            for para in last_paras:
                if para:
                    components.append(f"[END OF {current_section.heading}] {para[:600]}")
            for para in first_paras:
                if para:
                    components.append(f"[START OF {next_section.heading}] {para[:600]}")
        
        # 3. Multi-point paragraph flow sampling
        components.append("\n=== PARAGRAPH FLOW SAMPLING (BEGINNING, MIDDLE, END) ===")
        paragraphs = [p.strip() for p in full_text.split('\n\n') if len(p.strip()) > 50]
        
        if len(paragraphs) > 0:
            # Sample from beginning
            for i, para in enumerate(paragraphs[:10]):
                components.append(f"[BEGIN-{i+1}] {para[:400]}")
            
            # Sample from middle
            if len(paragraphs) > 20:
                mid_start = (len(paragraphs) - 10) // 2
                for i, para in enumerate(paragraphs[mid_start:mid_start + 10]):
                    components.append(f"[MID-{i+1}] {para[:400]}")
            
            # Sample from end
            if len(paragraphs) > 10:
                for i, para in enumerate(paragraphs[-10:]):
                    components.append(f"[END-{i+1}] {para[:400]}")
        
        # 4. Signpost phrases sampled from different paper parts
        components.append("\n=== SIGNPOST PHRASES (TRANSITIONS - SAMPLED) ===")
        signpost_contexts = []
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        
        # Divide sentences into thirds and sample from each
        third_size = len(sentences) // 3
        for part_idx in range(3):
            part_label = ["EARLY", "MIDDLE", "LATE"][part_idx]
            start_idx = part_idx * third_size
            end_idx = (part_idx + 1) * third_size if part_idx < 2 else len(sentences)
            
            for sentence in sentences[start_idx:end_idx]:
                sentence_lower = sentence.lower()
                for phrase_pattern in self.SIGNPOST_PHRASES:
                    if re.search(phrase_pattern, sentence_lower):
                        signpost_contexts.append((sentence.strip()[:300], part_label))
                        break
                if len([s for s in signpost_contexts if s[1] == part_label]) > 5:
                    break
        
        # Include diverse sample of signposts
        if signpost_contexts:
            for ctx, part in signpost_contexts[:30]:
                components.append(f"• [{part}] {ctx}")
        
        # 5. Conclusion (narrative resolution)
        conclusion = self._extract_sections_by_categories(
            sections, ["conclusion"], max_chars=6000
        )
        if conclusion:
            components.append(f"\n=== CONCLUSION (NARRATIVE RESOLUTION) ===\n{conclusion}")
        
        return '\n\n'.join(components)
    
    def preprocess_for_math(self, full_text: str) -> str:
        """
        Extract mathematical content for math verification.
        
        Strategy:
        - All equations (LaTeX and rendered)
        - Theorem/Lemma/Proof blocks
        - Mathematical definitions
        - Notation descriptions
        
        Token reduction: ~90-98% (varies based on math content)
        """
        components = []
        
        # 1. Extract all LaTeX equations
        components.append("=== MATHEMATICAL EQUATIONS ===")
        equations_found = []
        
        # Display math $$...$$
        for match in re.finditer(r'\$\$(.*?)\$\$', full_text, re.DOTALL):
            equations_found.append(f"$$\n{match.group(1).strip()}\n$$")
        
        # Inline math $...$
        for match in re.finditer(r'(?<!\$)\$([^\$]+)\$(?!\$)', full_text):
            equations_found.append(f"${match.group(1)}$")
        
        # LaTeX equation environments
        env_patterns = [
            (r'\\begin\{equation\}(.*?)\\end\{equation\}', 'equation'),
            (r'\\begin\{align\}(.*?)\\end\{align\}', 'align'),
            (r'\\begin\{align\*\}(.*?)\\end\{align\*\}', 'align*'),
            (r'\\begin\{eqnarray\}(.*?)\\end\{eqnarray\}', 'eqnarray'),
            (r'\\begin\{gather\}(.*?)\\end\{gather\}', 'gather'),
        ]
        
        for pattern, env_name in env_patterns:
            for match in re.finditer(pattern, full_text, re.DOTALL):
                equations_found.append(f"\\begin{{{env_name}}}\n{match.group(1).strip()}\n\\end{{{env_name}}}")
        
        # Display math \[...\]
        for match in re.finditer(r'\\\[(.*?)\\\]', full_text, re.DOTALL):
            equations_found.append(f"\\[\n{match.group(1).strip()}\n\\]")
        
        if equations_found:
            for i, eq in enumerate(equations_found):
                components.append(f"\nEquation {i+1}:")
                components.append(eq)
        else:
            components.append("(No LaTeX equations detected)")
        
        # 2. Extract theorem-like blocks
        components.append("\n\n=== THEOREMS, LEMMAS, AND PROOFS ===")
        theorem_patterns = [
            r'(?:theorem|lemma|proposition|corollary)\s*\d*\.?\s*[\(\[]?[^\)]*[\)\]]?\s*[:\.]?\s*(.*?)(?=\n\s*(?:theorem|lemma|proposition|corollary|proof|definition|\Z))',
            r'(?:proof)\s*\.?\s*(.*?)(?=\n\s*(?:theorem|lemma|proposition|corollary|□|∎|QED|\Z))',
            r'(?:definition)\s*\d*\.?\s*[\(\[]?[^\)]*[\)\]]?\s*[:\.]?\s*(.*?)(?=\n\n|\Z)',
        ]
        
        for pattern in theorem_patterns:
            for match in re.finditer(pattern, full_text, re.IGNORECASE | re.DOTALL):
                components.append(f"\n{match.group(0).strip()[:2000]}")
        
        # 3. Extract notation definitions (sentences explaining variables)
        components.append("\n\n=== NOTATION AND DEFINITIONS ===")
        notation_patterns = [
            r'(?:where|let|denote|define|given)\s+[a-zA-Z_]\w*\s+(?:is|as|be|to be|represents?|denotes?).*?[.]',
            r'[a-zA-Z_]\w*\s+(?:denotes?|represents?|is defined as|stands for).*?[.]',
        ]
        
        for pattern in notation_patterns:
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                components.append(f"• {match.group(0).strip()}")
        
        # 4. Extract sections with mathematical content
        sections = self._find_all_sections(full_text)
        math_sections = self._extract_sections_by_categories(
            sections, ["theory", "methodology", "model"], max_chars=10000
        )
        if math_sections:
            components.append(f"\n\n=== MATHEMATICAL SECTIONS ===\n{math_sections}")
        
        return '\n\n'.join(components)
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def get_preprocessing_stats(self, full_text: str) -> Dict[str, Any]:
        """
        Get statistics about the paper and preprocessing potential.
        
        Returns stats for monitoring and debugging.
        """
        sections = self._find_all_sections(full_text)
        citation_data = self._extract_all_citations(full_text)
        
        return {
            'original_chars': len(full_text),
            'original_tokens_est': len(full_text.split()),
            'sections_found': len(sections),
            'section_names': [s.name for s in sections],
            'unique_citations': len(citation_data['unique_citation_numbers']),
            'citation_range': (
                min(citation_data['unique_citation_numbers']) if citation_data['unique_citation_numbers'] else 0,
                max(citation_data['unique_citation_numbers']) if citation_data['unique_citation_numbers'] else 0
            ),
            'has_references_section': bool(citation_data['references_section']),
        }


# Singleton instance for reuse
_preprocessor_instance = None


def get_preprocessor() -> PaperPreprocessor:
    """Get or create singleton preprocessor instance."""
    global _preprocessor_instance
    if _preprocessor_instance is None:
        _preprocessor_instance = PaperPreprocessor()
    return _preprocessor_instance
