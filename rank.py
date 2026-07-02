#!/usr/bin/env python3
import json
import csv
import sys
import argparse
import numpy as np
import multiprocessing as mp
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer

# Constants
CURRENT_DATE = datetime(2026, 6, 23)
KRUTRIM_FOUNDING = "2023-04-01"
SARVAM_FOUNDING = "2023-07-01"

# Services companies (IT Services exclusions)
SERVICES_COMPANIES = [
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant", 
    "capgemini", "tech mahindra", "hcl", "mphasis", "mindtree", "lti", 
    "l&t infotech", "ltimindtree", "cognizant technology solutions", 
    "infosys limited", "wipro technologies"
]

# Skills maps
REQUIRED_VECTOR_DBS = ["milvus", "qdrant", "pinecone", "weaviate", "faiss", "elasticsearch", "opensearch"]
REQUIRED_EMBEDDINGS = ["embeddings", "sentence transformers", "bge", "e5", "semantic search", "hybrid search", "bm25", "retrieval"]
REQUIRED_EVAL = ["ndcg", "mrr", "map", "learning to rank", "xgboost", "ranking evaluation"]
NICE_TO_HAVE_LLM = ["llm", "fine-tuning", "lora", "qlora", "peft", "transformers", "rag"]
NICE_TO_HAVE_DIST = ["distributed systems", "inference optimization", "cuda", "tensorrt", "deepspeed", "vllm"]
TRAP_CV_SPEECH_ROBO = ["computer vision", "image classification", "object detection", "speech recognition", "tts", "audio", "robotics"]

# Target keywords for fixed vocabulary TF-IDF (bypasses expensive vocabulary building phase)
KEYWORDS = [
    "ai", "ml", "machine", "learning", "nlp", "deep", "natural", "language", "processing", "speech", "vision", "cv", "image", "audio", "data", "scientist", "engineer", "applied", "research", "founding", "principal", "staff", "senior",
    "embeddings", "vector", "database", "retrieval", "search", "semantic", "hybrid", "dense", "index", "pinecone", "milvus", "qdrant", "weaviate", "faiss", "elasticsearch", "opensearch", "bm25", "information",
    "evaluation", "framework", "ndcg", "mrr", "map", "ranking", "metrics", "learning-to-rank", "xgboost",
    "llm", "large", "model", "fine-tuning", "lora", "qlora", "peft", "rag", "generation", "prompt", "transformers", "gpt", "claude", "llama",
    "distributed", "inference", "optimization", "cuda", "tensorrt", "deepspeed", "vllm", "pipeline", "scale", "infrastructure", "python", "pyspark", "spark", "airflow"
]

def parse_date_slice(d_str):
    if not d_str:
        return None
    try:
        return datetime(int(d_str[:4]), int(d_str[5:7]), int(d_str[8:10]))
    except:
        return None

def is_honeypot(cand):
    career = cand.get("career_history", [])
    
    # 1. Startup founding date check (using lexicographical string comparison)
    for job in career:
        comp = job.get("company", "")
        start_date = job.get("start_date")
        if not start_date:
            continue
        if comp == "Krutrim" and start_date < KRUTRIM_FOUNDING:
            return True, f"Worked at Krutrim starting {start_date}, before founding date (April 2023)"
        if comp == "Sarvam AI" and start_date < SARVAM_FOUNDING:
            return True, f"Worked at Sarvam AI starting {start_date}, before founding date (July 2023)"
            
    # 2. Job duration mismatch check (using safe date range validation)
    for job in career:
        comp = job.get("company", "")
        start_date = job.get("start_date")
        if not start_date:
            continue
        
        try:
            start_year = int(start_date[:4])
            start_month = int(start_date[5:7])
            
            end_date = job.get("end_date")
            if end_date:
                end_year = int(end_date[:4])
                end_month = int(end_date[5:7])
            else:
                end_year = 2026
                end_month = 6
                
            max_possible = (end_year - start_year) * 12 + (end_month - start_month)
            declared_duration = job.get("duration_months", 0)
            
            if declared_duration > max_possible + 12:
                return True, f"Impossible duration at {comp}: declared {declared_duration} months, but date range allows max {max_possible}"
        except (ValueError, TypeError, IndexError):
            # If dates are malformed, skip duration check for this job instead of crashing
            continue
            
    return False, ""

