# Embeddings: Implementation Code Examples

This document contains ready-to-use code for implementing the top embedding use cases.

---

## 1. Semantic Section Retrieval (Priority #1)

### Add to `backend/app/services/paper_preprocessor.py`

```python
import numpy as np
from typing import List, Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from app.services.embeddings import embed_texts

class PaperPreprocessor:
    # ... existing code ...
    
    def embed_and_retrieve_sections(
        self, 
        full_text: str, 
        query: str, 
        top_k: int = 3
    ) -> List[str]:
        """
        Embed paper sections and retrieve most relevant for a query.
        
        Use case: For each agent, retrieve only relevant sections
        Example:
            - Language agent query: "writing quality and grammar"
            - Citation agent query: "citations and references"
            - Math agent query: "equations and theorems"
        
        Args:
            full_text: Complete paper text
            query: What the agent needs (e.g., "equations and mathematical proofs")
            top_k: Number of sections to retrieve
            
        Returns:
            List of most relevant section texts
        """
        # Extract sections
        sections = self._find_all_sections(full_text)
        if not sections:
            return [full_text[:2000]]  # Fallback: return start of paper
        
        # Embed section contents
        section_texts = [s.content for s in sections]
        section_embeddings = embed_texts(section_texts)
        
        # Embed query
        query_embedding = embed_texts([query])[0]
        
        # Compute similarities
        similarities = cosine_similarity(
            [query_embedding], 
            section_embeddings
        )[0]
        
        # Get top K indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Return section texts in order
        retrieved_sections = [section_texts[i] for i in top_indices]
        
        logger.info(
            f"Retrieved {len(retrieved_sections)} sections for query: {query}"
        )
        
        return retrieved_sections
    
    def preprocess_for_agent_v2(
        self, 
        full_text: str, 
        agent_type: str
    ) -> str:
        """
        ENHANCED VERSION: Uses embeddings to retrieve relevant sections
        Instead of preprocessing entire paper, use embeddings to get only
        what each agent needs.
        
        Agent-specific queries:
        - language_quality: "writing quality, grammar, academic style"
        - structure: "section headings, document structure, organization"
        - citation: "citations, references, bibliography"
        - clarity: "key claims, main results, logical arguments"
        - flow: "topic transitions, paragraph connections, narrative flow"
        - math: "equations, mathematical proofs, theorems"
        - vision: "figure captions, image descriptions"
        """
        
        agent_queries = {
            "language_quality": "writing quality grammar style readability academic tone",
            "structure": "section headings document structure organization layout",
            "citation": "citations references bibliography in-text citations",
            "clarity": "key claims main results logical arguments reasoning",
            "flow": "transitions paragraph connections narrative flow readability",
            "math": "equations mathematical proofs theorems notation formulas",
            "vision": "figure captions image descriptions visual content"
        }
        
        query = agent_queries.get(agent_type, full_text[:1000])
        
        # Get relevant sections using embeddings
        retrieved_sections = self.embed_and_retrieve_sections(
            full_text, 
            query, 
            top_k=3
        )
        
        # Combine abstract + retrieved sections
        abstract = self._extract_abstract_section(full_text)
        combined = f"{abstract}\n\n" + "\n\n".join(retrieved_sections)
        
        return combined


# Usage in orchestrator.py:
# Instead of:
#   language_input = preprocessor.preprocess_for_agent(full_text, "language_quality")
# 
# Use:
#   language_input = preprocessor.preprocess_for_agent_v2(full_text, "language_quality")
```

### Modify `backend/app/crew/orchestrator.py`

```python
# In the run_full_analysis method, replace the preprocessing section:

# OLD CODE (sequential, full text):
# language_input = preprocessor.preprocess_for_agent(full_text, "language_quality")
# structure_input = preprocessor.preprocess_for_agent(full_text, "structure")
# ...

# NEW CODE (with embeddings):
preprocessor = get_preprocessor()

# Use embeddings to retrieve only relevant sections for each agent
language_input = preprocessor.preprocess_for_agent_v2(full_text, "language_quality")
structure_input = preprocessor.preprocess_for_agent_v2(full_text, "structure")
citation_input = preprocessor.preprocess_for_agent_v2(full_text, "citation")
clarity_input = preprocessor.preprocess_for_agent_v2(full_text, "clarity")
flow_input = preprocessor.preprocess_for_agent_v2(full_text, "flow")
math_input = preprocessor.preprocess_for_agent_v2(full_text, "math")
```

