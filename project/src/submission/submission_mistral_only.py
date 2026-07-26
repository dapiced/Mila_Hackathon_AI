"""Submission: Mistral LLM-only with threshold 0.35 (like team_037 #1).

No mBERT classifier — pure LLM judge with OVERRIDE gates.
To activate: copy this file over submission.py
"""

from __future__ import annotations

import logging
import os
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
        LOGGER.warning("BUZZ_MISTRAL_LARGE_AUTH_TOKEN not set")
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


def method_mention_override(text: str, base_score: float) -> bool:
    """Gate 12: OVERRIDE if method/means mentioned + any distress signal."""
    text_lower = text.lower()
    has_method = any(term in text_lower for term in METHOD_TERMS)
    return has_method and base_score > 0.10


def get_guardrails() -> Tuple[Optional[Any], Optional[Any]]:
    """Return (input_guardrail, output_guardrail).

    Mistral-only with threshold 0.35 + Gate 12 OVERRIDE.
    """
    LOGGER.info("Loading guardrails — Mistral-only mode (no mBERT)")

    from src.guardrails.base import GuardrailConfig, GuardrailResult, GuardrailStatus, EvaluationType
    from src.guardrails.llm_judge import LLMJudgeGuardrail
    from src.prompt_templates.guardrail_prompt_template import EXPERT_GUARDRAIL_PROMPT

    judge_llm = _get_mistral_judge()
    if judge_llm is None:
        LOGGER.error("Mistral judge unavailable — cannot run")
        return (None, None)

    llm_judge = LLMJudgeGuardrail(
        config=GuardrailConfig(
            name="mistral_llm_judge",
            description="Mistral LLM Judge — sole guardrail",
            threshold=0.35,
            max_retries=2,
            timeout_seconds=30,
        ),
        llm_provider=judge_llm,
        user_input_prompt=EXPERT_GUARDRAIL_PROMPT,
    )

    class MistralOnlyGuardrail:
        """LLM-only guardrail with Gate 12 OVERRIDE."""

        def __init__(self, llm_judge, config):
            self.llm_judge = llm_judge
            self.config = config

        def evaluate(self, content, context=None, evaluation_type=None):
            if evaluation_type is None:
                evaluation_type = EvaluationType.USER_INPUT

            start_time = time.time()

            try:
                result = self.llm_judge.evaluate(
                    content, context=context, evaluation_type=evaluation_type
                )
                score = result.score if result.score is not None else (0.8 if result.is_high_risk else 0.2)
            except Exception as e:
                LOGGER.warning("LLM judge failed: %s", e)
                latency_ms = (time.time() - start_time) * 1000
                return GuardrailResult(
                    status=GuardrailStatus.FAIL,
                    score=0.5,
                    metadata={"error": str(e)},
                    latency_ms=latency_ms,
                )

            latency_ms = (time.time() - start_time) * 1000

            # Gate 12 OVERRIDE
            if method_mention_override(content, score):
                status = GuardrailStatus.FAIL
                LOGGER.info("MistralOnly | OVERRIDE method_means | score=%.3f latency=%.0fms", score, latency_ms)
            elif score >= 0.35:
                status = GuardrailStatus.FAIL
            else:
                status = GuardrailStatus.PASS

            LOGGER.info(
                "MistralOnly | status=%s score=%.3f threshold=0.35 latency=%.0fms",
                status.value, score, latency_ms,
            )

            return GuardrailResult(
                status=status,
                score=score,
                metadata={"mode": "mistral_only", "score": score},
                latency_ms=latency_ms,
            )

    input_guardrail = MistralOnlyGuardrail(
        llm_judge=llm_judge,
        config=GuardrailConfig(
            name="mistral_only_guardrail",
            description="Mistral-only with threshold 0.35 + Gate 12",
        ),
    )

    LOGGER.info("Guardrails loaded | mistral_only [threshold=0.35 + Gate 12]")
    output_guardrail = None
    return (input_guardrail, output_guardrail)
