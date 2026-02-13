#!/usr/bin/env python3
"""
LLM Benchmarking Script for AI LLM Service

Compares performance across different models and providers.
"""

import asyncio
import time
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass
import json

from app.core.llm.model_registry import ModelRegistry
from app.core.llm.base import LLMConfig
from app.core.utils.logger import setup_logging

# Setup logging
logger = setup_logging()

@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""
    model: str
    provider: str
    prompt: str
    response_length: int
    total_tokens: int
    latency_ms: float
    tokens_per_second: float
    cost_usd: float

class LLMBenchmarker:
    """Benchmark LLM performance"""

    def __init__(self):
        self.registry = ModelRegistry()
        self.test_prompts = [
            "Write a short paragraph about artificial intelligence.",
            "Explain quantum computing in simple terms.",
            "What are the benefits of renewable energy?",
            "Describe the water cycle in detail.",
            "How do vaccines work?"
        ]

    async def run_benchmarks(
        self,
        models: List[str] = None,
        iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Run benchmarks across models

        Args:
            models: List of model names to test (None = all available)
            iterations: Number of iterations per model

        Returns:
            Benchmark results
        """

        if models is None:
            available_models = self.registry.list_available_models()
            models = list(available_models.keys())

        if not models:
            logger.error("No models available for benchmarking")
            return {"error": "No models available"}

        results = []
        model_stats = {}

        logger.info(f"Starting benchmark with {len(models)} models, {iterations} iterations each")

        for model_name in models:
            logger.info(f"Benchmarking {model_name}...")

            model_results = []
            for i in range(iterations):
                try:
                    result = await self._benchmark_single_model(model_name, i)
                    if result:
                        model_results.append(result)
                        results.append(result)
                except Exception as e:
                    logger.error(f"Benchmark failed for {model_name} iteration {i}: {str(e)}")

            if model_results:
                model_stats[model_name] = self._calculate_model_stats(model_results)

        # Calculate overall statistics
        overall_stats = self._calculate_overall_stats(results)

        return {
            "results": [result.__dict__ for result in results],
            "model_stats": model_stats,
            "overall_stats": overall_stats,
            "metadata": {
                "total_models": len(models),
                "total_iterations": iterations,
                "total_requests": len(results)
            }
        }

    async def _benchmark_single_model(self, model_name: str, iteration: int) -> BenchmarkResult:
        """Benchmark a single model iteration"""

        # Select test prompt
        prompt = self.test_prompts[iteration % len(self.test_prompts)]

        # Get client
        client = self.registry.get_client(model_name)
        if not client:
            raise Exception(f"Client not available for {model_name}")

        # Create config
        config = LLMConfig(
            model=model_name,
            temperature=0.7,
            max_tokens=200
        )

        # Time the request
        start_time = time.time()

        response = await client.generate(prompt, config)

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Calculate metrics
        response_length = len(response.content)
        tokens_per_second = response.usage.get("total_tokens", 0) / (latency_ms / 1000)

        # Estimate cost (simplified)
        cost_usd = self._estimate_cost(model_name, response.usage)

        return BenchmarkResult(
            model=model_name,
            provider=self.registry.get_provider_for_model(model_name) or "unknown",
            prompt=prompt,
            response_length=response_length,
            total_tokens=response.usage.get("total_tokens", 0),
            latency_ms=latency_ms,
            tokens_per_second=tokens_per_second,
            cost_usd=cost_usd
        )

    def _estimate_cost(self, model_name: str, usage: Dict[str, int]) -> float:
        """Estimate cost for the request (simplified)"""

        model_config = self.registry.get_model_config(model_name)
        if not model_config:
            return 0.0

        input_cost = model_config.get("input_cost_per_token", 0.0)
        output_cost = model_config.get("output_cost_per_token", 0.0)

        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return (input_tokens * input_cost) + (output_tokens * output_cost)

    def _calculate_model_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate statistics for a model"""

        latencies = [r.latency_ms for r in results]
        tokens_per_sec = [r.tokens_per_second for r in results]
        costs = [r.cost_usd for r in results]

        return {
            "avg_latency_ms": statistics.mean(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "avg_tokens_per_sec": statistics.mean(tokens_per_sec),
            "avg_cost_usd": statistics.mean(costs),
            "total_cost_usd": sum(costs),
            "iterations_completed": len(results)
        }

    def _calculate_overall_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate overall benchmark statistics"""

        if not results:
            return {}

        latencies = [r.latency_ms for r in results]
        tokens_per_sec = [r.tokens_per_second for r in results]

        # Group by provider
        provider_stats = {}
        for result in results:
            provider = result.provider
            if provider not in provider_stats:
                provider_stats[provider] = []
            provider_stats[provider].append(result.latency_ms)

        provider_avg_latencies = {
            provider: statistics.mean(latencies)
            for provider, latencies in provider_stats.items()
        }

        return {
            "total_requests": len(results),
            "avg_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
            "avg_tokens_per_sec": statistics.mean(tokens_per_sec),
            "provider_comparison": provider_avg_latencies
        }


async def main():
    """Main benchmark function"""

    import argparse

    parser = argparse.ArgumentParser(description="LLM Benchmarking Tool")
    parser.add_argument("--models", nargs="*", help="Models to benchmark")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per model")
    parser.add_argument("--output", type=str, help="Output JSON file")

    args = parser.parse_args()

    benchmarker = LLMBenchmarker()
    results = await benchmarker.run_benchmarks(
        models=args.models,
        iterations=args.iterations
    )

    # Print results
    print(json.dumps(results, indent=2, default=str))

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
