"""
Knowledge Base Service for Government Scheme Copilot.

This service manages government scheme data and provides search capabilities
including semantic search using pre-computed embeddings and filtering by
various criteria.
"""

import json
import logging
import os
import math
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict, Counter
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import threading

from models.core import SchemeModel, SchemeCategoryEnum, StateEnum
from models.exceptions import ConfigurationException, ProcessingException

logger = logging.getLogger(__name__)


class OptimizedKnowledgeBase:
    """
    Optimized Knowledge Base with vectorized operations and fast lookups.
    
    This class provides high-performance data structures for scheme management:
    - NumPy arrays for vectorized similarity calculations
    - Hash maps for O(1) lookups by ID, category, and state
    - Thread-safe operations for concurrent access
    - LRU caching for frequently accessed data
    """
    
    def __init__(self, data_path: str = "data/schemes.json"):
        """
        Initialize the optimized knowledge base.
        
        Args:
            data_path: Path to the schemes JSON data file
        """
        self.data_path = data_path
        self.schemes: List[SchemeModel] = []
        
        # Optimized data structures for O(1) lookups
        self.schemes_by_id: Dict[str, SchemeModel] = {}
        self.schemes_by_category: Dict[str, List[SchemeModel]] = defaultdict(list)
        self.schemes_by_state: Dict[str, List[SchemeModel]] = defaultdict(list)
        self.schemes_by_occupation: Dict[str, List[SchemeModel]] = defaultdict(list)
        
        # Vectorized search components using NumPy
        self.embedding_matrix: Optional[np.ndarray] = None
        self.scheme_ids_array: Optional[np.ndarray] = None
        self.scheme_index_map: Dict[str, int] = {}
        
        # Performance optimization structures
        self.word_frequencies: Dict[str, Dict[str, int]] = {}
        self.category_embeddings: Dict[str, np.ndarray] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="kb_worker")
        
        # Load schemes on initialization
        self.load_schemes()
    
    def load_schemes(self) -> List[SchemeModel]:
        """
        Load schemes with optimized data structure initialization.
        
        Returns:
            List of loaded SchemeModel objects
        """
        with self._lock:
            if not os.path.exists(self.data_path):
                raise ConfigurationException(
                    config_key="schemes_data_path",
                    message=f"Schemes data file not found: {self.data_path}"
                )
            
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                schemes_data = data.get('schemes', [])
                if not schemes_data:
                    raise ConfigurationException(
                        config_key="schemes_data",
                        message="No schemes found in data file"
                    )
                
                # Clear existing data
                self._clear_data_structures()
                
                # Load and validate schemes
                embeddings = []
                scheme_ids = []
                
                for i, scheme_data in enumerate(schemes_data):
                    try:
                        scheme = SchemeModel(**scheme_data)
                        self.schemes.append(scheme)
                        
                        # Build optimized lookup indexes
                        self._index_scheme(scheme, i)
                        
                        # Collect embeddings for vectorized operations
                        if scheme.embedding:
                            embeddings.append(scheme.embedding)
                            scheme_ids.append(scheme.id)
                            self.scheme_index_map[scheme.id] = len(embeddings) - 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to load scheme {scheme_data.get('id', 'unknown')}: {e}")
                        continue
                
                # Initialize vectorized components
                if embeddings:
                    self.embedding_matrix = np.array(embeddings, dtype=np.float32)
                    self.scheme_ids_array = np.array(scheme_ids)
                    
                    # Pre-compute category embeddings for faster filtering
                    self._compute_category_embeddings()
                    
                    # Build word frequency index
                    self._build_word_frequencies()
                
                logger.info(f"Successfully loaded {len(self.schemes)} schemes with {len(embeddings)} embeddings")
                return self.schemes
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format in data file: {e}")
            except Exception as e:
                raise ProcessingException(
                    operation="load_schemes",
                    message=f"Error loading schemes: {str(e)}",
                    original_exception=e
                )
    
    def _clear_data_structures(self):
        """Clear all data structures for reloading."""
        self.schemes.clear()
        self.schemes_by_id.clear()
        self.schemes_by_category.clear()
        self.schemes_by_state.clear()
        self.schemes_by_occupation.clear()
        self.scheme_index_map.clear()
        self.word_frequencies.clear()
        self.category_embeddings.clear()
    
    def _index_scheme(self, scheme: SchemeModel, index: int):
        """Index a scheme in all lookup structures."""
        self.schemes_by_id[scheme.id] = scheme
        self.schemes_by_category[scheme.category].append(scheme)
        self.schemes_by_state[scheme.state].append(scheme)
        
        # Index by occupation for faster eligibility filtering
        occupation = scheme.eligibility.occupation.lower()
        self.schemes_by_occupation[occupation].append(scheme)
        if occupation != 'all':
            self.schemes_by_occupation['all'].append(scheme)
    
    def _compute_category_embeddings(self):
        """Pre-compute average embeddings for each category."""
        if self.embedding_matrix is None:
            return
        
        for category, schemes in self.schemes_by_category.items():
            category_indices = []
            for scheme in schemes:
                if scheme.id in self.scheme_index_map:
                    category_indices.append(self.scheme_index_map[scheme.id])
            
            if category_indices:
                category_embeddings = self.embedding_matrix[category_indices]
                self.category_embeddings[category] = np.mean(category_embeddings, axis=0)
    
    @lru_cache(maxsize=1000)
    def get_scheme_by_id(self, scheme_id: str) -> Optional[SchemeModel]:
        """
        Get a scheme by its ID with LRU caching.
        
        Args:
            scheme_id: Unique identifier of the scheme
            
        Returns:
            SchemeModel if found, None otherwise
        """
        return self.schemes_by_id.get(scheme_id)
    
    @lru_cache(maxsize=100)
    def filter_by_category(self, category: str) -> Tuple[SchemeModel, ...]:
        """
        Filter schemes by category with caching.
        
        Args:
            category: Scheme category
            
        Returns:
            Tuple of schemes in the specified category
        """
        return tuple(self.schemes_by_category.get(category, []))
    
    @lru_cache(maxsize=50)
    def filter_by_state(self, state: str) -> Tuple[SchemeModel, ...]:
        """
        Filter schemes by state with caching.
        
        Args:
            state: State name
            
        Returns:
            Tuple of schemes for the specified state
        """
        return tuple(self.schemes_by_state.get(state, []))
    
    def fast_similarity_search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 5,
        min_similarity: float = 0.3,
        category_filter: Optional[str] = None
    ) -> List[Tuple[int, float, str]]:
        """
        Vectorized similarity calculation for all schemes.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Maximum number of results
            min_similarity: Minimum similarity threshold
            category_filter: Optional category to filter by
            
        Returns:
            List of (index, similarity_score, scheme_id) tuples
        """
        if self.embedding_matrix is None or len(self.embedding_matrix) == 0:
            return []
        
        try:
            # Ensure query embedding is the right shape
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Filter by category if specified
            if category_filter and category_filter in self.schemes_by_category:
                # Get indices for schemes in the category
                category_indices = []
                category_scheme_ids = []
                for scheme in self.schemes_by_category[category_filter]:
                    if scheme.id in self.scheme_index_map:
                        idx = self.scheme_index_map[scheme.id]
                        category_indices.append(idx)
                        category_scheme_ids.append(scheme.id)
                
                if not category_indices:
                    return []
                
                # Use only category embeddings
                category_embeddings = self.embedding_matrix[category_indices]
                similarities = self._compute_cosine_similarity_vectorized(
                    query_embedding, category_embeddings
                )
                
                # Create results with original indices
                results = []
                for i, (idx, sim) in enumerate(zip(category_indices, similarities)):
                    if sim >= min_similarity:
                        results.append((idx, float(sim), category_scheme_ids[i]))
            else:
                # Calculate similarities for all schemes at once
                similarities = self._compute_cosine_similarity_vectorized(
                    query_embedding, self.embedding_matrix
                )
                
                # Filter by threshold and create results
                results = []
                for i, sim in enumerate(similarities):
                    if sim >= min_similarity:
                        scheme_id = self.scheme_ids_array[i]
                        results.append((i, float(sim), scheme_id))
            
            # Sort by similarity (descending) and return top K
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in vectorized similarity search: {e}")
            raise ProcessingException(
                operation="fast_similarity_search",
                message=f"Vectorized search failed: {str(e)}",
                original_exception=e
            )
    
    def _compute_cosine_similarity_vectorized(
        self, 
        query_embedding: np.ndarray, 
        scheme_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity using vectorized operations.
        
        Args:
            query_embedding: Query embedding (1, embedding_dim)
            scheme_embeddings: Scheme embeddings (n_schemes, embedding_dim)
            
        Returns:
            Array of similarity scores
        """
        # Normalize embeddings for cosine similarity
        query_norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
        scheme_norms = np.linalg.norm(scheme_embeddings, axis=1, keepdims=True)
        
        # Avoid division by zero
        query_norm = np.where(query_norm == 0, 1e-8, query_norm)
        scheme_norms = np.where(scheme_norms == 0, 1e-8, scheme_norms)
        
        # Normalize
        query_normalized = query_embedding / query_norm
        schemes_normalized = scheme_embeddings / scheme_norms
        
        # Compute dot product (cosine similarity)
        similarities = np.dot(query_normalized, schemes_normalized.T).flatten()
        
        # Ensure values are in [0, 1] range
        similarities = np.clip(similarities, 0.0, 1.0)
        
        return similarities
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the knowledge base.
        
        Returns:
            Dictionary with performance metrics
        """
        cache_info = self.get_scheme_by_id.cache_info()
        category_cache_info = self.filter_by_category.cache_info()
        state_cache_info = self.filter_by_state.cache_info()
        
        return {
            'total_schemes': len(self.schemes),
            'embedding_matrix_shape': self.embedding_matrix.shape if self.embedding_matrix is not None else None,
            'categories': len(self.schemes_by_category),
            'states': len(self.schemes_by_state),
            'occupations_indexed': len(self.schemes_by_occupation),
            'cache_stats': {
                'scheme_by_id': {
                    'hits': cache_info.hits,
                    'misses': cache_info.misses,
                    'hit_rate': cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
                },
                'category_filter': {
                    'hits': category_cache_info.hits,
                    'misses': category_cache_info.misses,
                    'hit_rate': category_cache_info.hits / (category_cache_info.hits + category_cache_info.misses) if (category_cache_info.hits + category_cache_info.misses) > 0 else 0
                },
                'state_filter': {
                    'hits': state_cache_info.hits,
                    'misses': state_cache_info.misses,
                    'hit_rate': state_cache_info.hits / (state_cache_info.hits + state_cache_info.misses) if (state_cache_info.hits + state_cache_info.misses) > 0 else 0
                }
            },
            'memory_usage': {
                'embedding_matrix_mb': self.embedding_matrix.nbytes / (1024 * 1024) if self.embedding_matrix is not None else 0,
                'schemes_count': len(self.schemes),
                'index_sizes': {
                    'by_id': len(self.schemes_by_id),
                    'by_category': sum(len(schemes) for schemes in self.schemes_by_category.values()),
                    'by_state': sum(len(schemes) for schemes in self.schemes_by_state.values())
                }
            }
        }
    
    def clear_caches(self):
        """Clear all LRU caches."""
        self.get_scheme_by_id.cache_clear()
        self.filter_by_category.cache_clear()
        self.filter_by_state.cache_clear()
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
class KnowledgeBaseService(OptimizedKnowledgeBase):
    """
    Knowledge Base Service for managing government scheme data.
    
    Provides fast in-memory access to scheme information with support for:
    - Loading schemes from JSON data
    - Semantic search using vector embeddings
    - Filtering by category, state, and eligibility criteria
    - Fast lookups using optimized data structures
    - Vectorized similarity calculations
    """
    
    def __init__(self, data_path: str = "data/schemes.json"):
        """
        Initialize the Knowledge Base Service.
        
        Args:
            data_path: Path to the schemes JSON data file
        """
        super().__init__(data_path)
        
        # Backward compatibility attributes
        self.embedding_matrix_legacy = None
        self.scheme_ids = []
    
    def get_scheme_by_id(self, scheme_id: str) -> Optional[SchemeModel]:
        """
        Get a scheme by its ID.
        
        Args:
            scheme_id: Unique identifier of the scheme
            
        Returns:
            SchemeModel if found, None otherwise
        """
        return self.schemes_by_id.get(scheme_id)
    
    def filter_by_category(self, category: str) -> List[SchemeModel]:
        """
        Filter schemes by category.
        
        Args:
            category: Scheme category (e.g., 'education', 'health')
            
        Returns:
            List of schemes in the specified category
        """
        return self.schemes_by_category.get(category, [])
    
    def filter_by_state(self, state: str) -> List[SchemeModel]:
        """
        Filter schemes by state.
        
        Args:
            state: State name (e.g., 'Karnataka', 'Central')
            
        Returns:
            List of schemes for the specified state
        """
        return self.schemes_by_state.get(state, [])
    
    def filter_schemes(
        self,
        category: Optional[str] = None,
        state: Optional[str] = None,
        occupation: Optional[str] = None
    ) -> List[SchemeModel]:
        """
        Filter schemes by multiple criteria.
        
        Args:
            category: Optional scheme category filter
            state: Optional state filter
            occupation: Optional occupation filter
            
        Returns:
            List of schemes matching all specified criteria
        """
        filtered_schemes = self.schemes
        
        if category:
            filtered_schemes = [s for s in filtered_schemes if s.category == category]
        
        if state:
            filtered_schemes = [s for s in filtered_schemes if s.state == state]
        
        if occupation:
            filtered_schemes = [
                s for s in filtered_schemes
                if s.eligibility.occupation.lower() in ['all', occupation.lower()]
            ]
        
        return filtered_schemes
    
    def _build_word_frequencies(self):
        """Build word frequency index for TF-IDF-like search."""
        self.word_frequencies = {}
        
        for scheme in self.schemes:
            # Combine all searchable text
            text = f"{scheme.name} {scheme.description} {scheme.keywords}".lower()
            words = text.split()
            
            # Count word frequencies for this scheme
            word_count = Counter(words)
            self.word_frequencies[scheme.id] = dict(word_count)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for a search query using simple TF-IDF approach.
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding as list of floats, None if no word frequencies available
        """
        if not self.word_frequencies:
            return None
        
        try:
            # Simple TF-IDF calculation
            query_words = query.lower().split()
            
            # Create a simple embedding based on word frequencies
            # This is a simplified approach - in production you'd use proper embeddings
            embedding = [0.0] * 384  # Match the expected embedding dimension
            
            # Calculate simple scores for each word
            for i, word in enumerate(query_words):
                if i < 384:  # Don't exceed embedding dimensions
                    # Simple frequency-based score
                    total_freq = sum(
                        freqs.get(word, 0) 
                        for freqs in self.word_frequencies.values()
                    )
                    if total_freq > 0:
                        embedding[i] = min(1.0, total_freq / len(self.schemes))
            
            return embedding
                
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise ProcessingException(
                operation="generate_query_embedding",
                message=f"Failed to generate query embedding: {str(e)}",
                original_exception=e
            )
    
    def search_semantic(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using optimized vectorized operations.
        
        Args:
            query: Search query text
            top_k: Maximum number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of search results with scheme and similarity score
        """
        if self.embedding_matrix is None or len(self.embedding_matrix) == 0:
            logger.warning("Vector search not available - no embeddings loaded")
            return []
        
        # Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        if query_embedding is None:
            return []
        
        try:
            # Convert to numpy array for vectorized operations
            query_np = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            
            # Use optimized vectorized search
            search_results = self.fast_similarity_search(
                query_np, top_k=top_k, min_similarity=min_similarity
            )
            
            # Convert results to expected format
            results = []
            for idx, similarity, scheme_id in search_results:
                scheme = self.schemes_by_id[scheme_id]
                results.append({
                    'scheme': scheme,
                    'similarity_score': float(similarity)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise ProcessingException(
                operation="semantic_search",
                message=f"Semantic search failed: {str(e)}",
                original_exception=e
            )
    
    def search_by_keywords(
        self,
        keywords: str,
        top_k: int = 10
    ) -> List[SchemeModel]:
        """
        Search schemes by keyword matching.
        
        Args:
            keywords: Space-separated keywords to search for
            top_k: Maximum number of results to return
            
        Returns:
            List of matching schemes
        """
        if not keywords.strip():
            return []
        
        search_terms = keywords.lower().split()
        results = []
        
        for scheme in self.schemes:
            # Search in name, description, and keywords
            searchable_text = (
                f"{scheme.name} {scheme.description} {scheme.keywords}"
            ).lower()
            
            # Calculate match score based on keyword presence
            matches = sum(1 for term in search_terms if term in searchable_text)
            if matches > 0:
                results.append((scheme, matches))
        
        # Sort by match count and return top K
        results.sort(key=lambda x: x[1], reverse=True)
        return [scheme for scheme, _ in results[:top_k]]
    
    def get_all_schemes(self) -> List[SchemeModel]:
        """
        Get all loaded schemes.
        
        Returns:
            List of all SchemeModel objects
        """
        return self.schemes.copy()
    
    def get_scheme_count(self) -> int:
        """
        Get total number of loaded schemes.
        
        Returns:
            Number of schemes in the knowledge base
        """
        return len(self.schemes)
    
    def get_categories(self) -> List[str]:
        """
        Get all available scheme categories.
        
        Returns:
            List of unique category names
        """
        return list(self.schemes_by_category.keys())
    
    def get_states(self) -> List[str]:
        """
        Get all available states.
        
        Returns:
            List of unique state names
        """
        return list(self.schemes_by_state.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.
        
        Returns:
            Dictionary with various statistics
        """
        return {
            'total_schemes': len(self.schemes),
            'categories': len(self.schemes_by_category),
            'states': len(self.schemes_by_state),
            'schemes_with_embeddings': len(self.scheme_ids) if self.scheme_ids else 0,
            'category_distribution': {
                category: len(schemes)
                for category, schemes in self.schemes_by_category.items()
            },
            'state_distribution': {
                state: len(schemes)
                for state, schemes in self.schemes_by_state.items()
            }
        }