# TOOLS Guide

This repository does not contain a `tool/` directory. The tooling directory present in the project is `tools/`.

The list below audits all current tool entries under `tools/`.

## AI Service Implementation Consistency

All AI-related tool behavior in this repository is routed through one shared mock
AI service implementation:

- Shared implementation: `tools/shared/mock_ai_service.py`
- Shared singleton accessor: `get_shared_mock_ai_service()`
- Mock model identifier: `mock-ai-v1` (default)
- External AI network calls: none from tool runtime paths

### AI Tool Usage Matrix
- `tools/ai_news_crawler/newsletter_summarizer.py`
  - Uses `get_shared_mock_ai_service().complete_summary(...)` for all article summary generation.
- `tools/ai_news_crawler/summarize_articles.py`
  - Uses `newsletter_summarizer.render_newsletter_html(...)`, which in turn uses the shared mock AI service.

### Non-AI Tools
The following tool families do not invoke AI services:
- `tools/security_audit/*`
- `tools/find_similar_item_names.py`
- `tools/generate_db_column_map.py`
- setup scripts under `tools/setup_*.py`

### Verification Notes
Consistency can be verified by checking:
- `tools/shared/mock_ai_service.py` for the canonical implementation.
- `tools/ai_news_crawler/newsletter_summarizer.py` for the shared-service import and call path.
- `tools/tests/test_mock_ai_service.py` and
  `tools/tests/test_ai_news_newsletter_summarizer.py` for coverage of the shared service contract.

## Top-Level Tools Directory
- `tools/.gitkeep`
- `tools/DESIGN.md`
- `tools/README.md`
- `tools/find_similar_item_names.py`
- `tools/generate_db_column_map.py`
- `tools/setup_ai_news_env.py`
- `tools/setup_security_audit_env.py`

## Shared Tooling Modules
- `tools/shared/mock_ai_service.py`

## AI News Crawler Tools
- `tools/ai_news_crawler/article_retriever.py`
- `tools/ai_news_crawler/newsletter_summarizer.py`
- `tools/ai_news_crawler/requirements.txt`
- `tools/ai_news_crawler/retrieve_articles.py`
- `tools/ai_news_crawler/sources.json`
- `tools/ai_news_crawler/summarize_articles.py`

## Security Audit Tools
- `tools/security_audit/README.md`
- `tools/security_audit/directory_structure_mapper.py`
- `tools/security_audit/function_call_relationship_mapper.py`
- `tools/security_audit/generate_security_audit_report.py`
- `tools/security_audit/map_directory_structure.py`
- `tools/security_audit/map_function_calls.py`
- `tools/security_audit/requirements.txt`
- `tools/security_audit/security_audit_report_generator.py`

## Sample Data and Config
- `tools/samples/create_item_similarity_sample_db.py`
- `tools/samples/item_similarity_sample.db`
- `tools/samples/item_similarity_sample_config.json`

## Tool Test Suite
- `tools/tests/run_tools_tests.py`
- `tools/tests/test_ai_news_article_retriever.py`
- `tools/tests/test_ai_news_newsletter_summarizer.py`
- `tools/tests/test_db_column_map.py`
- `tools/tests/test_item_name_similarity.py`
- `tools/tests/test_mock_ai_service.py`
- `tools/tests/test_security_audit_directory_mapper.py`
- `tools/tests/test_security_audit_function_call_mapper.py`
- `tools/tests/test_security_audit_report_generator.py`
