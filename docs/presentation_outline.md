# Team 021 — 404HarmNotFound
## Presentation Outline (10 minutes)

---

### Slide 1: Title (30 sec)
**Building Safer AI for Youth Mental Health**
Team 021 — 404HarmNotFound
Mila x Bell x Kids Help Phone AI Safety Hackathon 2026

---

### Slide 2: The Challenge (30 sec)
- KHP Virtual Assistant serves youth in mental health crisis
- Need: Real-time guardrail to detect HIGH RISK conversations
- Bilingual (EN/FR), multi-turn, subtle crisis signals
- Must balance: Recall (don't miss crises) vs Precision (avoid alert fatigue)

---

### Slide 3: Our Architecture — The Hybrid Approach (1 min)
**Diagram:**
```
Conversation → mBERT Classifier (40%) + Mistral LLM (60%)
            → Weighted Fusion → Gate 12 OVERRIDE
            → HIGH RISK → Escalate to Human
            → LOW RISK → Continue
```
- Using a unique innovative hybrid classifier + LLM approach

---

### Slide 4: Why Hybrid Works (1 min)
**Table: What each model catches**

| Signal Type | mBERT | Mistral LLM |
|------------|-------|-------------|
| Explicit crisis keywords | Strong | Strong |
| Subtle/veiled distress | Moderate | Strong |
| Negation patterns | Weak | Strong |
| French crisis language | Strong | Moderate |
| Novel/unseen patterns | Weak | Strong |
| Consistency/Speed | 20ms, deterministic | 500ms, probabilistic |

**The fusion compensates**: mBERT catches what Mistral misses, and vice versa
- mBERT alone: F1=0.818
- Mistral alone: F1=0.833
- **Fusion: F1=0.876** — better than either alone

---

### Slide 5: Competitive Analysis — Our Discovery (1 min)
**Table: Top Teams Pipeline Analysis**

| Rank | Team | F1 | Architecture |
|------|------|-----|-------------|
| 1 | Team 037 | 0.913 | Cohere only, t=0.35 |
| 2 | Team 045 | 0.916 | Mistral only, t=0.46 |
| 3 | Team 064 | 0.882 | Mistral only, t=0.60 |
| **8** | **Us** | **0.876** | **mBERT + Mistral hybrid** |

- We tested LLM-only (Mistral: 0.833, Cohere: 0.806) — **worse for us**
- The difference is **prompt quality**, not architecture
- Our mBERT compensates for prompt weakness = **engineering solution**
- Hybrid is more **robust for deployment** (API fallback, privacy, cost)

---

### Slide 6: Gate 12 — OVERRIDE Safety Net (30 sec)
When text contains method/means terms (pills, knife, bridge, rope...) + any distress signal → **Immediate FAIL**

**Example:**
- Score after fusion: 0.40 (below threshold 0.50 = would PASS)
- But text contains "pills" → **Gate 12 OVERRIDE → FAIL**
- Impact: F1 improved from 0.874 → **0.876**

---

### Slide 7: Data Generation & DEI (1 min)
- **784 bilingual conversations** (52.8% EN, 44.9% FR, 2.3% mixed)
- **DEI coverage**: 2SLGBTQ+, Indigenous, newcomers, neurodivergent, racialized, foster care
- **Key principle**: Topic ≠ Risk (suicide conversation can be LOW risk if academic)
- Tested retraining with expanded datasets (1,037 and 1,131 samples) — original 784 generalized best

---

### Slide 8: Red Team Results — KHP Chatbot Failures (1.5 min)
**1,440 total tests** across 3 test suites

**Red Mission v3 (461 adversarial prompts):**
- 319/411 HIGH cases got **no crisis resources** (77.6% failure rate)
- 0/50 LOW cases incorrectly escalated (0% false alarm)

**Top failure patterns:**
| Pattern | Missed |
|---------|--------|
| Cultural & Linguistic Edge Cases | 12/15 |
| Youth Slang & Emoji | 9/13 |
| Very Young Users (5-12) | 7/7 |
| Negation & Third-Party | 8/9 |

**Key finding**: Chatbot responds empathetically but **systematically fails to provide crisis resources**

---

### Slide 9: 30+ Experiments — What We Learned (1 min)
**Chart: F1 scores across all experiments**

| Experiment | F1 |
|-----------|-----|
| mBERT only | 0.818 |
| Mistral only | 0.833 |
| Cohere only | 0.806 |
| Fusion (baseline) | 0.872 |
| + Prompt tweak | 0.874 |
| + Gate 12 | **0.876** |
| Retrained models | 0.810-0.859 |
| Weight flip | 0.836 |
| Threshold changes | 0.861-0.870 |
| Other gates | 0.865-0.876 (neutral) |

**Key learnings:**
1. Simple > Complex (static weights beat adaptive)
2. Seed validation doesn't predict hidden (data leakage)
3. Retraining always worse on hidden
4. Prompt changes are high-risk (fragile equilibrium)

---

### Slide 10: Future Vision — 53-Gate Architecture (1 min)
**Proposed multi-stage pipeline:**
```
Input → Sanitization → Language Detection → Negation Fix
     → OVERRIDE Gates (5 gates: immediate crisis detection)
     → Lexicon Gates (fast, parallel)
     → ML Models (mBERT + LLM)
     → Ensemble Decision → Output Guardrail
```

**53 specialized detection gates** including:
- Paradoxical Calm (calm after sustained distress)
- Temporal Urgency ("tonight", "right now")
- Social Isolation / Perceived Burdensomeness
- Dark Humor Dismissal ("lol jk" after disclosure)
- Method/Means Detection (implemented as Gate 12)

---

### Slide 11: Impact & Deployment (30 sec)
**Why our solution matters for KHP:**
- **92.3% recall** — catches the vast majority of at-risk youth
- **~1s latency** — real-time deployment ready
- **Bilingual** — EN/FR natively supported
- **Fallback safe** — mBERT works without API (20ms, no internet needed)
- **Privacy** — classifier runs locally, no data leaves the server

---

### Slide 12: Thank You & Q&A
**Team 021 — 404HarmNotFound**
F1 = 0.876 | P = 0.833 | R = 0.923
Hybrid mBERT + Mistral + Gate 12 OVERRIDE

"In youth mental health, missing a crisis is far more dangerous than a false alarm."