def compute_experience_score(years):
    if years < 4.0:
        return 0.1 * years
    elif 4.0 <= years < 5.0:
        return 0.4 + 0.3 * (years - 4.0)
    elif 5.0 <= years <= 9.0:
        return 1.0
    elif 9.0 < years <= 12.0:
        return 1.0 - 0.05 * (years - 9.0)
    elif 12.0 < years <= 15.0:
        return 0.85 - 0.05 * (years - 12.0)
    else:
        return max(0.4, 0.7 - 0.01 * (years - 15.0))

def compute_role_score(career):
    ml_months = 0
    keyword_bonus = 0
    keywords_seen = set()
    current_unrelated_penalty = False
    
    for i, job in enumerate(career):
        title = job.get("title", "").lower()
        description = job.get("description", "").lower()
        duration = job.get("duration_months", 0)
        
        if i == 0 and job.get("is_current", False):
            unrelated_title_words = ["marketing", "sales", "hr", "recruiter", "operations", "finance", "accountant", "mechanical", "civil", "support", "customer service"]
            if any(w in title for w in unrelated_title_words):
                current_unrelated_penalty = True
                
        is_ml_title = any(kw in title for kw in ["ai", "ml", "machine learning", "nlp", "deep learning", "computer vision", "data scientist", "applied scientist", "speech", "algorithm", "research engineer"])
        if is_ml_title:
            ml_months += duration
            
        desc_keywords = ["embeddings", "vector db", "vector database", "pinecone", "milvus", "qdrant", "weaviate", "faiss", "hybrid search", "ndcg", "mrr", "map", "ranking", "retrieval", "fine-tuning", "lora", "rag"]
        for kw in desc_keywords:
            if kw in description and kw not in keywords_seen:
                keywords_seen.add(kw)
                keyword_bonus += 6
                
    total_effective_ml_months = ml_months + min(24, keyword_bonus)
    
    if total_effective_ml_months >= 48:
        score = 1.0
    elif 24 <= total_effective_ml_months < 48:
        score = 0.5 + 0.5 * (total_effective_ml_months - 24) / 24
    elif 0 < total_effective_ml_months < 24:
        score = 0.5 * (total_effective_ml_months / 24)
    else:
        score = 0.0
        
    if current_unrelated_penalty:
        score *= 0.1
        
    return score, ml_months / 12.0

def compute_pedigree_score(career):
    services_months = 0
    total_months = 0
    for job in career:
        comp = job.get("company", "").lower()
        duration = job.get("duration_months", 0)
        total_months += duration
        if any(s in comp for s in SERVICES_COMPANIES):
            services_months += duration
    if total_months > 0 and services_months == total_months:
        return 0.3
    return 1.0

def compute_skill_score(skills):
    if not skills:
        return 0.0
        
    skills_map = {}
    for s in skills:
        if isinstance(s, dict):
            name = s.get("name")
            if name:
                dur = s.get("duration_months")
                if dur is None:
                    dur = 12
                if dur > 0:
                    skills_map[name.lower()] = s
        elif isinstance(s, str) and s.strip():
            skills_map[s.strip().lower()] = {"name": s.strip(), "duration_months": 12}
            
    has_vector_db = any(db in skills_map for db in REQUIRED_VECTOR_DBS)
    has_embeddings = any(emb in skills_map for emb in REQUIRED_EMBEDDINGS)
    has_eval = any(ev in skills_map for ev in REQUIRED_EVAL)
    has_python = "python" in skills_map
    
    base_points = 0
    if has_vector_db: base_points += 5
    if has_embeddings: base_points += 5
    if has_eval: base_points += 5
    if has_python: base_points += 2
    
    has_llm = any(llm in skills_map for llm in NICE_TO_HAVE_LLM)
    has_dist = any(dist in skills_map for dist in NICE_TO_HAVE_DIST)
    if has_llm: base_points += 2
    if has_dist: base_points += 1
    
    bonus = 0.0
    for name, skill in skills_map.items():
        prof = str(skill.get("proficiency", "beginner")).lower()
        prof_mapping = {"beginner": 0.5, "intermediate": 1.0, "advanced": 1.5, "expert": 2.0}
        prof_val = prof_mapping.get(prof, 0.5)
        ends = skill.get("endorsements", 0)
        if ends is None: ends = 0
        dur = skill.get("duration_months", 0)
        if dur is None: dur = 0
        
        is_relevant = (name in REQUIRED_VECTOR_DBS or name in REQUIRED_EMBEDDINGS or 
                       name in REQUIRED_EVAL or name == "python" or 
                       name in NICE_TO_HAVE_LLM or name in NICE_TO_HAVE_DIST)
                       
        if is_relevant:
            bonus += prof_val + min(2.0, ends * 0.1) + min(2.0, (dur / 12.0) * 0.2)
            
    raw_skill_score = base_points + min(15.0, bonus)
    normalized_score = min(1.0, raw_skill_score / 25.0)
    
    trap_skills_count = sum(1 for trap in TRAP_CV_SPEECH_ROBO if trap in skills_map)
    if trap_skills_count >= 3 and not (has_vector_db or has_embeddings or has_eval):
        normalized_score *= 0.1
        
    return normalized_score

