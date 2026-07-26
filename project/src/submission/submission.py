"""Canonical participant submission module.

Participants should edit this file and implement get_guardrails().
The shared predict/evaluator runners load this exact path.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

LOGGER = logging.getLogger(__name__)


def _get_mistral_judge():
    """Build Mistral provider for LLM Judge."""
    try:
        from providers.mistral_provider import MistralProvider
    except ImportError:
        LOGGER.warning("MistralProvider import failed")
        return None

    api_key = os.getenv("BUZZ_MISTRAL_LARGE_AUTH_TOKEN")
    if not api_key:
        LOGGER.warning("BUZZ_MISTRAL_LARGE_AUTH_TOKEN not set; skipping Mistral judge")
        return None

    return MistralProvider(
        model="mistralai/Mistral-Large-3-675B-Instruct-2512-NVFP4",
        temperature=0.0,
        max_tokens=256,
        api_key=api_key,
    )


METHOD_TERMS = [
    'pills', 'overdose', 'bridge', 'jump off', 'rope', 'hanging',
    'hang myself', 'knife', 'cut myself', 'razor', 'gun', 'shoot myself',
    'poison', 'bleach', 'sleeping pills', 'bleed out', 'train tracks',
    'pilules', 'surdose', 'pont', 'sauter', 'corde', 'pendaison',
    'couteau', 'me couper', 'rasoir', 'fusil', 'me tirer', 'somniferes',
]


ACTIVE_EMERGENCY = [
    'i already took', 'i already did', 'i already cut',
    'i took all the pills', 'i am bleeding', 'i did it', 'i jumped',
    'i just took', 'it is done', 'i have done it',
    'j ai deja pris', 'j ai deja fait', 'je saigne',
    'j ai pris tous les medicaments', 'c est fait', 'je l ai fait',
]

PRIOR_ATTEMPT = [
    'last time i tried', 'when i attempted', 'my last attempt',
    'i tried before', 'i have tried to kill myself', 'previous attempt',
    'i survived', 'they found me', 'i was in the hospital after',
    'la derniere fois que j ai essaye', 'ma tentative precedente',
    'j ai essaye avant', 'j ai survecu', 'ils m ont trouve',
]

FAREWELL_MARKERS = [
    'i will not be here', 'this is goodbye', 'tell my family',
    'do not worry about me', 'take care of yourself',
    'i have decided', 'i am at peace', 'i will not be bothering',
    'je ne serai plus la', 'c est un adieu', 'dis a ma famille',
    'ne t inquiete pas pour moi', 'j ai decide',
]


def method_mention_override(text: str, base_score: float) -> bool:
    """Gate 12: OVERRIDE if method/means mentioned + any distress signal."""
    text_lower = text.lower()
    has_method = any(term in text_lower for term in METHOD_TERMS)
    return has_method and base_score > 0.15


def active_emergency_override(text: str) -> bool:
    """Gate 36: OVERRIDE if active emergency in progress. No conditions needed."""
    text_lower = text.lower()
    return any(term in text_lower for term in ACTIVE_EMERGENCY)


def prior_attempt_override(text: str) -> bool:
    """Gate 37: OVERRIDE if prior attempt disclosed. No conditions needed."""
    text_lower = text.lower()
    return any(term in text_lower for term in PRIOR_ATTEMPT)


def farewell_override(text: str, base_score: float) -> bool:
    """Gate 9 (adapted): OVERRIDE if farewell language + some distress detected."""
    text_lower = text.lower()
    has_farewell = any(term in text_lower for term in FAREWELL_MARKERS)
    return has_farewell and base_score > 0.15


class FullFusionGuardrail:
    """Weighted score fusion on ALL samples (no auto zones).

    Every sample goes through both mBERT and LLM.
    fused_score = mbert_weight * mbert_score + llm_weight * llm_score
    """

    def __init__(self, llm_judge, bert_guardrail, config, mbert_weight=0.4, llm_weight=0.6, threshold=0.50):
        self.llm_judge = llm_judge
        self.bert_guardrail = bert_guardrail
        self.config = config
        self.mbert_weight = mbert_weight
        self.llm_weight = llm_weight
        self.threshold = threshold

    def evaluate(self, content, context=None, evaluation_type=None):
        from src.guardrails.base import (
            EvaluationType,
            GuardrailResult,
            GuardrailStatus,
        )

        if evaluation_type is None:
            evaluation_type = EvaluationType.USER_INPUT

        start_time = time.time()

        # Run mBERT (fast)
        bert_result = self.bert_guardrail.evaluate(
            content, context=context, evaluation_type=evaluation_type
        )
        bert_score = bert_result.score or 0.0

        # Run LLM on EVERY sample
        try:
            llm_result = self.llm_judge.evaluate(
                content, context=context, evaluation_type=evaluation_type
            )
            llm_score = llm_result.score if llm_result.score is not None else (0.8 if llm_result.is_high_risk else 0.2)
        except Exception as e:
            LOGGER.warning("LLM judge failed, falling back to mBERT only: %s", e)
            latency_ms = (time.time() - start_time) * 1000
            return GuardrailResult(
                status=bert_result.status,
                score=bert_score,
                metadata={"fusion": "mbert_fallback", "error": str(e)},
                latency_ms=latency_ms,
            )

        latency_ms = (time.time() - start_time) * 1000

        # Weighted fusion on ALL samples
        fused_score = self.mbert_weight * bert_score + self.llm_weight * llm_score

        # Gate 12 OVERRIDE: method/means + distress → immediate FAIL
        if method_mention_override(content, fused_score):
            status = GuardrailStatus.FAIL
            reason = f"OVERRIDE_method_means (fused={fused_score:.3f})"
            LOGGER.info(
                "FullFusion | OVERRIDE method_means | bert=%.3f llm=%.3f fused=%.3f latency=%.0fms",
                bert_score, llm_score, fused_score, latency_ms,
            )
        elif fused_score >= self.threshold:
            status = GuardrailStatus.FAIL
            reason = f"fused_high ({bert_score:.3f}*{self.mbert_weight}+{llm_score:.3f}*{self.llm_weight}={fused_score:.3f})"
        else:
            status = GuardrailStatus.PASS
            reason = f"fused_low ({bert_score:.3f}*{self.mbert_weight}+{llm_score:.3f}*{self.llm_weight}={fused_score:.3f})"

        LOGGER.info(
            "FullFusion | status=%s bert=%.3f llm=%.3f fused=%.3f threshold=%.2f latency=%.0fms",
            status.value, bert_score, llm_score, fused_score, self.threshold, latency_ms,
        )

        return GuardrailResult(
            status=status,
            score=fused_score,
            metadata={
                "fusion": reason,
                "bert_score": bert_score,
                "llm_score": llm_score,
                "fused_score": fused_score,
            },
            latency_ms=latency_ms,
        )


def get_guardrails() -> Tuple[Optional[Any], Optional[Any]]:
    """Return (input_guardrail, output_guardrail).

    Full fusion: mBERT + Mistral LLM on every sample.
    """
    LOGGER.info("Loading guardrails from submission module")

    from src.guardrails.base import GuardrailConfig
    from src.guardrails.classifier import load_classifier_guardrail
    from src.guardrails.llm_judge import LLMJudgeGuardrail
    from src.prompt_templates.guardrail_prompt_template import EXPERT_GUARDRAIL_PROMPT
    from src.submission._runtime_config import resolve_device_from_hackathon

    device = resolve_device_from_hackathon(_PROJECT_ROOT)
    bert_guardrail = load_classifier_guardrail(
        model_path=str(_PROJECT_ROOT / "models" / "mbert_finetuned"),
        name="mbert_safety_classifier",
        description="Fine-tuned mBERT classifier for safety detection",
        threshold=0.5,
        device=device,
    )

    judge_llm = _get_mistral_judge()
    if judge_llm is not None:
        llm_judge_guardrail = LLMJudgeGuardrail(
            config=GuardrailConfig(
                name="mistral_llm_judge",
                description="Mistral LLM Judge for mental health crisis detection",
                threshold=0.5,
                max_retries=2,
                timeout_seconds=30,
            ),
            llm_provider=judge_llm,
            user_input_prompt=EXPERT_GUARDRAIL_PROMPT,
        )

        input_guardrail = FullFusionGuardrail(
            llm_judge=llm_judge_guardrail,
            bert_guardrail=bert_guardrail,
            config=GuardrailConfig(
                name="full_fusion_mbert_llm",
                description="Full fusion: mBERT(0.4) + Mistral(0.6) on all samples",
            ),
            mbert_weight=0.4,
            llm_weight=0.6,
            threshold=0.50,
        )
        LOGGER.info("Guardrails loaded | full_fusion [mbert(0.4) + mistral(0.6)]")
    else:
        LOGGER.warning("Mistral judge unavailable; falling back to mBERT only")
        input_guardrail = bert_guardrail

    output_guardrail = None
    return (input_guardrail, output_guardrail)


# Quick local test
if __name__ == "__main__":
    from src.guardrails.base import EvaluationType

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    in_gr, out_gr = get_guardrails()
    if in_gr is None:
        print("No input guardrail configured.")
    else:
        test_cases = [
            ("Low risk EN", "user: Can you share healthy coping strategies for stress?\nassistant: Of course! Here are some strategies..."),
            ("High risk EN", "user: I don't feel safe right now. I want to hurt myself tonight.\nassistant: I'm here to help."),
            ("Low risk FR", "user: salut, je cherche des ressources pour gérer mon stress scolaire\nassistant: Bien sûr, voici quelques options..."),
            ("High risk FR", "user: je suis un fardeau pour tout le monde... je veux juste que ça s'arrête\nassistant: Je t'entends."),
        ]
        for label, prompt in test_cases:
            result = in_gr.evaluate(prompt, evaluation_type=EvaluationType.USER_INPUT)
            print(f"[{label}] Status={result.status.value} | Score={result.score:.3f} | {result.metadata}")
