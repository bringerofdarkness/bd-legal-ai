"""
NLI Entailment & Hallucination Guardrail Service
Uses DeBERTa-v3 Cross-Encoder to verify whether LLM-generated legal explanations
are strictly entailed by the statutory ground-truth text retrieved from PostgreSQL.
"""

from typing import Dict, Any, Tuple, Optional
import torch
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder

from app.core.logging import get_logger

logger = get_logger("app.services.nli_validator")


class NLIValidationResult(BaseModel):
    is_entailed: bool = Field(description="True if the hypothesis is entailed by the statutory premise")
    verdict: str = Field(description="'VERIFIED', 'CONTRADICTED', or 'UNSUPPORTED'")
    entailment_score: float = Field(description="Softmax probability of entailment [0.0 - 1.0]")
    contradiction_score: float = Field(description="Softmax probability of contradiction [0.0 - 1.0]")
    neutral_score: float = Field(description="Softmax probability of neutral [0.0 - 1.0]")


class NLIValidatorService:
    _model: Optional[CrossEncoder] = None
    MODEL_NAME = "cross-encoder/nli-deberta-v3-small"
    ENTAILMENT_THRESHOLD = 0.50
    CONTRADICTION_THRESHOLD = 0.40

    @classmethod
    def get_model(cls) -> CrossEncoder:
        if cls._model is None:
            logger.info(f"Loading NLI Guardrail Cross-Encoder: {cls.MODEL_NAME}")
            cls._model = CrossEncoder(cls.MODEL_NAME)
        return cls._model

    @classmethod
    def validate_claim(cls, premise: str, hypothesis: str) -> NLIValidationResult:
        """
        Validates whether `hypothesis` (generated answer claim) is supported
        by `premise` (retrieved statutory ground truth text).
        DeBERTa-v3 NLI label mapping:
          0: contradiction
          1: entailment
          2: neutral
        """
        if not premise or not hypothesis:
            return NLIValidationResult(
                is_entailed=False,
                verdict="UNSUPPORTED",
                entailment_score=0.0,
                contradiction_score=0.0,
                neutral_score=1.0,
            )

        try:
            model = cls.get_model()
            # Predict logits for the (premise, hypothesis) pair
            raw_scores = model.predict([(premise[:2500], hypothesis[:1000])])
            probs = torch.softmax(torch.tensor(raw_scores), dim=-1).tolist()[0]
            
            p_contradiction = round(probs[0], 4)
            p_entailment = round(probs[1], 4)
            p_neutral = round(probs[2], 4)

            if p_contradiction >= cls.CONTRADICTION_THRESHOLD:
                verdict = "CONTRADICTED"
                is_entailed = False
            elif p_entailment >= cls.ENTAILMENT_THRESHOLD:
                verdict = "VERIFIED"
                is_entailed = True
            else:
                verdict = "UNSUPPORTED"
                is_entailed = False

            return NLIValidationResult(
                is_entailed=is_entailed,
                verdict=verdict,
                entailment_score=p_entailment,
                contradiction_score=p_contradiction,
                neutral_score=p_neutral,
            )
        except Exception as e:
            logger.error(f"Error during NLI entailment validation: {e}", exc_info=True)
            # Safe conservative fail-closed fallback
            return NLIValidationResult(
                is_entailed=False,
                verdict="UNSUPPORTED",
                entailment_score=0.0,
                contradiction_score=0.0,
                neutral_score=1.0,
            )
