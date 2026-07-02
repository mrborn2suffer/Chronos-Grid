#!/usr/bin/env python3
import http.server
import json
import urllib.parse
import os
import sys
import sqlite3

# Ensure current dir is in python path to import rank.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import rank

PORT = 8000
DB_PATH = "candidates.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            rank INTEGER,
            score REAL,
            reasoning TEXT,
            anonymized_name TEXT,
            headline TEXT,
            summary TEXT,
            years_of_experience REAL,
            location TEXT,
            country TEXT,
            current_title TEXT,
            current_company TEXT,
            current_industry TEXT,
            notice_period_days INTEGER,
            is_product_co INTEGER,
            skills_json TEXT,
            career_history_json TEXT,
            education_json TEXT,
            redrob_signals_json TEXT
        )
    """)
    # Create indexes for fast filtering and sorting
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_exp ON candidates(years_of_experience)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_notice ON candidates(notice_period_days)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_is_product ON candidates(is_product_co)")
    conn.commit()
    conn.close()

def save_candidates_to_db(candidates, replace=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if replace:
        cursor.execute("DELETE FROM candidates")
        
    for cand in candidates:
        cid = cand.get("candidate_id")
        if not cid:
            continue
        
        profile = cand.get("profile", {})
        signals = cand.get("redrob_signals", {})
        career = cand.get("career_history", [])
        
        # Calculate is_product_co
        services = [
            "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant", 
            "capgemini", "tech mahindra", "hcl", "mphasis", "mindtree", "lti", 
            "l&t infotech", "ltimindtree", "cognizant technology solutions", 
            "infosys limited", "wipro technologies"
        ]
        total_months = 0
        services_months = 0
        for job in career:
            comp = job.get("company", "").lower()
            duration = job.get("duration_months", 0)
            total_months += duration
            if any(s in comp for s in services):
                services_months += duration
        is_product = 1 if (total_months > 0 and services_months < total_months) else 0
        
        cursor.execute("""
            INSERT OR REPLACE INTO candidates (
                candidate_id, rank, score, reasoning, anonymized_name, headline, summary,
                years_of_experience, location, country, current_title, current_company, current_industry,
                notice_period_days, is_product_co, skills_json, career_history_json, education_json, redrob_signals_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid,
            cand.get("rank"),
            cand.get("score"),
            cand.get("reasoning"),
            profile.get("anonymized_name"),
            profile.get("headline"),
            profile.get("summary"),
            profile.get("years_of_experience", 0.0),
            profile.get("location"),
            profile.get("country"),
            profile.get("current_title"),
            profile.get("current_company"),
            profile.get("current_industry"),
            signals.get("notice_period_days", 30),
            is_product,
            json.dumps(cand.get("skills", [])),
            json.dumps(career),
            json.dumps(cand.get("education", [])),
            json.dumps(signals)
        ))
        
    conn.commit()
    conn.close()

def load_all_candidates_from_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates")
    rows = cursor.fetchall()
    
    candidates = []
    for r in rows:
        cand = {
            "candidate_id": r["candidate_id"],
            "rank": r["rank"],
            "score": r["score"],
            "reasoning": r["reasoning"],
            "profile": {
                "anonymized_name": r["anonymized_name"],
                "headline": r["headline"],
                "summary": r["summary"],
                "years_of_experience": r["years_of_experience"],
                "location": r["location"],
                "country": r["country"],
                "current_title": r["current_title"],
                "current_company": r["current_company"],
                "current_industry": r["current_industry"]
            },
            "skills": json.loads(r["skills_json"]),
            "career_history": json.loads(r["career_history_json"]),
            "education": json.loads(r["education_json"]),
            "redrob_signals": json.loads(r["redrob_signals_json"])
        }
        candidates.append(cand)
        
    conn.close()
    return candidates

