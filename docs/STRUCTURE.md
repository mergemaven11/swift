# Project structure

```text
.
├── .github/workflows/ci.yml   # test/package/container pipeline
├── Dockerfile                 # non-root runtime image
├── Makefile                   # developer workflow shortcuts
├── main.py                    # source-checkout CLI launcher
├── pyproject.toml             # package metadata + console commands
├── swift_files/
│   ├── app.py                 # Typer command surface
│   ├── config.py              # environment-driven runtime settings
│   ├── ai.py                  # optional OpenAI-compatible artifact explanations
│   ├── editors.py             # safe vim/nvim/nano launcher
│   ├── core.py                # hashing, scans, manifests, duplicates, safe copy
│   ├── csv_ops.py             # CSV inspect/dedupe/sort/validate/summarize
│   ├── docx_ops.py            # DOCX inspect/extract/copy
│   ├── pdf_ops.py             # PDF inspect/extract/copy
│   ├── ui.py                  # Rich + JSON presentation helpers
│   └── *.py                   # compatibility exports for prototype modules
├── tests/                     # unit and CLI policy-gate tests
└── docs/
    ├── PLATFORM_ENGINEERING.md
    ├── SIGNED_RELEASES.md
    └── STRUCTURE.md
```

The main dependency direction is `app -> domain operations -> filesystem`. Presentation code is kept out of the processing modules so the same functions can be reused from automation or future services.
