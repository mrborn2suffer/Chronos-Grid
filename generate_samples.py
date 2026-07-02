#!/usr/bin/env python3
import os
import json
import csv

def make_dummy_pdf(filename, text):
    content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(text)+150} >>
stream
BT
/F1 12 Tf
50 750 Td
15 TL
"""
    # Write line by line
    for line in text.split('\n'):
        line_escaped = line.replace('(', '\\(').replace(')', '\\)')
        content += f"({line_escaped}) Tj T*\n"
    content += """ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000056 00000 n 
0000000111 00000 n 
0000000244 00000 n 
0000000350 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
440
%%EOF
"""
    with open(filename, "wb") as f:
        f.write(content.encode('latin1'))

def main():
    os.makedirs("sample_imports", exist_ok=True)
    
    # 1. XML
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<candidates>
  <candidate>
    <candidate_id>xml_cand_alex</candidate_id>
    <profile>
      <anonymized_name>Alexander Vance</anonymized_name>
      <headline>Senior Applied ML Engineer</headline>
      <summary>Experienced AI practitioner with deep expertise in vector search systems, embeddings matching, and ranking evaluation.</summary>
      <years_of_experience>7.5</years_of_experience>
      <location>Noida, India</location>
      <country>India</country>
      <current_title>Senior AI Engineer</current_title>
      <current_company>Krutrim (Tech Platform)</current_company>
    </profile>
    <skills>
      <skill>
        <name>Python</name>
        <proficiency>expert</proficiency>
        <duration_months>60</duration_months>
        <endorsements>15</endorsements>
      </skill>
      <skill>
        <name>Qdrant</name>
        <proficiency>advanced</proficiency>
        <duration_months>24</duration_months>
        <endorsements>8</endorsements>
      </skill>
      <skill>
        <name>Embeddings</name>
        <proficiency>expert</proficiency>
        <duration_months>36</duration_months>
        <endorsements>12</endorsements>
      </skill>
      <skill>
        <name>NDCG</name>
        <proficiency>advanced</proficiency>
        <duration_months>18</duration_months>
        <endorsements>6</endorsements>
      </skill>
    </skills>
    <career_history>
      <job>
        <company>Krutrim</company>
        <title>Senior AI Engineer</title>
        <description>Lead development of embedding retrieval layers and vector database infrastructure using Qdrant and Milvus.</description>
        <duration_months>30</duration_months>
        <start_date>2023-10-01</start_date>
        <end_date></end_date>
        <is_current>true</is_current>
      </job>
    </career_history>
    <redrob_signals>
      <notice_period_days>15</notice_period_days>
      <recruiter_response_rate>0.95</recruiter_response_rate>
      <last_active_date>2026-06-22</last_active_date>
      <open_to_work_flag>true</open_to_work_flag>
      <github_activity_score>88</github_activity_score>
      <willing_to_relocate>true</willing_to_relocate>
      <profile_completeness_score>98</profile_completeness_score>
      <connection_count>450</connection_count>
      <preferred_work_mode>hybrid</preferred_work_mode>
      <avg_response_time_hours>0.5</avg_response_time_hours>
      <interview_completion_rate>1.0</interview_completion_rate>
    </redrob_signals>
  </candidate>
</candidates>
"""
    with open("sample_imports/candidate_example.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    # 2. YAML
    yaml_content = """# Candidate yaml format
candidate_id: yaml_cand_sophia
profile:
  anonymized_name: Sophia Sterling
  headline: Foundational ML Researcher
  summary: Applied ML specialist focusing on fine-tuning and retrieval evaluation NDCG. Extensive experience with Pinecone and Sentence-Transformers.
  years_of_experience: 5.5
  location: Pune, India
  country: India
  current_title: AI Engineer
  current_company: Cognitive Labs
skills:
  - name: Python
    proficiency: advanced
    duration_months: 48
    endorsements: 10
  - name: Pinecone
    proficiency: advanced
    duration_months: 24
    endorsements: 7
  - name: NDCG
    proficiency: intermediate
    duration_months: 12
    endorsements: 4
  - name: Fine-tuning
    proficiency: advanced
    duration_months: 24
    endorsements: 9
career_history:
  - company: Cognitive Labs
    title: AI Engineer
    description: Designed hybrid search indexing flow and fine-tuned domain-specific text embeddings.
    duration_months: 24
    start_date: "2024-05-01"
    end_date: null
    is_current: true
redrob_signals:
  notice_period_days: 30
  recruiter_response_rate: 0.90
  last_active_date: "2026-06-21"
  open_to_work_flag: true
  github_activity_score: 76
  willing_to_relocate: true
  profile_completeness_score: 95
  connection_count: 220
  preferred_work_mode: hybrid
  avg_response_time_hours: 1.0
  interview_completion_rate: 1.0
"""
    with open("sample_imports/candidate_example.yaml", "w", encoding="utf-8") as f:
        f.write(yaml_content)

    # 3. JSON
    json_content = [
      {
        "candidate_id": "json_cand_marcus",
        "profile": {
          "anonymized_name": "Marcus Aurelius",
          "headline": "Senior AI Systems Architect",
          "summary": "Building scalable distributed search indexes and pipeline optimization in Python. Expert in Milvus vector store and RAG frameworks.",
          "years_of_experience": 8.0,
          "location": "Noida, India",
          "country": "India",
          "current_title": "AI Architect",
          "current_company": "Apex AI",
          "current_industry": "Technology"
        },
        "skills": [
          {"name": "Python", "proficiency": "expert", "duration_months": 72, "endorsements": 25},
          {"name": "Milvus", "proficiency": "expert", "duration_months": 36, "endorsements": 14},
          {"name": "RAG", "proficiency": "advanced", "duration_months": 24, "endorsements": 10},
          {"name": "Distributed systems", "proficiency": "advanced", "duration_months": 36, "endorsements": 12}
        ],
        "career_history": [
          {
            "company": "Apex AI",
            "title": "AI Architect",
            "description": "Architected real-time RAG search engine servicing millions of queries. Integrated Milvus hybrid search index.",
            "duration_months": 36,
            "start_date": "2023-06-01",
            "end_date": None,
            "is_current": True
          }
        ],
        "redrob_signals": {
          "notice_period_days": 15,
          "recruiter_response_rate": 0.98,
          "last_active_date": "2026-06-23",
          "open_to_work_flag": True,
          "github_activity_score": 92,
          "willing_to_relocate": True,
          "profile_completeness_score": 100,
          "connection_count": 800,
          "preferred_work_mode": "hybrid",
          "avg_response_time_hours": 0.2,
          "interview_completion_rate": 1.0,
          "expected_salary_range_inr_lpa": {"min": 24, "max": 35}
        }
      }
    ]
    with open("sample_imports/candidate_example.json", "w", encoding="utf-8") as f:
        json.dump(json_content, f, indent=2)

    # 4. CSV
    csv_cand = {
      "candidate_id": "csv_cand_elizabeth",
      "profile": json.dumps({
        "anonymized_name": "Elizabeth Swann",
        "headline": "Staff ML Evaluation Engineer",
        "summary": "Dedicated validation engineer specializing in ranking metrics NDCG, MRR, and learning to rank models. Handled search retrieval scoring systems.",
        "years_of_experience": 6.0,
        "location": "Pune, India",
        "country": "India",
        "current_title": "Senior Evaluation Engineer",
        "current_company": "Maritime Tech",
        "current_industry": "E-Commerce"
      }),
      "skills": json.dumps([
        {"name": "Python", "proficiency": "advanced", "duration_months": 48, "endorsements": 12},
        {"name": "NDCG", "proficiency": "expert", "duration_months": 24, "endorsements": 18},
        {"name": "MRR", "proficiency": "expert", "duration_months": 24, "endorsements": 15},
        {"name": "XGBoost", "proficiency": "advanced", "duration_months": 36, "endorsements": 11}
      ]),
      "career_history": json.dumps([
        {
          "company": "Maritime Tech",
          "title": "Senior Evaluation Engineer",
          "description": "Built learning-to-rank evaluation suite for e-commerce search using MAP and NDCG metrics. Tuned XGBoost re-rankers.",
          "duration_months": 28,
          "start_date": "2024-02-01",
          "end_date": None,
          "is_current": True
        }
      ]),
      "redrob_signals": json.dumps({
        "notice_period_days": 30,
        "recruiter_response_rate": 0.88,
        "last_active_date": "2026-06-20",
        "open_to_work_flag": True,
        "github_activity_score": 68,
        "willing_to_relocate": True,
        "profile_completeness_score": 92,
        "connection_count": 310,
        "preferred_work_mode": "hybrid",
        "avg_response_time_hours": 2.5,
        "interview_completion_rate": 0.95,
        "expected_salary_range_inr_lpa": {"min": 18, "max": 24}
      })
    }
    with open("sample_imports/candidate_example.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["candidate_id", "profile", "skills", "career_history", "redrob_signals"])
        writer.writeheader()
        writer.writerow(csv_cand)

    # 5. PDF
    pdf_resume_text = """John Doe
Senior AI Engineer
Location: Pune, India
Experience: 6.5 Years of Experience

Summary:
Proven AI Engineer specializing in embeddings, RAG, and vector search engines. Proficient in Python, Qdrant, Pinecone, and NDCG evaluation frameworks.

Technical Skills:
- Programming: Python, C++
- Vector Databases: Qdrant, Pinecone, Milvus
- Machine Learning: PyTorch, Sentence-Transformers, Fine-tuning, RAG
- Evaluation: NDCG, MRR, Ranking Evaluation

Professional Experience:
Senior ML Engineer - Quantum AI (Jan 2024 to Present)
- Deployed Qdrant hybrid vector search system, boosting query NDCG metric from 0.72 to 0.86.
- Trained sentence-transformers embeddings model on custom corpus.
- Set up automated ranking evaluation pipelines in Python.

Notice Period: 15 Days
Willing to relocate: Yes
"""
    make_dummy_pdf("sample_imports/candidate_example.pdf", pdf_resume_text)
    
    print("Sample import files generated successfully in sample_imports/")

if __name__ == '__main__':
    main()