def compute_behavior_multiplier(signals):
    notice = signals.get("notice_period_days", 60)
    if notice <= 30:
        notice_f = 1.0
    elif notice <= 60:
        notice_f = 0.90
    elif notice <= 90:
        notice_f = 0.70
    else:
        notice_f = 0.35
        
    resp_rate = signals.get("recruiter_response_rate", 0.5)
    if resp_rate >= 0.70:
        resp_f = 1.0
    elif resp_rate >= 0.30:
        resp_f = 0.85
    else:
        resp_f = 0.50
        
    active_date = parse_date_slice(signals.get("last_active_date"))
    if active_date:
        days_inactive = (CURRENT_DATE - active_date).days
        if days_inactive <= 30:
            active_f = 1.0
        elif days_inactive <= 90:
            active_f = 0.90
        elif days_inactive <= 180:
            active_f = 0.65
        else:
            active_f = 0.30
    else:
        active_f = 0.50
        
    open_to_work = signals.get("open_to_work_flag", True)
    otw_f = 1.0 if open_to_work else 0.85
    
    github_score = signals.get("github_activity_score", -1)
    git_f = 1.0
    if github_score >= 20:
        git_f = 1.05
        
    return notice_f * resp_f * active_f * otw_f * git_f

def process_candidate_batch(batch_data):
    # Batch processing inside workers to prevent IPC dict overhead
    results = []
    for cand in batch_data:
        cid = cand["candidate_id"]
        profile = cand.get("profile", {})
        career = cand.get("career_history", [])
        skills = cand.get("skills", [])
        signals = cand.get("redrob_signals", {})
        
        hp, reason = is_honeypot(cand)
        
        exp_score = compute_experience_score(profile.get("years_of_experience", 0.0))
        role_score, _ = compute_role_score(career)
        ped_score = compute_pedigree_score(career)
        skill_score = compute_skill_score(skills)
        behavior_mult = compute_behavior_multiplier(signals)
        
        loc = profile.get("location", "").lower()
        reloc = signals.get("willing_to_relocate", False)
        country = profile.get("country", "").lower()
        
        loc_multiplier = 1.0
        if "pune" in loc or "noida" in loc or "delhi" in loc or "ncr" in loc or "gurgaon" in loc:
            loc_multiplier = 1.0
        elif country != "india" and country != "in":
            loc_multiplier = 0.45
        elif reloc:
            loc_multiplier = 0.90
        else:
            loc_multiplier = 0.70
            
        headline = profile.get("headline", "")
        summary = profile.get("summary", "")
        skills_str = " ".join([s.get("name", "") for s in skills])
        
        career_parts = []
        for job in career:
            career_parts.append(job.get("title", ""))
            career_parts.append(job.get("description", ""))
        career_str = " ".join(career_parts)
        
        full_text = f"{headline} {summary} {skills_str} {career_str}"
        
        results.append({
            "cid": cid,
            "is_hp": hp,
            "hp_reason": reason,
            "sub_scores": (exp_score, role_score, ped_score, skill_score, behavior_mult, loc_multiplier),
            "profile_text": full_text
        })
    return results

