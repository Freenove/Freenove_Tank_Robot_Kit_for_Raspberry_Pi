"""Train mission tuning parameters with a compact CMA-ES optimizer."""

from __future__ import annotations

import argparse
import csv
import math
import os
import platform
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from challenge.tuning import (
    EvalResult,
    default_param_vector,
    evaluate_one,
    evaluate_params,
    save_params,
    vector_to_params,
)


@dataclass
class CandidateResult:
    vector: np.ndarray
    score: float
    metrics: dict[str, float]


class CMAES:
    """Small full-covariance CMA-ES implementation for normalized vectors."""

    def __init__(
        self,
        mean: np.ndarray,
        *,
        sigma: float = 0.35,
        population: int | None = None,
        seed: int = 0,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.n = int(mean.size)
        self.mean = np.asarray(mean, dtype=np.float64).copy()
        self.sigma = float(sigma)
        self.population = population or (4 + int(3 * math.log(self.n)))
        self.mu = self.population // 2

        weights = np.log(self.mu + 0.5) - np.log(np.arange(1, self.mu + 1))
        self.weights = weights / np.sum(weights)
        self.mueff = float(np.sum(self.weights) ** 2 / np.sum(self.weights ** 2))

        self.cc = (4 + self.mueff / self.n) / (self.n + 4 + 2 * self.mueff / self.n)
        self.cs = (self.mueff + 2) / (self.n + self.mueff + 5)
        self.c1 = 2 / ((self.n + 1.3) ** 2 + self.mueff)
        self.cmu = min(
            1 - self.c1,
            2 * (self.mueff - 2 + 1 / self.mueff) / ((self.n + 2) ** 2 + self.mueff),
        )
        self.damps = 1 + 2 * max(0.0, math.sqrt((self.mueff - 1) / (self.n + 1)) - 1) + self.cs

        self.pc = np.zeros(self.n)
        self.ps = np.zeros(self.n)
        self.B = np.eye(self.n)
        self.D = np.ones(self.n)
        self.C = np.eye(self.n)
        self.invsqrtC = np.eye(self.n)
        self.chi_n = math.sqrt(self.n) * (1 - 1 / (4 * self.n) + 1 / (21 * self.n * self.n))
        self.generation = 0

    def ask(self) -> list[np.ndarray]:
        arz = self.rng.standard_normal((self.population, self.n))
        ary = arz @ (self.B * self.D).T
        candidates = self.mean + self.sigma * ary
        return [np.clip(candidate, -1.4, 1.4) for candidate in candidates]

    def tell(self, results: list[CandidateResult]) -> None:
        ranked = sorted(results, key=lambda item: item.score, reverse=True)
        old_mean = self.mean.copy()
        selected = np.asarray([item.vector for item in ranked[: self.mu]])
        self.mean = np.sum(selected * self.weights[:, None], axis=0)
        self.mean = np.clip(self.mean, -1.2, 1.2)

        y = (self.mean - old_mean) / max(self.sigma, 1e-12)
        self.ps = (1 - self.cs) * self.ps + math.sqrt(self.cs * (2 - self.cs) * self.mueff) * (
            self.invsqrtC @ y
        )
        norm_ps = float(np.linalg.norm(self.ps))
        hsig_threshold = (1.4 + 2 / (self.n + 1)) * self.chi_n
        hsig = int(norm_ps / math.sqrt(1 - (1 - self.cs) ** (2 * (self.generation + 1))) < hsig_threshold)
        self.pc = (1 - self.cc) * self.pc + hsig * math.sqrt(self.cc * (2 - self.cc) * self.mueff) * y

        artmp = (selected - old_mean) / max(self.sigma, 1e-12)
        rank_mu = np.zeros((self.n, self.n))
        for weight, row in zip(self.weights, artmp):
            rank_mu += weight * np.outer(row, row)

        self.C = (
            (1 - self.c1 - self.cmu) * self.C
            + self.c1 * (np.outer(self.pc, self.pc) + (1 - hsig) * self.cc * (2 - self.cc) * self.C)
            + self.cmu * rank_mu
        )
        self.sigma *= math.exp((self.cs / self.damps) * (norm_ps / self.chi_n - 1))
        self._update_eigensystem()
        self.generation += 1

    def _update_eigensystem(self) -> None:
        self.C = np.triu(self.C) + np.triu(self.C, 1).T
        eigvals, eigvecs = np.linalg.eigh(self.C)
        eigvals = np.maximum(eigvals, 1e-12)
        self.D = np.sqrt(eigvals)
        self.B = eigvecs
        self.invsqrtC = self.B @ np.diag(1.0 / self.D) @ self.B.T


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune tank mission params with CMA-ES.")
    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--sigma", type=float, default=0.35)
    parser.add_argument("--ticks", type=int, default=500)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--scenarios",
        default="straight-line,line-with-ball,obstacle-detour,noisy-sonic,flicker-ir,full-course",
    )
    parser.add_argument("--output-dir", default="outputs/ga")
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--log-candidates", action="store_true")
    parser.add_argument("--progress-interval", type=float, default=5.0)
    parser.add_argument("--workers", type=int, default=0,
                        help="parallel rollout workers; 0 chooses a conservative local default")
    parser.add_argument("--curriculum", choices=["staged", "all"], default="staged")
    parser.add_argument("--validation-seeds", type=int, default=20)
    parser.add_argument(
        "--validation-scenarios",
        default="line-with-ball,obstacle-detour,noisy-sonic,flicker-ir,full-course",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenarios = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    seeds = list(range(max(1, args.seeds)))
    workers = args.workers if args.workers > 0 else max(1, min(6, os.cpu_count() or 1))
    generation_scenarios = _build_curriculum(args.curriculum, scenarios, max(1, args.generations))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "history.csv"
    best_path = output_dir / "best_params.json"
    validation_path = output_dir / "validation.csv"

    optimizer = CMAES(
        default_param_vector(),
        sigma=args.sigma,
        population=args.population,
        seed=args.seed,
    )
    pool: ProcessPoolExecutor | None = None

    print(_hardware_summary())
    print(
        "[cma] scenarios=%s seeds=%s population=%s generations=%s ticks=%s domain_randomization=%s"
        % (
            ",".join(scenarios),
            len(seeds),
            args.population,
            args.generations,
            args.ticks,
            not args.no_domain_randomization,
        )
    )
    print("[cma] outputs best=%s history=%s" % (best_path, history_path))
    total_rollouts = sum(len(item) for item in generation_scenarios) * args.population * len(seeds)
    print(
        "[cma] parallelism=%s workers=%s total_rollouts=%s rollouts_per_generation=%s"
        % (
            "on" if workers > 1 else "off",
            workers,
            total_rollouts,
            args.population * len(generation_scenarios[0]) * len(seeds) if generation_scenarios else 0,
        )
    )

    if workers > 1:
        try:
            pool = ProcessPoolExecutor(max_workers=workers)
        except (OSError, PermissionError) as exc:
            print(f"[cma][parallel] disabled: {exc}; falling back to sequential rollouts")
            workers = 1

    try:
        _run_training(
            args=args,
            scenarios=scenarios,
            seeds=seeds,
            workers=workers,
            pool=pool,
            optimizer=optimizer,
            history_path=history_path,
            best_path=best_path,
            validation_path=validation_path,
            total_rollouts=total_rollouts,
            generation_scenarios=generation_scenarios,
        )
    finally:
        if pool is not None:
            pool.shutdown()


def _run_training(
    *,
    args: argparse.Namespace,
    scenarios: list[str],
    seeds: list[int],
    workers: int,
    pool: ProcessPoolExecutor | None,
    optimizer: CMAES,
    history_path: Path,
    best_path: Path,
    validation_path: Path,
    total_rollouts: int,
    generation_scenarios: list[list[str]],
) -> None:
    best: CandidateResult | None = None
    with history_path.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "generation",
            "candidate",
            "score",
            "best_score",
            "sigma",
            "mission_success_rate",
            "success_rate",
            "picked_rate",
            "returned_rate",
            "avg_ticks",
            "avg_watchdog",
            "avg_switches",
            "avg_line_lost",
            "avg_false_seek",
            "avg_home_m",
            "avg_balls_remaining",
        ]
        writer = csv.DictWriter(
            fh,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        run_start = time.monotonic()
        completed_rollouts = 0
        last_progress_ts = 0.0

        for generation, current_scenarios in enumerate(generation_scenarios):
            gen_start = time.monotonic()
            results: list[CandidateResult] = []
            for idx, vector in enumerate(optimizer.ask()):
                params = vector_to_params(vector)
                progress = _make_progress_callback(
                    generation=generation,
                    candidate=idx,
                    total_candidates=args.population,
                    total_rollouts=total_rollouts,
                    run_start=run_start,
                    completed_before_candidate=completed_rollouts,
                    last_progress_ts=last_progress_ts,
                    interval_s=args.progress_interval,
                )
                score, eval_results = evaluate_params_with_progress(
                    params,
                    scenarios=current_scenarios,
                    seeds=seeds,
                    max_ticks=args.ticks,
                    domain_randomization=not args.no_domain_randomization,
                    progress=progress,
                    workers=workers,
                    pool=pool,
                )
                completed_rollouts += len(eval_results)
                last_progress_ts = progress.last_print_ts
                metrics = _summarize_eval_results(eval_results)
                result = CandidateResult(vector=np.asarray(vector), score=score, metrics=metrics)
                results.append(result)
                if best is None or result.score > best.score:
                    best = CandidateResult(
                        vector=result.vector.copy(),
                        score=result.score,
                        metrics=dict(result.metrics),
                    )
                    save_params(
                        best_path,
                        vector_to_params(best.vector),
                        {
                            "score": best.score,
                            **best.metrics,
                            "generation": generation,
                            "candidate": idx,
                            "scenarios": current_scenarios,
                            "seeds": seeds,
                            "ticks": args.ticks,
                        },
                )
                writer.writerow(
                    {
                        "generation": generation,
                        "candidate": idx,
                        "score": round(score, 6),
                        "best_score": round(best.score if best else score, 6),
                        "sigma": round(optimizer.sigma, 8),
                        **{key: round(value, 6) for key, value in metrics.items()},
                    }
                )
                fh.flush()
                if args.log_candidates:
                    print(
                        "[cma][candidate] gen=%s idx=%s score=%.2f picked=%.2f returned=%.2f "
                        "ticks=%.1f watchdog=%.2f line_lost=%.1f false_seek=%.2f"
                        % (
                            generation,
                            idx,
                            score,
                            metrics["picked_rate"],
                            metrics["returned_rate"],
                            metrics["avg_ticks"],
                            metrics["avg_watchdog"],
                            metrics["avg_line_lost"],
                            metrics["avg_false_seek"],
                        )
                    )

            optimizer.tell(results)
            gen_metrics = _summarize_generation(results)
            elapsed = time.monotonic() - gen_start
            print(
                "[cma] gen=%s elapsed=%.1fs best=%.2f gen_best=%.2f mean=%.2f std=%.2f "
                "picked=%.2f returned=%.2f ticks=%.1f watchdog=%.2f switches=%.1f "
                "line_lost=%.1f false_seek=%.2f sigma=%.4f stage=%s"
                % (
                    generation,
                    elapsed,
                    best.score if best else float("nan"),
                    max(item.score for item in results),
                    gen_metrics["score_mean"],
                    gen_metrics["score_std"],
                    gen_metrics["picked_rate"],
                    gen_metrics["returned_rate"],
                    gen_metrics["avg_ticks"],
                    gen_metrics["avg_watchdog"],
                    gen_metrics["avg_switches"],
                    gen_metrics["avg_line_lost"],
                    gen_metrics["avg_false_seek"],
                    optimizer.sigma,
                    ",".join(current_scenarios),
                )
            )

    if best is not None:
        print(f"[cma] wrote {best_path} score={best.score:.2f}")
        print(f"[cma] wrote {history_path}")
        validation_scenarios = [
            item.strip() for item in args.validation_scenarios.split(",") if item.strip()
        ]
        validation_seed_start = max(seeds) + 100 if seeds else 100
        validation_seeds = list(
            range(validation_seed_start, validation_seed_start + max(1, args.validation_seeds))
        )
        validation_score, validation_results = evaluate_params(
            vector_to_params(best.vector),
            scenarios=validation_scenarios,
            seeds=validation_seeds,
            max_ticks=args.ticks,
            domain_randomization=not args.no_domain_randomization,
        )
        validation_metrics = _summarize_eval_results(validation_results)
        _write_validation_csv(validation_path, validation_results)
        failure_summary = _summarize_failure_reasons(validation_results)
        save_params(
            best_path,
            vector_to_params(best.vector),
            {
                "score": best.score,
                **best.metrics,
                "validation_score": validation_score,
                **{f"validation_{key}": value for key, value in validation_metrics.items()},
                "validation_scenarios": validation_scenarios,
                "validation_seeds": validation_seeds,
                "validation_failure_reasons": failure_summary,
                "ticks": args.ticks,
            },
        )
        print(
            "[cma][final] validation_score=%.2f mission_success_rate=%.2f "
            "picked_rate=%.2f returned_rate=%.2f success_rate=%.2f watchdog=%.2f false_seek=%.2f "
            "line_lost=%.1f avg_ticks=%.1f"
            % (
                validation_score,
                validation_metrics["mission_success_rate"],
                validation_metrics["picked_rate"],
                validation_metrics["returned_rate"],
                validation_metrics["success_rate"],
                validation_metrics["avg_watchdog"],
                validation_metrics["avg_false_seek"],
                validation_metrics["avg_line_lost"],
                validation_metrics["avg_ticks"],
            )
        )
        if failure_summary:
            print("[cma][final] failures=%s" % _format_failure_summary(failure_summary))
        print(f"[cma] wrote {validation_path}")


class _Progress:
    def __init__(
        self,
        *,
        generation: int,
        candidate: int,
        total_candidates: int,
        total_rollouts: int,
        run_start: float,
        completed_before_candidate: int,
        interval_s: float,
    ) -> None:
        self.generation = generation
        self.candidate = candidate
        self.total_candidates = total_candidates
        self.total_rollouts = total_rollouts
        self.run_start = run_start
        self.completed_before_candidate = completed_before_candidate
        self.interval_s = max(0.5, interval_s)
        self.last_print_ts = 0.0

    def __call__(
        self,
        *,
        scenario: str,
        seed: int,
        local_rollout_index: int,
        local_rollout_total: int,
        latest_score: float | None,
        latest_metrics: dict[str, float] | None,
    ) -> None:
        now = time.monotonic()
        if self.last_print_ts and now - self.last_print_ts < self.interval_s:
            return
        self.last_print_ts = now

        done = self.completed_before_candidate + local_rollout_index
        elapsed = max(1e-6, now - self.run_start)
        rate = done / elapsed if done else 0.0
        eta_s = (self.total_rollouts - done) / rate if rate > 0 else float("inf")
        metrics = latest_metrics or {}
        print(
            "[cma][progress] gen=%s cand=%s/%s rollout=%s/%s total=%s/%s "
            "scenario=%s seed=%s elapsed=%s eta=%s rate=%.2f/s "
            "score=%s picked=%s returned=%s success=%s watchdog=%s"
            % (
                self.generation,
                self.candidate + 1,
                self.total_candidates,
                local_rollout_index,
                local_rollout_total,
                done,
                self.total_rollouts,
                scenario,
                seed,
                _format_duration(elapsed),
                _format_duration(eta_s),
                rate,
                _fmt_optional(latest_score),
                _fmt_optional(metrics.get("picked_rate")),
                _fmt_optional(metrics.get("returned_rate")),
                _fmt_optional(metrics.get("mission_success_rate")),
                _fmt_optional(metrics.get("avg_watchdog")),
            )
        )


def evaluate_params_with_progress(
    params: dict,
    *,
    scenarios: list[str] | tuple[str, ...],
    seeds: list[int] | tuple[int, ...],
    max_ticks: int,
    domain_randomization: bool,
    progress: _Progress,
    workers: int = 1,
    pool: ProcessPoolExecutor | None = None,
) -> tuple[float, list[EvalResult]]:
    if workers > 1:
        return _evaluate_params_parallel(
            params,
            scenarios=scenarios,
            seeds=seeds,
            max_ticks=max_ticks,
            domain_randomization=domain_randomization,
            progress=progress,
            workers=workers,
            pool=pool,
        )

    results: list[EvalResult] = []
    total = len(scenarios) * len(seeds)
    latest_score: float | None = None
    latest_metrics: dict[str, float] | None = None
    rollout_index = 0
    for scenario in scenarios:
        for seed in seeds:
            progress(
                scenario=scenario,
                seed=int(seed),
                local_rollout_index=rollout_index,
                local_rollout_total=total,
                latest_score=latest_score,
                latest_metrics=latest_metrics,
            )
            result = evaluate_one(
                params,
                scenario=scenario,
                seed=int(seed),
                max_ticks=max_ticks,
                domain_randomization=domain_randomization,
            )
            results.append(result)
            rollout_index += 1
            latest_score = float(sum(item.score for item in results) / len(results))
            latest_metrics = _summarize_eval_results(results)
            progress(
                scenario=scenario,
                seed=int(seed),
                local_rollout_index=rollout_index,
                local_rollout_total=total,
                latest_score=latest_score,
                latest_metrics=latest_metrics,
            )
    if not results:
        return -1e9, []
    return float(sum(item.score for item in results) / len(results)), results


def _evaluate_params_parallel(
    params: dict,
    *,
    scenarios: list[str] | tuple[str, ...],
    seeds: list[int] | tuple[int, ...],
    max_ticks: int,
    domain_randomization: bool,
    progress: _Progress,
    workers: int,
    pool: ProcessPoolExecutor | None = None,
) -> tuple[float, list[EvalResult]]:
    jobs = [
        (params, scenario, int(seed), max_ticks, domain_randomization)
        for scenario in scenarios
        for seed in seeds
    ]
    total = len(jobs)
    results: list[EvalResult] = []
    progress(
        scenario="parallel-submit",
        seed=-1,
        local_rollout_index=0,
        local_rollout_total=total,
        latest_score=None,
        latest_metrics=None,
    )
    try:
        owns_pool = pool is None
        active_pool = pool or ProcessPoolExecutor(max_workers=max(1, workers))
        try:
            futures = [active_pool.submit(_evaluate_one_worker, job) for job in jobs]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                latest_score = float(sum(item.score for item in results) / len(results))
                latest_metrics = _summarize_eval_results(results)
                progress(
                    scenario=result.scenario,
                    seed=result.seed,
                    local_rollout_index=len(results),
                    local_rollout_total=total,
                    latest_score=latest_score,
                    latest_metrics=latest_metrics,
                )
        finally:
            if owns_pool:
                active_pool.shutdown()
    except (OSError, PermissionError) as exc:
        print(f"[cma][parallel] disabled: {exc}; falling back to sequential rollouts")
        return evaluate_params_with_progress(
            params,
            scenarios=scenarios,
            seeds=seeds,
            max_ticks=max_ticks,
            domain_randomization=domain_randomization,
            progress=progress,
            workers=1,
        )
    if not results:
        return -1e9, []
    return float(sum(item.score for item in results) / len(results)), results


def _evaluate_one_worker(job: tuple[dict, str, int, int, bool]) -> EvalResult:
    params, scenario, seed, max_ticks, domain_randomization = job
    return evaluate_one(
        params,
        scenario=scenario,
        seed=seed,
        max_ticks=max_ticks,
        domain_randomization=domain_randomization,
    )


def _make_progress_callback(
    *,
    generation: int,
    candidate: int,
    total_candidates: int,
    total_rollouts: int,
    run_start: float,
    completed_before_candidate: int,
    last_progress_ts: float,
    interval_s: float,
) -> _Progress:
    progress = _Progress(
        generation=generation,
        candidate=candidate,
        total_candidates=total_candidates,
        total_rollouts=total_rollouts,
        run_start=run_start,
        completed_before_candidate=completed_before_candidate,
        interval_s=interval_s,
    )
    progress.last_print_ts = last_progress_ts
    return progress


def _summarize_eval_results(results: list[EvalResult]) -> dict[str, float]:
    if not results:
        return {
            "mission_success_rate": 0.0,
            "success_rate": 0.0,
            "picked_rate": 0.0,
            "returned_rate": 0.0,
            "avg_ticks": 0.0,
            "avg_watchdog": 0.0,
            "avg_switches": 0.0,
            "avg_line_lost": 0.0,
            "avg_false_seek": 0.0,
            "avg_home_m": 0.0,
            "avg_balls_remaining": 0.0,
        }

    picked = [
        1.0 if item.ball_points > 0 or item.balls_remaining == 0 or item.carrying else 0.0
        for item in results
    ]
    returned = [
        1.0
        if item.ball_points > 0
        and item.carrying == 0
        and item.state == "follow_line"
        and item.home_m <= 0.35
        else 0.0
        for item in results
    ]
    mission_success = [
        1.0
        if returned_item
        and item.watchdog_resets == 0
        and item.false_seek_exits == 0
        else 0.0
        for item, returned_item in zip(results, returned)
    ]
    return {
        "mission_success_rate": float(np.mean(mission_success)),
        "success_rate": float(np.mean(mission_success)),
        "picked_rate": float(np.mean(picked)),
        "returned_rate": float(np.mean(returned)),
        "avg_ticks": float(np.mean([item.ticks for item in results])),
        "avg_watchdog": float(np.mean([item.watchdog_resets for item in results])),
        "avg_switches": float(np.mean([item.state_switches for item in results])),
        "avg_line_lost": float(np.mean([item.line_lost_ticks for item in results])),
        "avg_false_seek": float(np.mean([item.false_seek_exits for item in results])),
        "avg_home_m": float(np.mean([item.home_m for item in results])),
        "avg_balls_remaining": float(np.mean([item.balls_remaining for item in results])),
    }


def _summarize_generation(results: list[CandidateResult]) -> dict[str, float]:
    scores = np.asarray([item.score for item in results], dtype=np.float64)
    metrics: dict[str, float] = {
        "score_mean": float(np.mean(scores)) if scores.size else 0.0,
        "score_std": float(np.std(scores)) if scores.size else 0.0,
    }
    keys = [
        "mission_success_rate",
        "success_rate",
        "picked_rate",
        "returned_rate",
        "avg_ticks",
        "avg_watchdog",
        "avg_switches",
        "avg_line_lost",
        "avg_false_seek",
        "avg_home_m",
        "avg_balls_remaining",
    ]
    for key in keys:
        metrics[key] = float(np.mean([item.metrics[key] for item in results])) if results else 0.0
    return metrics


def _write_validation_csv(path: Path, results: list[EvalResult]) -> None:
    fieldnames = [
        "scenario",
        "seed",
        "score",
        "mission_success",
        "outcome",
        "failure_reason",
        "picked",
        "returned",
        "ticks",
        "state",
        "carrying",
        "balls_remaining",
        "home_m",
        "watchdog_resets",
        "state_switches",
        "line_lost_ticks",
        "false_seek_exits",
        "line_points",
        "obstacle_points",
        "ball_points",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            picked = item.ball_points > 0 or item.balls_remaining == 0 or item.carrying
            returned = (
                item.ball_points > 0
                and item.carrying == 0
                and item.state == "follow_line"
                and item.home_m <= 0.35
            )
            mission_success = returned and item.watchdog_resets == 0 and item.false_seek_exits == 0
            writer.writerow(
                {
                    "scenario": item.scenario,
                    "seed": item.seed,
                    "score": round(item.score, 6),
                    "mission_success": int(mission_success),
                    "outcome": item.outcome,
                    "failure_reason": item.failure_reason,
                    "picked": int(picked),
                    "returned": int(returned),
                    "ticks": item.ticks,
                    "state": item.state,
                    "carrying": item.carrying,
                    "balls_remaining": item.balls_remaining,
                    "home_m": round(item.home_m, 6),
                    "watchdog_resets": item.watchdog_resets,
                    "state_switches": item.state_switches,
                    "line_lost_ticks": item.line_lost_ticks,
                    "false_seek_exits": item.false_seek_exits,
                    "line_points": item.line_points,
                    "obstacle_points": item.obstacle_points,
                    "ball_points": item.ball_points,
                }
            )


def _build_curriculum(curriculum: str, scenarios: list[str], generations: int) -> list[list[str]]:
    if generations <= 0:
        return []
    if curriculum == "all" or len(scenarios) <= 1:
        return [list(scenarios) for _ in range(generations)]

    stages: list[list[str]] = []
    for end in range(1, len(scenarios)):
        stages.append(list(scenarios[:end]))
    stages.append(list(scenarios))

    if generations <= len(stages):
        positions = np.linspace(0, len(stages) - 1, generations)
        return [stages[int(round(pos))] for pos in positions]

    schedule: list[list[str]] = []
    base = max(1, generations // len(stages))
    remaining = generations
    for index, stage in enumerate(stages):
        slots_left = len(stages) - index - 1
        count = min(base, max(1, remaining - slots_left))
        if index == len(stages) - 1:
            count = remaining
        schedule.extend([stage] * count)
        remaining -= count
        if remaining <= 0:
            break

    if len(schedule) < generations:
        schedule.extend([stages[-1]] * (generations - len(schedule)))
    return schedule[:generations]


def _summarize_failure_reasons(results: list[EvalResult]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        if item.outcome == "success":
            continue
        key = item.failure_reason or item.outcome or "unknown"
        summary[key] = summary.get(key, 0) + 1
    return dict(sorted(summary.items(), key=lambda pair: (-pair[1], pair[0])))


def _format_failure_summary(summary: dict[str, int]) -> str:
    return ", ".join(f"{key}:{value}" for key, value in summary.items())


def _hardware_summary() -> str:
    torch_bits = "torch=not-installed mps=unavailable"
    try:
        import torch  # type: ignore[import-not-found]

        mps = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        torch_bits = f"torch={torch.__version__} mps={'available' if mps else 'unavailable'}"
    except Exception:
        pass
    return (
        "[cma][hardware] optimizer=numpy/cpu simulator=python/cpu "
        f"cpu={platform.processor() or platform.machine()} cores={os.cpu_count()} {torch_bits}"
    )


def _format_duration(seconds: float) -> str:
    if math.isinf(seconds):
        return "unknown"
    seconds = max(0, int(round(seconds)))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def _fmt_optional(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


if __name__ == "__main__":
    main()