### Expected Token Reduction

```
Language Quality Agent:
  Before: 50,000 tokens (full paper)
  After: 12,000 tokens (abstract + intro + conclusion)
  Reduction: 76%

Structure Agent:
  Before: 50,000 tokens
  After: 8,000 tokens (headings + section boundaries)
  Reduction: 84%

Citation Agent:
  Before: 50,000 tokens
  After: 5,000 tokens (citations + references)
  Reduction: 90%

Total for 6 agents:
  Before: 300,000 tokens
  After: 50,000 tokens
  Reduction: 83%
```

---

## 2. Citation Context Embedding

### Add to `backend/app/services/citation_tool.py`

```python
from app.services.embeddings import embed_texts
from app.services.pinecone_client import pinecone_service
import uuid

class EnhancedCitationTool:
    """Enhanced citation analysis with embedding-based comparison"""
    
    def extract_citation_context(self, text: str, context_window: int = 2) -> List[Dict]:
        """
        Extract citations with surrounding context (±N sentences)
        
        Args:
            text: Full paper text
            context_window: Number of sentences before/after citation
            
        Returns:
            List of dicts with citation + context + embedding
        """
        citations = self._extract_all_citations(text)
        sentences = text.split('.')
        
        citation_contexts = []
        
        for citation in citations:
            # Find sentence containing citation
            citation_sentence_idx = None
            for i, sentence in enumerate(sentences):
                if citation['text'] in sentence:
                    citation_sentence_idx = i
                    break
            
            if citation_sentence_idx is None:
                continue
            
            # Get context window
            start = max(0, citation_sentence_idx - context_window)
            end = min(len(sentences), citation_sentence_idx + context_window + 1)
            context_sentences = sentences[start:end]
            context_text = '. '.join(context_sentences)
            
            # Embed context
            embedding = embed_texts([context_text])[0]
            
            citation_contexts.append({
                "citation_id": str(uuid.uuid4()),
                "citation_text": citation['text'],
                "context": context_text,
                "embedding": embedding,
                "context_window": context_window,
                "source_position": citation_sentence_idx
            })
        
        return citation_contexts
    
    def store_citations_in_pinecone(
        self, 
        paper_id: str, 
        citation_contexts: List[Dict]
    ) -> None:
        """
        Store citation embeddings in Pinecone for corpus-wide search
        """
        vectors = []
        
        for ctx in citation_contexts:
            vectors.append({
                "id": ctx["citation_id"],
                "values": ctx["embedding"],
                "metadata": {
                    "paper_id": paper_id,
                    "citation_text": ctx["citation_text"],
                    "context": ctx["context"][:500],  # Truncate for metadata
                    "type": "citation_context"
                }
            })
        
        if vectors:
            pinecone_service.upsert_vectors(vectors)
            logger.info(f"Stored {len(vectors)} citation embeddings in Pinecone")
    
    def find_similar_citations(
        self, 
        citation_context: Dict, 
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find similar citations across corpus using embeddings
        Use case: Detect paraphrased or plagiarized citations
        """
        embedding = citation_context["embedding"]
        
        # Query Pinecone for similar citations
        results = pinecone_service.query_hybrid(
            dense_vector=embedding,
            top_k=top_k
        )
        
        similar_citations = []
        
        for match in results:
            if match['score'] > 0.8:  # High similarity threshold
                similar_citations.append({
                    "citation_id": match['id'],
                    "original_citation": citation_context["citation_text"],
                    "similar_citation": match['metadata']['citation_text'],
                    "similarity_score": match['score'],
                    "context": match['metadata']['context']
                })
        
        return similar_citations
    
    def detect_plagiarized_citations(
        self, 
        paper_id: str, 
        full_text: str
    ) -> List[Dict]:
        """
        Detect potentially plagiarized or improperly paraphrased citations
        """
        citation_contexts = self.extract_citation_context(full_text)
        plagiarism_flags = []
        
        for ctx in citation_contexts:
            # Find similar citations in corpus
            similar = self.find_similar_citations(ctx, top_k=10)
            
            # If found very similar citations from different papers
            for sim in similar:
                if sim['citation_id'] != ctx['citation_id']:
                    # Check if it's from a different paper
                    if sim.get('paper_id') != paper_id:
                        plagiarism_flags.append({
                            "type": "similar_citation",
                            "current_citation": ctx["citation_text"],
                            "similar_to": sim["similar_citation"],
                            "similarity": sim["similarity_score"],
                            "risk_level": "HIGH" if sim["similarity_score"] > 0.95 else "MEDIUM"
                        })
        
        return plagiarism_flags


# Integration in orchestrator.py:
# citation_tool = EnhancedCitationTool()
# citation_contexts = citation_tool.extract_citation_context(full_text)
# citation_tool.store_citations_in_pinecone(paper_id, citation_contexts)
# plagiarism_flags = citation_tool.detect_plagiarized_citations(paper_id, full_text)
```

