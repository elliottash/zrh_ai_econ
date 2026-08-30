#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target="deploy@138.201.189.28:/opt/zrh-ai-econ/site/"
rsync_args=(
  -rltz
  --checksum
  --delete
  --delete-excluded
  --exclude=.git/
  --itemize-changes
  --chmod=D755,F644
  -e ssh
)

echo "Dry-running deployment"
rsync "${rsync_args[@]}" --dry-run "$repo_dir/" "$target"

echo "Deploying course website"
rsync "${rsync_args[@]}" "$repo_dir/" "$target"

echo "Verifying live website"
html=$(curl --fail --silent --show-error --max-time 30 https://zrh-ai-econ.com/)
grep -Fq '<title>Zurich Summer School in AI & Applied Economics</title>' <<<"$html"
curl --fail --silent --show-error --head --max-time 30 \
  https://zrh-ai-econ.com/slides/00-course-syllabus.pdf >/dev/null
echo "Deployment verified"
