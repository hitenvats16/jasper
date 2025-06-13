from pydantic import BaseModel
from typing import Optional, List
import numpy as np
import uuid

class VoiceEmbedding(BaseModel):
    id: str  # This will be a UUID
    job_id: int
    voice_id: Optional[int]
    embedding: List[float]  # The target_se tensor converted to a list
    metadata: dict  # Additional metadata like filename, processing time, etc.

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_tensor(cls, job_id: int, voice_id: Optional[int], target_se: np.ndarray, metadata: dict = None):
        """Create a VoiceEmbedding instance from a tensor"""
        # The target_se tensor has shape [1, 256, 1], we need to extract the 256-dimensional vector
        if target_se.shape != (1, 256, 1):
            raise ValueError(f"Expected tensor shape (1, 256, 1), got {target_se.shape}")
        
        # Extract the 256-dimensional vector from the middle dimension
        embedding_vector = target_se[0, :, 0].flatten().tolist()
        
        return cls(
            id=str(uuid.uuid4()),  # Generate a UUID for the point ID
            job_id=job_id,
            voice_id=voice_id,
            embedding=embedding_vector,
            metadata={
                **(metadata or {}),
                "tensor_shape": list(target_se.shape),
                "vector_size": len(embedding_vector),
                "job_id": job_id,  # Include job_id in metadata for querying
                "voice_id": voice_id  # Include voice_id in metadata for querying
            }
        ) 