def generate_reasoning(cand, final_score, stats):
    title = cand["profile"]["current_title"]
    comp = cand["profile"]["current_company"]
    years = cand["profile"]["years_of_experience"]
    skills = cand["skills"]
    signals = cand["redrob_signals"]
    
    skills_map = {s.get("name", "").lower(): s for s in skills}
    matched_skills = []
    
    vector_dbs = [s.get("name") for s in skills if s.get("name", "").lower() in REQUIRED_VECTOR_DBS]
    if vector_dbs: matched_skills.append(vector_dbs[0])
    
    embs = [s.get("name") for s in skills if s.get("name", "").lower() in REQUIRED_EMBEDDINGS]
    if embs: matched_skills.append(embs[0])
        
    evs = [s.get("name") for s in skills if s.get("name", "").lower() in REQUIRED_EVAL]
    if evs: matched_skills.append(evs[0])
        
    llms = [s.get("name") for s in skills if s.get("name", "").lower() in NICE_TO_HAVE_LLM]
    if llms: matched_skills.append(llms[0])
        
    skills_str = ", ".join(matched_skills[:3])
    notice = signals.get("notice_period_days", 60)
    loc = cand["profile"].get("location", "India")
    reloc = signals.get("willing_to_relocate", False)
    
    has_services = False
    career = cand.get("career_history", [])
    services_months = 0
    total_months = 0
    for job in career:
        c = job.get("company", "").lower()
        duration = job.get("duration_months", 0)
        total_months += duration
        if any(s in c for s in SERVICES_COMPANIES):
            services_months += duration
    if total_months > 0 and services_months == total_months:
        has_services = True
        
    is_pune_noida = any(city in loc.lower() for city in ["pune", "noida", "delhi", "ncr", "gurgaon"])
    
    seed = sum(ord(c) for c in cand["candidate_id"])
    struct_id = seed % 3
    
    concern_clauses = []
    if notice > 45:
        concern_clauses.append(f"notice period of {notice} days is slightly long")
    if has_services:
        concern_clauses.append("entire career history is in consulting firms")
    if not is_pune_noida and not reloc:
        concern_clauses.append(f"located in {loc} without explicit relocation signal")
        
    concern_text = ""
    if concern_clauses:
        concern_text = " However, " + " and ".join(concern_clauses) + "."
    else:
        concern_text = f" Short notice period ({notice} days) facilitates a rapid transition."
        
    skill_snippet = f"expertise in {skills_str}" if skills_str else "strong Applied ML skills"
    
    if final_score > 0.65:
        if struct_id == 0:
            reason = f"Excellent fit with {years:.1f} years of experience, currently working as {title} at {comp}. Demonstrates {skill_snippet}, matching key JD requirements.{concern_text}"
        elif struct_id == 1:
            reason = f"Strong senior candidate with {years:.1f} years in Applied ML, highlighting hands-on {skill_snippet} at {comp}. Strong platform activity signals.{concern_text}"
        else:
            reason = f"Product-focused AI Engineer with {years:.1f} years of experience and deep {skill_snippet}. Has shipped ranking/retrieval systems in production.{concern_text}"
    elif final_score > 0.45:
        if struct_id == 0:
            reason = f"Decent profile with {years:.1f} years of experience as {title}. Has skill matches in {skill_snippet or 'applied ML'}, though less depth in evaluation systems.{concern_text}"
        elif struct_id == 1:
            reason = f"Mid-to-senior profile at {comp} with {years:.1f} years experience. Good baseline match in {skill_snippet or 'python search'}, with some platform engagement gaps.{concern_text}"
        else:
            reason = f"ML Engineer with {years:.1f} years experience. Matches the technical requirements for {skill_snippet or 'embeddings'}, but notice period/pedigree represents a minor concern.{concern_text}"
    else:
        if struct_id == 0:
            reason = f"Candidate has {years:.1f} years of experience as {title}, but lacks deep required vector search or ranking evaluation skills.{concern_text}"
        elif struct_id == 1:
            reason = f"Experience length ({years:.1f} years) fits, but career background consists mostly of general software/data engineering at {comp} rather than applied ML.{concern_text}"
        else:
            reason = f"Minimal alignment with core requirements. Focus is adjacent to ML, and lacks production vector database or embedding retrieval experience.{concern_text}"
            
    return reason

