"""
Inference Speed Analyzer

Analyzes model inference speed and efficiency.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass
class SpeedMetrics:
    """Inference speed metrics"""
    fps: float
    avg_inference_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    gpu_memory_mb: float
    cpu_usage_percent: float
    throughput_images_per_second: float
    device: str
    batch_size: int


@dataclass
class EfficiencyMetrics:
    """Model efficiency metrics"""
    parameters_m: float
    gflops: float
    model_size_mb: float
    efficiency_score: float
    map_fifo_curve: list[dict]


@dataclass
class BenchmarkResult:
    """Benchmark result container"""
    model_name: str
    speed: SpeedMetrics
    efficiency: Optional[EfficiencyMetrics] = None
    timestamp: datetime = field(default_factory=datetime.now)


class InferenceSpeedAnalyzer:
    """Analyzer for model inference speed and efficiency"""

    def __init__(self):
        pass

    def benchmark_model(
        self,
        model_path: Path,
        test_images: list[Path],
        device: str = "cuda",
        batch_size: int = 1,
        warmup_runs: int = 10,
        num_runs: int = 100
    ) -> SpeedMetrics:
        """
        Benchmark model inference speed.

        Args:
            model_path: Path to model weights
            test_images: List of test image paths
            device: Device to use ('cuda', 'cpu', or 'mps')
            batch_size: Batch size for inference
            warmup_runs: Number of warmup runs
            num_runs: Number of benchmark runs

        Returns:
            SpeedMetrics
        """
        try:
            from ultralytics import YOLO
        except ImportError:
            return SpeedMetrics(
                fps=0,
                avg_inference_ms=0,
                p50_ms=0,
                p95_ms=0,
                p99_ms=0,
                gpu_memory_mb=0,
                cpu_usage_percent=0,
                throughput_images_per_second=0,
                device=device,
                batch_size=batch_size,
            )

        model = YOLO(str(model_path))

        import time

        # Warmup
        for _ in range(warmup_runs):
            model.predict(str(test_images[0]), verbose=False, device=device, batch=batch_size)

        # Benchmark
        times = []
        gpu_memories = []

        for _ in range(num_runs):
            start = time.time()

            if device == "cuda":
                import torch
                torch.cuda.synchronize() if torch.cuda.is_available() else None

            results = model.predict(str(test_images[0]), verbose=False, device=device, batch=batch_size)

            if device == "cuda":
                import torch
                torch.cuda.synchronize() if torch.cuda.is_available() else None

            elapsed = time.time() - start
            times.append(elapsed * 1000)  # Convert to ms

            if device == "cuda":
                try:
                    gpu_mem = torch.cuda.memory_allocated() / 1024 / 1024
                    gpu_memories.append(gpu_mem)
                except:
                    pass

        times = np.array(times)

        avg_time = times.mean()
        fps = 1000 / avg_time if avg_time > 0 else 0
        throughput = fps * batch_size

        return SpeedMetrics(
            fps=float(fps),
            avg_inference_ms=float(avg_time),
            p50_ms=float(np.percentile(times, 50)),
            p95_ms=float(np.percentile(times, 95)),
            p99_ms=float(np.percentile(times, 99)),
            gpu_memory_mb=float(np.mean(gpu_memories)) if gpu_memories else 0,
            cpu_usage_percent=0,  # Would need psutil
            throughput_images_per_second=float(throughput),
            device=device,
            batch_size=batch_size,
        )

    def compare_inference_speed(
        self,
        model_results: list[tuple[str, SpeedMetrics]]
    ) -> dict:
        """
        Compare inference speed across multiple models.

        Args:
            model_results: List of (model_name, SpeedMetrics) tuples

        Returns:
            Comparison dictionary
        """
        comparison = {
            "models": [],
            "rankings": {
                "by_fps": [],
                "by_latency": [],
                "by_memory": [],
            },
        }

        for name, metrics in model_results:
            comparison["models"].append({
                "name": name,
                "fps": metrics.fps,
                "avg_latency_ms": metrics.avg_inference_ms,
                "p95_latency_ms": metrics.p95_ms,
                "gpu_memory_mb": metrics.gpu_memory_mb,
                "throughput": metrics.throughput_images_per_second,
            })

        # Sort rankings
        comparison["rankings"]["by_fps"] = sorted(
            comparison["models"],
            key=lambda x: x["fps"],
            reverse=True
        )
        comparison["rankings"]["by_latency"] = sorted(
            comparison["models"],
            key=lambda x: x["avg_latency_ms"]
        )
        comparison["rankings"]["by_memory"] = sorted(
            comparison["models"],
            key=lambda x: x["gpu_memory_mb"]
        )

        return comparison

    def analyze_model_efficiency(
        self,
        model_path: Path,
        mAP: float,
        fps: float
    ) -> EfficiencyMetrics:
        """
        Calculate model efficiency metrics.

        Args:
            model_path: Path to model
            mAP: Model mAP score
            fps: Inference FPS

        Returns:
            EfficiencyMetrics
        """
        # Estimate model size
        model_size_mb = model_path.stat().st_size / (1024 * 1024) if model_path.exists() else 0

        # Estimate parameters (rough heuristic based on size)
        # Assuming ~4 bytes per parameter (float32)
        parameters_m = model_size_mb * 250 / 4  # Very rough estimate

        # Estimate GFLOPs (rough heuristic)
        gflops = parameters_m * 0.5  # Very rough estimate

        # Calculate efficiency score: mAP / sqrt(FPS)
        # Higher is better, balances accuracy and speed
        efficiency_score = mAP / np.sqrt(fps) if fps > 0 else 0

        # Generate mAP-FPS tradeoff curve points
        map_fifo_curve = []
        for fps_target in [10, 20, 30, 60, 100, 200]:
            efficiency = mAP / np.sqrt(fps_target) if fps_target > 0 else 0
            map_fifo_curve.append({
                "fps": fps_target,
                "efficiency_score": float(efficiency),
                "relative_efficiency": float(efficiency / efficiency_score) if efficiency_score > 0 else 0,
            })

        return EfficiencyMetrics(
            parameters_m=float(parameters_m),
            gflops=float(gflops),
            model_size_mb=float(model_size_mb),
            efficiency_score=float(efficiency_score),
            map_fifo_curve=map_fifo_curve,
        )

    def generate_efficiency_report(
        self,
        comparison: dict,
        metrics: list[EfficiencyMetrics]
    ) -> str:
        """Generate efficiency comparison report."""
        lines = []
        lines.append("=" * 60)
        lines.append("MODEL EFFICIENCY COMPARISON REPORT")
        lines.append("=" * 60)

        lines.append("\n## Speed Rankings (by FPS)")
        lines.append("-" * 50)
        for i, model in enumerate(comparison["rankings"]["by_fps"], 1):
            lines.append(f"{i}. {model['name']}: {model['fps']:.1f} FPS")

        lines.append("\n## Latency Rankings")
        lines.append("-" * 50)
        for i, model in enumerate(comparison["rankings"]["by_latency"], 1):
            lines.append(f"{i}. {model['name']}: {model['avg_latency_ms']:.2f} ms (p95: {model['p95_latency_ms']:.2f} ms)")

        lines.append("\n## Memory Usage Rankings")
        lines.append("-" * 50)
        for i, model in enumerate(comparison["rankings"]["by_memory"], 1):
            lines.append(f"{i}. {model['name']}: {model['gpu_memory_mb']:.1f} MB")

        if metrics:
            lines.append("\n## Efficiency Analysis")
            lines.append("-" * 50)
            for i, m in enumerate(metrics):
                lines.append(f"\n### Model {i+1}")
                lines.append(f"- Parameters: {m.parameters_m:.1f}M")
                lines.append(f"- GFLOPs: {m.gflops:.1f}")
                lines.append(f"- Model Size: {m.model_size_mb:.1f} MB")
                lines.append(f"- Efficiency Score: {m.efficiency_score:.4f}")

        # Application recommendations
        lines.append("\n## Application Recommendations")
        lines.append("-" * 50)
        lines.append("- **Real-time applications**: Choose highest FPS with acceptable mAP")
        lines.append("- **Edge deployment**: Prioritize small model size and low memory")
        lines.append("- **Batch processing**: Prioritize throughput over latency")

        return "\n".join(lines)
