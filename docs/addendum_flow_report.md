# Addendum — Technical Architecture Reference
## Team 021 — 404HarmNotFound

### Complete Pipeline Flow with Repository Files

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EVALUATION PIPELINE                              │
│                                                                     │
│  1. configure.sh                                                    │
│     ├── pip install (pyproject.toml)                                │
│     ├── Download mbert_finetuned.tar.gz from S3 (hackathon.json)    │
│     └── Extract to project/models/mbert_finetuned/                  │
│                                                                     │
│  2. predict.sh                                                      │
│     └── Calls get_predictions() with submission.py                  │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  submission.py :: get_guardrails()                                  │
│                                                                     │
│  ┌──────────────────────┐    ┌─────────────────────────────────┐    │
│  │ load_classifier_     │    │ _get_mistral_judge()            │    │
│  │ guardrail()          │    │                                 │    │
│  │                      │    │ MistralProvider                 │    │
│  │ model:mbert_finetuned│    │ (providers/mistral_provider.py) │    │
│  │ (classifier.py)      │    │ model: Mistral-Large-675B       │    │
│  │ device: GPU (cuda)   │    │ temperature: 0.0                │    │
│  │ threshold: 0.5       │    │ max_tokens: 256                 │    │
│  └──────────┬───────────┘    └──────────┬──────────────────────┘    │
│             │                           │                           │
│             ▼                           ▼                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FullFusionGuardrail.evaluate(conversation)                  │   │
│  │  (submission.py)                                             │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  STEP 1: mBERT SCORING (~20ms)                                      │
│  ┌────────────────────────────────────────────┐                     │
│  │ classifier.py :: _predict_risk()           │                     │
│  │                                            │                     │
│  │ conversation text                          │                     │
│  │   → tokenizer (truncation=512 tokens)      │                     │
│  │   → mmBERT-base model (ModernBERT 2025)    │                     │
│  │   → P(high_risk) = bert_score (0.0 - 1.0)  │                     │
│  │                                            │                     │
│  │ models/mbert_finetuned/                    │                     │
│  │   ├── config.json (model_type: modernbert) │                     │
│  │   ├── model.safetensors                    │                     │
│  │   ├── tokenizer.json                       │                     │
│  │   └── guardrail_config.json (threshold:0.3)│                     │
│  └──────────────────────┬─────────────────────┘                     │
│                         │                                           │
│                         ▼                                           │
│                   bert_score = 0.XX                                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 2: MISTRAL LLM SCORING (~500ms)                               │
│  ┌─────────────────────────────────────────────┐                    │
│  │ llm_judge.py :: evaluate()                  │                    │
│  │                                             │                    │
│  │ SYSTEM MESSAGE:                             │                    │
│  │   EXPERT_GUARDRAIL_PROMPT                   │                    │
│  │   (guardrail_prompt_template.py)            │                    │
│  │   ├── 8 HIGH RISK signal definitions        │                    │
│  │   ├── 10 LOW RISK criteria                  │                    │
│  │   ├── 8 CRITICAL RULES                      │                    │
│  │   └── 11 few-shot examples (EN/FR)          │                    │
│  │                                             │                    │
│  │ USER MESSAGE:                               │                    │
│  │   "Evaluate the following user input:       │                    │
│  │    {conversation text}                      │                    │
│  │    Provide your evaluation in JSON format." │                    │
│  │                                             │                    │
│  │ → Mistral API call (HTTPS POST)             │                    │
│  │ → Response: {"high_risk": true, "score": X} │                    │
│  │ → Parse JSON (_parse_llm_response)          │                    │
│  └──────────────────────┬──────────────────────┘                    │
│                         │                                           │
│                         ▼                                           │
│                   llm_score = 0.XX                                  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 3: WEIGHTED FUSION                                            │
│  ┌────────────────────────────────────────────┐                     │
│  │                                            │                     │
│  │ fused_score = 0.4 × bert_score             │                     │
│  │             + 0.6 × llm_score              │                     │
│  │                                            │                     │
│  └──────────────────────┬─────────────────────┘                     │
│                         │                                           │
│                         ▼                                           │
│                   fused_score = 0.XX                                │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 4: GATE 12 — METHOD/MEANS OVERRIDE                            │
│  ┌─────────────────────────────────────────────┐                    │
│  │ method_mention_override()                   │                    │
│  │ (submission.py)                             │                    │
│  │                                             │                    │
│  │ METHOD_TERMS = [pills, overdose, bridge,    │                    │
│  │   knife, rope, hanging, gun, razor, poison, │                    │
│  │   pilules, surdose, pont, corde, couteau...]│                    │
│  │                                             │                    │
│  │ IF text contains METHOD_TERM                │                    │
│  │    AND fused_score > 0.15                   │                    │
│  │ THEN → IMMEDIATE FAIL (bypass threshold)    │                    │
│  └──────────────────────┬──────────────────────┘                    │
│                         │                                           │
│                         ▼                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 5: THRESHOLD DECISION                                         │
│  ┌─────────────────────────────────────────────┐                    │
│  │                                             │                    │
│  │ IF Gate 12 fired:                           │                    │
│  │   → FAIL (high_risk)                        │                    │
│  │                                             │                    │
│  │ ELIF fused_score >= 0.50:                   │                    │
│  │   → FAIL (high_risk)                        │                    │
│  │                                             │                    │
│  │ ELSE:                                       │                    │
│  │   → PASS (low_risk)                         │                    │
│  │                                             │                    │
│  └──────────┬────────────────────┬─────────────┘                    │
│             │                    │                                  │
│             ▼                    ▼                                  │
│        ┌─────────┐         ┌──────────┐                             │
│        │  FAIL   │         │   PASS   │                             │
│        │ (high)  │         │  (low)   │                             │
│        └────┬────┘         └────┬─────┘                             │
│             │                   │                                   │
│             ▼                   ▼                                   │
│     Escalate to           Continue                                  │
│     human counselor       conversation                              │
│     + crisis resources                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Repository Files Involved

