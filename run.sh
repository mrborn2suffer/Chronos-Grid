#!/bin/bash
set -e

# Resolve the directory of this script to run reliably from any folder
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if candidates path argument is provided
if [ -z "$1" ]; then
    echo "❌ Error: No candidates dataset path provided."
    echo "Usage: ./run.sh <path_to_candidates_file_or_dir> [output_path]"
    exit 1
fi

CANDIDATES_PATH="$1"
OUT_PATH="${2:-./submission.csv}"

if [ ! -f "$CANDIDATES_PATH" ] && [ ! -d "$CANDIDATES_PATH" ]; then
    echo "❌ Error: Candidates dataset not found at '$CANDIDATES_PATH'."
    echo "Usage: ./run.sh <path_to_candidates_file_or_dir> [output_path]"
    exit 1
fi

echo "=========================================================="
echo "🚀 Redrob Matcher Engine: Running Candidate Ranker"
echo "=========================================================="

# Run the python ranker for the official submission (exactly 100 candidates)
python3 rank.py --candidates "$CANDIDATES_PATH" --out "$OUT_PATH" --top 100

echo ""
echo "=========================================================="
echo "✅ Ranking complete! Official submission saved to: $OUT_PATH"
echo "=========================================================="

# Populate SQLite database for the web dashboard with the ranked candidates
echo "📊 Populating SQLite database with ranked candidates..."
python3 populate_db.py "$CANDIDATES_PATH"
echo "=========================================================="
echo "🖥️ Web dashboard database updated! To launch, run: ./serve.sh"
echo "=========================================================="
