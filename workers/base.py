from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseWorker(ABC):
    @abstractmethod
    def process(self, job_data: Dict[str, Any]) -> None:
        """
        Process a job from the RabbitMQ queue.
        
        Args:
            job_data: The job data received from the queue
        """
        pass 