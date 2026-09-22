#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/build_site.py
rsync -rltzn --checksum --delete --itemize-changes --chmod=D755,F644 -e ssh build/ deploy@138.201.189.28:/opt/zrh-ai-econ/site/
rsync -rltz --checksum --delete --chmod=D755,F644 -e ssh build/ deploy@138.201.189.28:/opt/zrh-ai-econ/site/
html=$(curl -fsS --max-time 30 https://zrh-ai-econ.com/)
grep -Fq '<title>Zurich Summer School in AI & Applied Economics</title>' <<<"$html"
if grep -Fq 'Economics Lab' <<<"$html"; then echo 'Unexpected lab content'; exit 1; fi
curl -fsSI --max-time 30 https://zrh-ai-econ.com/slides/00-course-syllabus.pdf >/dev/null
printf '%s\n' 'Course deployment verified.'