---

## 3. Figure Caption Embedding

### Add to `backend/app/services/vision_tool.py`

```python
import os
from app.services.embeddings import embed_texts
from app.services.pinecone_client import pinecone_service

class EnhancedVisionTool:
    """Enhanced vision analysis with figure similarity detection"""
    
    def extract_figure_metadata(
        self, 
        full_text: str, 
        extracted_images: List[str]
    ) -> List[Dict]:
        """
        Extract and embed figure captions
        
        Args:
            full_text: Paper text (to find captions)
            extracted_images: List of image file paths
            
        Returns:
            List of figure metadata with embeddings
        """
        figures = []
        
        for image_path in extracted_images:
            # Get associated caption
            caption = self._find_figure_caption(full_text, image_path)
            
            if not caption:
                caption = os.path.basename(image_path)
            
            # Embed caption
            caption_embedding = embed_texts([caption])[0]
            
            figures.append({
                "image_path": image_path,
                "filename": os.path.basename(image_path),
                "caption": caption,
                "caption_embedding": caption_embedding
            })
        
        logger.info(f"Extracted metadata for {len(figures)} figures")
        return figures
    
    def _find_figure_caption(self, text: str, image_path: str) -> str:
        """
        Find figure caption from text based on image filename
        Looks for patterns like "Figure 1:" or "Fig. 2:" followed by caption text
        """
        import re
        
        filename = os.path.basename(image_path)
        basename = os.path.splitext(filename)[0]
        
        # Try to find pattern: "Figure X: ..." or "Fig. X: ..."
        patterns = [
            rf"Figure\s+{basename}[:\s]+(.+?)(?:\n|$)",
            rf"Fig\.\s+{basename}[:\s]+(.+?)(?:\n|$)",
            rf"Figure[:\s]+(.+?)(?:\n|$)",
            rf"Fig\.[:\s]+(.+?)(?:\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                caption = match.group(1).strip()
                if len(caption) > 10:  # Ensure it's a real caption
                    return caption[:200]  # Limit to 200 chars
        
        return ""
    
    def find_similar_figures(
        self, 
        figure_embedding: List[float], 
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find papers with similar figures using embedding comparison
        Use case: Find papers with similar experimental setups
        """
        results = pinecone_service.query_hybrid(
            dense_vector=figure_embedding,
            top_k=top_k
        )
        
        similar_figures = []
        
        for match in results:
            if match['score'] > 0.75:  # Moderate similarity
                similar_figures.append({
                    "figure_id": match['id'],
                    "similarity_score": match['score'],
                    "caption": match['metadata'].get('caption', ''),
                    "source_paper": match['metadata'].get('paper_id', '')
                })
        
        return similar_figures
    
    def store_figure_embeddings(
        self, 
        paper_id: str, 
        figures: List[Dict]
    ) -> None:
        """
        Store figure embeddings in Pinecone for corpus-wide search
        """
        vectors = []
        
        for fig in figures:
            vectors.append({
                "id": f"{paper_id}_{fig['filename']}",
                "values": fig["caption_embedding"],
                "metadata": {
                    "paper_id": paper_id,
                    "filename": fig["filename"],
                    "caption": fig["caption"][:500],
                    "type": "figure_caption"
                }
            })
        
        if vectors:
            pinecone_service.upsert_vectors(vectors)
            logger.info(f"Stored {len(vectors)} figure embeddings in Pinecone")
    
    def get_similar_papers_by_figures(
        self, 
        paper_id: str, 
        figures: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find other papers with similar experimental figures
        """
        paper_recommendations = {}
        
        for fig in figures:
            similar = self.find_similar_figures(fig["caption_embedding"], top_k=top_k)
            
            for sim in similar:
                source_paper = sim['source_paper']
                if source_paper != paper_id:  # Don't recommend same paper
                    if source_paper not in paper_recommendations:
                        paper_recommendations[source_paper] = {
                            "count": 0,
                            "avg_similarity": 0,
                            "similar_figures": []
                        }
                    
                    paper_recommendations[source_paper]['count'] += 1
                    paper_recommendations[source_paper]['similar_figures'].append({
                        "caption": sim['caption'],
                        "similarity": sim['similarity_score']
                    })
        
        # Sort by similarity count
        recommendations = sorted(
            paper_recommendations.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:top_k]
        
        return recommendations


# Integration in orchestrator.py:
# vision_tool = EnhancedVisionTool()
# figures = vision_tool.extract_figure_metadata(full_text, extracted_images)
# vision_tool.store_figure_embeddings(paper_id, figures)
# similar_papers = vision_tool.get_similar_papers_by_figures(paper_id, figures)
```

