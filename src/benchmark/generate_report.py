import os
import glob
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from rich.console import Console

console = Console()
sns.set_theme(style="whitegrid", context="talk")

def load_results():
    data = []
    # Find all results_*.json files
    files = glob.glob("results_*.json")
    for f in files:
        db_name = f.replace("results_", "").replace(".json", "").capitalize()
        with open(f, 'r') as file:
            res = json.load(file)
            
            # Extract traversals
            for hop in ['1-hop', '2-hop', '3-hop']:
                data.append({
                    'Database': db_name,
                    'Workload': f'{hop} Traversal',
                    'Latency (ms)': res.get(hop, {}).get('p50', 0),
                    'Metric': 'p50'
                })
                data.append({
                    'Database': db_name,
                    'Workload': f'{hop} Traversal',
                    'Latency (ms)': res.get(hop, {}).get('p95', 0),
                    'Metric': 'p95'
                })
                
            # Extract Lookups
            data.append({
                'Database': db_name,
                'Workload': 'Point Lookup',
                'Latency (ms)': res.get('lookup', {}).get('p50', 0),
                'Metric': 'p50'
            })
            data.append({
                'Database': db_name,
                'Workload': 'Point Lookup',
                'Latency (ms)': res.get('lookup', {}).get('p95', 0),
                'Metric': 'p95'
            })
            
            # Extract Aggregations
            data.append({
                'Database': db_name,
                'Workload': 'Aggregation',
                'Latency (ms)': res.get('aggregation', {}).get('p50', 0),
                'Metric': 'p50'
            })
            
    return pd.DataFrame(data)

def generate_charts():
    df = load_results()
    if df.empty:
        console.print("[bold red]No results_*.json files found. Run the benchmarks first![/bold red]")
        return
        
    os.makedirs("charts", exist_ok=True)
    
    # 1. Traversal Latencies Chart (p50)
    plt.figure(figsize=(12, 6))
    df_trav = df[(df['Workload'].str.contains('hop')) & (df['Metric'] == 'p50')]
    sns.barplot(data=df_trav, x='Workload', y='Latency (ms)', hue='Database', palette="viridis")
    plt.title("Traversal Latency (p50) - Lower is Better", pad=20, fontsize=16)
    plt.yscale('log')
    plt.ylabel("Latency (ms) - Log Scale")
    plt.tight_layout()
    plt.savefig("charts/traversals_p50.png", dpi=300)
    plt.close()
    
    # 2. Lookups and Aggregations Chart
    plt.figure(figsize=(10, 6))
    df_misc = df[(df['Workload'].isin(['Point Lookup', 'Aggregation'])) & (df['Metric'] == 'p50')]
    sns.barplot(data=df_misc, x='Workload', y='Latency (ms)', hue='Database', palette="rocket")
    plt.title("Lookup & Aggregation Latency (p50) - Lower is Better", pad=20, fontsize=16)
    plt.ylabel("Latency (ms)")
    plt.tight_layout()
    plt.savefig("charts/lookups_aggs_p50.png", dpi=300)
    plt.close()
    
    console.print("[bold green]Successfully generated publication-quality charts in the 'charts' directory![/bold green]")

if __name__ == "__main__":
    console.print("[cyan]Generating benchmark charts...[/cyan]")
    generate_charts()