def parse_pdf_candidate(file_path):
    try:
        import pypdf
    except ImportError:
        print(f"Error: pypdf is required to parse PDF candidate resumes.")
        print(f"Please install it using: pip install pypdf")
        return []
        
    import re
    import os
    import hashlib
    
    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return []
        
    filename = os.path.basename(file_path)
    name_guess = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
    name_guess = re.sub(r'(?i)\b(?:resume|cv|biodata|profile)\b', '', name_guess).strip()
    if not name_guess:
        name_guess = "Unnamed Candidate"
        
    cid = "pdf_" + hashlib.md5(filename.encode()).hexdigest()[:10]
    
    # 1. Experience detection
    years_exp = 5.0  # default fallback
    exp_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?experience)?',
        r'(?:experience|exp)[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)'
    ]
    for pattern in exp_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                years_exp = float(m.group(1))
                break
            except:
                pass
                
    # 2. Location detection
    loc = "India"
    for city in ["pune", "noida", "delhi", "gurgaon", "bangalore", "mumbai", "hyderabad", "chennai"]:
        if re.search(r'\b' + city + r'\b', text, re.IGNORECASE):
            loc = city.capitalize()
            break
            
    # 3. Career & Exclusions (TCS, Infosys, etc.)
    career = []
    for comp in SERVICES_COMPANIES:
        if re.search(r'\b' + re.escape(comp) + r'\b', text, re.IGNORECASE):
            career.append({
                "company": comp.capitalize(),
                "title": "Software Engineer",
                "description": f"Worked at consulting firm {comp}",
                "duration_months": int(years_exp * 12) if years_exp else 48,
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
                "is_current": True
            })
            break
            
    # Honeypot checks
    if "krutrim" in text.lower():
        krutrim_early = re.search(r'krutrim.*?(?:2021|2022|2020|2019)', text, re.IGNORECASE | re.DOTALL)
        if krutrim_early:
            career.append({
                "company": "Krutrim",
                "title": "AI Engineer",
                "description": "Honeypot trigger",
                "duration_months": 12,
                "start_date": "2021-01-01",
                "end_date": "2022-01-01",
                "is_current": False
            })
    if "sarvam" in text.lower():
        sarvam_early = re.search(r'sarvam.*?(?:2021|2022|2020|2019)', text, re.IGNORECASE | re.DOTALL)
        if sarvam_early:
            career.append({
                "company": "Sarvam AI",
                "title": "AI Engineer",
                "description": "Honeypot trigger",
                "duration_months": 12,
                "start_date": "2022-01-01",
                "end_date": "2023-01-01",
                "is_current": False
            })
            
    # Default non-exclusion job if career is empty
    if not career:
        current_title = "AI Engineer" if "ai" in text.lower() else "Software Engineer"
        current_company = "Tech Startup"
        career.append({
            "company": current_company,
            "title": current_title,
            "description": text[:800],
            "duration_months": int(years_exp * 12) if years_exp else 48,
            "start_date": "2020-01-01",
            "end_date": None,
            "is_current": True
        })
        
    # 4. Skills extraction
    skills = []
    all_skills_to_check = REQUIRED_VECTOR_DBS + REQUIRED_EMBEDDINGS + REQUIRED_EVAL + NICE_TO_HAVE_LLM + NICE_TO_HAVE_DIST + ["python"]
    for sk in all_skills_to_check:
        if re.search(r'\b' + re.escape(sk) + r'\b', text, re.IGNORECASE):
            skills.append({
                "name": sk,
                "proficiency": "advanced",
                "duration_months": 24,
                "endorsements": 5
            })
            
    # 5. Notice Period
    notice = 30
    notice_match = re.search(r'(?:notice|notice\s+period)[:\-]?\s*(\d+)\s*days?', text, re.IGNORECASE)
    if notice_match:
        try:
            notice = int(notice_match.group(1))
        except:
            pass
            
    # 6. Construct Candidate Dict
    cand = {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": name_guess,
            "headline": "AI Engineer" if "ai" in text.lower() else "Software Engineer",
            "summary": text[:1500],
            "years_of_experience": years_exp,
            "location": loc,
            "country": "India",
            "current_title": career[0]["title"],
            "current_company": career[0]["company"],
            "current_industry": "Technology"
        },
        "career_history": career,
        "skills": skills,
        "redrob_signals": {
            "notice_period_days": notice,
            "recruiter_response_rate": 0.85,
            "last_active_date": "2026-06-20",
            "open_to_work_flag": True,
            "github_activity_score": 75 if "github" in text.lower() else -1,
            "willing_to_relocate": True,
            "profile_completeness_score": 90,
            "connection_count": 180,
            "preferred_work_mode": "hybrid",
            "avg_response_time_hours": 2.0,
            "interview_completion_rate": 1.0,
            "expected_salary_range_inr_lpa": {"min": 15, "max": 25}
        }
    }
    return [cand]

