"""Multi-AI Consensus Validator for Phoring prediction reports.

After the report agent generates predictions, this service:
1. Extracts key predictions from the report markdown.
2. Sends each prediction to 2-3 different AI models independently.
3. Each AI scores and validates the prediction.
4. Produces a consensus summary with agreement level and risk factors.

Designed to be additive — never modifies OASIS/camel-ai core behaviour.
"""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from ..utils.llm_client import LLMClient, get_validator_clients
from ..utils.logger import get_logger

logger = get_logger('phoring.consensus')

# ─── Assessment schemas ───

EXTRACT_PREDICTIONS_PROMPT = """\
You are a prediction extraction specialist. Given a simulation-based predictive report,
extract the KEY predictions (claims about what will happen in the future).

Rules:
- Extract 3-7 of the most important, concrete predictions
- Each prediction should be a single, testable statement
- Include the confidence tag if present ([HIGH], [MEDIUM], [LOW])
- Ignore background context, methodology descriptions, or summaries that aren't predictions

Return JSON:
{
    "predictions": [
        {
            "text": "the exact prediction statement",
            "original_confidence": "HIGH|MEDIUM|LOW|UNKNOWN",
            "category": "market|political|social|economic|technology|other"
        }
    ]
}"""

ASSESS_PREDICTION_PROMPT = """\
You are an independent prediction validator. Assess the following prediction
made by a simulation-based forecasting system.

Prediction scenario: {scenario}
Prediction to validate: {prediction}

Evaluate this prediction based on:
1. Logical coherence — does the reasoning chain hold?
2. Historical precedent — have similar dynamics played out before?
3. Completeness — does it account for key variables?
4. Risk factors — what could invalidate this prediction?

Return JSON:
{{
    "agreement": "agree|partially_agree|disagree",
    "confidence_score": 0.0-1.0,
    "reasoning": "2-3 sentence explanation of your assessment",
    "risk_factors": ["risk 1", "risk 2"],
    "alternative_view": "brief alternative scenario if you disagree or partially agree",
    "strength": "what makes this prediction strong (1 sentence)"
}}"""


@dataclass
class PredictionAssessment:
    """One AI model's assessment of a single prediction."""
    validator_id: int
    model_name: str
    agreement: str  # agree | partially_agree | disagree
    confidence_score: float
    reasoning: str
    risk_factors: List[str] = field(default_factory=list)
    alternative_view: str = ""
    strength: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PredictionConsensus:
    """Consensus result for one prediction across multiple validators."""
    prediction_text: str
    original_confidence: str
    category: str
    assessments: List[PredictionAssessment] = field(default_factory=list)
    consensus_level: str = ""  # full_consensus | majority | split | dissent
    consensus_confidence: float = 0.0
    combined_risk_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_text": self.prediction_text,
            "original_confidence": self.original_confidence,
            "category": self.category,
            "assessments": [a.to_dict() for a in self.assessments],
            "consensus_level": self.consensus_level,
            "consensus_confidence": round(self.consensus_confidence, 2),
            "combined_risk_factors": self.combined_risk_factors,
        }


@dataclass
class ValidationReport:
    """Full consensus validation report across all predictions."""
    total_predictions: int = 0
    validators_used: int = 0
    validator_models: List[str] = field(default_factory=list)
    predictions: List[PredictionConsensus] = field(default_factory=list)
    overall_consensus: str = ""  # strong | moderate | weak | mixed
    overall_confidence: float = 0.0
    markdown_section: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_predictions": self.total_predictions,
            "validators_used": self.validators_used,
            "validator_models": self.validator_models,
            "predictions": [p.to_dict() for p in self.predictions],
            "overall_consensus": self.overall_consensus,
            "overall_confidence": round(self.overall_confidence, 2),
            "markdown_section": self.markdown_section,
        }


