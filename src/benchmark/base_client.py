from abc import ABC, abstractmethod
from typing import Dict, Any, List

class GraphDatabaseClient(ABC):
    """
    Abstract Base Class for all Graph Database clients in the benchmarking suite.
    Enforces a strict interface so all databases are benchmarked identically.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        pass

    @abstractmethod
    def teardown(self) -> None:
        """Close connection and clean up resources."""
        pass

    @abstractmethod
    def load_data(self, nodes_path: str, edges_path: str) -> Dict[str, float]:
        """
        Load nodes and edges into the database.
        Returns a dictionary with metrics:
        - 'nodes_per_sec': float
        - 'edges_per_sec': float
        - 'total_time_sec': float
        """
        pass

    @abstractmethod
    def run_traversal(self, start_node_id: str, hops: int) -> float:
        """
        Run an N-hop traversal from a starting node.
        Returns the latency in milliseconds.
        """
        pass

    @abstractmethod
    def run_lookup(self, property_name: str, property_value: Any, indexed: bool = False) -> float:
        """
        Run a point lookup.
        Returns the latency in milliseconds.
        """
        pass

    @abstractmethod
    def run_aggregation(self) -> float:
        """
        Run a count/group-by aggregation query.
        Returns the latency in milliseconds.
        """
        pass

    @abstractmethod
    async def run_mixed_workload(self, concurrency: int, duration_sec: int) -> Dict[str, float]:
        """
        Run a mixed read/write workload using `asyncio` for the given duration.
        Returns throughput metrics:
        - 'queries_per_sec': float
        """
        pass
