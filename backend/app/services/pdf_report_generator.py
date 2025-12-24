"""
PDF Report Generator Service

Generates PDF reports from the analysis results.
Uses ReportLab for PDF generation - outputs raw agent text as-is.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted, PageBreak, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.utils.logging import logger


class PDFReportGenerator:
    """
    Generates PDF reports from research paper analysis results.
    Simply outputs the raw text from agents as-is.
    """
    
    def __init__(self, output_dir: str = "storage/reports"):
        # Resolve output directory relative to backend root to avoid CWD issues
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if not os.path.isabs(output_dir):
            self.output_dir = os.path.join(base_dir, output_dir)
        else:
            self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = self._create_styles()
    
    def _create_styles(self):
        """Create paragraph styles for the report."""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d'),
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4a5568'),
        ))
        
        # Section header style
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2c5282'),
            fontName='Helvetica-Bold',
        ))
        
        # Content style - for raw agent output
        styles.add(ParagraphStyle(
            name='AgentOutput',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
            fontName='Helvetica',
            alignment=TA_LEFT,
        ))
        
        # Footer style
        styles.add(ParagraphStyle(
            name='ReportFooter',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER,
            spaceBefore=30,
        ))
        
        return styles
    
    def _sanitize_text(self, text: str) -> str:
        """Remove common LLM meta like thoughts/final-answer markers."""
        if not text:
            return ""
        s = str(text)
        # Common headings/phrases to remove entirely
        blacklist = [
            "Final Answer", "FINAL ANSWER", "Thought:", "Thoughts:", "Reasoning:",
            "Chain of Thought", "Self-critique", "Critique:", "Plan:", "Reflection:",
            "I now can give a great answer", "Let's think", "I will now",
        ]
        for b in blacklist:
            s = s.replace(b, "")
        # Remove markdown bold markers that were part of meta headings
        s = s.replace("**Final Answer**", "").replace("**Thought**", "")
        # Collapse excessive blank lines
        lines = [ln.rstrip() for ln in s.split("\n")]
        cleaned: List[str] = []
        for ln in lines:
            # skip lone meta lines
            lower = ln.strip().lower()
            if lower in {"final answer:", "thought:", "thoughts:", "reasoning:", "plan:", "reflection:"}:
                continue
            cleaned.append(ln)
        # Remove sequences of >2 empty lines
        out: List[str] = []
        empty = 0
        for ln in cleaned:
            if ln.strip() == "":
                empty += 1
                if empty <= 2:
                    out.append(ln)
            else:
                empty = 0
                out.append(ln)
        return "\n".join(out).strip()

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters for ReportLab."""
        if not text:
            return ""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def _add_section(self, elements: list, title: str, content: Any, section_num: int):
        """Add a section with the raw agent output."""
        # Section header
        elements.append(Paragraph(f"{section_num}. {title}", self.styles['SectionHeader']))
        
        if content is None:
            elements.append(Paragraph(
                "<i>This analysis was not run or not applicable.</i>",
                self.styles['AgentOutput']
            ))
        else:
            # Convert content to string and escape XML characters
            text = self._sanitize_text(str(content) if content else "No output available.")
            
            # Split by lines and add each as a paragraph to preserve formatting
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    escaped_line = self._escape_xml(line)
                    elements.append(Paragraph(escaped_line, self.styles['AgentOutput']))
                else:
                    elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 15))

    def _is_meaningful_analysis(self, text: str) -> bool:
        """Heuristic to decide if vision analysis contains useful info."""
        if not text:
            return False
        t = text.strip().lower()
        if len(t) < 40:
            return False
        bad_phrases = [
            "cannot extract", "can't extract", "unclear", "blurry", "illegible",
            "no discernible", "not readable", "unable to analyze", "no analysis available",
        ]
        if any(p in t for p in bad_phrases):
            return False
        return True

    def _add_vision_gallery(self, elements: list, vision_items: List[Dict[str, Any]]):
        """Add images with their analyses into the PDF."""
        elements.append(Paragraph("Visual Elements Analysis", self.styles['SectionHeader']))
        for idx, item in enumerate(vision_items, 1):
            img_path = item.get("path") or item.get("image_path")
            analysis = self._sanitize_text(item.get("analysis") or item.get("analysis_sanitized") or "")
            if not img_path or not os.path.exists(img_path):
                continue
            if not self._is_meaningful_analysis(analysis):
                continue
            # Add image
            try:
                rl_img = RLImage(img_path)
                max_width = 6.0 * inch
                # Scale keeping aspect ratio
                iw, ih = rl_img.imageWidth, rl_img.imageHeight
                if iw > max_width:
                    scale = max_width / float(iw)
                    rl_img.drawWidth = iw * scale
                    rl_img.drawHeight = ih * scale
                elements.append(rl_img)
            except Exception as e:
                logger.debug(f"Failed to embed image {img_path}: {e}")
                # Skip embedding but keep analysis
            # Add caption/analysis
            caption = f"Image {idx}: {os.path.basename(img_path)}"
            elements.append(Paragraph(self._escape_xml(caption), self.styles['AgentOutput']))
            if analysis:
                for line in analysis.split("\n"):
                    if line.strip():
                        elements.append(Paragraph(self._escape_xml(line), self.styles['AgentOutput']))
                    else:
                        elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 15))
    
    def generate_report(
        self,
        results: Dict[str, Any],
        file_id: str,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Generate a PDF report from analysis results.
        
        Args:
            results: Dictionary containing analysis results from all agents
            file_id: Unique identifier for the analyzed file
            output_filename: Optional custom filename for the PDF
        
        Returns:
            Path to the generated PDF file
        """
        logger.info(f"Generating PDF report for file: {file_id}")
        
        # Determine output path
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"analysis_report_{file_id}_{timestamp}.pdf"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build document content
        elements = []
        
        # Title
        elements.append(Paragraph("Research Paper Analysis Report", self.styles['ReportTitle']))
        
        # Subtitle with metadata
        timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
        elements.append(Paragraph(
            f"Generated on {timestamp}<br/>File ID: {file_id}",
            self.styles['ReportSubtitle']
        ))
        
        # Add sections with raw agent output
        section_num = 1
        
        # Language Quality
        self._add_section(elements, "Language Quality Analysis", 
                         results.get("language_quality"), section_num)
        section_num += 1
        
        # Structure
        self._add_section(elements, "Paper Structure Analysis", 
                         results.get("structure"), section_num)
        section_num += 1
        
        # Citations
        self._add_section(elements, "Citation Analysis", 
                         results.get("citations"), section_num)
        section_num += 1
        
        # Clarity
        self._add_section(elements, "Clarity of Thought Analysis", 
                         results.get("clarity"), section_num)
        section_num += 1
        
        # Flow
        self._add_section(elements, "Flow & Readability Analysis", 
                         results.get("flow"), section_num)
        section_num += 1
        
        # Citation Validation & Suggestions (optional)
        if results.get("citations_validation"):
            self._add_section(elements, "Citation Validation & Suggestions", 
                             results.get("citations_validation"), section_num)
            section_num += 1

        # Vision (only if present)
        vision_items = results.get("vision_items")
        if isinstance(vision_items, list) and vision_items:
            self._add_vision_gallery(elements, vision_items)
            section_num += 1
        elif results.get("vision"):
            self._add_section(elements, "Visual Elements Analysis",
                              results.get("vision"), section_num)
            section_num += 1
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "Report generated by Research Paper Analyst",
            self.styles['ReportFooter']
        ))
        
        # Build PDF
        try:
            doc.build(elements)
            logger.info(f"PDF report generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise
    
    def generate_report_bytes(
        self,
        results: Dict[str, Any],
        file_id: str
    ) -> bytes:
        """
        Generate a PDF report and return as bytes.
        
        Args:
            results: Dictionary containing analysis results from all agents
            file_id: Unique identifier for the analyzed file
        
        Returns:
            PDF file content as bytes
        """
        logger.info(f"Generating PDF report bytes for file: {file_id}")
        
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build same content as generate_report
        elements = []
        
        # Title
        elements.append(Paragraph("Research Paper Analysis Report", self.styles['ReportTitle']))
        
        timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
        elements.append(Paragraph(
            f"Generated on {timestamp}<br/>File ID: {file_id}",
            self.styles['ReportSubtitle']
        ))
        
        section_num = 1
        for title, key in [
            ("Language Quality Analysis", "language_quality"),
            ("Paper Structure Analysis", "structure"),
            ("Citation Analysis", "citations"),
            ("Clarity of Thought Analysis", "clarity"),
            ("Flow & Readability Analysis", "flow"),
        ]:
            self._add_section(elements, title, results.get(key), section_num)
            section_num += 1
        
        if results.get("citations_validation"):
            self._add_section(elements, "Citation Validation & Suggestions", 
                             results.get("citations_validation"), section_num)
            section_num += 1
        
        vision_items = results.get("vision_items")
        if isinstance(vision_items, list) and vision_items:
            self._add_vision_gallery(elements, vision_items)
        elif results.get("vision"):
            self._add_section(elements, "Visual Elements Analysis",
                              results.get("vision"), section_num)
        
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "Report generated by Research Paper Analyst",
            self.styles['ReportFooter']
        ))
        
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF report generated ({len(pdf_bytes)} bytes)")
        return pdf_bytes


def generate_analysis_pdf(
    results: Dict[str, Any],
    file_id: str,
    output_dir: str = "storage/reports"
) -> str:
    """
    Generate a PDF report from analysis results.
    
    Args:
        results: Analysis results dictionary
        file_id: File identifier
        output_dir: Directory to save the PDF
    
    Returns:
        Path to generated PDF file
    """
    generator = PDFReportGenerator(output_dir=output_dir)
    return generator.generate_report(results, file_id)
