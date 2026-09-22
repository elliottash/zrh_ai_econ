# Zurich Summer School in AI & Applied Economics

Public course website and student materials for the 2026 summer school at ETH Zurich.

- Website: <https://zrh-ai-econ.com>
- Course chat: <https://summer-chat.zrh-ai-econ.com> (also `/chat` on the course website)
- Lab website: <https://ai-econ-lab.org>, maintained in [elliottash/ai-econ-lab](https://github.com/elliottash/ai-econ-lab)

## Contents

- `index.html` and `assets/` — course homepage, schedule, and styling
- `slides/` — released lecture handouts and syllabus
- `notebooks/` — student notebooks
- `assignments/` — public problem set, dataset, and build script

Private instructor sources remain in the separate teaching repository.

## Build and deploy

Run `python3 scripts/build_site.py` to validate local links and stage the public site in `build/`.
Run `./deploy.sh` to build, dry-run the upload, deploy to
`deploy@138.201.189.28:/opt/zrh-ai-econ/site/`, and check production.
Only the explicit public files are uploaded. No Node.js build is needed.
Nginx routing is recorded in `ops/zrh-ai-econ.nginx.conf`.

The summer-school homepage was restored from commit `1649f8c` on 2026-09-22.
The subsequent uncommitted lab implementation was preserved and moved to its own repository.
Existing `/summer-school/2026/` links redirect to the course homepage, and former
lab routes (`/people/`, `/research/`, `/grants/`, `/kb/`) redirect to `ai-econ-lab.org`.
Existing chat hostnames remain available.