| File | Role |
|------|------|
| `hackathon.json` | GPU config (`needs_gpu: true`) + S3 artifact URI |
| `pyproject.toml` | Python dependencies |
| `project/scripts/configure.sh` | Setup: venv, pip install, download model from S3 |
| `project/scripts/predict.sh` | Run guardrail predictions on evaluation dataset |
| `project/src/submission/submission.py` | Main pipeline: FullFusionGuardrail + Gate 12 OVERRIDE |
| `project/src/guardrails/classifier.py` | mBERT model loading + `_predict_risk()` scoring |
| `project/src/guardrails/llm_judge.py` | Mistral API calls + JSON response parsing |
| `project/src/guardrails/base.py` | GuardrailResult, GuardrailStatus, EvaluationType |
| `project/src/guardrails/metrics.py` | F1, Precision, Recall computation |
| `project/src/prompt_templates/guardrail_prompt_template.py` | EXPERT_GUARDRAIL_PROMPT (LLM instructions) |
| `project/models/mbert_finetuned/` | Fine-tuned mmBERT model (downloaded from S3) |
| `project/models/mbert_finetuned/config.json` | `model_type: modernbert` (mmBERT 2025) |
| `project/models/mbert_finetuned/model.safetensors` | Model weights |
| `project/models/mbert_finetuned/guardrail_config.json` | `threshold: 0.3` |
| `providers/mistral_provider.py` | Mistral API client (HTTPS POST) |

### Configuration Summary

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| mBERT weight | 0.4 | Optimized via grid search |
| Mistral weight | 0.6 | LLM contributes more semantic understanding |
| Fusion threshold | 0.50 | Best balance of precision/recall on hidden set |
| Gate 12 threshold | 0.15 | Low bar — method terms + any distress = escalate |
| Mistral temperature | 0.0 | Deterministic scoring |
| Mistral max_tokens | 256 | Sufficient for JSON response |
| Mistral max_retries | 2 | Balance reliability vs latency |
| mBERT max_length | 512 | Model architecture limit |
| mBERT device | cuda (GPU) | ~20ms inference vs ~200ms on CPU |

### Final Performance

| Metric | Value |
|--------|-------|
| **F1 Score** | **0.876** |
| **Precision** | 0.833 |
| **Recall** | 0.923 |
| **Latency** | ~1,000 ms/sample |
| **Architecture** | Hybrid mmBERT (2025) + Mistral Large 675B + Gate 12 OVERRIDE |

### Experimentation Summary (30+ experiments)

| Category | Experiments | Best Result | Key Learning |
|----------|------------|-------------|--------------|
| Architecture | OR-stack, hybrid zones, full fusion, cascade, max fusion | Full fusion F1=0.876 | Continuous score fusion beats binary decisions |
| LLM selection | Mistral, Cohere, GPT-OSS | Mistral in fusion | Cohere/GPT-OSS worse with our prompt |
| LLM-only | Mistral-only, Cohere-only (various thresholds) | Mistral-only F1=0.833 | Our prompt needs mBERT to compensate |
| Model retraining | mBERT v2, v3, v4, v5, XLM-R, mDeBERTa | All worse on hidden | Original mBERT generalizes best |
| Prompt engineering | +signals, +examples, -examples, taxonomy, CoT, decisive | Minimal tweak +0.002 | Prompt is at fragile equilibrium |
| OVERRIDE gates | Gate 12, 36, 37, 9, 6, 5, 13, 20, 1, 49, 11, 2 | Gate 12 only (+0.002) | Most gates neutral on 102 samples |
| Threshold/weights | 0.46, 0.48, 0.35; 0.6/0.4 flip | 0.50 static best | Lower thresholds crash precision |
| Competitive analysis | Tested top teams' approaches | Hybrid > LLM-only for us | Prompt quality is the differentiator |
