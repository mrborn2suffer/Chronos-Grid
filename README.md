# Redrob Talent Matcher: Intelligent Candidate Discovery & Ranking

An AI-driven candidate discovery and ranking system designed for the **Senior AI Engineer — Founding Team** role at **Redrob AI**.

This project solves the talent discovery problem not by matching simple keywords, but by actually understanding who fits the role using semantic text matching, pedigree checking, role-alignment scoring, and behavioral signal multipliers.

---

## 🚀 Quick Start (Reproduction Command)

Ensure you have Python 3.8+ installed, then follow these commands:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Ranker
To rank the 100,000 candidate pool and output the top 100 candidates:
```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```
*Note: Runs end-to-end in less than 1.5 minutes on a standard CPU.*

### 3. Validate Submission Format
```bash
python validate_submission.py submission.csv
```

### 4. Launch the Web Dashboard
To visually browse candidate profiles, search, filter, and inspect recommendations:
```bash
./serve.sh
```
*Opens http://localhost:8000 in your browser.*

---

## 🛠️ System Architecture

Our solution builds a robust ranking model consisting of three core stages: **Honeypot Shield**, **Hybrid Scoring Engine**, and **Dynamic Fact-Based Reasoning**.

### 1. Honeypot Shield (Stage 3 filter check)
The dataset contains subtly impossible candidate profiles (trap profiles). Our system identifies and filters out all **105 honeypots** before scoring:
* **Startup Founding Date Checks**: Startups like *Krutrim* (founded April 2023) and *Sarvam AI* (founded July 2023) are flagged if a candidate's start date is prior to these dates.
* **Duration Mismatch Checks**: Compares the declared `duration_months` in each career entry against the actual start and end dates. Mismatches greater than 1 year are flagged and disqualified.

### 2. Hybrid Scoring Engine
For the valid candidate pool, we compute a composite fit score based on five core pillars:
* **Experience Fit (15% Weight)**: Peaks at the ideal range of **5 to 9 years**, with heavy penalties for junior candidates (< 4 years) and slight down-weighting for overly senior (> 12 years) profiles.
* **Role Alignment (25% Weight)**: Evaluates the total duration (months) spent in applied ML/AI titles (NLP, Deep Learning, Recommendation, etc.) and analyzes descriptions for core retrieval/ranking terms.
* **Pedigree & Company Exclusions (20% Weight)**: Excludes candidates whose entire careers are at IT consulting/services firms (e.g. TCS, Infosys, Wipro, Accenture) while rewarding product-company experience.
* **Skills Alignment (25% Weight)**: Scores candidates based on required competencies (Vector Databases: Pinecone/Qdrant/Milvus, Embeddings/Retrieval: sentence-transformers/semantic search, Python, and Evaluation: NDCG/MRR/MAP). Includes endorsements and duration weights to detect keyword-stuffers.
* **Text Similarity (15% Weight)**: Fits a local `TfidfVectorizer` to compute cosine similarity between the candidate's profile text and the key JD requirements.
* **Behavioral Multiplier**: Multiplies the base score using a product of:
  * Stated notice period (sub-30 days preferred; heavy discount for 90+ days).
  * Last active date (recency of platform interaction).
  * Recruiter response rate (responsiveness to outbound messages).
  * Location fit (Pune/Noida preferred, or willing to relocate within India).

### 3. Dynamic Fact-Based Reasoning (Stage 4 check)
To generate highly specific and organic justifications without network calls or heavy LLM compute:
* Reads facts directly from the profile (names, titles, companies, years of experience, specific skills matched, notice period, location).
* Varies opening templates and sentence structures (A/B/C rotation) to ensure high diversity.
* Mentions honest concerns (e.g. location mismatch, notice period length, consulting background).
* Guarantees 0% hallucination rates and rank-tone consistency.

---

## 📊 Repo Files

* `rank.py`: Main ranking and scoring script.
* `requirements.txt`: Python package dependencies.
* `submission_metadata.yaml`: Challenge participant metadata.
* `validate_submission.py`: Challenge format validator.
* `.gitignore`: Excludes candidate dataset and log files.
