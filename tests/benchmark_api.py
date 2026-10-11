import time
import numpy as np
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def run_benchmark():
    # 1. Get a valid site
    sites = client.get("/api/v1/india/candidate-sites?limit=10").json()
    if not sites:
        print("No India sites available to benchmark.")
        return
        
    site_ids = [s["candidate_site_id"] for s in sites]
    
    print(f"Benchmarking telemetry retrieval for {len(site_ids)} candidate sites...")
    
    latencies = []
    
    for i in range(100):
        site_id = site_ids[i % len(site_ids)]
        start = time.perf_counter()
        res = client.get(f"/api/v1/india/candidate-sites/{site_id}/telemetry?limit=500")
        end = time.perf_counter()
        assert res.status_code == 200
        latencies.append((end - start) * 1000)
        
    p95 = np.percentile(latencies, 95)
    mean_lat = np.mean(latencies)
    
    print("--- Benchmark Results ---")
    print(f"Total Requests: {len(latencies)}")
    print(f"Mean Latency: {mean_lat:.2f} ms")
    print(f"p95 Latency:  {p95:.2f} ms")
    
if __name__ == "__main__":
    run_benchmark()
