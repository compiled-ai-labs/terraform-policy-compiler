"""Command line entry point: `tpcompile build` and `tpcompile plan`."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import compiler, planner, validator


@click.group()
def main() -> None:
    """Compile Terraform plan examples into gate-verified Conftest/OPA Rego policies."""


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
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
def build(spec_dir: Path, rego_dir: Path, cache_dir: Path) -> None:
    """Compile every policy folder under SPEC_DIR."""
    try:
        results = compiler.compile_all(spec_dir, rego_dir, cache_dir)
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