def query_candidates(page=1, limit=20, search_query="", active_filter="all", min_score=0):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Construct WHERE clause
    where_clauses = []
    params = []
    
    if search_query:
        query_pattern = f"%{search_query.lower()}%"
        where_clauses.append("(LOWER(anonymized_name) LIKE ? OR LOWER(headline) LIKE ? OR LOWER(current_title) LIKE ? OR LOWER(skills_json) LIKE ?)")
        params.extend([query_pattern, query_pattern, query_pattern, query_pattern])
        
    if active_filter == "exp":
        where_clauses.append("years_of_experience >= 5.0 AND years_of_experience <= 9.0")
    elif active_filter == "product":
        where_clauses.append("is_product_co = 1")
    elif active_filter == "notice":
        where_clauses.append("notice_period_days <= 30")
    elif active_filter == "local":
        where_clauses.append("(LOWER(location) LIKE '%pune%' OR LOWER(location) LIKE '%noida%' OR LOWER(location) LIKE '%delhi%' OR LOWER(location) LIKE '%ncr%' OR LOWER(location) LIKE '%gurgaon%')")
        
    if min_score > 0:
        where_clauses.append("score * 100 >= ?")
        params.append(min_score)
        
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
    # Count total matching rows
    count_sql = f"SELECT COUNT(*) FROM candidates {where_sql}"
    cursor.execute(count_sql, params)
    total_count = cursor.fetchone()[0]
    
    # Query slice sorted by rank
    if limit == -1:
        select_sql = f"SELECT * FROM candidates {where_sql} ORDER BY rank ASC"
        query_params = params
    else:
        offset = (page - 1) * limit
        select_sql = f"SELECT * FROM candidates {where_sql} ORDER BY rank ASC LIMIT ? OFFSET ?"
        query_params = params + [limit, offset]
        
    cursor.execute(select_sql, query_params)
    rows = cursor.fetchall()
    
    candidates = []
    for r in rows:
        cand = {
            "candidate_id": r["candidate_id"],
            "rank": r["rank"],
            "score": r["score"],
            "reasoning": r["reasoning"],
            "profile": {
                "anonymized_name": r["anonymized_name"],
                "headline": r["headline"],
                "summary": r["summary"],
                "years_of_experience": r["years_of_experience"],
                "location": r["location"],
                "country": r["country"],
                "current_title": r["current_title"],
                "current_company": r["current_company"],
                "current_industry": r["current_industry"]
            },
            "skills": json.loads(r["skills_json"]),
            "career_history": json.loads(r["career_history_json"]),
            "education": json.loads(r["education_json"]),
            "redrob_signals": json.loads(r["redrob_signals_json"])
        }
        candidates.append(cand)
        
    conn.close()
    
    if limit == -1:
        total_pages = 1
        page_val = 1
        limit_val = total_count
    else:
        total_pages = (total_count + limit - 1) // limit
        if total_pages == 0:
            total_pages = 1
        page_val = page
        limit_val = limit
        
    return {
        "candidates": candidates,
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page_val,
        "limit": limit_val
    }

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/api/candidates':
            self.handle_api_candidates(parsed_url)
        else:
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/api/import':
            self.handle_api_import(parsed_url)
        elif parsed_url.path == '/api/reset':
            self.handle_api_reset()
        else:
            self.send_error(404, "Endpoint not found")
            
    def handle_api_candidates(self, parsed_url):
        params = urllib.parse.parse_qs(parsed_url.query)
        try:
            page = int(params.get('page', [1])[0])
        except ValueError:
            page = 1
            
        try:
            limit = int(params.get('limit', [20])[0])
        except ValueError:
            limit = 20
            
        search_query = params.get('search', [''])[0]
        active_filter = params.get('filter', ['all'])[0]
        
        try:
            min_score = float(params.get('min_score', [0])[0])
        except ValueError:
            min_score = 0.0
            
        try:
            result = query_candidates(
                page=page,
                limit=limit,
                search_query=search_query,
                active_filter=active_filter,
                min_score=min_score
            )
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def handle_api_import(self, parsed_url):
        params = urllib.parse.parse_qs(parsed_url.query)
        filename = params.get('filename', ['imported_file'])[0]
        replace_mode = params.get('replace', ['false'])[0].lower() == 'true'
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_error(400, "Empty payload")
            return
            
        body_bytes = self.rfile.read(content_length)
        os.makedirs("tmp_imports", exist_ok=True)
        temp_file_path = os.path.join("tmp_imports", filename)
        
        try:
            with open(temp_file_path, "wb") as f:
                f.write(body_bytes)
                
            imported_cands = rank.load_candidates_from_path(temp_file_path)
            
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
            if not imported_cands:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Failed to parse candidates. Check file format (JSON, CSV, XML, YAML, or PDF)."}).encode('utf-8'))
                return
                
            existing_cands = []
            if not replace_mode:
                existing_cands = load_all_candidates_from_db()
                        
            seen_ids = set()
            merged_cands = []
            
            for cand in imported_cands:
                cid = cand.get("candidate_id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    cand.pop("score", None)
                    cand.pop("rank", None)
                    cand.pop("reasoning", None)
                    merged_cands.append(cand)
                    
            for cand in existing_cands:
                cid = cand.get("candidate_id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    cand.pop("score", None)
                    cand.pop("rank", None)
                    cand.pop("reasoning", None)
                    merged_cands.append(cand)
                    
            print(f"Ranking {len(merged_cands)} candidates ({len(imported_cands)} imported, {len(existing_cands)} existing)...")
            ranked_cands = rank.rank_candidates(merged_cands, top_n=-1)
            
            # Save to SQLite DB
            save_candidates_to_db(ranked_cands, replace=True)
            
            # Respond with page 1 of results
            result = query_candidates(page=1, limit=20)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def handle_api_reset(self):
        try:
            print("Clearing candidate database...")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidates")
            conn.commit()
            conn.close()
            
            # Respond with page 1 of results (which will now be empty)
            result = query_candidates(page=1, limit=20)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

def run_server():
    init_db()
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, CustomHTTPRequestHandler)
    print(f"==========================================================")
    print(f"🚀 Custom Redrob SQLite-backed Server running at: http://localhost:{PORT}")
    print(f"Supports GET /api/candidates, POST /api/import, and POST /api/reset")
    print(f"==========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)

if __name__ == '__main__':
    run_server()
