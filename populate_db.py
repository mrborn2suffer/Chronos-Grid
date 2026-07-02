#!/usr/bin/env python3
import os
import sys
import json
import sqlite3

# Ensure we can import rank.py and serve.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import rank
import serve

def main():
    default_path = "../[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl"
    if not os.path.exists(default_path):
        default_path = "candidates.jsonl"
        
    if not os.path.exists(default_path):
        print(f"Error: candidates file not found at {default_path}")
        sys.exit(1)
        
    print(f"Populating database from {default_path}...")
    serve.init_db()
    
    # Load all candidates
    candidates = rank.load_candidates_from_path(default_path)
    print(f"Loaded {len(candidates)} candidates. Ranking top 500 for dashboard...")
    
    # Rank them
    ranked = rank.rank_candidates(candidates, top_n=500)
    
    # Save to SQLite DB
    serve.save_candidates_to_db(ranked, replace=True)
    print("Database populated successfully with 500 ranked candidates!")

if __name__ == "__main__":
    main()
