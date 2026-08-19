from __future__ import annotations

"""
v2.2 D2.8 numerical-null calibration.

Implements the preregistered exact multiplicative-separability null for
M-A1, M-A2, and M-A3. This is numerical calibration only, not a scientific
effect-size calibration and not a candidate-generator evaluation.
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

NULL_MASTER_SEED = 76001
ACTIVE_COUNTS = (5, 6)
NULL_REPLICATES_PER_COUNT = 2000
N_CONTEXTS = 1000

EPS = 1.0e-12
POSITIVE_FLOOR = 1.0e-12
ENERGY_FLOOR = 1.0e-24

FLOOR_NS = 1.0e-12
FLOOR_LRV = 1.0e-10
FLOOR_NSV = 1.0e-10


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


d27 = _load_module(
    "d28_d27_metrics",
    ROOT / "src" / "v2_2_d2_7_positive_control.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def require_clean_git() -> tuple[str, str]:
    status = _git("status", "--porcelain")
    if status:
        raise RuntimeError(
            "D2.8 REFUSES TO RUN FROM A DIRTY WORKING TREE.\n"
            f"{status}"
        )
    return (
        _git("rev-parse", "HEAD"),
        _git("rev-parse", "--abbrev-ref", "HEAD"),
    )


def rank_one_energy(x: np.ndarray) -> float:
    """M-A1 non-separability energy without epsilon regularization."""
    s = np.linalg.svd(
        np.asarray(x, dtype=float),
        compute_uv=False,
        full_matrices=False,
    )
    energy = float(np.sum(s ** 2))

    if energy <= ENERGY_FLOOR:
        raise ValueError(
            "Rank-one energy is undefined for "
            "structural-zero-energy matrices."
        )

    residual = (
        1.0
        - float(s[0] ** 2) / energy
    )

    return float(
        np.clip(
            residual,
            0.0,
            1.0,
        )
    )


def max_pairwise_lrv(x: np.ndarray) -> float:
    values = []
    for a, b in combinations(range(x.shape[1]), 2):
        xa = x[:, a]
        xb = x[:, b]
        mask = (
            (xa > POSITIVE_FLOOR)
            & (xb > POSITIVE_FLOOR)
        )
        lr = np.log(xa[mask] / xb[mask])
        values.append(
            float(np.std(lr, ddof=0))
        )
    return float(max(values))


def make_null_matrix(
    rng: np.random.Generator,
    m: int,
) -> np.ndarray:
    theta = rng.uniform(
        0.05,
        0.40,
        size=m,
    )
    c = (
        np.arange(1, N_CONTEXTS + 1, dtype=float)
        - 0.5
    ) / N_CONTEXTS
    c = c[rng.permutation(N_CONTEXTS)]
    return c[:, None] * theta[None, :]


def q999(values: np.ndarray) -> float:
    return float(
        np.quantile(
            np.asarray(values, dtype=float),
            0.999,
            method="linear",
        )
    )


def calibrate_nulls() -> tuple[pd.DataFrame, dict]:
    rows = []

    for m in ACTIVE_COUNTS:
        rng = np.random.default_rng(
            np.random.SeedSequence(
                [NULL_MASTER_SEED, m]
            )
        )
        for replicate in range(
            NULL_REPLICATES_PER_COUNT
        ):
            x = make_null_matrix(rng, m)
            rows.append(
                {
                    "active_alternatives": m,
                    "replicate": replicate,
                    "NS_null": rank_one_energy(x),
                    "LRV_null_max":
                        max_pairwise_lrv(x),
                    "NSV_vector_null":
                        d27.nsv(x, "vector"),
                }
            )

    frame = pd.DataFrame(rows)

    q_ns = q999(frame["NS_null"].to_numpy())
    q_lrv = q999(frame["LRV_null_max"].to_numpy())
    q_nsv = q999(frame["NSV_vector_null"].to_numpy())

    thresholds = {
        "T_num_NS": max(
            100.0 * q_ns,
            FLOOR_NS,
        ),
        "T_num_LRV": max(
            100.0 * q_lrv,
            FLOOR_LRV,
        ),
        "T_num_NSV_vector": max(
            100.0 * q_nsv,
            FLOOR_NSV,
        ),
        "Q999_NS_null": q_ns,
        "Q999_LRV_null_max": q_lrv,
        "Q999_NSV_vector_null": q_nsv,
        "safety_multiplier": 100.0,
        "floors": {
            "NS": FLOOR_NS,
            "LRV": FLOOR_LRV,
            "NSV_vector": FLOOR_NSV,
            "energy": ENERGY_FLOOR,
        },
    }
    return frame, thresholds


def run(output_dir: Path) -> None:
    commit, branch = require_clean_git()

    null_frame, thresholds = calibrate_nulls()

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    null_frame.to_csv(
        output_dir / "null_metrics.csv",
        index=False,
    )

    metadata = {
        "git_commit": commit,
        "git_branch": branch,
        "master_seed": NULL_MASTER_SEED,
        "active_counts": list(ACTIVE_COUNTS),
        "replicates_per_count":
            NULL_REPLICATES_PER_COUNT,
        "contexts_per_null": N_CONTEXTS,
        "theta_distribution": "U(0.05,0.40)",
        "context_grid":
            "(s-0.5)/1000, deterministically permuted per replicate",
        "candidate_responses_used": False,
        "external_test_used": False,
        "primary_seeds_used": False,
    }

    (output_dir / "thresholds.json").write_text(
        json.dumps(
            thresholds,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "run_metadata.json").write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "D2.8 NUMERICAL-NULL CALIBRATION",
        f"git_commit: {commit}",
        f"T_num_NS: {thresholds['T_num_NS']:.16g}",
        f"T_num_LRV: {thresholds['T_num_LRV']:.16g}",
        f"T_num_NSV_vector: {thresholds['T_num_NSV_vector']:.16g}",
        f"Q999_NS_null: {thresholds['Q999_NS_null']:.16g}",
        f"Q999_LRV_null_max: {thresholds['Q999_LRV_null_max']:.16g}",
        f"Q999_NSV_vector_null: {thresholds['Q999_NSV_vector_null']:.16g}",
        "candidate_responses_used: False",
        "external_TEST_used: False",
        "primary_seeds_used: False",
    ]
    (output_dir / "summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("\n".join(lines))
    print(f"WROTE: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "results"
            / "v2_2_d2_8_numerical_null"
        ),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
