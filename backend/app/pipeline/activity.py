"""Persistence helpers for processing stages and model calls."""

from datetime import datetime
import time
from typing import Any

from app.db import SessionLocal
from app.models import LlmCall, ProcessingEvent


def start_processing_event(job_id: int | None, document_id: int, step: str) -> tuple[int, float]:
    now = datetime.now()
    with SessionLocal() as session:
        event = ProcessingEvent(
            job_id=job_id,
            document_id=document_id,
            step=step,
            status="running",
            started_at=now,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id
    return event_id, time.perf_counter()


def finish_processing_event(
    event_id: int,
    started: float,
    *,
    result_summary: dict[str, Any] | None = None,
    error: Exception | None = None,
    status: str | None = None,
) -> None:
    with SessionLocal() as session:
        event = session.get(ProcessingEvent, event_id)
        if event is None:
            return
        event.status = status or ("failed" if error else "completed")
        event.finished_at = datetime.now()
        event.duration_seconds = time.perf_counter() - started
        event.result_summary = result_summary
        if error is not None:
            event.error_type = type(error).__name__
            event.error_message = str(error)[:500]
        session.commit()


def start_llm_call(
    *,
    job_id: int | None,
    document_id: int,
    step: str,
    prompt_hash: str,
    page_start: int | None,
    page_end: int | None,
    parameters: dict[str, Any],
) -> tuple[int, float]:
    started_at = datetime.now()
    with SessionLocal() as session:
        call = LlmCall(
            job_id=job_id,
            document_id=document_id,
            step=step,
            model=parameters["model"],
            status="running",
            started_at=started_at,
            page_start=page_start,
            page_end=page_end,
            prompt_hash=prompt_hash,
            parameters={key: value for key, value in parameters.items() if key != "model"},
            seconds=0,
        )
        session.add(call)
        session.commit()
        session.refresh(call)
        call_id = call.id
    return call_id, time.perf_counter()


def _response_data(
    message: Any,
) -> tuple[int, int, float | None, str | None, str | None]:
    metadata = getattr(message, "response_metadata", None) or {}
    usage_metadata = getattr(message, "usage_metadata", None) or {}
    token_usage = metadata.get("token_usage") or metadata.get("usage") or {}
    if not isinstance(token_usage, dict):
        token_usage = {}
    input_tokens = usage_metadata.get("input_tokens")
    if input_tokens is None:
        input_tokens = token_usage.get("prompt_tokens", 0)
    output_tokens = usage_metadata.get("output_tokens")
    if output_tokens is None:
        output_tokens = token_usage.get("completion_tokens", 0)
    cost = token_usage.get("cost")
    if cost is None:
        cost = metadata.get("cost")
    actual_model = metadata.get("model_name") or metadata.get("model")
    response_id = metadata.get("id") or metadata.get("request_id")
    return (
        int(input_tokens or 0),
        int(output_tokens or 0),
        float(cost) if cost is not None else None,
        str(actual_model)[:128] if actual_model else None,
        str(response_id)[:128] if response_id else None,
    )


def finish_llm_call(
    call_id: int,
    started: float,
    *,
    message: Any = None,
    result_summary: dict[str, Any] | None = None,
    error: Exception | None = None,
    status: str | None = None,
) -> None:
    input_tokens = output_tokens = 0
    cost = None
    actual_model = response_id = None
    if message is not None:
        input_tokens, output_tokens, cost, actual_model, response_id = _response_data(
            message
        )

    with SessionLocal() as session:
        call = session.get(LlmCall, call_id)
        if call is None:
            return
        call.status = status or ("failed" if error else "completed")
        call.input_tokens = input_tokens
        call.output_tokens = output_tokens
        call.cost_usd = cost
        call.seconds = time.perf_counter() - started
        call.finished_at = datetime.now()
        call.actual_model = actual_model
        call.response_id = response_id
        call.result_summary = result_summary
        if error is not None:
            call.error_type = type(error).__name__
            call.error_message = str(error)[:500]
        session.commit()
