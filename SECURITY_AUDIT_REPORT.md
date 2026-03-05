# Security Audit Report

Root: `/workspace`
Generated: `2026-03-05T05:44:41+00:00`

## Summary

- Directories scanned: 12
- Files scanned: 66
- Python files scanned: 24
- Functions discovered: 195
- Intra-module call relations discovered: 178
- High findings: 1
- Medium findings: 1
- Low findings: 1

## Findings

### SA-001 [HIGH] Unrestricted URL fetching from configuration

Source URLs are accepted from JSON config and fetched without scheme or host allowlisting. If config is attacker-influenced, the crawler can be used for SSRF or internal network probing.

Evidence:
- `parse_source_definitions` accepts any non-empty URL string.
- `UrllibFetcher.fetch_text` performs direct `urlopen` on that URL.
- No `urlparse`-based scheme/host validation is present in the retriever.
Related files:
- `tools/ai_news_crawler/article_retriever.py`
- `tools/ai_news_crawler/sources.json`
Related functions:
- `tools.ai_news_crawler.article_retriever.UrllibFetcher.fetch_text`
- `tools.ai_news_crawler.article_retriever.parse_source_definitions`
Recommended fixes:
- Validate source URLs with `urllib.parse.urlparse` and reject non-`https` schemes.
- Add an allowlist of approved hostnames for production source configs.
- Block loopback/private-network targets by resolving and checking IP ranges.
- Add unit tests covering rejected schemes such as `file://`, `ftp://`, and local IP hosts.

### SA-002 [MEDIUM] Newsletter links are rendered without URL scheme filtering

HTML headline extraction preserves arbitrary anchor URLs, which are later rendered as clickable links in newsletter output. Escaping prevents HTML injection, but it does not block unsafe schemes like `javascript:`.

Evidence:
- `parse_html_headlines` stores `href` values directly as article URLs.
- `render_newsletter_html` emits those URLs into `<a href=...>` links.
- No scheme validation exists before rendering newsletter anchors.
Related files:
- `tools/ai_news_crawler/article_retriever.py`
- `tools/ai_news_crawler/newsletter_summarizer.py`
Related functions:
- `tools.ai_news_crawler.article_retriever.parse_html_headlines`
- `tools.ai_news_crawler.newsletter_summarizer.render_newsletter_html`
Recommended fixes:
- Normalize and validate article URLs before persistence and rendering.
- Allow only `https` and `http` schemes; reject `javascript:`, `data:`, and empty hosts.
- Add tests to ensure malicious schemes are dropped or replaced with safe placeholders.

### SA-003 [LOW] Dependencies are version-pinned but not hash-verified

Setup scripts install dependencies from requirements files without `--require-hashes` or per-package hashes. This leaves room for tampered package artifact retrieval in supply-chain attack scenarios.

Evidence:
- Environment setup scripts run `pip install -r <requirements>`.
- Requirement files pin versions but do not include `--hash` entries.
Related files:
- `tools/ai_news_crawler/requirements.txt`
- `tools/security_audit/requirements.txt`
- `tools/setup_ai_news_env.py`
- `tools/setup_security_audit_env.py`
Related functions:
- `tools.setup_ai_news_env.install_requirements`
- `tools.setup_security_audit_env.install_requirements`
Recommended fixes:
- Generate hashed lock files (e.g., with `pip-compile --generate-hashes`).
- Install with `pip install --require-hashes -r <file>` in setup scripts.
- Enforce dependency integrity checks in CI verification steps.
