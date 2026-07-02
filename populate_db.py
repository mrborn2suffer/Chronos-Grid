#!/usr/bin/env python3
import os
import sys
import sqlite3

# Ensure current dir is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import rank
import serve

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 populate_db.py <path_to_candidates_file_or_dir>")
        sys.exit(1)
        
    candidates_path = sys.argv[1]
    if not os.path.exists(candidates_path):
        print(f"Error: file not found at {candidates_path}")
        sys.exit(1)
        
    print(f"Initializing database...")
    serve.init_db()
    
    # Load all candidates from the given path
    print(f"Loading candidates from: {candidates_path}")
    candidates = rank.load_candidates_from_path(candidates_path)
    print(f"Loaded {len(candidates)} candidates. Evaluating and ranking candidates...")
    
    # Rank all of them dynamically
    ranked = rank.rank_candidates(candidates, top_n=-1)
    
    # Save to SQLite DB
    serve.save_candidates_to_db(ranked, replace=True)
    print(f"Database populated successfully with {len(ranked)} ranked candidates!")

if __name__ == "__main__":
    main()
