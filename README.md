# Zurich Summer School in AI & Applied Economics

Public course website and student-facing materials for the 2026 Zurich Summer
School in AI & Applied Economics.

- Course website: <https://zrh-ai-econ.com>
- Course chat: <https://chat.zrh-ai-econ.com>
- Current syllabus: [Google Doc](https://docs.google.com/document/d/17osu56j6d13mOvw5NK-IEnD2HOxAc5Rw-oLF5scFsA0/edit?tab=t.0)

## Repository layout

- `index.html` and `assets/` contain the static course website.
- `materials/` contains the public syllabus and final lecture PDFs.
- `problem-sets/` contains student-facing assignments as they are released.

Instructor source files, solutions, applications, participant data, and internal
planning documents are intentionally kept outside this public repository.

## Deployment

`./deploy.sh` performs a checksum dry run, syncs the complete public tree to the
shared Hetzner host, and verifies the live homepage and syllabus. Git metadata is
explicitly excluded from the document root.
