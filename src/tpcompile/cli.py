"""Command line entry point: `tpcompile build`, `tpcompile verify`, `tpcompile plan`."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import compiler, planner, validator


@click.group()
def main() -> None:
    """Compile written standards into gate-verified Conftest/OPA Rego policies."""


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("policy_ids", nargs=-1)
@click.option(
    "--rego-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("rego"),
    help="Output directory for compiled Rego policies.",
)
@click.option(
    "--cache-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=planner.CACHE_DIR,
    help="Directory for cached plan JSON.",
)
def build(spec_dir: Path, policy_ids: tuple[str, ...], rego_dir: Path, cache_dir: Path) -> None:
    """Compile policy folders under SPEC_DIR.

    With POLICY_IDS, compile only those folders (e.g. `build ./policies
    004-my-policy`); otherwise compile all of them.
    """
    for pid in policy_ids:
        if not (spec_dir / pid / "source.md").is_file():
            raise click.ClickException(f"policy folder not found or has no source.md: {spec_dir / pid}")
    try:
        results = compiler.compile_all(
            spec_dir, rego_dir, cache_dir, only=set(policy_ids) or None
        )
    except (planner.PlanError, validator.ValidatorError) as exc:
        raise click.ClickException(str(exc)) from exc

    failed = 0
    skipped = 0
    for r in results:
        if r.skipped:
            skipped += 1
            click.echo(f"SKIP  {r.policy_id}  (unexpressible: {r.reason})")
        elif r.ok:
            click.echo(f"PASS  {r.policy_id}  ({r.attempts} attempt(s))")
        else:
            failed += 1
            click.echo(f"FAIL  {r.policy_id}  ({r.attempts} attempt(s))")
            if r.failure:
                click.echo(_indent(r.failure))
    compiled = len(results) - failed - skipped
    summary = f"{compiled}/{len(results)} policy(ies) compiled"
    if skipped:
        summary += f", {skipped} skipped (unexpressible)"
    click.echo(summary)
    if failed:
        sys.exit(1)


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--rego-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("rego"),
    help="Directory of committed Rego policies.",
)
@click.option(
    "--cache-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=planner.CACHE_DIR,
    help="Directory for cached plan JSON.",
)
def verify(spec_dir: Path, rego_dir: Path, cache_dir: Path) -> None:
    """Verify committed Rego artifacts against their specs. Needs no API key.

    Checks spec/artifact drift in both directions, regenerates plan JSON from
    each policy's fixtures, and re-runs the four gates on the committed Rego.
    Requires terraform, opa, and conftest on PATH.
    """
    spec_ids = {
        p.name for p in spec_dir.iterdir() if p.is_dir() and (p / "source.md").is_file()
    }
    rego_files = sorted(rego_dir.glob("*.rego")) if rego_dir.is_dir() else []
    if not rego_files:
        click.echo(f"{rego_dir}/ is empty; nothing compiled yet.")
        return
    rego_ids = {f.stem for f in rego_files}

    ok = True
    for rid in sorted(rego_ids - spec_ids):
        click.echo(f"DRIFT {rid}: {rego_dir / rid}.rego has no matching {spec_dir / rid}/source.md")
        ok = False
    for sid in sorted(spec_ids - rego_ids):
        click.echo(
            f"DRIFT {sid}: {spec_dir / sid} has no matching {rego_dir / sid}.rego "
            "(spec changed without recompiling?)"
        )
        ok = False

    for pid in sorted(rego_ids & spec_ids):
        policy_dir = spec_dir / pid
        missing = [n for n in ("bad.tf", "good.tf") if not (policy_dir / n).is_file()]
        if missing:
            click.echo(f"DRIFT {pid}: missing fixture(s): {', '.join(missing)}")
            ok = False
            continue
        try:
            paths = planner.plan_policy(policy_dir, spec_dir / "provider.tf", cache_dir)
            rego_text = (rego_dir / f"{pid}.rego").read_text(encoding="utf-8")
            gate = validator.run_gates(rego_text, paths["bad"], paths["good"])
        except (planner.PlanError, validator.ValidatorError) as exc:
            raise click.ClickException(str(exc)) from exc
        if gate.passed:
            click.echo(f"PASS  {pid}")
        else:
            ok = False
            click.echo(f"FAIL  {pid}")
            click.echo(_indent(gate.feedback))

    if not ok:
        sys.exit(1)


@main.command()
@click.argument("policy_id")
@click.option(
    "--spec-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("policies"),
    help="Directory containing policy folders and provider.tf.",
)
@click.option(
    "--cache-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=planner.CACHE_DIR,
    help="Directory for cached plan JSON.",
)
def plan(policy_id: str, spec_dir: Path, cache_dir: Path) -> None:
    """Generate and cache bad/good plan JSON for POLICY_ID."""
    policy_dir = spec_dir / policy_id
    if not policy_dir.is_dir():
        raise click.ClickException(f"policy folder not found: {policy_dir}")
    try:
        paths = planner.plan_policy(policy_dir, spec_dir / "provider.tf", cache_dir)
    except planner.PlanError as exc:
        raise click.ClickException(str(exc)) from exc
    for label, path in paths.items():
        click.echo(f"{label}: {path}")


def _indent(text: str, width: int = 12) -> str:
    pad = " " * width
    return "\n".join(pad + line for line in text.splitlines())
