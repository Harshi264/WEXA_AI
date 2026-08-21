import os
import time
import json
import asyncio
import numpy as np
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.benchmark.clients import Neo4jClient, ArangoDBClient

app = typer.Typer(help="Graph Database Benchmarking Suite")
console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
NODES_PATH = os.path.join(DATA_DIR, "nodes.csv")
EDGES_PATH = os.path.join(DATA_DIR, "edges.csv")

def get_client(db_name: str):
    if db_name.lower() == "cognodb":
        return Neo4jClient(os.getenv("COGNO_URI"), os.getenv("COGNO_USER"), os.getenv("COGNO_PASSWORD"), name="CognoDB")
    elif db_name.lower() == "neo4j":
        return Neo4jClient(os.getenv("NEO4J_URI"), os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"), name="Neo4j")
    elif db_name.lower() == "memgraph":
        return Neo4jClient(os.getenv("MEMGRAPH_URI"), os.getenv("MEMGRAPH_USER", ""), os.getenv("MEMGRAPH_PASSWORD"), name="Memgraph")
    elif db_name.lower() == "arangodb":
        return ArangoDBClient(os.getenv("ARANGO_URL"), os.getenv("ARANGO_USER"), os.getenv("ARANGO_PASSWORD"))
    else:
        raise ValueError(f"Unknown database: {db_name}")

@app.command()
def ingest(db: str):
    """Load data into the specified database."""
    client = get_client(db)
    client.connect()
    try:
        metrics = client.load_data(NODES_PATH, EDGES_PATH)
        console.print(f"[bold green]Ingestion Metrics for {db}:[/bold green]")
        console.print(metrics)
    finally:
        client.teardown()

@app.command()
def run(db: str, runs: int = 100, warmup: int = 20):
    """Run read and mixed workloads."""
    client = get_client(db)
    client.connect()
    
    results = {}
    
    try:
        # We need some valid start nodes for traversals and lookups. 
        # Using a few hardcoded ones that exist in Enron dataset
        sample_nodes = ["1", "10", "100", "500", "1000"]
        
        with Progress(TextColumn("[progress.description]{task.description}"), console=console) as progress:
            
            # --- 1. Traversals ---
            task_trav = progress.add_task(f"[cyan]Running Traversals on {db}...", total=None)
            for hops in [1, 2, 3]:
                latencies = []
                for _ in range(warmup):
                    client.run_traversal(random.choice(sample_nodes), hops)
                for _ in range(runs):
                    node = random.choice(sample_nodes)
                    latencies.append(client.run_traversal(node, hops))
                
                results[f'{hops}-hop'] = {
                    'p50': np.percentile(latencies, 50),
                    'p95': np.percentile(latencies, 95)
                }
            progress.update(task_trav, completed=True)
                
            # --- 2. Lookups ---
            task_look = progress.add_task(f"[cyan]Running Lookups on {db}...", total=None)
            lookups = []
            for _ in range(warmup):
                client.run_lookup('id', random.choice(sample_nodes), indexed=True)
            for _ in range(runs):
                lookups.append(client.run_lookup('id', random.choice(sample_nodes), indexed=True))
            results['lookup'] = {
                'p50': np.percentile(lookups, 50),
                'p95': np.percentile(lookups, 95)
            }
            progress.update(task_look, completed=True)
            
            # --- 3. Aggregations ---
            task_agg = progress.add_task(f"[cyan]Running Aggregations on {db}...", total=None)
            aggs = []
            for _ in range(warmup // 2):
                client.run_aggregation()
            for _ in range(runs // 2): # Less runs for heavy aggs
                aggs.append(client.run_aggregation())
            results['aggregation'] = {
                'p50': np.percentile(aggs, 50),
                'p95': np.percentile(aggs, 95)
            }
            progress.update(task_agg, completed=True)
            
            # --- 4. Mixed Workload ---
            task_mix = progress.add_task(f"[cyan]Running Mixed Concurrency on {db}...", total=None)
            results['mixed_throughput'] = {}
            for concurrency in [1, 10, 40]:
                res = asyncio.run(client.run_mixed_workload(concurrency, duration_sec=5))
                results['mixed_throughput'][f'{concurrency}_clients'] = res['queries_per_sec']
            progress.update(task_mix, completed=True)
            
        console.print(f"[bold green]Benchmark Results for {db}:[/bold green]")
        console.print(json.dumps(results, indent=2))
        
        # Save to file
        with open(f"results_{db}.json", "w") as f:
            json.dump(results, f, indent=2)
            
    finally:
        client.teardown()

if __name__ == "__main__":
    import random # ensure random is available inside
    app()
