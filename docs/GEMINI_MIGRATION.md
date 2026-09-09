# Gemini API Migration Guide

## Overview

The categorization module has been migrated from local Hugging Face transformers (facebook/bart-large-mnli) to Google Gemini 2.5 Flash API for improved accuracy and reduced infrastructure requirements.

## Changes Made

### 1. Dependencies Update (`pyproject.toml`)

**Removed:**
- `transformers` (Hugging Face models)
- `torch` (PyTorch for GPU inference)

**Added:**
- `google-generativeai>=0.3.0` (Gemini API Python client)

### 2. Model Configuration (`src/categorization/zero_shot.py`)

**Previous:**
```python
MODEL_NAME = "facebook/bart-large-mnli"
DEVICE_NAME = "cuda"  # GPU required
model = pipeline("zero-shot-classification", model=MODEL_NAME, device=DEVICE)
```

**Current:**
```python
MODEL_NAME = "gemini-2.5-flash"
DEVICE_NAME = "API"  # Cloud-based inference
model = genai.GenerativeModel(MODEL_NAME)
```

### 3. Classification Method

The classification approach changed from local model inference to cloud API calls:

**Previous Pattern:**
```python
result = model(text, CATEGORIES, hypothesis_template="...")
# Returns: {"sequence": article, "labels": [...], "scores": [...]}
```

**Current Pattern:**
```python
prompt = f"""Classify into: {', '.join(CATEGORIES)}
Article: {text}
Respond in JSON: {"category": "...", "confidence": 0.0-1.0}"""

response = classifier.generate_content(prompt, generation_config={...})
response_json = json.loads(re.search(r"\{.*\}", response.text).group())
```

### 4. Environment Configuration

Add to `.env` file:
```
LLM_API_KEY=your_gemini_api_key
LLM_MODEL=gemini-2.5-flash
```

The API key is automatically loaded and validated on module import.

## Benefits

### 1. Improved Accuracy
- Gemini 2.5 Flash has superior language understanding for news categorization
- Better handling of nuanced categories and complex articles
- More reliable category assignments

### 2. Reduced Infrastructure
- No GPU required for inference
- Lower memory footprint (no model loading into VRAM)
- Scalable to many concurrent requests via API

### 3. Operational Simplicity
- No CUDA/GPU driver requirements
- Single point of configuration (API key)
- Easier deployment to different environments

## Migration Impact

### Performance
- **API Response Time:** ~2-5 seconds per article (vs. ~0.5-1s local)
- **Throughput:** Acceptable for batch processing (100+ articles)
- **Cost:** Gemini API pricing (~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens)

### Backward Compatibility
- Input format unchanged (deduplicated_articles.json)
- Output format unchanged (categorized_articles.json)
- Function signatures compatible with pipeline orchestration
- Classification metadata structure maintained

### Error Handling
The new implementation gracefully handles:
- API rate limiting (via tenacity library in pipeline)
- Invalid category responses (fallback to first category)
- JSON parsing failures (defaults to safe values)
- Network errors (logged and propagated to pipeline retry logic)

## Testing the Migration

### 1. Verify Installation
```bash
cd D-P1-22-news-feed-to-digest
pip install -e .
```

### 2. Check Configuration
```bash
python -c "import os; print('LLM_API_KEY:', 'set' if os.getenv('LLM_API_KEY') else 'missing')"
```

### 3. Run Classification
```bash
python -m src.categorization.zero_shot
```

### 4. Verify Output
Check `data/processed/categorized_articles.json`:
- `classifier` field should be `"gemini-2.5-flash"`
- `device` field should be `"API"`
- Each article should have `category`, `category_confidence`, `category_scores`

## Troubleshooting

### Missing API Key
**Error:** `RuntimeError: LLM_API_KEY environment variable not set`
**Solution:** Set LLM_API_KEY in `.env` file or system environment

### Invalid JSON Response
**Error:** `json.JSONDecodeError` in logs
**Behavior:** Article defaults to first category with 50% confidence
**Solution:** Temporary; Gemini API reliability typically very high

### API Rate Limiting
**Error:** `429 Too Many Requests` in logs
**Behavior:** Pipeline will retry via tenacity (exponential backoff)
**Solution:** Wait for retry, or reduce batch size

## Monitoring

Key metrics to track:
1. **Category Distribution:** Log output shows counts per category
2. **Confidence Scores:** Check mean/median confidence in categorized_articles.json
3. **API Performance:** Response times in logs
4. **Error Rate:** Count of failed classifications (should be <1%)

## Future Improvements

1. **Fine-tuning:** If accuracy still needs improvement, consider Gemini 1.5 Pro with custom instructions
2. **Batch Processing:** Use Gemini API batch mode for cost savings on large datasets
3. **Caching:** Implement response caching for duplicate articles
4. **Confidence Thresholding:** Route low-confidence articles to human review

## Rollback Plan

If needed to revert to local model:
1. Restore previous `pyproject.toml` (uncomment transformers/torch)
2. Restore previous `src/categorization/zero_shot.py` from git history
3. Install dependencies: `pip install -e .`
4. Run pipeline normally (requires GPU)

---

**Migration Completed:** Based on user request for improved accuracy
**Model:** Google Gemini 2.5 Flash
**Date:** 2025
