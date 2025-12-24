"""
Image Reference Filter Service

Intelligently filters extracted images to only include those that are 
explicitly referenced in the paper text. If an image is not mentioned 
(e.g., "Figure 1", "Fig. 2", "Table 3", etc.), it is excluded from analysis.

This prevents processing of unnecessary images like headers, footers, logos,
or watermarks that don't contribute to the research analysis.
"""

import re
from typing import List, Dict, Tuple, Set
from app.utils.logging import logger


class ImageReferenceFilter:
    """
    Filters images based on whether they are referenced in the paper text.
    
    An image is considered referenced if:
    - The paper text contains "Figure X", "Fig. X", "Figure(s)", etc.
    - The paper text contains "Table X", "Tab. X", etc.
    - The paper text contains "Image X", "Picture X", etc.
    - The paper text contains "Appendix X with figures/images" (for appendix images)
    """
    
    # Patterns for figure/table/image references
    FIGURE_PATTERNS = [
        r'fig(?:ure)?s?\.?\s*(\d+)',  # Figure 1, Fig. 1, Figs. 1-3
        r'figure\s+(\d+)',              # Figure 1
        r'f\.?\s*(\d+)',                # F. 1
        r'\(fig(?:ure)?\.?\s*(\d+)\)',  # (fig. 1)
        r'shown\s+in\s+fig(?:ure)?(?:s?)\.?\s*(\d+)',  # shown in figure 1
        r'see\s+fig(?:ure)?(?:s?)\.?\s*(\d+)',  # see figure 1
    ]
    
    TABLE_PATTERNS = [
        r'table\s+(\d+)',               # Table 1
        r'tab(?:le)?\.?\s*(\d+)',       # Tab. 1, Table. 1
        r't\.?\s*(\d+)',                # T. 1
        r'\(tab(?:le)?\.?\s*(\d+)\)',   # (tab. 1)
        r'shown\s+in\s+table\s+(\d+)',  # shown in table 1
        r'see\s+table\s+(\d+)',         # see table 1
    ]
    
    IMAGE_PATTERNS = [
        r'image\s+(\d+)',               # Image 1
        r'picture\s+(\d+)',             # Picture 1
        r'diagram\s+(\d+)',             # Diagram 1
        r'illustration\s+(\d+)',        # Illustration 1
        r'graph\s+(\d+)',               # Graph 1
        r'chart\s+(\d+)',               # Chart 1
    ]
    
    # General reference patterns
    GENERAL_REFERENCE_PATTERNS = [
        r'above\s+(?:figure|fig|table|image)',  # above figure
        r'below\s+(?:figure|fig|table|image)',  # below figure
        r'(?:figure|fig|table|image)(?:s)?',    # Any mention of figures/tables
    ]
    
    def __init__(self):
        """Initialize with compiled regex patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns for efficiency."""
        self.figure_re = [re.compile(p, re.IGNORECASE) for p in self.FIGURE_PATTERNS]
        self.table_re = [re.compile(p, re.IGNORECASE) for p in self.TABLE_PATTERNS]
        self.image_re = [re.compile(p, re.IGNORECASE) for p in self.IMAGE_PATTERNS]
        self.general_re = [re.compile(p, re.IGNORECASE) for p in self.GENERAL_REFERENCE_PATTERNS]
    
    def extract_referenced_numbers(self, text: str) -> Dict[str, Set[int]]:
        """
        Extract all figure, table, and image numbers referenced in the text.
        
        Args:
            text: Paper text to analyze
            
        Returns:
            Dictionary with keys 'figures', 'tables', 'images' containing sets of referenced numbers
        """
        text_lower = text.lower()
        
        referenced = {
            'figures': set(),
            'tables': set(),
            'images': set()
        }
        
        # Extract figure numbers
        for pattern in self.figure_re:
            matches = pattern.finditer(text_lower)
            for match in matches:
                try:
                    num = int(match.group(1))
                    referenced['figures'].add(num)
                except (ValueError, IndexError):
                    pass
        
        # Extract table numbers
        for pattern in self.table_re:
            matches = pattern.finditer(text_lower)
            for match in matches:
                try:
                    num = int(match.group(1))
                    referenced['tables'].add(num)
                except (ValueError, IndexError):
                    pass
        
        # Extract image numbers
        for pattern in self.image_re:
            matches = pattern.finditer(text_lower)
            for match in matches:
                try:
                    num = int(match.group(1))
                    referenced['images'].add(num)
                except (ValueError, IndexError):
                    pass
        
        return referenced
    
    def has_any_figure_reference(self, text: str) -> bool:
        """
        Quick check if paper mentions any figures, tables, or images at all.
        
        Args:
            text: Paper text to check
            
        Returns:
            True if any reference found, False otherwise
        """
        text_lower = text.lower()
        
        for pattern in self.general_re:
            if pattern.search(text_lower):
                return True
        
        return False
    
    def get_referenced_image_indices(
        self, 
        text: str, 
        images: List[Dict],
        image_numbering_scheme: str = "sequential"
    ) -> List[int]:
        """
        Get indices of images that are referenced in the paper.
        
        Args:
            text: Full paper text
            images: List of extracted image dictionaries
            image_numbering_scheme: 
                - "sequential": Images are numbered 1, 2, 3... in extraction order
                - "page-based": Images are numbered by page number
                
        Returns:
            List of indices (into the images list) that should be used
        """
        if not images:
            return []
        
        # Check if paper even mentions figures/tables
        if not self.has_any_figure_reference(text):
            logger.info("No figure/table/image references found in paper. Excluding all images.")
            return []
        
        # Extract referenced numbers from text
        referenced = self.extract_referenced_numbers(text)
        
        all_referenced = (
            referenced['figures'] | 
            referenced['tables'] | 
            referenced['images']
        )
        
        if not all_referenced:
            logger.info("No specific figure/table/image numbers found in paper. Excluding all images.")
            return []
        
        # Filter images based on references
        # Assume images are numbered sequentially (1-indexed in text, 0-indexed in list)
        valid_indices = []
        
        for idx, image_dict in enumerate(images):
            # Image number in text would be idx + 1 (since text uses 1-based numbering)
            image_num = idx + 1
            
            if image_num in all_referenced:
                valid_indices.append(idx)
                logger.debug(f"Image {image_num} is referenced in text. Including.")
            else:
                logger.debug(f"Image {image_num} is NOT referenced in text. Excluding.")
        
        return valid_indices
    
    def filter_images(
        self,
        text: str,
        images: List[Dict]
    ) -> List[Dict]:
        """
        Filter images to only include those referenced in the paper.
        
        Args:
            text: Full paper text
            images: List of extracted image dictionaries
            
        Returns:
            Filtered list of images that are referenced in the paper
        """
        if not images:
            return []
        
        valid_indices = self.get_referenced_image_indices(text, images)
        
        if not valid_indices:
            logger.info(f"Filtered {len(images)} extracted images down to 0 referenced images")
            return []
        
        # Return only valid images in order
        filtered_images = [images[idx] for idx in valid_indices]
        logger.info(f"Filtered {len(images)} extracted images down to {len(filtered_images)} referenced images")
        
        return filtered_images
    
    def get_filtering_report(
        self,
        text: str,
        images: List[Dict]
    ) -> Dict[str, any]:
        """
        Get a detailed report of image filtering for debugging.
        
        Args:
            text: Full paper text
            images: List of extracted images
            
        Returns:
            Dictionary with filtering details
        """
        report = {
            'total_images_extracted': len(images),
            'paper_mentions_figures': False,
            'paper_mentions_tables': False,
            'paper_mentions_images': False,
            'referenced_figure_numbers': set(),
            'referenced_table_numbers': set(),
            'referenced_image_numbers': set(),
            'images_to_keep': [],
            'images_to_exclude': [],
        }
        
        # Check for references
        report['paper_mentions_figures'] = any(
            p.search(text.lower()) for p in self.figure_re
        )
        report['paper_mentions_tables'] = any(
            p.search(text.lower()) for p in self.table_re
        )
        report['paper_mentions_images'] = any(
            p.search(text.lower()) for p in self.image_re
        )
        
        if not self.has_any_figure_reference(text):
            report['all_images_excluded_reason'] = 'No figure/table/image references found in text'
            report['images_to_exclude'] = list(range(len(images)))
            return report
        
        referenced = self.extract_referenced_numbers(text)
        report['referenced_figure_numbers'] = referenced['figures']
        report['referenced_table_numbers'] = referenced['tables']
        report['referenced_image_numbers'] = referenced['images']
        
        all_referenced = referenced['figures'] | referenced['tables'] | referenced['images']
        
        for idx in range(len(images)):
            image_num = idx + 1
            if image_num in all_referenced:
                report['images_to_keep'].append(idx)
            else:
                report['images_to_exclude'].append(idx)
        
        return report


# Singleton instance
_filter_instance = None


def get_image_reference_filter() -> ImageReferenceFilter:
    """Get or create singleton image reference filter."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = ImageReferenceFilter()
    return _filter_instance