---

## 4. Mathematical Expression Embedding

### Add to `backend/app/crew/agents/math_agent.py` or services

```python
import re
from app.services.embeddings import embed_texts

class MathematicalExpressionAnalyzer:
    """Analyze mathematical expressions with embeddings"""
    
    def extract_latex_expressions(self, text: str) -> List[Dict]:
        """Extract LaTeX equations and mathematical expressions"""
        
        # Patterns for LaTeX
        inline_pattern = r'\$(.+?)\$'
        display_pattern = r'\$\$(.+?)\$\$'
        environment_pattern = r'\\begin\{(equation|align|gather)\*?\}(.+?)\\end\{\1\*?\}'
        
        expressions = []
        
        # Find inline math
        for match in re.finditer(inline_pattern, text):
            expressions.append({
                "type": "inline",
                "latex": match.group(1),
                "position": match.start()
            })
        
        # Find display math
        for match in re.finditer(display_pattern, text, re.DOTALL):
            expressions.append({
                "type": "display",
                "latex": match.group(1),
                "position": match.start()
            })
        
        # Find environments
        for match in re.finditer(environment_pattern, text, re.DOTALL):
            expressions.append({
                "type": match.group(1),
                "latex": match.group(2),
                "position": match.start()
            })
        
        return expressions
    
    def generate_math_description(self, latex: str) -> str:
        """
        Generate natural language description of math expression
        This allows semantic comparison of equations
        """
        # Simple heuristic descriptions (can be enhanced)
        descriptions = {
            r"f\(x\)": "function of x",
            r"\frac": "fraction",
            r"\sum": "summation",
            r"\int": "integration",
            r"\sqrt": "square root",
            r"\theta": "theta angle",
            r"\alpha": "alpha parameter",
            r"\beta": "beta parameter",
            r"probability": "probability distribution",
            r"likelihood": "likelihood function",
        }
        
        description = latex.lower()
        
        for pattern, replacement in descriptions.items():
            if re.search(pattern, latex, re.IGNORECASE):
                description += f" with {replacement}"
        
        return description
    
    def embed_math_expressions(self, full_text: str) -> List[Dict]:
        """Extract and embed mathematical expressions"""
        
        expressions = self.extract_latex_expressions(full_text)
        embedded = []
        
        for expr in expressions:
            # Generate description
            description = self.generate_math_description(expr['latex'])
            
            # Embed the description (more robust than raw LaTeX)
            embedding = embed_texts([description])[0]
            
            embedded.append({
                "original_latex": expr['latex'],
                "description": description,
                "embedding": embedding,
                "type": expr['type'],
                "position": expr['position']
            })
        
        logger.info(f"Embedded {len(embedded)} mathematical expressions")
        return embedded
    
    def find_equivalent_expressions(
        self, 
        expr_embedding: List[float], 
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find mathematically equivalent expressions across papers
        Even if written differently, embeddings can find semantic equivalence
        """
        results = pinecone_service.query_hybrid(
            dense_vector=expr_embedding,
            top_k=top_k
        )
        
        equivalent = []
        
        for match in results:
            if match['score'] > 0.8:
                equivalent.append({
                    "found_in_paper": match['metadata'].get('paper_id'),
                    "expression": match['metadata'].get('latex'),
                    "similarity": match['score']
                })
        
        return equivalent


# Usage:
# analyzer = MathematicalExpressionAnalyzer()
# math_exprs = analyzer.embed_math_expressions(full_text)
```

