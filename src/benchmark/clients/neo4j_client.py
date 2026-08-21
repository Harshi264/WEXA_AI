import time
import random
import polars as pl
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from neo4j import GraphDatabase
from rich.console import Console
from src.benchmark.base_client import GraphDatabaseClient

console = Console()

class Neo4jClient(GraphDatabaseClient):
    """
    Client for Neo4j, CognoDB, and Memgraph.
    """
    def __init__(self, uri: str, user: str, password: str, name: str = "Neo4j"):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.name = name

    def connect(self) -> None:
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.driver.verify_connectivity()
        console.print(f"[bold green]Connected to {self.name} at {self.uri}[/bold green]")

    def teardown(self) -> None:
        if self.driver:
            self.driver.close()

    def load_data(self, nodes_path: str, edges_path: str) -> Dict[str, float]:
        console.print(f"[bold blue]Starting ingestion for {self.name}...[/bold blue]")
        df_nodes = pl.read_csv(nodes_path)
        df_edges = pl.read_csv(edges_path)
        
        nodes_batch = df_nodes.to_dicts()
        edges_batch = df_edges.to_dicts()
        
        start_time = time.time()
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            
            node_query = """
            UNWIND $batch AS row
            CREATE (n:Node {id: row.id, label: row.label})
            """
            session.run(node_query, batch=nodes_batch)
            
            try:
                session.run("CREATE INDEX FOR (n:Node) ON (n.id)")
            except Exception:
                pass
                
        nodes_time = time.time() - start_time
        edges_start = time.time()
        
        with self.driver.session() as session:
            edge_query = """
            UNWIND $batch AS row
            MATCH (source:Node {id: row.source})
            MATCH (target:Node {id: row.target})
            CREATE (source)-[:EMAILED {type: row.type}]->(target)
            """
            batch_size = 10000
            for i in range(0, len(edges_batch), batch_size):
                session.run(edge_query, batch=edges_batch[i:i+batch_size])
                
        end_time = time.time()
        return {
            'nodes_per_sec': len(nodes_batch) / nodes_time,
            'edges_per_sec': len(edges_batch) / (end_time - edges_start),
            'total_time_sec': end_time - start_time
        }

    def run_traversal(self, start_node_id: str, hops: int) -> float:
        query = f"MATCH (start:Node {{id: $id}})-[*1..{hops}]->(end) RETURN count(end)"
        start_time = time.perf_counter()
        with self.driver.session() as session:
            session.run(query, id=start_node_id).consume()
        return (time.perf_counter() - start_time) * 1000

    def run_lookup(self, property_name: str, property_value: Any, indexed: bool = False) -> float:
        # Assuming index exists on 'id' if indexed=True
        query = f"MATCH (n:Node) WHERE n.{property_name} = $val RETURN n.id LIMIT 1"
        start_time = time.perf_counter()
        with self.driver.session() as session:
            session.run(query, val=property_value).consume()
        return (time.perf_counter() - start_time) * 1000

    def run_aggregation(self) -> float:
        query = "MATCH (n:Node) RETURN n.label, count(n)"
        start_time = time.perf_counter()
        with self.driver.session() as session:
            session.run(query).consume()
        return (time.perf_counter() - start_time) * 1000

    async def run_mixed_workload(self, concurrency: int, duration_sec: int) -> Dict[str, float]:
        # Using a thread pool to simulate concurrent clients
        def _worker():
            queries_run = 0
            end_time = time.time() + duration_sec
            with self.driver.session() as session:
                while time.time() < end_time:
                    op = random.choice(["read", "write", "traverse"])
                    node_id = random.choice(["1", "10", "100", "500", "1000"])
                    try:
                        if op == "read":
                            session.run("MATCH (n:Node {id: $id}) RETURN n", id=node_id).consume()
                        elif op == "write":
                            session.run("MATCH (n:Node {id: $id}) SET n.updated = timestamp()", id=node_id).consume()
                        else:
                            session.run("MATCH (n:Node {id: $id})-[:EMAILED]->(m) RETURN m LIMIT 5", id=node_id).consume()
                        queries_run += 1
                    except Exception:
                        pass
            return queries_run

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(_worker) for _ in range(concurrency)]
            results = [f.result() for f in futures]
            
        total_queries = sum(results)
        actual_duration = time.time() - start_time
        
        return {'queries_per_sec': total_queries / actual_duration}
