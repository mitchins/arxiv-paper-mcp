from __future__ import annotations

import argparse
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Variant:
    name: str
    env: dict[str, str]


def wait_health(port: int, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def parse_metrics(output: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in output.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"macro_hit_rate", "weighted_hit_rate", "broad_macro_hit_rate"}:
            out[key] = float(value)
    return out


def default_variants() -> list[Variant]:
    return [
        Variant("control_broad_off", {"ARXIV_ENABLE_BROAD_QUERY_ROUTING": "0"}),
        Variant(
            "mmr_l085",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "mmr",
                "ARXIV_BROAD_MMR_LAMBDA": "0.85",
            },
        ),
        Variant(
            "mmr_l075",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "mmr",
                "ARXIV_BROAD_MMR_LAMBDA": "0.75",
            },
        ),
        Variant(
            "mmr_l065",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "mmr",
                "ARXIV_BROAD_MMR_LAMBDA": "0.65",
            },
        ),
        Variant(
            "fusion_ref",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "60",
                "ARXIV_BROAD_FUSION_ALPHA": "0.72",
                "ARXIV_BROAD_FUSION_BETA": "0.18",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.10",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.08",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.08",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "4",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "9",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.80",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "1",
            },
        ),
        Variant(
            "fusion_lex_heavy",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "40",
                "ARXIV_BROAD_FUSION_ALPHA": "0.82",
                "ARXIV_BROAD_FUSION_BETA": "0.12",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.03",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.14",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.14",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "1",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "3",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.88",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "1",
            },
        ),
        Variant(
            "fusion_balanced",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "50",
                "ARXIV_BROAD_FUSION_ALPHA": "0.76",
                "ARXIV_BROAD_FUSION_BETA": "0.14",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.06",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.10",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.10",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "2",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "5",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.84",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "1",
            },
        ),
        Variant(
            "fusion_wide_no_anchor_gate",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "80",
                "ARXIV_BROAD_FUSION_ALPHA": "0.68",
                "ARXIV_BROAD_FUSION_BETA": "0.20",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.12",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.06",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.06",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "4",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "10",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.78",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "0",
            },
        ),
        Variant(
            "fusion_high_anchor",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "35",
                "ARXIV_BROAD_FUSION_ALPHA": "0.78",
                "ARXIV_BROAD_FUSION_BETA": "0.10",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.04",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.20",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.20",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "2",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "4",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.86",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "1",
            },
        ),
        Variant(
            "fusion_minilm_edge",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "30",
                "ARXIV_BROAD_FUSION_ALPHA": "0.70",
                "ARXIV_BROAD_FUSION_BETA": "0.10",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.16",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.04",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.12",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "1",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "3",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.90",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "1",
            },
        ),
        Variant(
            "fusion_tightest",
            {
                "ARXIV_ENABLE_BROAD_QUERY_ROUTING": "1",
                "ARXIV_BROAD_RERANK_MODE": "minilm_fusion",
                "ARXIV_BROAD_RERANK_FAILURE_MODE": "error",
                "ARXIV_BROAD_FUSION_WINDOW": "25",
                "ARXIV_BROAD_FUSION_ALPHA": "0.86",
                "ARXIV_BROAD_FUSION_BETA": "0.08",
                "ARXIV_BROAD_FUSION_MINILM_WEIGHT": "0.02",
                "ARXIV_BROAD_FUSION_ANCHOR_GAMMA": "0.10",
                "ARXIV_BROAD_FUSION_MISSING_ANCHOR_PENALTY": "0.10",
                "ARXIV_BROAD_FUSION_MAX_JUMP": "0",
                "ARXIV_BROAD_FUSION_MAX_JUMP_CONFIDENT": "2",
                "ARXIV_BROAD_FUSION_CONFIDENCE": "0.92",
                "ARXIV_BROAD_FUSION_REQUIRE_ANCHOR_FOR_BIG_JUMP": "1",
            },
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep B-mode rerank variants against truth metrics")
    parser.add_argument("--python", default=".venv/bin/python")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--query-set", default="benchmarks/queries/v1.json")
    parser.add_argument(
        "--truth-summary",
        default="benchmarks/runs/exp_widenet_judge_20260328T213320Z.summary.csv",
    )
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--start-port", type=int, default=8040)
    parser.add_argument("--health-timeout", type=float, default=60.0)
    parser.add_argument("--eval-timeout", type=float, default=600.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    # Do not resolve symlinks for virtualenv python, otherwise we can escape the venv.
    py = str(root / args.python) if not os.path.isabs(args.python) else args.python

    eval_cmd_base = [
        py,
        "scripts/eval_live_search_vs_120b_truth.py",
        "--query-set",
        args.query_set,
        "--truth-summary",
        args.truth_summary,
        "--k",
        str(args.k),
    ]

    base_env = os.environ.copy()
    base_env.update(
        {
            "DB_PATH": args.db_path,
            "ARXIV_DB_IMMUTABLE": "1",
            "ARXIV_DEV_MAX_LIMIT": "1000",
            "ARXIV_ENABLE_JARGON_EXPANSION": "1",
        }
    )

    rows: list[dict[str, object]] = []
    variants = default_variants()

    for idx, variant in enumerate(variants):
        port = args.start_port + idx
        env = base_env.copy()
        env.update(variant.env)

        server_cmd = [py, "main.py", "--host", "127.0.0.1", "--port", str(port)]
        proc = subprocess.Popen(
            server_cmd,
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            if not wait_health(port, timeout_s=args.health_timeout):
                stderr_tail = ""
                stdout_tail = ""
                if proc.poll() is not None:
                    try:
                        out, err = proc.communicate(timeout=2)
                        stdout_tail = (out or "")[-300:]
                        stderr_tail = (err or "")[-300:]
                    except Exception:
                        pass
                rows.append(
                    {
                        "variant": variant.name,
                        "status": "boot_failed",
                        "stdout_tail": stdout_tail,
                        "stderr_tail": stderr_tail,
                    }
                )
                continue

            cmd = eval_cmd_base + ["--endpoint", f"http://127.0.0.1:{port}"]
            run = subprocess.run(
                cmd,
                cwd=root,
                env=base_env,
                capture_output=True,
                text=True,
                timeout=args.eval_timeout,
            )

            if run.returncode != 0:
                rows.append({"variant": variant.name, "status": f"eval_failed_{run.returncode}"})
                continue

            metrics = parse_metrics(run.stdout)
            row: dict[str, object] = {"variant": variant.name, "status": "ok"}
            row.update(metrics)
            rows.append(row)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()

    print("variant,status,macro,weighted,broad_macro,stderr_tail")
    for row in rows:
        macro = row.get("macro_hit_rate")
        weighted = row.get("weighted_hit_rate")
        broad = row.get("broad_macro_hit_rate")
        stderr_tail = str(row.get("stderr_tail", "")).replace("\n", " ").replace(",", ";")
        print(
            ",".join(
                [
                    str(row.get("variant", "")),
                    str(row.get("status", "")),
                    f"{float(macro):.3f}" if macro is not None else "",
                    f"{float(weighted):.3f}" if weighted is not None else "",
                    f"{float(broad):.3f}" if broad is not None else "",
                    stderr_tail,
                ]
            )
        )

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    ok_rows.sort(
        key=lambda r: (
            float(r.get("weighted_hit_rate", -1.0)),
            float(r.get("broad_macro_hit_rate", -1.0)),
            float(r.get("macro_hit_rate", -1.0)),
        ),
        reverse=True,
    )

    if ok_rows:
        best = ok_rows[0]
        print(
            "\nBEST:",
            best.get("variant", ""),
            f"weighted={float(best.get('weighted_hit_rate', 0.0)):.3f}",
            f"broad={float(best.get('broad_macro_hit_rate', 0.0)):.3f}",
            f"macro={float(best.get('macro_hit_rate', 0.0)):.3f}",
        )
        guardrail = [
            r
            for r in ok_rows
            if float(r.get("weighted_hit_rate", 0.0)) >= 0.875
            and float(r.get("broad_macro_hit_rate", 0.0)) >= 0.750
        ]
        print("GUARDRAIL_PASS_COUNT:", len(guardrail))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())