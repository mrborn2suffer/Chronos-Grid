#!/usr/bin/env python3
import json
import csv
import os

def extract():
    csv_path = "dashboard_candidates.csv"
    if not os.path.exists(csv_path):
        csv_path = "submission.csv"
        
    candidates_path = "../[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl"
    output_path = "extracted_details.json"
    
    if not os.path.exists(csv_path):
        print(f"Error: neither dashboard_candidates.csv nor submission.csv found.")
        return
        
    # 1. Read submission.csv to get candidates in ranked order
    ranked_meta = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row:
                continue
            cid, rank, score, reasoning = row
            ranked_meta.append({
                "candidate_id": cid,
                "rank": int(rank),
                "score": float(score),
                "reasoning": reasoning
            })
            
    cids_set = {item["candidate_id"] for item in ranked_meta}
    total_shortlist = len(ranked_meta)
    print(f"Reading {total_shortlist} candidates from {csv_path}...")
    
    # 2. Scan candidates.jsonl for these IDs
    candidates_data = {}
    print(f"Scanning {candidates_path} for profiles...")
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            cid = cand["candidate_id"]
            if cid in cids_set:
                candidates_data[cid] = cand
                if len(candidates_data) == total_shortlist:
                    # Found all, we can stop scanning to save time!
                    break
                
    # 3. Combine meta and full data in ranked order
    combined_data = []
    for meta in ranked_meta:
        cid = meta["candidate_id"]
        if cid in candidates_data:
            full_cand = candidates_data[cid]
            # Merge fields
            full_cand["rank"] = meta["rank"]
            full_cand["score"] = meta["score"]
            full_cand["reasoning"] = meta["reasoning"]
            combined_data.append(full_cand)
            
    # 4. Write to JSON
    print(f"Writing {len(combined_data)} profiles to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2)
        
    print("Extraction completed successfully!")

if __name__ == "__main__":
    extract()
