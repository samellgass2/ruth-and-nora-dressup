# TOOLS Guide

This repository does not contain a `tool/` directory. The tooling directory present in the project is `tools/`.

The list below audits all current tool entries under `tools/`.

## Top-Level Tools Directory
- `tools/.gitkeep`
- `tools/DESIGN.md`
- `tools/README.md`
- `tools/find_similar_item_names.py`
- `tools/generate_db_column_map.py`
- `tools/setup_ai_news_env.py`
- `tools/setup_security_audit_env.py`

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
- `tools/tests/test_security_audit_directory_mapper.py`
- `tools/tests/test_security_audit_function_call_mapper.py`
- `tools/tests/test_security_audit_report_generator.py`
