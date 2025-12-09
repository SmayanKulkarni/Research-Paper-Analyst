"""
PDF Report Generator Service

Generates professional PDF reports from the analysis results.
Uses ReportLab for PDF generation with proper formatting and styling.
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, HRFlowable, Image
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from app.utils.logging import logger


class PDFReportGenerator:
    """
    Generates professional PDF reports from research paper analysis results.
    """
    
    def __init__(self, output_dir: str = "storage/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles for the report."""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d'),
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4a5568'),
            fontName='Helvetica'
        ))
        
        # Section header style
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2c5282'),
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=5
        ))
        
        # Subsection header style
        styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=styles['Heading3'],
            fontSize=13,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#2d3748'),
            fontName='Helvetica-Bold'
        ))
        
        # Custom body text style (different from default BodyText)
        styles.add(ParagraphStyle(
            name='ReportBodyText',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            leading=14,
            fontName='Helvetica'
        ))
        
        # Bullet point style
        styles.add(ParagraphStyle(
            name='BulletText',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceAfter=4,
            leading=14,
            fontName='Helvetica'
        ))
        
        # Quote/highlight style
        styles.add(ParagraphStyle(
            name='HighlightText',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=10,
            spaceBefore=10,
            backColor=colors.HexColor('#f7fafc'),
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=10,
            fontName='Helvetica-Oblique'
        ))
        
        # Status badge styles
        styles.add(ParagraphStyle(
            name='StatusGood',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#276749'),
            backColor=colors.HexColor('#c6f6d5'),
            borderPadding=5,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='StatusWarning',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#975a16'),
            backColor=colors.HexColor('#fefcbf'),
            borderPadding=5,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='StatusError',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#c53030'),
            backColor=colors.HexColor('#fed7d7'),
            borderPadding=5,
            fontName='Helvetica-Bold'
        ))
        
        # Footer style
        styles.add(ParagraphStyle(
            name='ReportFooter',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER
        ))
        
        return styles
    
    def _clean_markdown(self, text: str) -> str:
        """Convert markdown formatting to plain text or basic HTML for ReportLab."""
        if not text:
            return ""
        
        # Remove markdown headers (keep text)
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Convert bold markdown to HTML bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        
        # Convert italic markdown to HTML italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        # Convert code blocks to monospace
        text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)
        
        # Remove horizontal rules
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _parse_section_content(self, content: str) -> List[Any]:
        """Parse content and return a list of flowable elements."""
        elements = []
        
        if not content or content.strip() == "":
            elements.append(Paragraph("<i>No analysis available</i>", self.styles['ReportBodyText']))
            return elements
        
        # Check for failure messages
        if "failed" in content.lower()[:50] or "error" in content.lower()[:50]:
            elements.append(Paragraph(
                f"<font color='#c53030'>⚠️ {self._clean_markdown(content)}</font>",
                self.styles['ReportBodyText']
            ))
            return elements
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if it's a bullet list
            lines = para.split('\n')
            is_bullet_list = all(
                line.strip().startswith(('-', '•', '*', '–')) or not line.strip()
                for line in lines if line.strip()
            )
            
            if is_bullet_list:
                bullet_items = []
                for line in lines:
                    line = line.strip()
                    if line:
                        # Remove bullet character
                        line = re.sub(r'^[-•*–]\s*', '', line)
                        bullet_items.append(
                            ListItem(Paragraph(self._clean_markdown(line), self.styles['BulletText']))
                        )
                if bullet_items:
                    elements.append(ListFlowable(bullet_items, bulletType='bullet', leftIndent=10))
                    elements.append(Spacer(1, 6))
            else:
                # Regular paragraph
                cleaned = self._clean_markdown(para)
                if cleaned:
                    elements.append(Paragraph(cleaned, self.styles['ReportBodyText']))
        
        return elements
    
    def _create_header(self, file_id: str) -> List[Any]:
        """Create report header with title and metadata."""
        elements = []
        
        # Title
        elements.append(Paragraph(
            "Research Paper Analysis Report",
            self.styles['ReportTitle']
        ))
        
        # Subtitle with metadata
        timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
        elements.append(Paragraph(
            f"Generated on {timestamp}<br/>File ID: {file_id}",
            self.styles['ReportSubtitle']
        ))
        
        # Horizontal rule
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#e2e8f0'),
            spaceBefore=10,
            spaceAfter=20
        ))
        
        return elements
    
    def _create_executive_summary(self, results: Dict[str, Any]) -> List[Any]:
        """Create executive summary section."""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        # Analysis status table
        status_data = [["Analysis Type", "Status"]]
        
        analysis_types = [
            ("Language Quality", results.get("language_quality")),
            ("Paper Structure", results.get("structure")),
            ("Citation Analysis", results.get("citations")),
            ("Plagiarism Check", results.get("plagiarism")),
            ("Mathematical Content", results.get("math_review")),
            ("Visual Elements", results.get("vision")),
        ]
        
        for name, content in analysis_types:
            if content is None:
                status = "Not Analyzed"
                status_color = colors.HexColor('#718096')
            elif isinstance(content, str) and "failed" in content.lower():
                status = "Failed"
                status_color = colors.HexColor('#c53030')
            elif content:
                status = "✓ Completed"
                status_color = colors.HexColor('#276749')
            else:
                status = "Not Available"
                status_color = colors.HexColor('#718096')
            
            status_data.append([name, status])
        
        # Create status table
        table = Table(status_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_section(self, title: str, content: Any, section_num: int) -> List[Any]:
        """Create a report section with proper formatting."""
        elements = []
        
        elements.append(Paragraph(f"{section_num}. {title}", self.styles['SectionHeader']))
        
        if content is None:
            elements.append(Paragraph(
                "<i>This analysis was not enabled or not applicable for this paper.</i>",
                self.styles['ReportBodyText']
            ))
        elif isinstance(content, str):
            elements.extend(self._parse_section_content(content))
        elif isinstance(content, list):
            # Handle list results (e.g., plagiarism matches)
            for item in content:
                if isinstance(item, dict):
                    elements.extend(self._format_dict_item(item))
                else:
                    elements.append(Paragraph(str(item), self.styles['ReportBodyText']))
        elif isinstance(content, dict):
            elements.extend(self._format_dict_content(content))
        else:
            elements.append(Paragraph(str(content), self.styles['ReportBodyText']))
        
        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#e2e8f0'),
            spaceBefore=5,
            spaceAfter=10
        ))
        
        return elements
    
    def _format_dict_item(self, item: dict) -> List[Any]:
        """Format a dictionary item (e.g., plagiarism match) as flowable elements."""
        elements = []
        
        # Create a mini-table for structured data
        data = [[k.replace('_', ' ').title(), str(v)[:100]] for k, v in item.items() if v]
        
        if data:
            table = Table(data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 10))
        
        return elements
    
    def _format_dict_content(self, content: dict) -> List[Any]:
        """Format dictionary content as flowable elements."""
        elements = []
        
        for key, value in content.items():
            if value is None:
                continue
            
            # Format key as subsection
            formatted_key = key.replace('_', ' ').title()
            elements.append(Paragraph(f"<b>{formatted_key}:</b>", self.styles['SubsectionHeader']))
            
            if isinstance(value, str):
                elements.extend(self._parse_section_content(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        elements.extend(self._format_dict_item(item))
                    else:
                        elements.append(Paragraph(f"• {item}", self.styles['BulletText']))
            else:
                elements.append(Paragraph(str(value), self.styles['ReportBodyText']))
        
        return elements
    
    def _create_footer(self) -> List[Any]:
        """Create report footer."""
        elements = []
        
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#2c5282'),
            spaceBefore=10,
            spaceAfter=15
        ))
        
        elements.append(Paragraph(
            "Report generated by <b>Research Paper Analyst</b><br/>"
            "An AI-powered research paper analysis tool",
            self.styles['ReportFooter']
        ))
        
        return elements
    
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
        
        # Header
        elements.extend(self._create_header(file_id))
        
        # Executive Summary
        elements.extend(self._create_executive_summary(results))
        
        # Main sections
        section_num = 1
        
        # Language Quality
        elements.extend(self._create_section(
            "Language Quality Analysis",
            results.get("language_quality"),
            section_num
        ))
        section_num += 1
        
        # Structure
        elements.extend(self._create_section(
            "Paper Structure Analysis",
            results.get("structure"),
            section_num
        ))
        section_num += 1
        
        # Citations
        elements.extend(self._create_section(
            "Citation Analysis",
            results.get("citations"),
            section_num
        ))
        section_num += 1
        
        # Plagiarism
        elements.extend(self._create_section(
            "Plagiarism Check",
            results.get("plagiarism"),
            section_num
        ))
        section_num += 1
        
        # Math Review (conditional)
        if results.get("math_review"):
            elements.extend(self._create_section(
                "Mathematical Content Review",
                results.get("math_review"),
                section_num
            ))
            section_num += 1
        
        # Vision (conditional)
        if results.get("vision"):
            elements.extend(self._create_section(
                "Visual Elements Analysis",
                results.get("vision"),
                section_num
            ))
            section_num += 1
        
        # Footer
        elements.extend(self._create_footer())
        
        # Build PDF
        try:
            doc.build(elements)
            logger.info(f"✅ PDF report generated: {output_path}")
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
        Generate a PDF report and return as bytes (for streaming response).
        
        Args:
            results: Dictionary containing analysis results from all agents
            file_id: Unique identifier for the analyzed file
        
        Returns:
            PDF file content as bytes
        """
        logger.info(f"Generating PDF report bytes for file: {file_id}")
        
        # Create PDF in memory
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build document content (same as generate_report)
        elements = []
        elements.extend(self._create_header(file_id))
        elements.extend(self._create_executive_summary(results))
        
        section_num = 1
        for title, key in [
            ("Language Quality Analysis", "language_quality"),
            ("Paper Structure Analysis", "structure"),
            ("Citation Analysis", "citations"),
            ("Plagiarism Check", "plagiarism"),
        ]:
            elements.extend(self._create_section(title, results.get(key), section_num))
            section_num += 1
        
        if results.get("math_review"):
            elements.extend(self._create_section(
                "Mathematical Content Review",
                results.get("math_review"),
                section_num
            ))
            section_num += 1
        
        if results.get("vision"):
            elements.extend(self._create_section(
                "Visual Elements Analysis",
                results.get("vision"),
                section_num
            ))
        
        elements.extend(self._create_footer())
        
        # Build PDF
        doc.build(elements)
        
        # Get bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"✅ PDF report generated ({len(pdf_bytes)} bytes)")
        return pdf_bytes


# Convenience function for quick report generation
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
