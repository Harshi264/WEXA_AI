import time
import random
import polars as pl
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from arango import ArangoClient
from rich.console import Console
from src.benchmark.base_client import GraphDatabaseClient

console = Console()

class ArangoDBClient(GraphDatabaseClient):
    """
    Client for ArangoDB. Uses AQL instead of Cypher.
    """
    def __init__(self, url: str, user: str, password: str, database: str = "benchmark"):
        self.client = ArangoClient(hosts=url)
        self.user = user
        self.password = password
        self.db_name = database
        self.sys_db = None
        self.db = None

    def connect(self) -> None:
        self.sys_db = self.client.db("_system", username=self.user, password=self.password)
        if not self.sys_db.has_database(self.db_name):
            self.sys_db.create_database(self.db_name)
        self.db = self.client.db(self.db_name, username=self.user, password=self.password)
        console.print(f"[bold green]Connected to ArangoDB database '{self.db_name}'[/bold green]")

    def teardown(self) -> None:
        pass

    def load_data(self, nodes_path: str, edges_path: str) -> Dict[str, float]:
        console.print("[bold blue]Starting ingestion for ArangoDB...[/bold blue]")
        if self.db.has_collection("Nodes"):
            self.db.delete_collection("Nodes")
        if self.db.has_collection("Edges"):
            self.db.delete_collection("Edges")
            
        nodes_coll = self.db.create_collection("Nodes")
        edges_coll = self.db.create_collection("Edges", edge=True)
        
        # Create an index on 'id' for fast lookups
        nodes_coll.add_hash_index(fields=["id"], unique=False)
        
        df_nodes = pl.read_csv(nodes_path)
        df_edges = pl.read_csv(edges_path)
        
        nodes_batch = [{"_key": str(row["id"]), "id": row["id"], "label": row["label"]} for row in df_nodes.to_dicts()]
        edges_batch = [{"_from": f"Nodes/{row['source']}", "_to": f"Nodes/{row['target']}", "type": row["type"]} for row in df_edges.to_dicts()]
        
        start_time = time.time()
        batch_size = 10000
        for i in range(0, len(nodes_batch), batch_size):
            nodes_coll.insert_many(nodes_batch[i:i+batch_size])
            
        nodes_time = time.time() - start_time
        edges_start = time.time()
        for i in range(0, len(edges_batch), batch_size):
            edges_coll.insert_many(edges_batch[i:i+batch_size])
            
        end_time = time.time()
        return {
            'nodes_per_sec': len(nodes_batch) / nodes_time,
            'edges_per_sec': len(edges_batch) / (end_time - edges_start),
            'total_time_sec': end_time - start_time
        }

    def run_traversal(self, start_node_id: str, hops: int) -> float:
        query = f"""
        FOR v IN 1..{hops} OUTBOUND 'Nodes/{start_node_id}' Edges
            COLLECT WITH COUNT INTO length
            RETURN length
        """
        start_time = time.perf_counter()
        cursor = self.db.aql.execute(query)
        # Force evaluation
        list(cursor)
        return (time.perf_counter() - start_time) * 1000

    def run_lookup(self, property_name: str, property_value: Any, indexed: bool = False) -> float:
        query = f"""
        FOR n IN Nodes
            FILTER n.{property_name} == @val
            LIMIT 1
            RETURN n._key
        """
        start_time = time.perf_counter()
        cursor = self.db.aql.execute(query, bind_vars={"val": property_value})
        list(cursor)
        return (time.perf_counter() - start_time) * 1000

    def run_aggregation(self) -> float:
        query = """
        FOR n IN Nodes
            COLLECT label = n.label WITH COUNT INTO count
            RETURN {label: label, count: count}
        """
        start_time = time.perf_counter()
        cursor = self.db.aql.execute(query)
        list(cursor)
        return (time.perf_counter() - start_time) * 1000

    async def run_mixed_workload(self, concurrency: int, duration_sec: int) -> Dict[str, float]:
        def _worker():
            queries_run = 0
            end_time = time.time() + duration_sec
            while time.time() < end_time:
                op = random.choice(["read", "write", "traverse"])
                node_id = random.choice(["1", "10", "100", "500", "1000"])
                try:
                    if op == "read":
                        self.db.aql.execute("FOR n IN Nodes FILTER n._key == @id RETURN n", bind_vars={"id": node_id}).batch()
                    elif op == "write":
                        self.db.aql.execute("FOR n IN Nodes FILTER n._key == @id UPDATE n WITH { updated: DATE_NOW() } IN Nodes", bind_vars={"id": node_id})
                    else:
                        self.db.aql.execute("FOR v IN 1..1 OUTBOUND CONCAT('Nodes/', @id) Edges LIMIT 5 RETURN v", bind_vars={"id": node_id}).batch()
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
