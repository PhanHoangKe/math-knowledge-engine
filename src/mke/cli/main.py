"""Command Line Interface (CLI) for Math Knowledge Engine Verification Foundation."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mke.audit.audit_reporter import generate_dev01_audit_report
from mke.audit.smoke_runner import SmokeSuiteRunner
from mke.methods.catalogue import CATALOGUE
from mke.models.enums import MethodAdmissibility, SolutionProofStatus
from mke.parsing.exceptions import OutOfScopeSyntaxError, ParserError
from mke.parsing.lexer import Lexer
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine

app = typer.Typer(
    name="mke",
    help="Math Knowledge Engine - Mathematical Verification Foundation (DEV-01)",
    add_completion=False,
)
console = Console()


@app.command("parse")
def parse_cmd(
    equation: str = typer.Argument(..., help="Mathematical equation string to parse, e.g. 'x^2-5*x+6=0'")
):
    """Check if an equation conforms to the safe whitelist grammar and limits."""
    console.print(f"[bold cyan]Parsing equation:[/bold cyan] {equation}")
    try:
        lexer = Lexer(equation)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse_equation()

        console.print("[green][PASS] Syntax is valid and within safe resource limits.[/green]")
        console.print(f"AST Depth: [yellow]{ast.depth()}[/yellow]")
        console.print(f"AST Node Count: [yellow]{ast.node_count()}[/yellow]")
        console.print(f"Mathematical Notation: [bold]{ast.to_math_string()}[/bold]")
    except OutOfScopeSyntaxError as e:
        console.print(f"[bold red]OUT_OF_SCOPE:[/bold red] {e.message}")
        raise typer.Exit(code=2)
    except ParserError as e:
        console.print(f"[bold red]PARSER_ERROR:[/bold red] {e.message}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]UNEXPECTED_ERROR:[/bold red] {type(e).__name__}: {str(e)}")
        raise typer.Exit(code=1)


@app.command("domain")
def domain_cmd(
    equation: str = typer.Argument(..., help="Equation string, e.g. '(x-2)/(x-2)=1'")
):
    """Inspect the original mathematical domain extracted from the unreduced AST."""
    console.print(f"[bold cyan]Inspecting domain for:[/bold cyan] {equation}")
    try:
        ast = Parser.from_text(equation).parse_equation()
        norm = normalize_equation(ast, raw_text=equation)
        domain = norm.domain

        table = Table(title="Original Mathematical Domain Analysis")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Domain Set", domain.format_domain())
        table.add_row("Is All Reals", str(domain.is_all_reals()))
        table.add_row("Excluded Points", str(sorted([str(v) for v in domain.excluded_values])))
        table.add_row("Extracted Constraints Count", str(len(domain.conditions)))

        console.print(table)

        if domain.conditions:
            console.print("\n[bold]Individual Domain Constraints:[/bold]")
            for idx, c in enumerate(domain.conditions, 1):
                console.print(f"  {idx}. [yellow]{c.condition_str}[/yellow] (excluded: {c.excluded_values})")
    except OutOfScopeSyntaxError as e:
        console.print(f"[bold red]OUT_OF_SCOPE:[/bold red] {e.message}")
        raise typer.Exit(code=2)
    except ParserError as e:
        console.print(f"[bold red]PARSER_ERROR:[/bold red] {e.message}")
        raise typer.Exit(code=1)


@app.command("methods")
def methods_cmd(
    equation: str = typer.Argument(..., help="Equation string to evaluate candidate methods for")
):
    """Evaluate structural and mathematical guards for all catalogue methods."""
    console.print(f"[bold cyan]Evaluating candidate methods for:[/bold cyan] {equation}")
    try:
        ast = Parser.from_text(equation).parse_equation()
        norm = normalize_equation(ast, raw_text=equation)

        results = CATALOGUE.find_applicable_methods(norm)

        table = Table(title="Method Catalogue Admissibility Evaluation")
        table.add_column("Method ID", style="bold cyan")
        table.add_column("Method Name", style="white")
        table.add_column("Admissibility", style="bold")
        table.add_column("Guards Summary", style="dim")

        for method, admissibility, guards in results:
            color = "green" if admissibility == MethodAdmissibility.APPLICABLE else (
                "yellow" if admissibility == MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS else "red"
            )
            passed_guards = sum(1 for g in guards if g.passed)
            total_guards = len(guards)
            table.add_row(
                method.method_id.value,
                method.name,
                f"[{color}]{admissibility.value}[/{color}]",
                f"{passed_guards}/{total_guards} guards passed",
            )

        console.print(table)
    except OutOfScopeSyntaxError as e:
        console.print(f"[bold red]OUT_OF_SCOPE:[/bold red] {e.message}")
        raise typer.Exit(code=2)
    except ParserError as e:
        console.print(f"[bold red]PARSER_ERROR:[/bold red] {e.message}")
        raise typer.Exit(code=1)


@app.command("verify")
def verify_cmd(
    equation: str = typer.Argument(..., help="Equation string to verify"),
    method: Optional[str] = typer.Option(None, "--method", "-m", help="Specific Method ID to test"),
):
    """Run full verification pipeline: domain, method admissibility, obligations, and solution."""
    console.print(f"[bold cyan]Running Verification Pipeline:[/bold cyan] {equation}")
    engine = VerificationEngine()
    result = engine.verify(equation, method_id=method)

    panel_content = []
    panel_content.append(f"[bold]Original Domain:[/bold] {result.domain_str}")

    if result.method_instance:
        panel_content.append(f"[bold]Method:[/bold] {result.method_instance.method_id.value} ({result.method_instance.admissibility.value})")
    else:
        panel_content.append("[bold red]Method:[/bold red] None applicable")

    panel_content.append(f"[bold]Method Verified:[/bold] {'[green]YES[/green]' if result.is_verified_method else '[red]NO[/red]'}")
    panel_content.append(f"[bold]Solution Verified:[/bold] {'[green]YES (SOUND & COMPLETE)[/green]' if result.is_verified_solution else '[yellow]NO (UNRESOLVED OR REFUTED)[/yellow]'}")
    panel_content.append(f"[bold]Proof Status:[/bold] {result.solution_status.value}")

    if result.is_identity_on_domain:
        panel_content.append(f"[bold green]Roots:[/bold green] All x in {result.domain_str}")
    elif result.verified_roots:
        panel_content.append(f"[bold green]Roots:[/bold green] {{{', '.join(result.verified_roots)}}}")
    else:
        panel_content.append("[bold]Roots:[/bold] None (empty set or undetermined)")

    panel_content.append(f"[bold]Explanation:[/bold] {result.explanation}")

    console.print(Panel("\n".join(panel_content), title="Verification Result", border_style="cyan"))

    if result.obligations:
        console.print("\n[bold]Proof Obligations Checklist:[/bold]")
        ob_table = Table()
        ob_table.add_column("Obligation ID", style="cyan")
        ob_table.add_column("Status", style="bold")
        ob_table.add_column("Description", style="white")
        ob_table.add_column("Evidence", style="dim")

        for ob in result.obligations:
            status_color = "green" if ob.status.value == "PASS" else ("red" if ob.status.value == "FAIL" else "yellow")
            ob_table.add_row(
                ob.obligation_id.value,
                f"[{status_color}]{ob.status.value}[/{status_color}]",
                ob.description,
                ob.evidence,
            )
        console.print(ob_table)


@app.command("smoke")
def smoke_cmd():
    """Run handcrafted smoke test suite (T1 - T8) and display audit results."""
    console.print("[bold cyan]Executing Handcrafted Smoke Test Suite (T1 - T8)...[/bold cyan]\n")
    runner = SmokeSuiteRunner()
    suite_res = runner.run_all()

    table = Table(title=f"Smoke Suite Summary (Total: {suite_res['total_tests']}, Passed: {suite_res['passed']}, Failed: {suite_res['failed']})")
    table.add_column("ID", style="bold cyan")
    table.add_column("Test Case Name", style="white")
    table.add_column("Equation", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Duration", style="dim")

    for case in suite_res["results"]:
        status_str = "[green]PASS[/green]" if case["passed"] else "[red]FAIL[/red]"
        table.add_row(
            case["id"],
            case["name"],
            case["equation"],
            status_str,
            f"{case['duration_ms']} ms",
        )

    console.print(table)
    console.print(f"\n[bold]Total Execution Time:[/bold] {suite_res['total_execution_time_ms']} ms")


@app.command("report")
def report_cmd(
    output: Optional[Path] = typer.Option(
        Path("reports/DEV01_AUDIT.json"), "--output", "-o", help="Destination JSON path"
    )
):
    """Run smoke audit and export structured audit JSON file."""
    console.print(f"[bold cyan]Generating audit report at:[/bold cyan] {output}")
    audit_data = generate_dev01_audit_report(output_path=output)
    console.print(f"[green][PASS] Audit report generated successfully ({len(audit_data['smoke_test_results']['results'])} smoke cases).[/green]")


if __name__ == "__main__":
    app()
