#!/bin/bash
# Pebbles News Crawler — run crawler, commit, deploy
set -e

PROJECT_DIR="/Users/kongmini/workspace/git/pebbles"
LOG_FILE="$PROJECT_DIR/crawler.log"
PYTHON="/usr/bin/python3"
export PATH="/Users/kongmini/.local/bin:/opt/homebrew/opt/node@24/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$PROJECT_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') — Crawler started" >> "$LOG_FILE"

# Run crawler
$PYTHON crawler.py >> "$LOG_FILE" 2>&1

# Git commit & push if data changed
if ! git diff --quiet public/data/news.json 2>/dev/null; then
    git add public/data/
    git commit -m "data: update news $(date '+%Y-%m-%d %H:%M')" >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S') — Git pushed" >> "$LOG_FILE"
fi

# Deploy to Vercel
npx vercel --prod --yes >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') — Deploy complete" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
