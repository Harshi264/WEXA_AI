import os
import gzip
import urllib.request
import polars as pl
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
SNAP_URL = "https://snap.stanford.edu/data/email-Enron.txt.gz"
GZ_PATH = os.path.join(DATA_DIR, "email-Enron.txt.gz")
TXT_PATH = os.path.join(DATA_DIR, "email-Enron.txt")

NODES_CSV = os.path.join(DATA_DIR, "nodes.csv")
EDGES_CSV = os.path.join(DATA_DIR, "edges.csv")

def download_data():
    """Download the Enron Email network from SNAP."""
    if not os.path.exists(GZ_PATH) and not os.path.exists(TXT_PATH):
        console.print(f"[bold blue]Downloading dataset from {SNAP_URL}...[/bold blue]")
        urllib.request.urlretrieve(SNAP_URL, GZ_PATH)
        console.print("[green]Download complete.[/green]")

    if not os.path.exists(TXT_PATH):
        console.print("[bold blue]Extracting dataset...[/bold blue]")
        with gzip.open(GZ_PATH, 'rb') as f_in:
            with open(TXT_PATH, 'wb') as f_out:
                f_out.write(f_in.read())
        console.print("[green]Extraction complete.[/green]")

def process_data():
    """Process the SNAP txt file into nodes and edges CSVs using Polars."""
    console.print("[bold blue]Processing data with Polars...[/bold blue]")
    
    # Read edges, skipping the 4 header lines starting with '#'
    df_edges = pl.read_csv(
        TXT_PATH, 
        separator="\t", 
        has_header=False, 
        skip_rows=4,
        new_columns=["source", "target"]
    )
    
    # Generate unique nodes from both source and target columns
    unique_nodes = pl.concat([df_edges["source"], df_edges["target"]]).unique().to_frame("id")
    
    # Add a static label to nodes and a type to edges (helps with some DB schemas)
    df_nodes = unique_nodes.with_columns(pl.lit("Employee").alias("label"))
    df_edges = df_edges.with_columns(pl.lit("EMAILED").alias("type"))
    
    # Downsample slightly if needed (optional), but 183k edges is perfect for free tiers.
    # We will use the full Enron set.
    
    # Save to CSV
    df_nodes.write_csv(NODES_CSV)
    df_edges.write_csv(EDGES_CSV)
    
    console.print(f"[bold green]Saved {len(df_nodes)} nodes to {NODES_CSV}[/bold green]")
    console.print(f"[bold green]Saved {len(df_edges)} edges to {EDGES_CSV}[/bold green]")

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    download_data()
    process_data()
    console.print("[bold green]Phase 1: Data Preparation Complete![/bold green]")
