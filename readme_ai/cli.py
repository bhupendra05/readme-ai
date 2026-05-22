"""CLI for readme-ai."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

load_dotenv()
console = Console()


@click.group()
def cli():
    """readme-ai — Generate polished GitHub READMEs using AI."""


@cli.command("generate")
@click.argument("repo_path", default=".", type=click.Path(exists=True))
@click.option(
    "--backend", "-b",
    default="openai",
    type=click.Choice(["openai", "anthropic", "ollama"]),
    show_default=True,
)
@click.option("--model", "-m", default=None, help="Override model name")
@click.option(
    "--style", "-s",
    default="standard",
    type=click.Choice(["standard", "minimal", "detailed"]),
    show_default=True,
    help="README style",
)
@click.option("--output", "-o", default=None, help="Write output to file (default: print to stdout)")
@click.option("--improve", is_flag=True, help="Improve existing README instead of generating from scratch")
@click.option("--preview", is_flag=True, help="Render markdown preview in terminal")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt before writing file")
def generate_cmd(repo_path, backend, model, style, output, improve, preview, yes):
    """Analyze a repository and generate a README.md using AI.

    \b
    Examples:
      readme-ai generate .
      readme-ai generate ~/my-project --backend anthropic
      readme-ai generate . --style detailed --output README.md
      readme-ai generate . --improve --output README.md
    """
    from readme_ai.analyzer import analyze_local
    from readme_ai.generator import generate_readme

    # Analyze repo
    with console.status("[dim]Analyzing repository…[/]"):
        ctx = analyze_local(repo_path)

    # Print analysis summary
    table = Table(title="Repository Analysis", box=box.SIMPLE, show_lines=False)
    table.add_column("Property", style="dim")
    table.add_column("Value")
    table.add_row("Name", ctx.name)
    table.add_row("Language", ctx.primary_language or "—")
    table.add_row("Frameworks", ", ".join(ctx.frameworks) or "—")
    table.add_row("Dependencies", str(len(ctx.dependencies)))
    table.add_row("Tests", "✓" if ctx.has_tests else "✗")
    table.add_row("Docker", "✓" if ctx.has_docker else "✗")
    table.add_row("CI/CD", "✓" if ctx.has_ci else "✗")
    table.add_row("License", ctx.license_type or ("✓" if ctx.has_license else "✗"))
    table.add_row("Existing README", "yes (will improve)" if (improve and ctx.existing_readme) else ("yes" if ctx.existing_readme else "no"))
    console.print(table)

    # Generate
    console.print(f"\n[dim]Generating README ({style} style) via {backend}…[/]")
    with console.status(f"[dim]{backend} is writing your README…[/]"):
        try:
            readme_content = generate_readme(ctx, backend, model, style, improve)
        except Exception as e:
            console.print(f"[red]Generation failed:[/] {e}")
            sys.exit(1)

    # Preview
    if preview:
        console.print("\n")
        console.rule("[bold]README Preview[/]")
        console.print(Markdown(readme_content))
        console.rule()

    # Output
    if output:
        out_path = Path(output)
        if out_path.exists() and not yes:
            overwrite = click.confirm(f"{output} already exists. Overwrite?", default=False)
            if not overwrite:
                console.print("[yellow]Aborted.[/]")
                sys.exit(0)
        out_path.write_text(readme_content, encoding="utf-8")
        console.print(f"\n[bold green]README written to:[/] {output}")
        console.print(f"[dim]{len(readme_content.splitlines())} lines, {len(readme_content):,} characters[/]")
    else:
        # Print raw markdown
        console.print()
        console.print(Syntax(readme_content, "markdown", theme="monokai", word_wrap=True))


@cli.command("analyze")
@click.argument("repo_path", default=".", type=click.Path(exists=True))
def analyze_cmd(repo_path):
    """Analyze a repository and print the extracted context (no LLM call)."""
    from readme_ai.analyzer import analyze_local

    with console.status("Analyzing…"):
        ctx = analyze_local(repo_path)

    console.print(Panel(ctx.file_tree, title="File Tree", border_style="dim"))

    table = Table(box=box.ROUNDED)
    table.add_column("Property")
    table.add_column("Value")
    rows = [
        ("Name", ctx.name),
        ("Primary Language", ctx.primary_language),
        ("All Languages", ", ".join(ctx.languages)),
        ("Frameworks", ", ".join(ctx.frameworks)),
        ("Package", f"{ctx.package_name} v{ctx.package_version}"),
        ("Description", ctx.description[:80] if ctx.description else ""),
        ("Entry Points", ", ".join(ctx.entry_points)),
        ("Top Dependencies", ", ".join(ctx.dependencies[:10])),
        ("Has Tests", str(ctx.has_tests)),
        ("Has Docker", str(ctx.has_docker)),
        ("Has CI/CD", str(ctx.has_ci)),
        ("License", ctx.license_type or str(ctx.has_license)),
        ("Git Remote", ctx.git_remote),
    ]
    for k, v in rows:
        table.add_row(f"[dim]{k}[/]", v)
    console.print(table)

    if ctx.recent_commits:
        console.print("\n[dim]Recent commits:[/]")
        for c in ctx.recent_commits:
            console.print(f"  {c}")


def main():
    cli()


if __name__ == "__main__":
    main()
