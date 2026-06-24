#!/bin/bash
set -e

# Resolve the directory of this script to run reliably from any folder
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🚀 Redrob Matcher Engine: Running Candidate Ranker"
echo "=========================================================="

CANDIDATES_PATH="../[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl"
OUT_PATH="./submission.csv"
VALIDATOR_PATH="../[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py"

# Run the python ranker for the official submission (exactly 100 candidates)
python3 rank.py --candidates "$CANDIDATES_PATH" --out "$OUT_PATH" --top 100

echo ""
echo "=========================================================="
echo "✅ Ranking complete! Official submission saved to: $OUT_PATH"
echo "=========================================================="

# Run format validation check on the official submission
if [ -f "$VALIDATOR_PATH" ]; then
    echo "🔍 Running format validation check..."
    python3 "$VALIDATOR_PATH" "$OUT_PATH"
    echo "=========================================================="
fi

# Run the python ranker for the frontend dashboard (500 candidates for pagination showcase)
echo "📈 Generating 500 ranked candidates for the web dashboard..."
python3 rank.py --candidates "$CANDIDATES_PATH" --out "./dashboard_candidates.csv" --top 500
echo "=========================================================="

# Extract profile details for the frontend
echo "📊 Extracting candidate details for the dashboard..."
python3 extract_profiles.py
echo "=========================================================="
echo "🖥️ Web dashboard data updated! To launch, run: ./serve.sh"
echo "=========================================================="