class ConsensusValidator:
    """Multi-AI cross-validation pipeline for simulation predictions.

    Usage:
        validator = ConsensusValidator(validator_indices=[1, 2])
        if validator.is_available():
            result = validator.validate_report(markdown, requirement)
    """

    def __init__(self, validator_indices: Optional[List[int]] = None):
        self.clients = get_validator_clients(validator_indices)

    def is_available(self) -> bool:
        """Return True when at least 1 AI model is available for validation."""
        return len(self.clients) >= 1

    def validate_report(
        self,
        report_markdown: str,
        simulation_requirement: str
    ) -> ValidationReport:
        """Run multi-AI consensus validation on a completed report.

        Args:
            report_markdown: Full report markdown content.
            simulation_requirement: Original scenario description.

        Returns:
            ValidationReport with per-prediction consensus and overall rating.
        """
        logger.info(
            f"Starting consensus validation with {len(self.clients)} AI models"
        )

        result = ValidationReport(
            validators_used=len(self.clients),
            validator_models=[c.model for c in self.clients],
        )

        # Step 1: Extract predictions using primary model
        predictions = self._extract_predictions(report_markdown)
        if not predictions:
            logger.warning("No predictions extracted from report")
            result.overall_consensus = "no_predictions"
            result.markdown_section = self._build_empty_markdown()
            return result

        result.total_predictions = len(predictions)
        logger.info(f"Extracted {len(predictions)} predictions for validation")

        # Step 1.5: Gather real-world context for factual cross-checking
        web_context = self._gather_web_context(simulation_requirement)

        # Step 2: Validate each prediction with all models + web context
        for pred in predictions:
            consensus = self._validate_prediction(
                pred, simulation_requirement, web_context=web_context
            )
            result.predictions.append(consensus)

        # Step 3: Calculate overall consensus
        result.overall_consensus = self._calculate_overall_consensus(
            result.predictions
        )
        result.overall_confidence = self._calculate_overall_confidence(
            result.predictions
        )

        # Step 4: Generate markdown summary
        result.markdown_section = self._build_markdown(result)

        logger.info(
            f"Consensus validation complete: {result.overall_consensus} "
            f"(confidence: {result.overall_confidence:.2f})"
        )
        return result

    # ─── Internal methods ───

    def _gather_web_context(self, simulation_requirement: str) -> str:
        """Fetch real-world news context for factual cross-checking of predictions."""
        try:
            from .web_intelligence import NewsScraperService
            svc = NewsScraperService()
            if not svc.enabled:
                return ""
            data = svc.gather_for_entity(
                simulation_requirement or "scenario",
                "Scenario",
                max_articles=3,
                context=simulation_requirement,
            )
            return (data.get("combined_text", "") or "")[:6000]
        except Exception as e:
            logger.debug(f"Web context for consensus validation unavailable: {e}")
            return ""

    def _extract_predictions(
        self, report_markdown: str
    ) -> List[Dict[str, str]]:
        """Extract key predictions from report markdown using primary LLM."""
        try:
            # Truncate to avoid oversized prompts
            content = report_markdown[:16000]
            response = self.clients[0].chat_json(
                messages=[
                    {"role": "system", "content": EXTRACT_PREDICTIONS_PROMPT},
                    {"role": "user", "content": content},
                ],
                temperature=0.2,
            )
            predictions = response.get("predictions", [])
            # Cap at 7 predictions to control cost
            return predictions[:7]
        except Exception as e:
            logger.error(f"Prediction extraction failed: {e}")
            return self._fallback_extract_predictions(report_markdown)

    def _fallback_extract_predictions(
        self, markdown: str
    ) -> List[Dict[str, str]]:
        """Regex-based fallback to extract blockquoted predictions."""
        predictions = []
        # Look for blockquoted predictions
        pattern = re.compile(
            r'>\s*(?:\*\*)?Prediction[:\s]*(.+?)(?:\*\*)?$',
            re.MULTILINE | re.IGNORECASE,
        )
        for match in pattern.finditer(markdown):
            text = match.group(1).strip().strip('"').strip("*")
            if len(text) > 20:
                predictions.append({
                    "text": text,
                    "original_confidence": "UNKNOWN",
                    "category": "other",
                })
        # Also look for [HIGH], [MEDIUM], [LOW] tagged sentences
        tag_pattern = re.compile(
            r'([^.!?\n]{20,}?)\s*\[(HIGH|MEDIUM|LOW)\]',
            re.IGNORECASE,
        )
        for match in tag_pattern.finditer(markdown):
            text = match.group(1).strip()
            conf = match.group(2).upper()
            if text not in [p["text"] for p in predictions]:
                predictions.append({
                    "text": text,
                    "original_confidence": conf,
                    "category": "other",
                })
        return predictions[:7]

    def _validate_prediction(
        self,
        prediction: Dict[str, str],
        simulation_requirement: str,
        web_context: str = "",
    ) -> PredictionConsensus:
        """Validate one prediction across all configured AI models."""
        consensus = PredictionConsensus(
            prediction_text=prediction.get("text", ""),
            original_confidence=prediction.get("original_confidence", "UNKNOWN"),
            category=prediction.get("category", "other"),
        )

        for idx, client in enumerate(self.clients):
            assessment = self._assess_with_model(
                client, idx, prediction, simulation_requirement, web_context=web_context
            )
            consensus.assessments.append(assessment)

        # Calculate consensus level
        consensus.consensus_level = self._calculate_consensus_level(
            consensus.assessments
        )
        consensus.consensus_confidence = self._calculate_prediction_confidence(
            consensus.assessments
        )

        # Merge risk factors (dedupe)
        seen_risks = set()
        for a in consensus.assessments:
            for risk in a.risk_factors:
                normalised = risk.strip().lower()
                if normalised not in seen_risks:
                    seen_risks.add(normalised)
                    consensus.combined_risk_factors.append(risk.strip())

        return consensus

    def _assess_with_model(
        self,
        client: LLMClient,
        validator_id: int,
        prediction: Dict[str, str],
        scenario: str,
        web_context: str = "",
    ) -> PredictionAssessment:
        """Get one model's assessment of a prediction, grounded in real-world context."""
        try:
            web_section = ""
            if web_context:
                web_section = (
                    f"\n\nReal-world context (recent news for fact-checking):\n{web_context}\n\n"
                    "Use this real-world context to check whether the prediction aligns with "
                    "or contradicts current real-world developments. If the prediction contradicts "
                    "known facts, flag it in your risk_factors."
                )
            prompt = ASSESS_PREDICTION_PROMPT.format(
                scenario=scenario,
                prediction=prediction.get("text", ""),
            ) + web_section
            response = client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an independent prediction validator. "
                            "Return structured JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            return PredictionAssessment(
                validator_id=validator_id,
                model_name=client.model,
                agreement=response.get("agreement", "partially_agree"),
                confidence_score=max(
                    0.0, min(1.0, float(response.get("confidence_score", 0.5)))
                ),
                reasoning=response.get("reasoning", ""),
                risk_factors=response.get("risk_factors", [])[:5],
                alternative_view=response.get("alternative_view", ""),
                strength=response.get("strength", ""),
            )
        except Exception as e:
            logger.warning(
                f"Validator {validator_id} ({client.model}) failed: {e}"
            )
            return PredictionAssessment(
                validator_id=validator_id,
                model_name=client.model,
                agreement="error",
                confidence_score=0.0,
                reasoning=f"Assessment failed: {str(e)[:100]}",
            )

    # ─── Consensus calculation ───

    @staticmethod
    def _calculate_consensus_level(
        assessments: List[PredictionAssessment],
    ) -> str:
        """Determine consensus level from multiple assessments."""
        valid = [a for a in assessments if a.agreement != "error"]
        if not valid:
            return "error"

        agreements = [a.agreement for a in valid]
        total = len(agreements)
        agree_count = agreements.count("agree")
        partial_count = agreements.count("partially_agree")
        disagree_count = agreements.count("disagree")

        if agree_count == total:
            return "full_consensus"
        if agree_count + partial_count == total and agree_count >= 1:
            return "majority"
        if disagree_count > total / 2:
            return "dissent"
        return "split"

    @staticmethod
    def _calculate_prediction_confidence(
        assessments: List[PredictionAssessment],
    ) -> float:
        """Calculate aggregated confidence for one prediction."""
        valid = [a for a in assessments if a.agreement != "error"]
        if not valid:
            return 0.0
        return sum(a.confidence_score for a in valid) / len(valid)

    @staticmethod
    def _calculate_overall_consensus(
        predictions: List[PredictionConsensus],
    ) -> str:
        """Derive overall report consensus from per-prediction results."""
        if not predictions:
            return "no_predictions"

        levels = [p.consensus_level for p in predictions]
        full = levels.count("full_consensus")
        majority = levels.count("majority")
        total = len(levels)

        strong_count = full + majority
        if strong_count == total:
            return "strong"
        if strong_count >= total * 0.6:
            return "moderate"
        if strong_count >= total * 0.3:
            return "weak"
        return "mixed"

    @staticmethod
    def _calculate_overall_confidence(
        predictions: List[PredictionConsensus],
    ) -> float:
        """Derive overall report confidence from per-prediction averages."""
        if not predictions:
            return 0.0
        return sum(p.consensus_confidence for p in predictions) / len(predictions)

    # ─── Markdown output ───

    def _build_empty_markdown(self) -> str:
        return (
            "\n\n---\n\n## Multi-AI Consensus Validation\n\n"
            "*No extractable predictions found for cross-validation.*\n"
        )

    def _build_markdown(self, report: ValidationReport) -> str:
        """Build a Markdown section summarizing the consensus validation."""
        lines = [
            "\n\n---\n",
            "## Multi-AI Consensus Validation\n",
            f"**Validators:** {', '.join(report.validator_models)}  ",
            f"**Overall Consensus: {report.overall_consensus.upper()}** "
            f"(confidence: {report.overall_confidence:.0%})\n",
        ]

        # Emoji/text indicators for consensus levels
        level_icons = {
            "full_consensus": "UNANIMOUS",
            "majority": "MAJORITY AGREE",
            "split": "SPLIT",
            "dissent": "DISSENT",
            "error": "ERROR",
        }

        for i, pred in enumerate(report.predictions, 1):
            icon = level_icons.get(pred.consensus_level, "?")
            lines.append(
                f"\n**Prediction {i}** [{icon}] "
                f"(confidence: {pred.consensus_confidence:.0%})"
            )
            lines.append(f"> {pred.prediction_text}\n")

            for a in pred.assessments:
                agreement_display = a.agreement.replace("_", " ").title()
                lines.append(
                    f"- **{a.model_name}**: {agreement_display} "
                    f"({a.confidence_score:.0%}) — {a.reasoning}"
                )

            if pred.combined_risk_factors:
                lines.append(
                    f"- **Risk factors:** {'; '.join(pred.combined_risk_factors[:3])}"
                )
            lines.append("")

        lines.append(
            "> *Cross-validation performed by "
            f"{report.validators_used} independent AI models.*\n"
        )
        return "\n".join(lines)