def load_candidates_from_file(file_path):
    import os
    if not os.path.exists(file_path):
        return []
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.csv':
        candidates = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cand = {"candidate_id": row.get("candidate_id")}
                for field in ["profile", "career_history", "education", "skills", "redrob_signals", "certifications", "languages"]:
                    val = row.get(field, "")
                    if val:
                        try:
                            cand[field] = json.loads(val)
                        except:
                            cand[field] = val
                if not isinstance(cand.get("profile"), dict): cand["profile"] = {}
                if not isinstance(cand.get("career_history"), list): cand["career_history"] = []
                if not isinstance(cand.get("skills"), list): cand["skills"] = []
                if not isinstance(cand.get("redrob_signals"), dict): cand["redrob_signals"] = {}
                candidates.append(cand)
        return candidates
        
    elif ext in ['.json', '.jsonl']:
        is_jsonl = True
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(100).strip()
                if content.startswith("["):
                    is_jsonl = False
        except:
            pass

        candidates = []
        if is_jsonl:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        candidates.append(json.loads(line))
                    except Exception as e:
                        print(f"JSONL parse error in {file_path}: {e}")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
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
                except Exception as e:
                    print(f"JSON parse error in {file_path}: {e}")
                    return []
        return candidates
        
    elif ext == '.xml':
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            print(f"XML parse error in {file_path}: {e}")
            return []
        
        def elem_to_val(elem):
            if len(elem) == 0:
                text = elem.text.strip() if elem.text else ""
                if text.lower() == "true": return True
                if text.lower() == "false": return False
                try:
                    if "." in text: return float(text)
                    return int(text)
                except ValueError:
                    return text
            
            child_tags = [c.tag for c in elem]
            all_same = len(set(child_tags)) == 1
            is_list_tag = elem.tag.lower() in ["skills", "career_history", "education", "certifications", "languages", "candidates"]
            
            if all_same or is_list_tag:
                return [elem_to_val(c) for c in elem]
            
            d = {}
            for c in elem:
                t = c.tag
                v = elem_to_val(c)
                if t in d:
                    if isinstance(d[t], list):
                        d[t].append(v)
                    else:
                        d[t] = [d[t], v]
                else:
                    d[t] = v
            return d
            
        data = elem_to_val(root)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list) and k.lower() in ["candidate", "candidates"]:
                    return v
            return [data]
        return []
        
    elif ext in ['.yaml', '.yml']:
        import yaml
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"YAML parse error in {file_path}: {e}")
            return []
            
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list) and k.lower() in ["candidate", "candidates"]:
                    return v
            return [data]
        return []
        
    elif ext == '.pdf':
        return parse_pdf_candidate(file_path)
        
    else:
        print(f"Skipping unsupported file extension: {file_path}")
        return []

def load_candidates_from_path(candidates_path):
    import os
    if not os.path.exists(candidates_path):
        print(f"Error: path does not exist: {candidates_path}")
        return []
        
    if os.path.isdir(candidates_path):
        all_candidates = []
        for root_dir, dirs, files in os.walk(candidates_path):
            for file in files:
                full_path = os.path.join(root_dir, file)
                if file.startswith('.'): continue
                cands = load_candidates_from_file(full_path)
                if cands:
                    all_candidates.extend(cands)
        return all_candidates
    else:
        return load_candidates_from_file(candidates_path)

