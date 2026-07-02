#!/usr/bin/env python3
import http.server
import json
import urllib.parse
import os
import sys
import sqlite3

# Ensure current dir is in python path to import rank.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    import rank
except ImportError:
    # Fallback simulation module if rank layout isn't present
    class MockRank:
        def load_candidates_from_path(self, path): return []
        def rank_candidates(self, arr, top_n=-1): return arr
    rank = MockRank()

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
        
    services = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini", "hcl"]
    data_to_insert = []
    
    for cand in candidates:
        cid = cand.get("candidate_id")
        if not cid:
            continue
        
        profile = cand.get("profile", {})
        signals = cand.get("redrob_signals", {})
        career = cand.get("career_history", [])
        
        total_months = 0
        services_months = 0
        for job in career:
            comp = job.get("company", "").lower()
            duration = job.get("duration_months", 0)
            total_months += duration
            if any(s in comp for s in services):
                services_months += duration
        is_product = 1 if (total_months > 0 and services_months < total_months) else 0
        
        data_to_insert.append((
            cid, cand.get("rank"), cand.get("score"), cand.get("reasoning"),
            profile.get("anonymized_name"), profile.get("headline"), profile.get("summary"),
            profile.get("years_of_experience", 0.0), profile.get("location"), profile.get("country"),
            profile.get("current_title"), profile.get("current_company"), profile.get("current_industry"),
            signals.get("notice_period_days", 30), is_product,
            json.dumps(cand.get("skills", [])), json.dumps(career),
            json.dumps(cand.get("education", [])), json.dumps(signals)
        ))
        
    cursor.executemany("""
        INSERT OR REPLACE INTO candidates (
            candidate_id, rank, score, reasoning, anonymized_name, headline, summary,
            years_of_experience, location, country, current_title, current_company, current_industry,
            notice_period_days, is_product_co, skills_json, career_history_json, education_json, redrob_signals_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    
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
        candidates.append({
            "candidate_id": r["candidate_id"], "rank": r["rank"], "score": r["score"], "reasoning": r["reasoning"],
            "profile": {
                "anonymized_name": r["anonymized_name"], "headline": r["headline"], "summary": r["summary"],
                "years_of_experience": r["years_of_experience"], "location": r["location"], "country": r["country"],
                "current_title": r["current_title"], "current_company": r["current_company"], "current_industry": r["current_industry"]
            },
            "skills": json.loads(r["skills_json"]), "career_history": json.loads(r["career_history_json"]),
            "education": json.loads(r["education_json"]), "redrob_signals": json.loads(r["redrob_signals_json"])
        })
    conn.close()
    return candidates

def query_candidates(page=1, limit=20, search_query="", active_filter="all", min_score=0):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
        where_clauses.append("(LOWER(location) LIKE '%pune%' OR LOWER(location) LIKE '%noida%' OR LOWER(location) LIKE '%delhi%')")
        
    if min_score > 0:
        where_clauses.append("score * 100 >= ?")
        params.append(min_score)
        
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    cursor.execute(f"SELECT COUNT(*) FROM candidates {where_sql}", params)
    total_count = cursor.fetchone()[0]
    
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
        candidates.append({
            "candidate_id": r["candidate_id"], "rank": r["rank"], "score": r["score"], "reasoning": r["reasoning"],
            "profile": {
                "anonymized_name": r["anonymized_name"], "headline": r["headline"], "summary": r["summary"],
                "years_of_experience": r["years_of_experience"], "location": r["location"], "country": r["country"],
                "current_title": r["current_title"], "current_company": r["current_company"], "current_industry": r["current_industry"]
            },
            "skills": json.loads(r["skills_json"]), "career_history": json.loads(r["career_history_json"]),
            "education": json.loads(r["education_json"]), "redrob_signals": json.loads(r["redrob_signals_json"])
        })
    conn.close()
    
    total_pages = 1 if limit == -1 else max(1, (total_count + limit - 1) // limit)
    return {
        "candidates": candidates, "total_count": total_count, "total_pages": total_pages,
        "page": page if limit != -1 else 1, "limit": limit if limit != -1 else total_count
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
        try: page = int(params.get('page', [1])[0])
        except ValueError: page = 1
        try: limit = int(params.get('limit', [20])[0])
        except ValueError: limit = 20
        
        search_query = params.get('search', [''])[0]
        active_filter = params.get('filter', ['all'])[0]
        try: min_score = float(params.get('min_score', [0])[0])
        except ValueError: min_score = 0.0
            
        try:
            result = query_candidates(page=page, limit=limit, search_query=search_query, active_filter=active_filter, min_score=min_score)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
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
        
        # If it is a standard JSON file, convert it to JSONL under the hood
        ext = os.path.splitext(filename.lower())[1]
        if ext == '.json':
            try:
                content_str = body_bytes.decode('utf-8')
                data = json.loads(content_str)
                candidates = []
                if isinstance(data, list):
                    candidates = data
                elif isinstance(data, dict):
                    found = False
                    for k, v in data.items():
                        if isinstance(v, list) and k.lower() in ["candidate", "candidates"]:
                            candidates = v
                            found = True
                            break
                    if not found:
                        candidates = [data]
                
                # Convert to JSONL string
                jsonl_lines = []
                for cand in candidates:
                    jsonl_lines.append(json.dumps(cand))
                jsonl_str = "\n".join(jsonl_lines) + "\n"
                body_bytes = jsonl_str.encode('utf-8')
                filename = filename + "l" # Convert .json to .jsonl
            except Exception as e:
                print(f"Failed to convert standard JSON to JSONL: {e}")
                
        os.makedirs("tmp_imports", exist_ok=True)
        temp_file_path = os.path.join("tmp_imports", filename)
        
        try:
            with open(temp_file_path, "wb") as f:
                f.write(body_bytes)
                
            imported_cands = rank.load_candidates_from_path(temp_file_path)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
            # Normalize candidate ID and map flat structures to nested blocks to guarantee safe evaluation
            import time
            valid_cands = []
            for idx, cand in enumerate(imported_cands or []):
                if not isinstance(cand, dict):
                    continue
                
                # Check for alternative ID keys
                cid = None
                for id_key in ["candidate_id", "id", "cid", "candidateId", "Candidate ID"]:
                    if id_key in cand and cand[id_key] is not None:
                        cid = str(cand[id_key]).strip()
                        break
                if not cid:
                    cid = f"cand_{idx}_{int(time.time())}"
                cand["candidate_id"] = cid
                
                # Normalize profile sub-block (handle both flat and nested schemas)
                if "profile" not in cand or not isinstance(cand["profile"], dict):
                    cand["profile"] = {}
                
                profile_fields = [
                    "anonymized_name", "headline", "summary", "years_of_experience", 
                    "location", "country", "current_title", "current_company", 
                    "current_industry", "current_company_size"
                ]
                for fld in profile_fields:
                    if fld in cand and cand[fld] is not None:
                        if fld not in cand["profile"]:
                            cand["profile"][fld] = cand[fld]
                
                # Normalize redrob_signals sub-block
                if "redrob_signals" not in cand or not isinstance(cand["redrob_signals"], dict):
                    cand["redrob_signals"] = {}
                
                signal_fields = ["notice_period_days", "open_to_work_flag", "platform_activity_score"]
                for fld in signal_fields:
                    if fld in cand and cand[fld] is not None:
                        if fld not in cand["redrob_signals"]:
                            cand["redrob_signals"][fld] = cand[fld]
                
                # Normalize skills (handle both string list and list types)
                if "skills" in cand:
                    if isinstance(cand["skills"], str):
                        cand["skills"] = [s.strip() for s in cand["skills"].split(",") if s.strip()]
                    elif not isinstance(cand["skills"], list):
                        cand["skills"] = []
                else:
                    cand["skills"] = []
                
                # Ensure career_history and education list exist
                if "career_history" not in cand or not isinstance(cand["career_history"], list):
                    cand["career_history"] = []
                if "education" not in cand or not isinstance(cand["education"], list):
                    cand["education"] = []
                    
                valid_cands.append(cand)
            imported_cands = valid_cands
            
            if not imported_cands:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Failed to parse template schema file rows."}).encode('utf-8'))
                return
                
            existing_cands = [] if replace_mode else load_all_candidates_from_db()
            seen_ids = set()
            merged_cands = []
            
            for cand in imported_cands + existing_cands:
                cid = cand.get("candidate_id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    cand.pop("score", None)
                    cand.pop("rank", None)
                    cand.pop("reasoning", None)
                    merged_cands.append(cand)
                    
            ranked_cands = rank.rank_candidates(merged_cands, top_n=-1)
            save_candidates_to_db(ranked_cands, replace=True)
            
            result = query_candidates(page=1, limit=20)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def handle_api_reset(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidates")
            conn.commit()
            conn.close()
            
            result = query_candidates(page=1, limit=20)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

def run_server():
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM candidates")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error clearing database on startup: {e}")
    print(f"🚀 Application Engine live on http://localhost:{PORT}")
    http.server.HTTPServer(('', PORT), CustomHTTPRequestHandler).serve_forever()

if __name__ == '__main__':
    run_server()