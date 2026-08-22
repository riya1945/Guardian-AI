from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError

from regret_engine.src.config import Settings
from regret_engine.src.schemas import DecisionRecord, EvidenceItem


class LlmDraft(BaseModel):
    summary: str
    explanation: str
    alternative_action: str


class LlmProvider(Protocol):
    provider_name: str

    def generate(
        self,
        record: DecisionRecord,
        evidence: list[EvidenceItem],
        latency_ms: float,
    ) -> LlmDraft:
        ...


class LlmUnavailable(RuntimeError):
    pass


@dataclass
class DeterministicProvider:
    provider_name: str = "deterministic"

    def generate(
        self,
        record: DecisionRecord,
        evidence: list[EvidenceItem],
        latency_ms: float,
    ) -> LlmDraft:
        top_titles = ", ".join(sorted({item.title for item in evidence}))
        counterfactual = (
            f"Selected price {record.regret.actual_price:.2f} INR was compared with "
            f"best counterfactual price {record.regret.best_price:.2f} INR."
        )
        alternative_action = (
            "Accept submitted price"
            if record.risk_level == "LOW"
            else f"Review price before release and compare against {record.regret.best_price:.2f} INR counterfactual."
        )
        return LlmDraft(
            summary=(
                f"{record.decision_id} is {record.risk_level.lower()} risk. "
                f"Guardian-AI recommends: {record.recommendation}."
            ),
            explanation=(
                f"Grounded evidence: {top_titles}. Regret engine output shows "
                f"{record.regret.regret:.2f} INR regret "
                f"({record.regret.regret_percentage:.2f}%). {counterfactual} "
                f"Retrieval latency was {latency_ms:.1f} ms."
            ),
            alternative_action=alternative_action,
        )


class GroqProvider:
    provider_name = "groq"

    def __init__(self, api_key: str, model: str, timeout: float = 20.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        record: DecisionRecord,
        evidence: list[EvidenceItem],
        latency_ms: float,
    ) -> LlmDraft:
        messages = [
            {
                "role": "system",
                "content": _system_prompt(),
            },
            {
                "role": "user",
                "content": _prompt(record, evidence, latency_ms),
            },
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        if response.status_code in {408, 409, 429, 500, 502, 503, 504}:
            raise LlmUnavailable(response.text[:400])
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_draft(content)


class GeminiChatProvider:
    provider_name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float = 20.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        record: DecisionRecord,
        evidence: list[EvidenceItem],
        latency_ms: float,
    ) -> LlmDraft:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": _system_prompt()
                            + "\n\n"
                            + _prompt(record, evidence, latency_ms)
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
        if response.status_code in {408, 409, 429, 500, 502, 503, 504}:
            raise LlmUnavailable(response.text[:400])
        response.raise_for_status()
        content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_draft(content)


class ProviderChain:
    def __init__(self, providers: list[LlmProvider]):
        self.providers = providers
        self.last_provider = "none"

    def generate(
        self,
        record: DecisionRecord,
        evidence: list[EvidenceItem],
        latency_ms: float,
    ) -> LlmDraft:
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                draft = provider.generate(record, evidence, latency_ms)
                self.last_provider = provider.provider_name
                return draft
            except (LlmUnavailable, httpx.HTTPError, KeyError, ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                continue
        raise LlmUnavailable(str(last_error) if last_error else "No LLM providers configured.")


def build_provider_chain(settings: Settings) -> ProviderChain:
    providers: list[LlmProvider] = []
    for name in settings.llm_chain:
        if name == "groq" and settings.groq_api_key:
            providers.append(GroqProvider(settings.groq_api_key, settings.groq_model))
        elif name == "gemini" and settings.gemini_api_key:
            providers.append(GeminiChatProvider(settings.gemini_api_key, settings.gemini_chat_model))
        elif name == "deterministic":
            providers.append(DeterministicProvider())
    if not providers:
        providers.append(DeterministicProvider())
    return ProviderChain(providers)


def _parse_draft(content: str) -> LlmDraft:
    payload = json.loads(content)
    return LlmDraft.model_validate(payload)


def _system_prompt() -> str:
    return (
        "Return strict JSON with summary, explanation, and alternative_action. "
        "Use only supplied engine output and evidence. Do not invent evidence."
    )


def _prompt(
    record: DecisionRecord,
    evidence: list[EvidenceItem],
    latency_ms: float,
) -> str:
    factor_payloads = [
        factor.model_dump() if hasattr(factor, "model_dump") else factor.dict()
        for factor in record.factors
    ]
    evidence_text = "\n\n".join(
        f"Source: {item.source}\nTitle: {item.title}\nSnippet: {item.content}"
        for item in evidence
    )
    return (
        f"Decision: {record.decision_id}\n"
        f"Risk: {record.risk_level}\n"
        f"Recommendation: {record.recommendation}\n"
        f"Regret INR: {record.regret.regret:.2f}\n"
        f"Regret percent: {record.regret.regret_percentage:.2f}\n"
        f"Selected price: {record.regret.actual_price:.2f}\n"
        f"Best price: {record.regret.best_price:.2f}\n"
        f"Factors: {factor_payloads}\n"
        f"Retrieval latency ms: {latency_ms:.1f}\n"
        f"Evidence:\n{evidence_text}"
    )
