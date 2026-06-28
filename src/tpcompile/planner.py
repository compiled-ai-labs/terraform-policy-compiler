"""Turn a Terraform file into plan JSON.

Copies provider.tf plus a single target .tf into a temp dir, then runs
`terraform init`, `terraform plan -out`, and `terraform show -json`. The JSON
that Conftest consumes is the output of `terraform show -json`, so the policy is
written against the same shape CI and the runtime see. Plan JSON is cached under
`.compile-cache/` for reuse by the compiler and by the CI verify workflow.

Stdlib only: shutil + subprocess + tempfile. terraform is expected on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

CACHE_DIR = Path(".compile-cache")


class PlanError(RuntimeError):
    """Raised when terraform cannot produce plan JSON for a target file."""


def _require_terraform() -> None:
    if shutil.which("terraform") is None:
        raise PlanError(
            "terraform not found on PATH. Install Terraform and ensure `terraform` is callable."
        )


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def plan_to_json(target_tf: Path, provider_tf: Path) -> str:
    """Run init/plan/show on `target_tf` + `provider_tf`, return show -json output."""
    _require_terraform()
    target_tf = Path(target_tf)
    provider_tf = Path(provider_tf)
    if not target_tf.is_file():
        raise PlanError(f"target terraform file not found: {target_tf}")
    if not provider_tf.is_file():
        raise PlanError(f"provider file not found: {provider_tf}")

    with tempfile.TemporaryDirectory(prefix="tpcompile-plan-") as tmp:
        work = Path(tmp)
        shutil.copy(provider_tf, work / "provider.tf")
        shutil.copy(target_tf, work / "main.tf")

        init = _run(["terraform", "init", "-input=false", "-backend=false"], work)
        if init.returncode != 0:
            raise PlanError(
                f"terraform init failed for {target_tf}:\n{init.stdout}\n{init.stderr}"
            )

        plan = _run(["terraform", "plan", "-out=plan.bin", "-input=false"], work)
        if plan.returncode != 0:
            raise PlanError(
                f"terraform plan failed for {target_tf}:\n{plan.stdout}\n{plan.stderr}"
            )

        show = _run(["terraform", "show", "-json", "plan.bin"], work)
        if show.returncode != 0:
            raise PlanError(
                f"terraform show failed for {target_tf}:\n{show.stdout}\n{show.stderr}"
            )

        try:
            json.loads(show.stdout)
        except json.JSONDecodeError as exc:
            raise PlanError(
                f"terraform show did not emit valid JSON for {target_tf}: {exc}"
            ) from exc
        return show.stdout


def plan_policy(
    policy_dir: Path, provider_tf: Path, cache_dir: Path = CACHE_DIR
) -> dict[str, Path]:
    """Plan bad.tf and good.tf for one policy folder, cache the JSON, return paths.

    Writes `<cache_dir>/<id>-bad.json` and `<cache_dir>/<id>-good.json`.
    """
    policy_dir = Path(policy_dir)
    policy_id = policy_dir.name
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for label in ("bad", "good"):
        plan_json = plan_to_json(policy_dir / f"{label}.tf", provider_tf)
        out = cache_dir / f"{policy_id}-{label}.json"
        out.write_text(plan_json, encoding="utf-8")
        paths[label] = out
    return paths
