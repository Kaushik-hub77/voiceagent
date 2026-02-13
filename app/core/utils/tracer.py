"""
Tracing utilities for observability and debugging
"""

import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator
from contextvars import ContextVar
import uuid

from app.core.utils.logger import get_logger

logger = get_logger(__name__)

# Context variables for tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)

# Per-request LLM metrics
# IMPORTANT: Using a single mutable dict stored in a contextvar so increments from
# child asyncio tasks are visible to the parent task (no "llm_calls=0" summary).
llm_metrics_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar("llm_metrics", default=None)
llm_stage_var: ContextVar[Optional[str]] = ContextVar("llm_stage", default=None)


class TraceContext:
    """Context for tracing operations"""

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.trace_id = trace_id or self.correlation_id
        self.span_id = span_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id
        }


def get_current_trace_context() -> TraceContext:
    """Get the current trace context"""
    return TraceContext(
        correlation_id=correlation_id_var.get(),
        trace_id=trace_id_var.get(),
        span_id=span_id_var.get()
    )


def set_trace_context(context: TraceContext) -> None:
    """Set the current trace context"""
    correlation_id_var.set(context.correlation_id)
    trace_id_var.set(context.trace_id)
    span_id_var.set(context.span_id)


@contextmanager
def trace_operation(
    operation_name: str,
    component: str = "unknown",
    **attributes
) -> Generator[TraceContext, None, None]:
    """
    Context manager for tracing operations

    Args:
        operation_name: Name of the operation being traced
        component: Component/service performing the operation
        **attributes: Additional attributes to include in traces

    Yields:
        TraceContext for the operation
    """

    # Get or create trace context
    current_context = get_current_trace_context()

    # Create new span context
    span_context = TraceContext(
        correlation_id=current_context.correlation_id,
        trace_id=current_context.trace_id,
        span_id=str(uuid.uuid4()),
        parent_span_id=current_context.span_id
    )

    # Set context for this span
    token = correlation_id_var.set(span_context.correlation_id)
    trace_token = trace_id_var.set(span_context.trace_id)
    span_token = span_id_var.set(span_context.span_id)

    start_time = time.time()

    try:
        logger.info(
            f"Starting {operation_name}",
            operation=operation_name,
            component=component,
            **span_context.to_dict(),
            **attributes
        )

        yield span_context

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Operation {operation_name} failed",
            operation=operation_name,
            component=component,
            duration=f"{duration:.3f}s",
            error=str(e),
            **span_context.to_dict(),
            **attributes
        )
        raise

    else:
        duration = time.time() - start_time
        logger.info(
            f"Completed {operation_name}",
            operation=operation_name,
            component=component,
            duration=f"{duration:.3f}s",
            **span_context.to_dict(),
            **attributes
        )

    finally:
        # Restore previous context
        correlation_id_var.reset(token)
        trace_id_var.reset(trace_token)
        span_id_var.reset(span_token)


def trace_function(
    component: str = "unknown",
    operation_name: Optional[str] = None
):
    """
    Decorator for tracing function calls

    Args:
        component: Component name
        operation_name: Override operation name (defaults to function name)
    """

    def decorator(func):
        actual_operation_name = operation_name or f"{func.__module__}.{func.__name__}"

        async def async_wrapper(*args, **kwargs):
            with trace_operation(actual_operation_name, component):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            with trace_operation(actual_operation_name, component):
                return func(*args, **kwargs)

        if hasattr(func, '__call__'):
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return func

    return decorator


# ---------------------------------------------------------------------
# LLM metrics helpers
# ---------------------------------------------------------------------

def reset_llm_metrics() -> None:
    """Reset per-request LLM counters/timers."""
    llm_metrics_var.set({
        "llm_calls": 0,
        "llm_time_s": 0.0,
        "llm_stage_counts": {},
        "llm_stage_time_s": {},
    })


def record_llm_call(processing_time_s: float) -> None:
    """
    Record an LLM call timing into contextvars.
    Called by provider clients (e.g., OpenAIClient) after each request.
    """
    try:
        metrics = llm_metrics_var.get()
        if metrics is None:
            # If not initialized, create one (best-effort)
            reset_llm_metrics()
            metrics = llm_metrics_var.get() or {}

        metrics["llm_calls"] = int(metrics.get("llm_calls", 0)) + 1
        metrics["llm_time_s"] = float(metrics.get("llm_time_s", 0.0)) + float(processing_time_s or 0.0)

        stage = llm_stage_var.get() or "unknown"
        counts = metrics.setdefault("llm_stage_counts", {})
        times = metrics.setdefault("llm_stage_time_s", {})
        counts[stage] = int(counts.get(stage, 0)) + 1
        times[stage] = float(times.get(stage, 0.0)) + float(processing_time_s or 0.0)
    except Exception:
        # Metrics must never break request flow
        return


def get_llm_metrics() -> Dict[str, Any]:
    """Get current per-request LLM metrics snapshot."""
    metrics = llm_metrics_var.get() or {}
    stage_times = metrics.get("llm_stage_time_s") or {}
    return {
        "llm_calls": int(metrics.get("llm_calls", 0)),
        "llm_time_s": round(float(metrics.get("llm_time_s", 0.0)), 3),
        "llm_stage_counts": dict(metrics.get("llm_stage_counts") or {}),
        "llm_stage_time_s": {k: round(float(v), 3) for k, v in dict(stage_times).items()},
    }


@contextmanager
def set_llm_stage(stage: str) -> Generator[None, None, None]:
    """Context manager to tag subsequent LLM calls with a stage name."""
    token = llm_stage_var.set(stage)
    try:
        yield
    finally:
        llm_stage_var.reset(token)


class MetricsCollector:
    """Simple metrics collection for operations"""

    def __init__(self):
        self.metrics = {}

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value"""

        if name not in self.metrics:
            self.metrics[name] = []

        metric_data = {
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {}
        }

        self.metrics[name].append(metric_data)

        # Log the metric
        logger.info(
            f"Metric recorded: {name}",
            metric_name=name,
            value=value,
            tags=tags
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        summary = {}

        for name, measurements in self.metrics.items():
            if measurements:
                values = [m["value"] for m in measurements]
                summary[name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1]
                }

        return summary


# Global metrics collector
metrics_collector = MetricsCollector()
