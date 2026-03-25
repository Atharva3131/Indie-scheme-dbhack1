"""
Search Service for Government Scheme Copilot.

This service provides semantic search capabilities using TF-IDF vectorization
and cosine similarity with optimized NumPy operations. It integrates with the 
KnowledgeBaseService and EligibilityService to provide combined scoring that 
merges semantic similarity with eligibility matching.
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import lru_cache

from models.core import SchemeModel, UserProfile, SearchResult
from models.exceptions import EmbeddingServiceException, ProcessingException
from services.knowledge_base import KnowledgeBaseService
from services.eligibility import EligibilityService

logger = logging.getLogger(__name__)


class VectorizedSearchService:
    """
    High-performance search service with vectorized operations.
    
    This service provides optimized semantic search using:
    - Batch processing for multiple queries
    - Vectorized similarity calculations
    - Parallel processing for large datasets
    - Memory-efficient operations
    """
    
    def __init__(
        self,
        knowledge_base: KnowledgeBaseService,
        eligibility_service: Optional[EligibilityService] = None,
        max_workers: int = 4
    ):
        """
        Initialize the vectorized search service.
        
        Args:
            knowledge_base: Knowledge base service for scheme data
            eligibility_service: Optional eligibility service for combined scoring
            max_workers: Maximum number of worker threads for parallel processing
        """
        self.knowledge_base = knowledge_base
        self.eligibility_service = eligibility_service or EligibilityService()
        self.embedding_service = MockEmbeddingService()
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="search_worker")
        
        # Initialize embeddings for all schemes
        self._initialize_embeddings()
    
    def _initialize_embeddings(self) -> None:
        """Initialize embeddings for all schemes in the knowledge base."""
        schemes = self.knowledge_base.get_all_schemes()
        if schemes:
            # Fit the embedding service on scheme data
            self.embedding_service.fit_on_schemes(schemes)
            
            # Re-generate embeddings for all schemes to ensure they are in the same vector space
            # as the MockEmbeddingService (TF-IDF), overriding any pre-loaded JSON embeddings.
            embeddings_list = []
            for scheme in schemes:
                text = f"{scheme.name} {scheme.description} {scheme.keywords}"
                scheme.embedding = self.embedding_service.generate_embedding(text)
                embeddings_list.append(scheme.embedding)
                
            # Update the knowledge base embedding matrix with the new consistent vectors
            self.knowledge_base.embedding_matrix = np.array(embeddings_list, dtype=np.float32)
    
    def batch_similarity_calculation(
        self,
        query_embeddings: np.ndarray,
        scheme_embeddings: np.ndarray,
        batch_size: int = 1000
    ) -> np.ndarray:
        """
        Calculate similarities in batches for memory efficiency.
        
        Args:
            query_embeddings: Query embedding matrix (n_queries, embedding_dim)
            scheme_embeddings: Scheme embedding matrix (n_schemes, embedding_dim)
            batch_size: Number of schemes to process per batch
            
        Returns:
            Similarity matrix (n_queries, n_schemes)
        """
        n_queries, n_schemes = query_embeddings.shape[0], scheme_embeddings.shape[0]
        similarities = np.zeros((n_queries, n_schemes), dtype=np.float32)
        
        # Process schemes in batches to manage memory
        for start_idx in range(0, n_schemes, batch_size):
            end_idx = min(start_idx + batch_size, n_schemes)
            batch_schemes = scheme_embeddings[start_idx:end_idx]
            
            # Calculate cosine similarity for this batch
            batch_similarities = cosine_similarity(query_embeddings, batch_schemes)
            similarities[:, start_idx:end_idx] = batch_similarities
        
        return similarities
    
    def parallel_search(
        self,
        queries: List[str],
        user_profiles: Optional[List[UserProfile]] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[List[SearchResult]]:
        """
        Perform parallel search for multiple queries.
        
        Args:
            queries: List of search queries
            user_profiles: Optional list of user profiles (one per query)
            top_k: Maximum number of results per query
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of search results for each query
        """
        if not queries:
            return []
        
        # Generate embeddings for all queries at once
        query_embeddings = []
        for query in queries:
            embedding = self.embedding_service.generate_embedding(query)
            query_embeddings.append(embedding)
        
        query_embeddings = np.array(query_embeddings, dtype=np.float32)
        
        # Get scheme embeddings from knowledge base
        if self.knowledge_base.embedding_matrix is None:
            return [[] for _ in queries]
        
        scheme_embeddings = self.knowledge_base.embedding_matrix
        
        # Calculate similarities for all queries at once
        similarities = self.batch_similarity_calculation(
            query_embeddings, scheme_embeddings
        )
        
        # Process results for each query
        all_results = []
        for i, query in enumerate(queries):
            user_profile = user_profiles[i] if user_profiles and i < len(user_profiles) else None
            query_similarities = similarities[i]
            
            # Get top results for this query
            results = self._process_query_results(
                query_similarities, user_profile, top_k, similarity_threshold
            )
            all_results.append(results)
        
        return all_results
    
    def _process_query_results(
        self,
        similarities: np.ndarray,
        user_profile: Optional[UserProfile],
        top_k: int,
        similarity_threshold: float
    ) -> List[SearchResult]:
        """Process similarity results for a single query."""
        # Filter by threshold and get top indices
        valid_indices = np.where(similarities >= similarity_threshold)[0]
        if len(valid_indices) == 0:
            return []
        
        valid_similarities = similarities[valid_indices]
        
        # Sort by similarity (descending)
        sorted_indices = np.argsort(valid_similarities)[::-1][:top_k]
        top_indices = valid_indices[sorted_indices]
        top_similarities = valid_similarities[sorted_indices]
        
        # Create search results
        results = []
        schemes = self.knowledge_base.get_all_schemes()
        
        for idx, similarity in zip(top_indices, top_similarities):
            if idx >= len(schemes):
                continue
                
            scheme = schemes[idx]
            
            # Calculate combined score if user profile provided
            combined_score = None
            if user_profile:
                eligibility_score = self.eligibility_service.calculate_match_score(
                    user_profile, scheme
                )
                semantic_score_scaled = float(similarity) * 100
                combined_score = (semantic_score_scaled + eligibility_score) / 2
            
            search_result = SearchResult(
                scheme=scheme,
                similarity_score=float(similarity),
                combined_score=combined_score
            )
            results.append(search_result)
        
        return results
    
    async def async_search(
        self,
        query: str,
        user_profile: Optional[UserProfile] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform asynchronous search using thread pool.
        
        Args:
            query: Search query text
            user_profile: Optional user profile for combined scoring
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of SearchResult objects
        """
        loop = asyncio.get_event_loop()
        
        # Run search in thread pool to avoid blocking
        results = await loop.run_in_executor(
            self._executor,
            self.semantic_search,
            query,
            user_profile,
            top_k,
            similarity_threshold
        )
        
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the search service.
        
        Returns:
            Dictionary with performance statistics
        """
        kb_stats = self.knowledge_base.get_performance_stats()
        
        return {
            'knowledge_base': kb_stats,
            'embedding_service': {
                'fitted': self.embedding_service.fitted,
                'vocabulary_size': len(self.embedding_service.vectorizer.vocabulary_) if self.embedding_service.fitted else 0,
                'embedding_dimension': self.embedding_service.embedding_dim
            },
            'thread_pool': {
                'max_workers': self.max_workers,
                'active_threads': self._executor._threads if hasattr(self._executor, '_threads') else 0
            }
        }
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
class MockEmbeddingService:
    """
    Mock embedding service using TF-IDF vectorization with optimized operations.
    
    This service provides a lightweight alternative to foundation models by using
    TF-IDF (Term Frequency-Inverse Document Frequency) to generate embeddings
    for search queries and scheme content with vectorized operations.
    """
    
    def __init__(self, embedding_dim: int = 384):
        """
        Initialize the mock embedding service.
        
        Args:
            embedding_dim: Dimension of the generated embeddings
        """
        self.embedding_dim = embedding_dim
        self.vectorizer = TfidfVectorizer(
            max_features=embedding_dim,
            stop_words='english',
            lowercase=True,
            ngram_range=(1, 2),  # Include both unigrams and bigrams
            min_df=1,  # Include all terms
            max_df=0.95  # Exclude very common terms
        )
        self.fitted = False
        self.scheme_texts = []
        self._embedding_cache = {}
    
    def fit_on_schemes(self, schemes: List[SchemeModel]) -> None:
        """
        Fit the TF-IDF vectorizer on scheme texts.
        
        Args:
            schemes: List of schemes to train the vectorizer on
        """
        # Combine all searchable text from schemes
        self.scheme_texts = []
        for scheme in schemes:
            text = f"{scheme.name} {scheme.description} {scheme.keywords}".lower()
            self.scheme_texts.append(text)
        
        if self.scheme_texts:
            # Fit the vectorizer on all scheme texts
            self.vectorizer.fit(self.scheme_texts)
            self.fitted = True
    
    @lru_cache(maxsize=1000)
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text using TF-IDF with caching.
        
        Args:
            text: Input text to generate embedding for
            
        Returns:
            List of float values representing the embedding
        """
        if not self.fitted:
            # Return zero vector if not fitted
            return [0.0] * self.embedding_dim
        
        try:
            # Transform text to TF-IDF vector
            tfidf_vector = self.vectorizer.transform([text.lower()])
            
            # Convert sparse matrix to dense array
            dense_vector = tfidf_vector.toarray()[0]
            
            # Pad or truncate to match embedding dimension
            if len(dense_vector) < self.embedding_dim:
                # Pad with zeros
                padded_vector = np.zeros(self.embedding_dim, dtype=np.float32)
                padded_vector[:len(dense_vector)] = dense_vector
                return padded_vector.tolist()
            else:
                # Truncate to embedding dimension
                return dense_vector[:self.embedding_dim].astype(np.float32).tolist()
                
        except Exception as e:
            logger.error(f"Error generating embedding for text: {str(e)}")
            raise EmbeddingServiceException(
                query=text,
                message=f"Failed to generate embedding: {str(e)}",
                original_exception=e
            )
    
    def generate_batch_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts in batch for efficiency.
        
        Args:
            texts: List of input texts
            
        Returns:
            NumPy array of embeddings (n_texts, embedding_dim)
        """
        if not self.fitted:
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
        
        try:
            # Transform all texts at once
            tfidf_matrix = self.vectorizer.transform([text.lower() for text in texts])
            
            # Convert to dense array
            dense_matrix = tfidf_matrix.toarray().astype(np.float32)
            
            # Pad or truncate to match embedding dimension
            n_texts, current_dim = dense_matrix.shape
            
            if current_dim < self.embedding_dim:
                # Pad with zeros
                padded_matrix = np.zeros((n_texts, self.embedding_dim), dtype=np.float32)
                padded_matrix[:, :current_dim] = dense_matrix
                return padded_matrix
            else:
                # Truncate to embedding dimension
                return dense_matrix[:, :self.embedding_dim]
                
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise EmbeddingServiceException(
                query=f"Batch of {len(texts)} texts",
                message=f"Failed to generate batch embeddings: {str(e)}",
                original_exception=e
            )
    
    def generate_scheme_embeddings(self, schemes: List[SchemeModel]) -> Dict[str, List[float]]:
        """
        Generate embeddings for all schemes using batch processing.
        
        Args:
            schemes: List of schemes to generate embeddings for
            
        Returns:
            Dictionary mapping scheme IDs to their embeddings
        """
        if not self.fitted:
            self.fit_on_schemes(schemes)
        
        # Prepare texts for batch processing
        texts = []
        scheme_ids = []
        for scheme in schemes:
            text = f"{scheme.name} {scheme.description} {scheme.keywords}"
            texts.append(text)
            scheme_ids.append(scheme.id)
        
        # Generate embeddings in batch
        embeddings_matrix = self.generate_batch_embeddings(texts)
        
        # Convert to dictionary
        embeddings = {}
        for i, scheme_id in enumerate(scheme_ids):
            embeddings[scheme_id] = embeddings_matrix[i].tolist()
        
        return embeddings
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self.generate_embedding.cache_clear()
        self._embedding_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_info = self.generate_embedding.cache_info()
        return {
            'cache_hits': cache_info.hits,
            'cache_misses': cache_info.misses,
            'cache_size': cache_info.currsize,
            'cache_maxsize': cache_info.maxsize,
            'hit_rate': cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
        }


class SearchService(VectorizedSearchService):
    """
    Service for semantic search capabilities with combined scoring.
    
    This service provides semantic search using TF-IDF embeddings and cosine
    similarity, with optional integration of eligibility matching for combined
    scoring that considers both relevance and user eligibility.
    Enhanced with vectorized operations for better performance.
    """
    
    def __init__(
        self,
        knowledge_base: KnowledgeBaseService,
        eligibility_service: Optional[EligibilityService] = None
    ):
        """
        Initialize the search service.
        
        Args:
            knowledge_base: Knowledge base service for scheme data
            eligibility_service: Optional eligibility service for combined scoring
        """
        super().__init__(knowledge_base, eligibility_service)
        
        # Backward compatibility methods
        self._legacy_mode = False
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding as list of floats
        """
        return self.embedding_service.generate_embedding(query)
    
    def calculate_similarity(
        self,
        query_embedding: List[float],
        scheme_embedding: List[float]
    ) -> float:
        """
        Calculate cosine similarity between query and scheme embeddings.
        
        Args:
            query_embedding: Query embedding vector
            scheme_embedding: Scheme embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            # Convert to numpy arrays and reshape for sklearn
            query_vec = np.array(query_embedding).reshape(1, -1)
            scheme_vec = np.array(scheme_embedding).reshape(1, -1)
            
            # Calculate cosine similarity using scikit-learn
            similarity = cosine_similarity(query_vec, scheme_vec)[0][0]
            
            # Ensure similarity is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            raise ProcessingException(
                operation="cosine_similarity_calculation",
                message=f"Failed to calculate similarity: {str(e)}",
                original_exception=e
            )
    
    def semantic_search(
        self,
        query: str,
        user_profile: Optional[UserProfile] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform semantic search with optional combined scoring.
        
        Args:
            query: Search query text
            user_profile: Optional user profile for combined scoring
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not query.strip():
            return []
        
        # Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        
        # Get all schemes from knowledge base
        schemes = self.knowledge_base.get_all_schemes()
        if not schemes:
            return []
        
        # Calculate similarities and create search results
        results = []
        for scheme in schemes:
            if not scheme.embedding:
                continue
            
            # Calculate semantic similarity
            similarity_score = self.calculate_similarity(query_embedding, scheme.embedding)
            
            # Skip if below threshold
            if similarity_score < similarity_threshold:
                continue
            
            # Calculate combined score if user profile provided
            combined_score = None
            if user_profile:
                # Get eligibility match score (0-100)
                eligibility_score = self.eligibility_service.calculate_match_score(
                    user_profile, scheme
                )
                
                # Combine semantic similarity (0-1) with eligibility (0-100)
                # Convert similarity to 0-100 scale and weight both equally
                semantic_score_scaled = similarity_score * 100
                combined_score = (semantic_score_scaled + eligibility_score) / 2
            
            # Create search result
            search_result = SearchResult(
                scheme=scheme,
                similarity_score=similarity_score,
                combined_score=combined_score
            )
            results.append(search_result)
        
        # Sort results by combined score if available, otherwise by similarity
        if user_profile:
            results.sort(key=lambda x: x.combined_score or 0, reverse=True)
        else:
            results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Return top K results
        return results[:top_k]
    
    def search_with_filters(
        self,
        query: str,
        user_profile: Optional[UserProfile] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform semantic search with additional filters.
        
        Args:
            query: Search query text
            user_profile: Optional user profile for combined scoring
            category: Optional category filter
            state: Optional state filter
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of filtered SearchResult objects
        """
        # Get filtered schemes from knowledge base
        filtered_schemes = self.knowledge_base.filter_schemes(
            category=category,
            state=state
        )
        
        if not filtered_schemes:
            return []
        
        # Generate query embedding
        query_embedding = self.generate_query_embedding(query)
        
        # Calculate similarities for filtered schemes
        results = []
        for scheme in filtered_schemes:
            if not scheme.embedding:
                continue
            
            # Calculate semantic similarity
            similarity_score = self.calculate_similarity(query_embedding, scheme.embedding)
            
            # Skip if below threshold
            if similarity_score < similarity_threshold:
                continue
            
            # Calculate combined score if user profile provided
            combined_score = None
            if user_profile:
                eligibility_score = self.eligibility_service.calculate_match_score(
                    user_profile, scheme
                )
                semantic_score_scaled = similarity_score * 100
                combined_score = (semantic_score_scaled + eligibility_score) / 2
            
            # Create search result
            search_result = SearchResult(
                scheme=scheme,
                similarity_score=similarity_score,
                combined_score=combined_score
            )
            results.append(search_result)
        
        # Sort and return top K results
        if user_profile:
            results.sort(key=lambda x: x.combined_score or 0, reverse=True)
        else:
            results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results[:top_k]
    
    def get_similar_schemes(
        self,
        scheme_id: str,
        top_k: int = 3,
        similarity_threshold: float = 0.4
    ) -> List[SearchResult]:
        """
        Find schemes similar to a given scheme.
        
        Args:
            scheme_id: ID of the reference scheme
            top_k: Maximum number of similar schemes to return
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of similar SearchResult objects
        """
        # Get the reference scheme
        reference_scheme = self.knowledge_base.get_scheme_by_id(scheme_id)
        if not reference_scheme or not reference_scheme.embedding:
            return []
        
        # Get all other schemes
        all_schemes = self.knowledge_base.get_all_schemes()
        similar_schemes = []
        
        for scheme in all_schemes:
            # Skip the reference scheme itself
            if scheme.id == scheme_id or not scheme.embedding:
                continue
            
            # Calculate similarity
            similarity_score = self.calculate_similarity(
                reference_scheme.embedding,
                scheme.embedding
            )
            
            # Skip if below threshold
            if similarity_score < similarity_threshold:
                continue
            
            # Create search result
            search_result = SearchResult(
                scheme=scheme,
                similarity_score=similarity_score,
                combined_score=None
            )
            similar_schemes.append(search_result)
        
        # Sort by similarity and return top K
        similar_schemes.sort(key=lambda x: x.similarity_score, reverse=True)
        return similar_schemes[:top_k]
    
    def update_scheme_embeddings(self, schemes: List[SchemeModel]) -> None:
        """
        Update embeddings for a list of schemes.
        
        Args:
            schemes: List of schemes to update embeddings for
        """
        for scheme in schemes:
            if not scheme.embedding:
                text = f"{scheme.name} {scheme.description} {scheme.keywords}"
                scheme.embedding = self.embedding_service.generate_embedding(text)
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        Get search service statistics.
        
        Returns:
            Dictionary with search service statistics
        """
        schemes = self.knowledge_base.get_all_schemes()
        schemes_with_embeddings = sum(1 for s in schemes if s.embedding)
        
        return {
            'total_schemes': len(schemes),
            'schemes_with_embeddings': schemes_with_embeddings,
            'embedding_dimension': self.embedding_service.embedding_dim,
            'vectorizer_fitted': self.embedding_service.fitted,
            'vocabulary_size': len(self.embedding_service.vectorizer.vocabulary_) if self.embedding_service.fitted else 0
        }