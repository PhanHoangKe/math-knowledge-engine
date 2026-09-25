import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mke.audit.audit_reporter import generate_dev01_audit_report
from mke.audit.smoke_runner import SmokeSuiteRunner
from mke.knowledge.dev01_adapter import Dev01Adapter
from mke.knowledge.repository import KnowledgeRepository
from mke.knowledge.validator import KnowledgeBaseValidator
from mke.methods.catalogue import CATALOGUE
from mke.models.enums import MethodAdmissibility, SolutionProofStatus
from mke.parsing.exceptions import OutOfScopeSyntaxError, ParserError
from mke.parsing.lexer import Lexer
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine

app = typer.Typer(
    name="mke",
    help="Math Knowledge Engine - Mathematical Verification Foundation (DEV-01 & DEV-02A)",
    add_completion=False,
)
kb_app = typer.Typer(
    name="kb",
    help="Method Knowledge Base and Pilot Dataset commands (DEV-02A)",
    add_completion=False,
)
app.add_typer(kb_app, name="kb")

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


# ==============================================================================
# DEV-02A: Knowledge Base & Pilot Dataset CLI Subcommands (mke kb ...)
# ==============================================================================

@kb_app.command("validate")
def kb_validate_cmd(
    knowledge_dir: Path = typer.Option(Path("data/knowledge"), "--knowledge-dir", "-k", help="Knowledge base directory"),
    dataset_dir: Path = typer.Option(Path("data/dev_pilot"), "--dataset-dir", "-d", help="Pilot dataset directory"),
):
    """Validate knowledge base schemas, referential integrity, and leakage constraints."""
    console.print("[bold cyan]Running Knowledge Base Validation...[/bold cyan]")
    validator = KnowledgeBaseValidator(knowledge_dir=knowledge_dir, dataset_dir=dataset_dir)
    res = validator.validate_all()

    table = Table(title="Knowledge Base Validation Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="yellow")

    status_str = "[green]VALID[/green]" if res.is_valid else "[bold red]INVALID[/bold red]"
    table.add_row("Overall Status", status_str, f"Errors: {res.total_errors}, Warnings: {res.total_warnings}")
    for stat_key, stat_val in res.stats.items():
        table.add_row(stat_key, "[green]OK[/green]", str(stat_val))
    console.print(table)

    errors = [i for i in res.issues if i.severity == "ERROR"]
    warnings = [i for i in res.issues if i.severity == "WARNING"]

    if warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in warnings:
            console.print(f"  - [{w.category}] {w.message}")

    if errors:
        console.print("\n[bold red]Validation Errors:[/bold red]")
        for e in errors:
            console.print(f"  - [{e.category}] {e.message}")
        raise typer.Exit(code=1)
    else:
        console.print("\n[bold green][PASS] Knowledge Base and DEV_PILOT dataset are 100% valid![/bold green]")


@kb_app.command("list-methods")
def kb_list_methods_cmd(
    knowledge_dir: Path = typer.Option(Path("data/knowledge"), "--knowledge-dir", "-k", help="Knowledge base directory"),
):
    """List all method templates in the knowledge base."""
    repo = KnowledgeRepository(knowledge_dir=knowledge_dir)
    methods = repo.list_methods()

    table = Table(title=f"Method Templates Catalogue ({len(methods)} methods)")
    table.add_column("Method ID", style="bold cyan")
    table.add_column("Name (VI / EN)", style="white")
    table.add_column("Classes", style="green")
    table.add_column("Version", style="dim")
    table.add_column("Obligations", style="magenta")

    for m in methods:
        classes_str = ", ".join([c.value for c in m.supported_equation_classes])
        table.add_row(
            m.method_id.value,
            f"{m.name_vi} ({m.name_en})",
            classes_str,
            m.method_version,
            str(len(m.required_proof_obligations)),
        )
    console.print(table)


@kb_app.command("show-method")
def kb_show_method_cmd(
    method_id: str = typer.Argument(..., help="Method ID to inspect, e.g. M1_LINEAR"),
    knowledge_dir: Path = typer.Option(Path("data/knowledge"), "--knowledge-dir", "-k", help="Knowledge base directory"),
):
    """Show detailed specification for a specific method template."""
    repo = KnowledgeRepository(knowledge_dir=knowledge_dir)
    method = repo.get_method(method_id)
    if not method:
        console.print(f"[bold red]Method not found:[/bold red] {method_id}")
        raise typer.Exit(code=1)

    panel_lines = [
        f"[bold cyan]Method ID:[/bold cyan] {method.method_id.value} (v{method.method_version})",
        f"[bold]Name (VI):[/bold] {method.name_vi}",
        f"[bold]Name (EN):[/bold] {method.name_en}",
        f"[bold]Scope:[/bold] {method.mathematical_scope}",
        f"[bold]Classes:[/bold] {', '.join([c.value for c in method.supported_equation_classes])}",
        f"[bold]Structural Preconditions:[/bold] {', '.join(method.structural_preconditions)}",
        f"[bold]Mathematical Preconditions:[/bold] {', '.join(method.mathematical_preconditions)}",
        f"[bold]Required Proof Obligations:[/bold] {[o.value for o in method.required_proof_obligations]}",
        f"[bold]Known Failure Modes:[/bold] {len(method.possible_failure_modes)}",
        f"[bold]Explanation:[/bold] {method.human_readable_explanation}",
    ]
    console.print(Panel("\n".join(panel_lines), title=f"Method: {method.name_en}", border_style="cyan"))


@kb_app.command("list-families")
def kb_list_families_cmd(
    dataset_dir: Path = typer.Option(Path("data/dev_pilot"), "--dataset-dir", "-d", help="Pilot dataset directory"),
):
    """List all equation families in DEV_PILOT dataset."""
    repo = KnowledgeRepository(dataset_dir=dataset_dir)
    families = repo.list_families()

    table = Table(title=f"Equation Families in DEV_PILOT ({len(families)} families)")
    table.add_column("Family ID", style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Equation Class", style="green")
    table.add_column("Split Group", style="magenta")
    table.add_column("Methods", style="yellow")

    for f in families:
        methods_str = ", ".join([m.value for m in f.supported_methods])
        table.add_row(
            f.family_id,
            f.name,
            f.equation_class.value,
            f.split_group_id,
            methods_str,
        )
    console.print(table)


@kb_app.command("inspect-problem")
def kb_inspect_problem_cmd(
    problem_id: str = typer.Argument(..., help="Problem ID to inspect, e.g. PROB_FAM01_V01"),
    dataset_dir: Path = typer.Option(Path("data/dev_pilot"), "--dataset-dir", "-d", help="Pilot dataset directory"),
):
    """Inspect detailed problem record, annotations, and transfer pairs."""
    repo = KnowledgeRepository(dataset_dir=dataset_dir)
    problem = repo.get_problem(problem_id)
    if not problem:
        console.print(f"[bold red]Problem not found:[/bold red] {problem_id}")
        raise typer.Exit(code=1)

    annotations = repo.get_annotations_for_problem(problem_id)
    pairs = repo.get_transfer_pairs_for_problem(problem_id)

    panel_lines = [
        f"[bold cyan]Problem ID:[/bold cyan] {problem.problem_id} (Family: {problem.family_id})",
        f"[bold]Original Expression:[/bold] {problem.original_expression}",
        f"[bold]Canonical Form:[/bold] {problem.canonical_representation}",
        f"[bold]Split:[/bold] {problem.split.value}",
        f"[bold]Domain:[/bold] {problem.domain_str}",
        f"[bold]Excluded Points:[/bold] {problem.excluded_points}",
        f"[bold]Expected Roots:[/bold] {problem.expected_roots}",
        f"[bold]Is Identity on Domain:[/bold] {problem.is_identity_on_domain}",
        f"[bold]Is Empty Domain:[/bold] {problem.is_empty_domain}",
        f"[bold]Near-Miss Category:[/bold] {problem.near_miss_category.value}",
        f"[bold]Annotations Count:[/bold] {len(annotations)}",
        f"[bold]Transfer Pairs Count:[/bold] {len(pairs)}",
    ]
    console.print(Panel("\n".join(panel_lines), title=f"Problem: {problem.problem_id}", border_style="cyan"))


@kb_app.command("run-dev-validation")
def kb_run_dev_validation_cmd(
    dataset_dir: Path = typer.Option(Path("data/dev_pilot"), "--dataset-dir", "-d", help="Pilot dataset directory"),
    knowledge_dir: Path = typer.Option(Path("data/knowledge"), "--knowledge-dir", "-k", help="Knowledge base directory"),
):
    """Run DEV-01 verification engine against all DEV_PILOT problems."""
    console.print("[bold cyan]Running DEV-01 Verification Adapter on DEV_PILOT...[/bold cyan]")
    adapter = Dev01Adapter(knowledge_dir=knowledge_dir, dataset_dir=dataset_dir)
    results = adapter.validate_dataset()

    table = Table(title="DEV-01 Adapter Execution Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Problems", str(results["total_problems"]))
    table.add_row("Normalizable Count", str(results["normalizable_count"]))
    table.add_row("Method Verified Count", str(results["method_verified_count"]))
    table.add_row("Solution Verified Count", str(results["solution_verified_count"]))
    table.add_row("Matches Ground Truth", str(results["match_ground_truth_count"]))
    table.add_row("Discrepancies Count", str(results["discrepancy_count"]))

    console.print(table)


@kb_app.command("export-report")
def kb_export_report_cmd(
    reports_dir: Path = typer.Option(Path("reports"), "--reports-dir", "-r", help="Destination reports directory"),
    dataset_dir: Path = typer.Option(Path("data/dev_pilot"), "--dataset-dir", "-d", help="Pilot dataset directory"),
    knowledge_dir: Path = typer.Option(Path("data/knowledge"), "--knowledge-dir", "-k", help="Knowledge base directory"),
):
    """Generate and export all DEV-02A audit, validation, and discrepancy reports."""
    console.print(f"[bold cyan]Exporting DEV-02A reports to {reports_dir}...[/bold cyan]")
    adapter = Dev01Adapter(knowledge_dir=knowledge_dir, dataset_dir=dataset_dir)
    exported = adapter.export_reports(reports_dir=reports_dir)

    table = Table(title="Exported Reports")
    table.add_column("Report Type", style="cyan")
    table.add_column("Path", style="green")

    for key, path in exported.items():
        table.add_row(key, str(path))
    console.print(table)


if __name__ == "__main__":
    app()