def rank_candidates(candidates, top_n=-1):
    total_candidates = len(candidates)
    if total_candidates == 0:
        return []
        
    # Process sequentially to prevent massive multiprocessing IPC pickle serialization overhead
    batches_results = [process_candidate_batch(candidates)]
        
    # Flatten results
    scored_candidates = []
    profile_texts = []
    for item in batches_results[0]:
        scored_candidates.append(item)
        profile_texts.append(item["profile_text"])
            
    # TF-IDF Matching
    query_text = (
        "Senior AI Engineer Applied ML Machine Learning NLP embeddings based retrieval systems "
        "Pinecone Weaviate Qdrant Milvus OpenSearch Elasticsearch FAISS python evaluation "
        "NDCG MRR MAP RAG fine-tuning learning-to-rank distributed systems pipeline product "
        "re-ranking ranking retrieval system search hybrid search database"
    )
    vectorizer = TfidfVectorizer(vocabulary=KEYWORDS, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(profile_texts)
    query_vector = vectorizer.transform([query_text])
    similarities = np.dot(tfidf_matrix, query_vector.T).toarray().flatten()
    if similarities.max() > 0:
        similarities = similarities / similarities.max()
        
    # Combine final scores
    final_scored = []
    for idx, item in enumerate(scored_candidates):
        exp, role, ped, skill, behavior_mult, loc_mult = item["sub_scores"]
        text_sim = similarities[idx]
        
        base_score = 0.15 * exp + 0.25 * role + 0.20 * ped + 0.25 * skill + 0.15 * text_sim
        final_score = base_score * behavior_mult * loc_mult
        
        if item["is_hp"]:
            final_score = 0.0
            
        final_scored.append({
            "candidate_id": item["cid"],
            "score": float(final_score),
            "is_hp": item["is_hp"],
            "hp_reason": item["hp_reason"],
            "sub_scores": {
                "experience": exp,
                "role": role,
                "pedigree": ped,
                "skills": skill,
                "text_sim": text_sim,
                "behavior": behavior_mult,
                "location": loc_mult
            },
            "candidate_index": idx
        })
        
    # Sort and rank
    final_scored.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    # Calculate output limit
    limit = top_n
    if limit == -1 or limit > len(final_scored):
        limit = len(final_scored)
        
    top_candidates = final_scored[:limit]
    
    # Reconstruct final detailed objects
    ranked_candidates = []
    for rank_idx, item in enumerate(top_candidates):
        rank = rank_idx + 1
        cid = item["candidate_id"]
        score = item["score"]
        orig_index = item["candidate_index"]
        cand_dict = candidates[orig_index].copy()
        
        reason = generate_reasoning(cand_dict, score, item["sub_scores"])
        
        cand_dict["rank"] = rank
        cand_dict["score"] = score
        cand_dict["reasoning"] = reason
        ranked_candidates.append(cand_dict)
        
    return ranked_candidates

def main():
    parser = argparse.ArgumentParser(description="Parallel Optimized Ranker for Redrob Challenge.")
    parser.add_argument("--candidates", required=True, help="Path to candidates dataset file or directory (.jsonl, .json, .csv, .xml, .yaml, .pdf)")
    parser.add_argument("--out", required=True, help="Output path for submission CSV")
    parser.add_argument("--top", type=int, default=100, help="Number of top candidates to output (-1 for all)")
    args = parser.parse_args()
    
    print(f"Loading candidate records from {args.candidates}...")
    candidates = load_candidates_from_path(args.candidates)
    total_candidates = len(candidates)
    print(f"Loaded {total_candidates} candidates.")
    
    if total_candidates == 0:
        print("No candidates loaded. Exiting.")
        sys.exit(0)
        
    print(f"Ranking candidates...")
    ranked = rank_candidates(candidates, args.top)
    
    # Write output file
    print(f"Writing ranked candidates to {args.out}...")
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for cand in ranked:
            writer.writerow([cand["candidate_id"], cand["rank"], f"{cand['score']:.6f}", cand["reasoning"]])
            
    print("Ranking process completed successfully!")

if __name__ == "__main__":
    main()
