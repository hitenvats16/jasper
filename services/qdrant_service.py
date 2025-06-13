from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, Filter, FieldCondition, Match
from models.voice_embedding import VoiceEmbedding
from core.config import settings
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = "voice_embeddings"
        self.vector_size = 256  # Size of the voice embedding vector
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info(f"Initializing Qdrant client with URL: {self.url}")
        self.client = QdrantClient(url=self.url, api_key=self.api_key)
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Ensure the collection exists, create if it doesn't"""
        for attempt in range(self.max_retries):
            try:
                collections = self.client.get_collections().collections
                collection_names = [collection.name for collection in collections]
                
                if self.collection_name not in collection_names:
                    logger.info(f"Creating collection: {self.collection_name}")
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.vector_size,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Collection {self.collection_name} created successfully")
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed to connect to Qdrant: {str(e)}")
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect to Qdrant after {self.max_retries} attempts: {str(e)}")
                    raise

    def store_embedding(self, embedding: VoiceEmbedding):
        """Store a voice embedding in Qdrant"""
        try:
            # Validate vector size
            if len(embedding.embedding) != self.vector_size:
                raise ValueError(f"Expected vector size {self.vector_size}, got {len(embedding.embedding)}")
            
            # Upsert the embedding
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=embedding.id,
                        vector=embedding.embedding,
                        payload=embedding.metadata
                    )
                ]
            )
            logger.info(f"Successfully stored embedding for job {embedding.job_id}")
        except Exception as e:
            logger.error(f"Error storing embedding: {str(e)}")
            raise

    def get_embedding(self, job_id: int, voice_id: Optional[int] = None) -> Optional[VoiceEmbedding]:
        """Get a voice embedding by job_id and optionally voice_id"""
        try:
            # Create filter conditions
            conditions = [FieldCondition(key="job_id", match=Match(value=job_id))]
            if voice_id is not None:
                conditions.append(FieldCondition(key="voice_id", match=Match(value=voice_id)))
            
            # Search with filter
            results = self.client.scroll(
                collection_name=self.collection_name,
                filter=Filter(must=conditions),
                limit=1
            )[0]  # Get first page of results
            
            if not results:
                return None
                
            point = results[0]
            return VoiceEmbedding(
                id=point.id,
                job_id=point.payload["job_id"],
                voice_id=point.payload.get("voice_id"),
                embedding=point.vector,
                metadata=point.payload
            )
        except Exception as e:
            logger.error(f"Error retrieving embedding: {str(e)}")
            return None

    def search_similar_voices(self, embedding: List[float], limit: int = 5) -> List[dict]:
        """Search for similar voice embeddings"""
        try:
            # Validate vector size
            if len(embedding) != self.vector_size:
                raise ValueError(f"Expected vector size {self.vector_size}, got {len(embedding)}")
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limit
            )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Error searching similar voices: {str(e)}")
            return [] 