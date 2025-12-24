import os
import time
from typing import Dict, List, Optional, Any
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from crewai import Crew, Process

from app.config import get_settings
# Consolidated agents with clarity and flow analysis
from app.crew.agents.language_quality_agent import create_language_quality_agent
from app.crew.agents.structure_agent import create_structure_agent
from app.crew.agents.citation_agent import create_citation_agent
from app.crew.agents.clarity_agent import create_clarity_agent
from app.crew.agents.flow_agent import create_flow_agent
from app.crew.agents.vision_agent import create_vision_agent

# Consolidated tasks
from app.crew.tasks.language_quality_task import create_language_quality_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.clarity_task import create_clarity_task
from app.crew.tasks.flow_task import create_flow_task
from app.crew.tasks.vision_task import create_vision_task

from app.crew.tools.pdf_tool import load_pdf
from app.services.paper_discovery import PaperDiscoveryService
from app.services.image_extractor import extract_images_from_pdf
from app.services.image_reference_filter import get_image_reference_filter
from app.services.pdf_report_generator import PDFReportGenerator
from app.services.paper_preprocessor import get_preprocessor
from app.services.citation_resolver import get_citation_resolver
from app.utils.logging import logger

settings = get_settings()


def run_with_retry(func, *args, max_retries=1, retry_delay=5.0, **kwargs):
    """
    Run a function with minimal retry logic - fail fast approach.
    Only retry once for rate limits, otherwise fail immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Only retry on rate limit (429) errors
            if ("429" in error_str or "rate" in error_str) and attempt < max_retries:
                logger.warning(f"Rate limit hit. Waiting {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # For all other errors (including empty responses), fail immediately
                logger.error(f"Task failed: {str(e)[:100]}")
                raise


class AnalysisOrchestratorService:
    """
    Service responsible for orchestrating the CrewAI analysis pipeline.
    
    ACCURACY-FIRST APPROACH (v4):
    - Dynamic token allocation based on actual PDF content
    - Each agent receives the full context it needs for thorough analysis
    - No arbitrary token limits - agents use what they need
    - Budget scales with document complexity (up to 300k tokens)
    - Structured final report compilation
    
    PDF reports are saved to: storage/reports/
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.token_usage = {
            "language_quality": 0,
            "structure": 0,
            "citation": 0,
            "clarity": 0,
            "flow": 0,
            "vision": 0,
            "total_estimated": 0
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (roughly 4 chars = 1 token)."""
        return len(text) // self.settings.CHARS_PER_TOKEN
    
    def _calculate_token_budget(self, text: str, num_images: int) -> Dict[str, int]:
        """
        Calculate token budget for each agent based on actual content.
        
        Strategy:
        - Base input: Full paper text tokens
        - Output: Proportional to task complexity
        - No artificial limits - accuracy is priority
        """
        text_tokens = self._estimate_tokens(text)
        
        # Log the paper stats
        logger.info(f"Paper Analysis:")
        logger.info(f"   - Text length: {len(text):,} characters")
        logger.info(f"   - Estimated tokens: {text_tokens:,}")
        logger.info(f"   - Images: {num_images}")
        
        # Calculate per-agent budgets
        # Each agent needs: input (paper) + output (analysis)
        # Output size scales with paper complexity
        
        base_output = self.settings.MAX_COMPLETION_TOKENS  # 4096
        
        # Language Quality: Needs full text, produces detailed feedback
        # Output scales with paper length (more text = more potential issues)
        lang_output = min(base_output * 2, max(base_output, text_tokens // 10))
        
        # Structure: Needs full text for section analysis
        struct_output = base_output
        
        # Citation: Needs full text to find all citations
        # More citations in longer papers = more output
        cite_output = min(base_output * 2, max(base_output, text_tokens // 15))
        
        # Clarity: Analyzes logical reasoning throughout paper
        clarity_output = min(base_output * 2, max(base_output, text_tokens // 12))
        
        # Flow: Analyzes transitions and narrative structure
        flow_output = min(base_output * 2, max(base_output, text_tokens // 12))
        
        # Vision: Based on number of images
        vision_output = min(num_images * 500, self.settings.MAX_VISION_TOKENS * num_images // 5) if num_images > 0 else 0
        
        budget = {
            "language_quality": {
                "input": text_tokens,
                "output": lang_output,
                "total": text_tokens + lang_output
            },
            "structure": {
                "input": text_tokens,
                "output": struct_output,
                "total": text_tokens + struct_output
            },
            "citation": {
                "input": text_tokens,
                "output": cite_output,
                "total": text_tokens + cite_output
            },
            "clarity": {
                "input": text_tokens,
                "output": clarity_output,
                "total": text_tokens + clarity_output
            },
            "flow": {
                "input": text_tokens,
                "output": flow_output,
                "total": text_tokens + flow_output
            },
            "vision": {
                "input": num_images * 1000,  # ~1k tokens per image
                "output": vision_output,
                "total": num_images * 1000 + vision_output
            }
        }
        
        # Calculate total
        total = sum(b["total"] for b in budget.values())
        budget["total_estimated"] = total
        
        logger.info(f"Token Budget Allocation:")
        for agent, alloc in budget.items():
            if isinstance(alloc, dict):
                logger.info(f"   - {agent}: {alloc['total']:,} tokens (in: {alloc['input']:,}, out: {alloc['output']:,})")
            else:
                logger.info(f"   - {agent}: {alloc:,} tokens")
        
        return budget
    
    def _extract_section_headings(self, text: str) -> str:
        """
        Extract section headings from paper for structure analysis.
        This allows structure agent to analyze organization without full text.
        """
        lines = text.split('\n')
        headings = []
        
        # Common section keywords in research papers
        section_keywords = [
            'abstract', 'introduction', 'background', 'related work',
            'methodology', 'methods', 'approach', 'experiments',
            'results', 'discussion', 'conclusion', 'future work',
            'references', 'appendix', 'acknowledgments'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Check if line looks like a heading
            if any(kw in line_lower for kw in section_keywords):
                headings.append(f"Line {i+1}: {line.strip()}")
            # Also check for numbered sections like "1. Introduction"
            elif line.strip() and len(line.strip()) < 100:
                if line.strip()[0].isdigit() or line.strip().isupper():
                    headings.append(f"Line {i+1}: {line.strip()}")
        
        if headings:
            return "\n".join(headings[:50])  # Limit to 50 headings
        return "No clear section headings detected. Please analyze paper structure."

    def run_analysis(
        self,
        file_id: str = None,
        text: str = None,
        images: list = None,
        pdf_path: str = None,
        enable_vision: bool = True,
        enable_citation: bool = True,
    ) -> Dict[str, Any]:
        
        # 1. Determine Data Source
        if text is None:
            if file_id is None:
                raise ValueError("Either file_id or text must be provided")
            logger.info(f"Loading PDF data for file_id: {file_id}")
            pdf_data = load_pdf(file_id)
            text = pdf_data["text"]
            images = pdf_data["images"]
        else:
            if images is None:
                images = []

        log_id = file_id or "direct_input"
        logger.info(f"Starting pipeline for {log_id}")

        # ---------------------------------------------------------
        # Extract images from PDF for vision analysis
        # ---------------------------------------------------------
        if enable_vision and pdf_path and os.path.exists(pdf_path):
            logger.info(f"Extracting top 10 largest images from PDF for vision analysis...")
            try:
                images = extract_images_from_pdf(
                    pdf_path=pdf_path,
                    max_images=10,
                    min_width=100,
                    min_height=100,
                )
                logger.info(f"Extracted {len(images)} significant images for analysis")
            except Exception as e:
                logger.warning(f"Image extraction failed: {e}")
                images = []

        # ---------------------------------------------------------
        # Paper Discovery & Knowledge Base Update
        # ---------------------------------------------------------
        if file_id:
            try:
                # Construct path to the uploaded PDF file
                uploads_dir = os.path.join(self.settings.STORAGE_ROOT, self.settings.UPLOADS_DIR)
                pdf_path = os.path.join(uploads_dir, f"{file_id}.pdf")
                
                if os.path.exists(pdf_path):
                    logger.info(f"Running Paper Discovery Service for {file_id}...")
                    discovery_service = PaperDiscoveryService()
                    discovery_service.find_similar_papers(pdf_path)
                else:
                    logger.warning(f"PDF file not found at {pdf_path}, skipping discovery step.")
            except Exception as e:
                logger.error(f"Paper Discovery failed (continuing with analysis): {e}")

        # ---------------------------------------------------------
        # ACCURACY-FIRST Agent Analysis Pipeline
        # Each agent works INDEPENDENTLY on the FULL paper
        # No text truncation - agents see everything
        # ---------------------------------------------------------
        
        full_text = text
        text_length = len(full_text)
        
        # Filter images: Only use images that are explicitly referenced in the paper
        # If no "Figure X", "Table X", etc. mentions exist, exclude all images
        if images:
            logger.info(f"Filtering {len(images)} extracted images based on paper references...")
            image_filter = get_image_reference_filter()
            images = image_filter.filter_images(full_text, images)
            logger.info(f"After filtering: {len(images)} images will be used for analysis")
            
            # Get filtering report for debugging
            report = image_filter.get_filtering_report(full_text, images)
            if report.get('all_images_excluded_reason'):
                logger.info(f"Image filtering reason: {report['all_images_excluded_reason']}")
        
        num_images = len(images) if images else 0
        
        # Calculate dynamic token budget based on actual content
        token_budget = self._calculate_token_budget(full_text, num_images)
        self.token_usage["total_estimated"] = token_budget["total_estimated"]
        
        logger.info(f"Total estimated token usage: {token_budget['total_estimated']:,} tokens")
        
        # Extract section headings for structure analysis (supplementary, not replacement)
        section_headings = self._extract_section_headings(full_text)

        # ---------------------------------------------------------
        # PREPROCESSING: Extract relevant portions for each agent
        # Now with SEMANTIC ENHANCEMENT using embeddings
        # This reduces token usage by 60-90% while maintaining quality
        # ---------------------------------------------------------
        logger.info("Preprocessing paper for each agent (with semantic enhancement)...")
        preprocessor = get_preprocessor()
        
        # Generate unique paper ID for embedding cache
        import hashlib
        paper_id = hashlib.md5(full_text[:5000].encode()).hexdigest()[:16]
        
        # Pre-embed paper sections for all agents (done once, reused)
        logger.info("Embedding paper sections for semantic retrieval...")
        embedding_success = preprocessor.embed_paper_for_analysis(full_text, paper_id)
        if embedding_success:
            logger.info("Paper sections embedded successfully")
        else:
            logger.info("Semantic embedding unavailable, using regex-only preprocessing")
        
        # Get preprocessing stats for logging
        preprocess_stats = preprocessor.get_preprocessing_stats(full_text)
        logger.info(f"   - Sections detected: {preprocess_stats['sections_found']}")
        logger.info(f"   - Section types: {preprocess_stats['section_names'][:10]}...")
        logger.info(f"   - Unique citations: {preprocess_stats['unique_citations']}")
        logger.info(f"   - Citation range: {preprocess_stats['citation_range']}")
        
        # Preprocess for each agent type (using semantic enhancement if available)
        if embedding_success:
            # Use semantic-enhanced preprocessing
            language_input = preprocessor.preprocess_for_agent_semantic(full_text, "language_quality", paper_id)
            structure_input = preprocessor.preprocess_for_agent_semantic(full_text, "structure", paper_id)
            citation_input = preprocessor.preprocess_for_agent_semantic(full_text, "citation", paper_id)
            clarity_input = preprocessor.preprocess_for_agent_semantic(full_text, "clarity", paper_id)
            flow_input = preprocessor.preprocess_for_agent_semantic(full_text, "flow", paper_id)
        else:
            # Fallback to regex-only preprocessing
            language_input = preprocessor.preprocess_for_agent(full_text, "language_quality")
            structure_input = preprocessor.preprocess_for_agent(full_text, "structure")
            citation_input = preprocessor.preprocess_for_agent(full_text, "citation")
            clarity_input = preprocessor.preprocess_for_agent(full_text, "clarity")
            flow_input = preprocessor.preprocess_for_agent(full_text, "flow")
        
        logger.info("Preprocessing complete")

        # ---------------------------------------------------------
        # Create Agents with Dynamic Token Allocation
        # Each agent gets tokens based on its specific needs
        # ---------------------------------------------------------
        lang_tokens = token_budget["language_quality"]["output"]
        struct_tokens = token_budget["structure"]["output"]
        cite_tokens = token_budget["citation"]["output"]
        clarity_tokens = token_budget["clarity"]["output"]
        flow_tokens = token_budget["flow"]["output"]
        
        language_agent = create_language_quality_agent(max_tokens=lang_tokens)
        structure_agent = create_structure_agent(max_tokens=struct_tokens)
        citation_agent = create_citation_agent(max_tokens=cite_tokens) if enable_citation else None
        clarity_agent = create_clarity_agent(max_tokens=clarity_tokens)
        flow_agent = create_flow_agent(max_tokens=flow_tokens)

        # ---------------------------------------------------------
        # Citation Cross-Validation (arXiv only, no web search)
        # ---------------------------------------------------------
        citation_validation_report_str = None
        if enable_citation:
            try:
                logger.info("Running citation cross-validation (arXiv resolution)...")
                resolver = get_citation_resolver()
                file_tag = (file_id or "direct")
                citation_uses = resolver.validate_all(full_text, file_tag=file_tag)
                # Format concise report
                lines = ["# Citation Validation & Suggestions", ""]
                for cu in citation_uses[:50]:  # cap to 50 entries
                    ref = cu.reference
                    title = (ref.title if ref and ref.title else "Unknown Title")
                    arx = (ref.arxiv_id if ref and ref.arxiv_id else "-")
                    year = (str(ref.year) if ref and ref.year else "-")
                    lines.append(f"## Citation [{cu.citation_number}] - {title} (arXiv: {arx}, year: {year})")
                    lines.append(f"- Used Section: {cu.used_section_title or '-'}")
                    lines.append(f"- Support Score: {cu.support_score:.3f}")
                    chk = cu.checklist
                    lines.append(f"- Supports Claim: {'Yes' if chk.get('supports_claim') else 'No'}")
                    lines.append(f"- Source Credible: {'Yes' if chk.get('source_credible') else 'No'}")
                    lines.append(f"- Fairly Represented: {'Yes' if chk.get('fair_representation') else 'No'}")
                    lines.append(f"- Properly Formatted: {'Yes' if chk.get('proper_formatting') else 'No'}")
                    lines.append(f"- Current & Accessible: {'Yes' if chk.get('current_and_accessible') else 'No'}")
                    if cu.suggestions:
                        lines.append("- Suggestions:")
                        for s in cu.suggestions:
                            lines.append(f"  - {s}")
                    lines.append("")
                citation_validation_report_str = "\n".join(lines)
            except Exception as e:
                logger.error(f"Citation cross-validation failed: {e}")

        # ---------------------------------------------------------
        # Run Tasks IN PARALLEL with PREPROCESSED inputs
        # Each agent receives optimized, relevant content
        # ---------------------------------------------------------
        structured_results = {}
        structured_results["token_budget"] = token_budget  # Include budget info in results
        structured_results["preprocessing_stats"] = preprocess_stats  # Include preprocessing stats
        
        logger.info("Starting PARALLEL agent execution with preprocessed inputs...")
        logger.info("=" * 60)
        
        # Define all agent tasks to run in parallel (with preprocessed inputs)
        agent_tasks = []
        
        # Task 1: Language Quality (preprocessed input)
        agent_tasks.append({
            "name": "language_quality",
            "agent": language_agent,
            "task_creator": lambda input_text=language_input: create_language_quality_task(language_agent, input_text),
            "budget": lang_tokens,
        })
        
        # Task 2: Structure (preprocessed input)
        agent_tasks.append({
            "name": "structure",
            "agent": structure_agent,
            "task_creator": lambda input_text=structure_input: create_structure_task(structure_agent, input_text, section_headings),
            "budget": struct_tokens,
        })
        
        # Task 3: Citation (if enabled) - preprocessed input with COMPLETE citations
        if citation_agent:
            agent_tasks.append({
                "name": "citations",
                "agent": citation_agent,
                "task_creator": lambda input_text=citation_input: create_citation_task(citation_agent, input_text),
                "budget": cite_tokens,
            })
        
        # Task 4: Clarity of Thought (preprocessed input)
        agent_tasks.append({
            "name": "clarity",
            "agent": clarity_agent,
            "task_creator": lambda input_text=clarity_input: create_clarity_task(clarity_agent, input_text),
            "budget": clarity_tokens,
        })
        
        # Task 5: Flow Analysis (preprocessed input)
        agent_tasks.append({
            "name": "flow",
            "agent": flow_agent,
            "task_creator": lambda input_text=flow_input: create_flow_task(flow_agent, input_text),
            "budget": flow_tokens,
        })
        
        # Task 6: Vision (if enabled and images available)
        if enable_vision and images:
            vision_agent = create_vision_agent()
            agent_tasks.append({
                "name": "vision",
                "agent": vision_agent,
                "task_creator": lambda: create_vision_task(vision_agent, images),
                "budget": 0,  # Vision uses images, not text tokens
            })
        
        # Execute all agents in parallel using ThreadPoolExecutor
        def run_agent_task(task_info):
            """Execute a single agent task with error handling."""
            task_name = task_info["name"]
            agent = task_info["agent"]
            budget = task_info["budget"]
            
            logger.info(f"Starting {task_name} analysis (budget: {budget:,} output tokens)...")
            
            try:
                crew = Crew(
                    agents=[agent],
                    tasks=[task_info["task_creator"]()],
                    process=Process.sequential,
                    verbose=False,
                    memory=False,
                )
                
                result = run_with_retry(
                    crew.kickoff,
                    max_retries=self.settings.MAX_RETRIES,
                    retry_delay=self.settings.RETRY_DELAY
                )
                
                logger.info(f"{task_name} analysis complete")
                return (task_name, str(result), None)
                
            except Exception as e:
                logger.error(f"{task_name} analysis failed: {e}")
                return (task_name, None, f"Analysis failed: {str(e)[:100]}")
        
        # Run all agents in parallel
        with ThreadPoolExecutor(max_workers=len(agent_tasks)) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(run_agent_task, task_info): task_info["name"]
                for task_info in agent_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task_name = future_to_task[future]
                try:
                    result_name, result_output, error = future.result()
                    
                    if error:
                        structured_results[result_name] = error
                    else:
                        structured_results[result_name] = result_output
                        
                except Exception as e:
                    logger.error(f"Exception in {task_name}: {e}")
                    structured_results[task_name] = f"Analysis failed: {str(e)[:100]}"
        
        logger.info("=" * 60)
        logger.info("All parallel agents completed!")
        
        # Ensure all expected keys exist (even if they failed)
        if "language_quality" not in structured_results:
            structured_results["language_quality"] = "Analysis not available"
        if "structure" not in structured_results:
            structured_results["structure"] = "Analysis not available"
        if "citations" not in structured_results and citation_agent:
            structured_results["citations"] = "Analysis not available"
        if "clarity" not in structured_results:
            structured_results["clarity"] = "Analysis not available"
        if "flow" not in structured_results:
            structured_results["flow"] = "Analysis not available"
        if enable_vision and images and "vision" not in structured_results:
            structured_results["vision"] = "Analysis not available"
        
        # Set None for disabled features
        if not (enable_vision and images):
            structured_results["vision"] = None

        # Sanitize agent outputs to remove LLM meta like thoughts/final answers
        def _sanitize_text(text: Any) -> str:
            if text is None:
                return ""
            s = str(text)
            blacklist = [
                "Final Answer", "FINAL ANSWER", "Thought:", "Thoughts:", "Reasoning:",
                "Chain of Thought", "Self-critique", "Critique:", "Plan:", "Reflection:",
                "I now can give a great answer", "Let's think", "I will now",
            ]
            for b in blacklist:
                s = s.replace(b, "")
            # Remove common bold headings
            s = s.replace("**Final Answer**", "").replace("**Thought**", "")
            # Trim and collapse excess spacing
            s = "\n".join([ln.rstrip() for ln in s.split("\n")]).strip()
            return s

        for key in ["language_quality", "structure", "citations", "clarity", "flow", "vision"]:
            if key in structured_results and structured_results[key] is not None:
                structured_results[key] = _sanitize_text(structured_results[key])

        if citation_validation_report_str:
            structured_results["citations_validation"] = citation_validation_report_str

        # Build structured vision items (image + per-image analysis), if available
        def _extract_vision_items(vision_text: Optional[str], image_paths: Optional[List[str]]) -> List[Dict[str, Any]]:
            if not vision_text or not image_paths:
                return []
            items: List[Dict[str, Any]] = []
            by_name = {os.path.basename(p): p for p in image_paths}
            # Pattern like: "### Image 1: filename.png" then content until next ### or end
            pattern = re.compile(r"^###\s*Image\s*(\d+)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
            matches = list(pattern.finditer(vision_text))
            if matches:
                for i, m in enumerate(matches):
                    start = m.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(vision_text)
                    filename = m.group(2).strip()
                    analysis = vision_text[start:end].strip()
                    path = by_name.get(filename)
                    # fallback by order if filename not found
                    if not path and i < len(image_paths):
                        path = image_paths[i]
                        filename = os.path.basename(path)
                    items.append({"index": i + 1, "filename": filename, "path": path, "analysis": analysis})
            else:
                # Fallback: pair by order, split content roughly by lines
                # Use entire vision_text as common analysis
                for i, p in enumerate(image_paths):
                    items.append({"index": i + 1, "filename": os.path.basename(p), "path": p, "analysis": vision_text})
            return items

        if enable_vision and images and structured_results.get("vision"):
            structured_results["vision_items"] = _extract_vision_items(structured_results.get("vision"), images)

        # ---------------------------------------------------------
        # Generate Structured Final Report
        # ---------------------------------------------------------
        logger.info("Generating structured final report...")
        final_report = self._compile_final_report(structured_results)
        structured_results["final_report"] = final_report
        
        # ---------------------------------------------------------
        # Generate PDF Report
        # ---------------------------------------------------------
        logger.info("Generating PDF report...")
        try:
            pdf_generator = PDFReportGenerator()
            pdf_path = pdf_generator.generate_report(
                results=structured_results,
                file_id=log_id
            )
            structured_results["pdf_report_path"] = pdf_path
            logger.info(f"PDF report saved to: {pdf_path}")
        except Exception as e:
            logger.error(f"PDF report generation failed: {e}")
            structured_results["pdf_report_path"] = None
        
        logger.info("All analysis complete!")
        return structured_results
    
    def _compile_final_report(self, results: Dict[str, Any]) -> str:
        """
        Compile all agent outputs into a well-structured final report.
        
        This creates a comprehensive analysis document that synthesizes
        findings from all agents into a coherent paper review.
        """
        sections = []
        
        # Title
        sections.append("# Research Paper Analysis Report\n")
        sections.append("---\n")
        
        # Executive Summary
        sections.append("## Executive Summary\n")
        summary_points = []
        
        # Summarize each section's key finding
        if results.get("language_quality") and "failed" not in results["language_quality"].lower():
            summary_points.append("- **Language Quality**: Analysis completed")
        if results.get("structure") and "failed" not in results["structure"].lower():
            summary_points.append("- **Structure**: Analysis completed")
        if results.get("citations") and "failed" not in results["citations"].lower():
            summary_points.append("- **Citations**: Analysis completed")
        if results.get("clarity") and "failed" not in results["clarity"].lower():
            summary_points.append("- **Clarity of Thought**: Analysis completed")
        if results.get("flow") and "failed" not in results["flow"].lower():
            summary_points.append("- **Flow & Readability**: Analysis completed")
        if results.get("vision") and "failed" not in str(results["vision"]).lower():
            summary_points.append("- **Visual Elements**: Analysis completed")
        
        if summary_points:
            sections.append("\n".join(summary_points))
        else:
            sections.append("Analysis encountered issues. See individual sections for details.")
        sections.append("\n\n---\n")
        
        # Language Quality Section
        sections.append("## 1. Language Quality Analysis\n")
        sections.append("*Grammar, clarity, style, and consistency review*\n\n")
        if results.get("language_quality"):
            sections.append(str(results["language_quality"]))
        else:
            sections.append("*Analysis not available*")
        sections.append("\n\n---\n")
        
        # Structure Section
        sections.append("## 2. Paper Structure Analysis\n")
        sections.append("*Organization, section flow, and completeness*\n\n")
        if results.get("structure"):
            sections.append(str(results["structure"]))
        else:
            sections.append("*Analysis not available*")
        sections.append("\n\n---\n")
        
        # Citation Section
        sections.append("## 3. Citation Analysis\n")
        sections.append("*Reference verification and citation quality*\n\n")
        if results.get("citations"):
            sections.append(str(results["citations"]))
        else:
            sections.append("*Citation analysis was not enabled or not available*")
        sections.append("\n\n---\n")

        # Citation Validation & Suggestions
        if results.get("citations_validation"):
            sections.append("## 3b. Citation Validation & Suggestions\n")
            sections.append("*Checklist-based validation against arXiv sources*\n\n")
            sections.append(str(results["citations_validation"]))
            sections.append("\n\n---\n")
        
        # Clarity Section
        sections.append("## 4. Clarity of Thought Analysis\n")
        sections.append("*Logical reasoning, argument structure, and idea clarity*\n\n")
        if results.get("clarity"):
            sections.append(str(results["clarity"]))
        else:
            sections.append("*Clarity analysis not available*")
        sections.append("\n\n---\n")
        
        # Flow Section
        sections.append("## 5. Flow & Readability Analysis\n")
        sections.append("*Narrative flow, transitions, and reading experience*\n\n")
        if results.get("flow"):
            sections.append(str(results["flow"]))
        else:
            sections.append("*Flow analysis not available*")
        sections.append("\n\n---\n")
        
        # Vision Section (conditional)
        if results.get("vision"):
            sections.append(f"## 6. Visual Elements Analysis\n")
            sections.append("*Figures, charts, and image quality assessment*\n\n")
            sections.append(str(results["vision"]))
            sections.append("\n\n---\n")
        
        # Footer
        sections.append("\n*Report generated by Research Paper Analyst*\n")
        
        return "\n".join(sections)

# Wrapper function to maintain backward compatibility with run_analysis.py
def run_full_analysis(
    file_id: str = None,
    text: str = None,
    images: list = None,
    pdf_path: str = None,
    enable_vision: bool = True,
    enable_citation: bool = True,
):
    service = AnalysisOrchestratorService()
    return service.run_analysis(
        file_id=file_id,
        text=text,
        images=images,
        pdf_path=pdf_path,
        enable_vision=enable_vision,
        enable_citation=enable_citation
    )