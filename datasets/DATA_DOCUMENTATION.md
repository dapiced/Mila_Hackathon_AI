# Data Generation Documentation — Team 021

## 1. Dataset Overview

| Property | Value |
|---|---|
| Total conversations | 784 |
| High risk (label=1) | 421 (53.7%) |
| Low risk (label=0) | 363 (46.3%) |
| Languages | English: 414 (52.8%), French: 352 (44.9%), Mixed: 18 (2.3%) |
| Turns per conversation | Min: 3, Max: 35, Average: 13.4 |
| Format | CSV, one row per multi-turn conversation |

## 2. Data Sources

| Source | Conversations | Description |
|---|---|---|
| Seed validation set | 94 | Official KHP-annotated conversations provided by organizers |
| Custom training data | 35 | Hand-crafted conversations targeting specific risk signals and DEI scenarios |
| CEDD synthetic data | 600 | Claude-generated conversations covering 4 risk tiers (green/yellow/orange/red) with bilingual coverage |
| Adversarial test cases | 36 | Edge cases designed to test guardrail robustness (sarcasm, code-switching, euphemisms, etc.) |
| Gap-filling data | 19 | Conversations covering 5 missing taxonomy categories + DEI gaps (disabilities, housing instability) |
| expert_training_data.csv | 260 | KHP expert safety testcases (100 scenarios across 12 risk categories) + corner cases (160 edge cases: emoji ambiguity, sarcasm, code-switching, denial) |
| generated_v2.csv | 2,300 | Mistral-generated targeted conversations for model retraining experiments |
| training_final.csv | 890 | Combined clean + generated data used in retraining experiments |
| training_xlmr.csv | 1,044 | All data assembled for model experiments (XLM-R, mDeBERTa, etc.) |
| blue_mission_training.csv | 1,037 | Colleague's comprehensive training dataset (890 existing + 147 new guardrail-targeted conversations) |
| combined_training_v3.csv | 1,131 | Merged Blue Mission + 94 original exclusive conversations |
| Red Mission (Redmission.xlsx) | 461 | Adversarial QA test scenarios across 96 categories for stress-testing the KHP chatbot |

## 3. Generation Strategy

### 3.1 Custom Training Data (35 conversations)
- **Method**: Hand-crafted using Claude as a generation assistant
- **Goal**: Fill gaps in seed data for underrepresented categories and DEI scenarios
- **Categories covered**: Suicide, Self-Harm, Mental Health & Emotions, Isolation, Social Relationships, Home Life & Family, Bullying/Harassment, Identity & Belonging, School & Studies, Romantic/Sexual Relationships, Substance Use, Safety & Abuse, Grief/Loss, Body Image, Testing, Third Party, Hate Speech, Puberty/Life Changes
- **Each category**: minimum 1 low_risk + 1 high_risk conversation
- **Special attention**: subtle risk signals (identity-based isolation, self-worth collapse, functional shutdown, euphemisms)

### 3.2 CEDD Synthetic Data (600 conversations)
- **Method**: Generated using Claude API with structured prompts
- **Original 4-tier labels**: green (safe), yellow (mild concern), orange (moderate/escalation), red (crisis)
- **Mapped to binary**: green/yellow → low_risk (0), orange/red → high_risk (1)
- **Perfectly bilingual**: 300 English + 300 French conversations
- **Edge case categories**: physical_only, sarcasm_distress, adversarial_bypass, identity_distress, neurodivergent_flat, crisis_with_deflection

### 3.3 Adversarial Test Cases (36 conversations)
- **Method**: Hand-designed to stress-test guardrail boundaries
- **Categories include**: false positive physical pain, sarcasm, negation, code-switching, Quebecois slang, gradual drift, hidden intent, manipulation/downplay, somatization, identity conflict, sudden escalation, active bypass, cultural false positives, neurodivergent patterns, emoji-only, rapid recovery manipulation

## 4. DEI (Diversity, Equity, Inclusion) Coverage

### 4.1 Language Diversity
| Language | Count | Percentage |
|---|---|---|
| English | 414 | 52.8% |
| French | 352 | 44.9% |
| Mixed (bilingual) | 18 | 2.3% |

Includes: Quebecois slang, code-switching (FR/EN mix), non-native English patterns, youth texting abbreviations.

### 4.2 Identity & Community Representation
| Community | Included | Examples |
|---|---|---|
| 2SLGBTQ+ youth | Yes | Coming out scenarios, identity exploration, rejection by family/peers, trans experiences |
| First Nations / Indigenous | Yes | Reserve isolation, intergenerational trauma, Two-Spirit identity, cultural disconnection |
| Newcomers / Immigrants | Yes | Cultural adjustment, language barriers, immigration-related family stress |
| Neurodivergent youth | Yes | ADHD, autism spectrum, flat affect patterns, sensory overwhelm |
| Racialized youth | Yes | Racial harassment, cultural false positives, identity conflict |
| Youth in care (foster) | Yes | Multiple placements, attachment issues, abandonment |
| Youth facing housing instability | Yes | LGBTQ+ youth facing homelessness, family in shelter, rent crisis |
| Disabled youth | Yes | Wheelchair user, visual impairment, cerebral palsy, learning disability |

