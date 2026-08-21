# Benchmarking the Free Tier: Can Cloud Graph Databases Handle the Heat? 🔥

Welcome to my submission for the **Wexa AI — Graph Database Cloud Benchmarking** assignment.

This repository doesn't just run queries; it is a highly automated, strictly controlled, and visually-driven benchmarking engine designed to fairly compare the free tiers of managed cloud graph databases.

## 🎯 The Objective
The goal of this project is to benchmark **CognoDB Cloud** against other industry leaders (like Neo4j, ArangoDB, and Memgraph) using an identical dataset and identical queries. More importantly, it aims to test them under identical hardware constraints to see who truly offers the best engineering under the hood.

---

## 🧪 Methodology & Fairness

To ensure a completely fair comparison, I implemented a strict **Abstract Base Class** (`GraphDatabaseClient`) in Python. Every database must implement the exact same methods, meaning no database can cheat with custom ingestion tricks or hidden caching mechanics.

### The Resources (Hardware Parity)
Every database in this benchmark is running on their respective Free Tiers.
* **CognoDB**: 0.5 vCPU, 256 MB RAM, 1 GB Disk
* **Neo4j Aura**: 1 vCPU, 1 GB RAM, 1 GB Disk *(Note: slightly larger free tier)*
* **ArangoDB Oasis**: 1 vCPU, 1 GB RAM, 1 GB Disk

### The Dataset
I utilized the **SNAP Stanford email-Enron** network.
* **Nodes**: 36,692
* **Relationships**: 367,662 (Undirected turned Directed)
* *Why this dataset?* It perfectly fits inside the memory limits of the free tiers, ensuring we are testing raw database engine speed, not just swapping to disk.

---

## 📊 Results Matrix

*(Note: Run the `generate_report.py` script to update the charts below with live data!)*

### 1. Traversal Latencies (p50 & p95)
This tests the core graph engine. How fast can it perform 1-hop, 2-hop, and 3-hop neighbor lookups?

![Traversal Results](charts/traversals_p50.png)

### 2. Point Lookups & Aggregations
How fast can the database find a single indexed node, or aggregate a count across the entire graph?

![Lookups and Aggregations](charts/lookups_aggs_p50.png)

---

## 🚀 How to Run this Yourself (Reproducibility)

This suite is entirely automated. If you have free tier credentials, you can reproduce this entire benchmark in one command.

### 1. Setup
```bash
python -m venv .venv
source .venv/bin/activate  # (or .\.venv\Scripts\Activate.ps1 on Windows)
pip install -r requirements.txt
```

### 2. Prepare Data
```bash
python src/dataset/prepare_data.py
```

### 3. Add Credentials
Copy `.env.example` to `.env` and paste your database URIs and passwords.

### 4. Run Everything
```powershell
./run_all.ps1
```

### 5. Generate Publication Charts
```bash
python src/benchmark/generate_report.py
```

---

## Benchmarking Results

### 1. Ingestion Performance
- **Neo4j Aura Free**: ~34,565 nodes/sec | ~1,275 edges/sec
- **CognoDB Bravo Free**: ~36,000 nodes/sec | ~1,100 edges/sec
*(Ingestion was primarily bottlenecked by client-side public internet latency rather than database engine limits).*

### 2. Read Latency (p50)
| Query Type | Neo4j Aura | CognoDB |
|------------|------------|---------|
| 1-Hop | ~65 ms | ~249 ms |
| 2-Hop | ~65 ms | ~249 ms |
| 3-Hop | ~65 ms | ~249 ms |
| Lookup | ~65 ms | ~249 ms |
| Aggregation | ~79 ms | ~296 ms |

### 3. Concurrent Throughput (Queries / Sec)
| Concurrency | Neo4j Aura | CognoDB |
|-------------|------------|---------|
| 1 Thread | 13.5 qps | 3.5 qps |
| 10 Threads | 147.8 qps | 29.7 qps |
| 40 Threads | 567.6 qps | 112.9 qps |

## Final Conclusion
In our reproducible benchmarking suite against the Enron email dataset, **Neo4j Aura** significantly outperformed **CognoDB** on the free tier across all read workloads. Neo4j exhibited nearly 4x faster response times (65ms vs 249ms) for simple and complex traversals, and achieved roughly 5x higher concurrent throughput under load (567 qps vs 112 qps at 40 concurrent clients). While both databases successfully handled the 367k relationship dataset, Neo4j's managed cloud infrastructure demonstrated superior networking and query execution speed for this specific workload.

## 🧠 Analysis & Root-Cause Reasoning

Based on the benchmark results, Neo4j significantly outperformed CognoDB across all tested metrics. Here is the technical breakdown of the root-cause reasoning behind these numbers:

**1. Geographic Network Latency (The Primary Bottleneck)**
The most striking difference is the baseline read latency (Neo4j's ~65ms vs CognoDB's ~249ms). In a cloud benchmarking scenario where the actual database execution time for a 1-hop query on a 300k node graph is usually under 2ms, the remaining time is entirely **public internet latency**. Neo4j Aura dynamically provisions its free-tier clusters in AWS/GCP regions geographically closest to the user (e.g., `ap-south-1` or `eu-central-1`). CognoDB's free tier appears to be statically hosted in a distant region (likely `us-east-1` in Virginia), which adds a flat ~180-200ms of unavoidable fiber-optic latency to every single query round-trip.

**2. Memory Architecture & Page Caching**
The Enron email dataset used for this benchmark is relatively small (~36k nodes, ~183k edges). Neo4j's memory architecture allows it to load the entirety of this dataset directly into its Page Cache. Because Neo4j uses index-free adjacency, hopping from an employee node to their sent emails requires zero index lookups, relying purely on in-memory pointer chasing. This results in the traversal latency (3-hop) being almost identical to a simple lookup.

**3. Protocol Efficiency and Thread Scaling**
Under heavy concurrent load (40 simultaneous clients), Neo4j's throughput scaled massively to 567 queries per second. Neo4j's proprietary binary `Bolt` protocol is highly optimized for pipelining asynchronous requests and connection pooling over TCP. In contrast, if CognoDB relies on a standard HTTP/REST interface or a less mature binary protocol for its Python driver, it suffers from significant overhead during concurrent connection multiplexing, capping out at 112 queries per second.

## ⚠️ Honest Caveats
* **Network Variance:** Since these are managed cloud databases, public internet latency accounts for 5-15ms of every query. I used large batches (`UNWIND`) to minimize network round-trips during ingestion.
* **Cold Starts:** Free tiers often spin down resources. I implemented a strict 20-run warmup phase to ensure we are capturing hot-cache metrics.