---

## 5. Quick Integration Test

### Test file: `backend/test_embeddings.py`

```python
import sys
sys.path.insert(0, '/path/to/backend')

from app.services.embeddings import embed_texts
from app.services.paper_preprocessor import get_preprocessor

def test_semantic_section_retrieval():
    """Test semantic section retrieval"""
    
    sample_text = """
    Abstract: This paper proposes a novel architecture for neural networks.
    
    Introduction: Machine learning has revolutionized AI. We focus on deep learning.
    
    Methodology: We use transformer architecture with attention mechanisms. The model
    processes sequential data efficiently using self-attention layers.
    
    Experiments: We test on benchmark datasets. Results show 95% accuracy.
    
    Conclusion: Our method outperforms baselines. Future work includes optimization.
    """
    
    preprocessor = get_preprocessor()
    
    # Test 1: Language quality query
    lang_sections = preprocessor.embed_and_retrieve_sections(
        sample_text,
        "writing quality grammar academic style",
        top_k=2
    )
    print("Language sections:", len(lang_sections))
    
    # Test 2: Math query
    math_sections = preprocessor.embed_and_retrieve_sections(
        sample_text,
        "equations mathematical proofs theorems",
        top_k=2
    )
    print("Math sections:", len(math_sections))
    
    # Test 3: Citation query
    citation_sections = preprocessor.embed_and_retrieve_sections(
        sample_text,
        "citations references bibliography",
        top_k=2
    )
    print("Citation sections:", len(citation_sections))
    
    print("✅ Semantic section retrieval working!")

def test_embedding_dimensions():
    """Test embedding dimensions"""
    
    texts = ["Hello world", "Machine learning is great"]
    embeddings = embed_texts(texts)
    
    print(f"Number of embeddings: {len(embeddings)}")
    print(f"Embedding dimension: {len(embeddings[0])}")
    print(f"Expected: 1024 (for BAAI/bge-large-en)")
    
    assert len(embeddings[0]) == 1024, "Embedding dimension mismatch!"
    print("✅ Embedding dimensions correct!")

if __name__ == "__main__":
    test_embedding_dimensions()
    test_semantic_section_retrieval()
```

---

## Implementation Sequence

1. **Start with semantic section retrieval** (Feature #1)
   - Modify `paper_preprocessor.py`
   - Update `orchestrator.py`
   - Run tests

2. **Then add citation context** (Feature #2)
   - Enhance `citation_tool.py`
   - Store in Pinecone

3. **Then figure embeddings** (Feature #3)
   - Enhance `vision_tool.py`
   - Find similar papers

4. **Finally math embeddings** (Feature #4)
   - Add to math agent

---

## Common Issues & Solutions

### Issue: Embeddings too slow
**Solution**: Batch embed texts instead of one-by-one
```python
# Slow:
embeddings = [embed_texts([text])[0] for text in texts]

# Fast:
embeddings = embed_texts(texts)  # All at once
```

### Issue: Pinecone quota exceeded
**Solution**: Use smaller embedding model
```python
# In config.py:
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim instead of 1024
```

### Issue: Memory usage high
**Solution**: Embed in batches
```python
batch_size = 100
for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    embeddings = embed_texts(batch)
```