### 4.3 Age Diversity
Conversations represent youth ages approximately 10-25, including:
- Younger children (10-12): school friendship issues, early puberty concerns
- Teens (13-17): identity, relationships, school stress, self-harm, bullying
- Older youth (18-25): university stress, long-distance relationships, independence

## 5. Annotation Policy

### 5.1 Labeling Criteria
- **Label 0 (low_risk)**: No self-harm, suicide intent, abuse, or immediate danger signals. Distress (if present) is mild and stable. User is informational, exploratory, or coping.
- **Label 1 (high_risk)**: Any of the 7 risk signals present: burden language, finality language, escape framing, active self-harm, suicide ideation, immediate safety concern, high misuse signal. Also includes subtle signals: social withdrawal, self-worth collapse, identity-based isolation, functional shutdown.

### 5.2 Key Rule: Topic Does NOT Equal Risk
A conversation about suicide can be low_risk (e.g., informational, about a friend, school project).
A conversation about school stress can be high_risk (e.g., "je ne peux plus continuer", functional shutdown).

### 5.3 Quality Assurance
- All custom conversations reviewed for label consistency
- CEDD data validated against original 4-tier classification system
- Adversarial cases specifically designed to test boundary conditions
- No harmful instructional content included in any conversation
- Near-duplicate check performed across sources

## 6. Risk Signal Taxonomy

The following signals were used to determine high_risk labels:

### Explicit Crisis Signals
1. Burden language: "I'm a burden", "everyone would be better off without me"
2. Finality language: "it will never change", "there's no hope"
3. Escape framing: "I just want it to stop", "I want to disappear"
4. Active self-harm: description of current or recent acts
5. Suicide ideation with intent: plan, method, timeline, means
6. Immediate safety concern: "I don't feel safe", active abuse

### Subtle Risk Signals
7. Complete social withdrawal + functional shutdown
8. Self-worth collapse: "nobody cares", "I don't deserve help"
9. Identity-based isolation: LGBTQ+ rejection, trapped between identities
10. Escalating hopelessness across conversation turns
11. Ambiguous disappearance language: "what if I just disappear"
12. Emotional dependency or relationship fear combined with distress

## 7. Known Limitations and Biases

- **Data leakage**: The seed validation set (94 conversations) was included in training data. Model evaluation metrics on this set are therefore optimistic.
- **Synthetic data bias**: All non-seed conversations were generated by AI (Claude). They may not fully capture the unpredictability and diversity of real youth conversations.
- **Category imbalance**: All 23 taxonomy categories are now covered, though some (e.g., Sexual Health, Personality, Prank/Joke) have fewer than 5 examples.
- **Cultural representation**: While DEI groups are represented, depth of cultural nuance may be limited.
- **French variety**: French conversations are primarily Canadian French; limited representation of other French dialects.
- **Age verification**: Conversations simulate youth speech patterns but ages are not explicitly verified in the data.
- **Final model uses original data only**: The final submitted model still uses only the original 784 training conversations. Additional datasets (expert_training_data.csv, generated_v2.csv, training_final.csv, training_xlmr.csv) were used in retraining experiments that did not improve hidden validation performance and are therefore not reflected in the final mBERT model.
- **Blue Mission retraining unsuccessful**: We tested retraining mBERT with the Blue Mission dataset (1,037 conversations) both alone (F1=0.859) and merged with our original data (F1=0.857). Both scored worse than the original 784-sample model on hidden validation, confirming that the original training data distribution is well-calibrated for the evaluation set.

## 8. File Inventory

| File | Rows | Description |
|---|---|---|
| `seed_validation_set.csv` | 94 | Official evaluation dataset (DO NOT MODIFY) |
| `combined_training.csv` | 784 | Combined dataset used for mBERT fine-tuning |
| `training_data.csv` | 35 | Custom hand-crafted training conversations |
| `cedd_converted.csv` | 600 | CEDD synthetic data converted to hackathon format |
| `adversarial_converted.csv` | 36 | Adversarial edge cases converted to hackathon format |
| `gap_filling_data.csv` | 19 | Gap-filling conversations for missing categories + DEI |
| `sample_training_data.csv` | 5 | Original template (not used in final training) |
| `expert_training_data.csv` | 260 | KHP expert safety testcases + corner cases (used in retraining experiments only) |
| `generated_v2.csv` | 2,300 | Mistral-generated targeted conversations (used in retraining experiments only) |
| `training_final.csv` | 890 | Combined clean + generated data (used in retraining experiments only) |
| `training_xlmr.csv` | 1,044 | All data for model experiments — XLM-R, mDeBERTa, etc. (used in retraining experiments only) |
| `blue_mission_training.csv` | 1,037 | Colleague's comprehensive training dataset (used in retraining experiments only) |
| `combined_training_v3.csv` | 1,131 | Merged Blue Mission + original exclusive (used in retraining experiments only) |
| `combined_training_backup_784.csv` | 784 | Backup of original training data |
| `red_team_v3_results.json` | 461 | Red Mission stress test results against KHP chatbot |
