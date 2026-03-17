"""Debugging agent CLI commands (Tasks 011-012).

Provides ``autopilot debug`` subcommands for running debugging tasks,
managing tool plugins, and inspecting pipeline status. Config mutation
follows the load-modify-save pattern (ADR-D05).
"""

from __future__ import annotations

import importlib
from pathlib import Path  # noqa: TC003 — Typer needs Path at runtime
from typing import TYPE_CHECKING, Annotated, Any, cast

import typer

if TYPE_CHECKING:
    from collections.abc import Callable

    from autopilot.core.config import AutopilotConfig, DebuggingConfig

debug_app = typer.Typer(
    name="debug",
    help="Debugging agent tools and pipeline management.",
)


def _validate_plugin(cls: type) -> tuple[bool, str]:
    """Validate a plugin class for protocol compliance (wrapper for patching)."""
    from autopilot.debugging.loader import validate_plugin_class

    return validate_plugin_class(cls)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_debug_config() -> tuple[DebuggingConfig, Path, Path]:
    """Load debugging config from the current project.

    Returns:
        ``(debugging_config, project_root, config_path)``

    Raises:
        typer.Exit: If no ``.autopilot`` directory is found.
    """
    from autopilot.cli.display import console
    from autopilot.core.config import AutopilotConfig
    from autopilot.utils.paths import find_autopilot_dir

    ap_dir = find_autopilot_dir()
    if ap_dir is None:
        console.print("[error]No .autopilot directory found. Run 'autopilot init' first.[/error]")
        raise typer.Exit(code=1)

    project_root = ap_dir.parent
    config_path = ap_dir / "config.yaml"

    if config_path.exists():
        cfg = AutopilotConfig.from_yaml(config_path)
    else:
        from autopilot.core.config import ProjectConfig

        cfg = AutopilotConfig(project=ProjectConfig(name=project_root.name))

    return cfg.debugging, project_root, config_path


def _load_modify_save_config(
    config_path: Path,
    modifier: Callable[[dict[str, Any]], None],
) -> AutopilotConfig:
    """Load YAML config, apply modifier to the raw dict, validate, and save.

    Implements ADR-D05: load-modify-save pattern for config mutation.

    Args:
        config_path: Path to the project config.yaml.
        modifier: A callable that mutates the raw dict in-place.

    Returns:
        The validated ``AutopilotConfig`` after modification.
    """
    import yaml

    from autopilot.core.config import AutopilotConfig

    raw: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = cast("dict[str, Any]", loaded)

    modifier(raw)

    validated = AutopilotConfig.model_validate(raw)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(validated.model_dump(mode="json"), default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    return validated


# ---------------------------------------------------------------------------
# Task 011: Core operational commands (run, list-tools, status)
# ---------------------------------------------------------------------------


@debug_app.command("run")
def debug_run(
    task_file: Annotated[Path, typer.Argument(help="Path to debugging task YAML file.")],
    tool: str = typer.Option("", "--tool", "-t", help="Override the active debugging tool."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only; do not execute."),
) -> None:
    """Execute a debugging run against a task specification."""
    from autopilot.cli.display import console
    from autopilot.debugging.pipeline import load_debugging_task

    debug_cfg, _project_root, _config_path = _resolve_debug_config()

    if not task_file.exists():
        console.print(f"[error]Task file not found: {task_file}[/error]")
        raise typer.Exit(code=1)

    try:
        task = load_debugging_task(task_file)
    except ValueError as exc:
        console.print(f"[error]Invalid task file: {exc}[/error]")
        raise typer.Exit(code=1) from None

    active_tool = tool or debug_cfg.tool

    if dry_run:
        console.print(f"[info]Dry run: task '{task.task_id}' validated successfully.[/info]")
        console.print(f"  Tool: {active_tool}")
        console.print(f"  Steps: {len(task.steps)}")
        console.print(f"  Criteria: {len(task.acceptance_criteria)}")
        return

    from autopilot.debugging.loader import load_debugging_tool

    try:
        from autopilot.core.config import DebuggingConfig

        if tool:
            override_cfg = DebuggingConfig(
                enabled=True,
                tool=active_tool,
                tools=debug_cfg.tools,
            )
        else:
            override_cfg = debug_cfg

        debugging_tool = load_debugging_tool(override_cfg)
    except (ValueError, ImportError, TypeError) as exc:
        console.print(f"[error]Failed to load tool '{active_tool}': {exc}[/error]")
        raise typer.Exit(code=1) from None

    status = debugging_tool.check_provisioned()
    if not status.provisioned:
        console.print(
            f"[error]Tool '{active_tool}' is not provisioned. "
            f"Run 'autopilot debug provision {active_tool}' first.[/error]"
        )
        raise typer.Exit(code=1)

    console.print(
        f"[info]Running debugging task '{task.task_id}' with tool '{active_tool}'...[/info]"
    )


@debug_app.command("list-tools")
def debug_list_tools() -> None:
    """List registered debugging tools and their status."""
    from rich.table import Table

    from autopilot.cli.display import console

    debug_cfg, _project_root, _config_path = _resolve_debug_config()

    if not debug_cfg.tools:
        console.print("[info]No debugging tools configured.[/info]")
        return

    table = Table(title="Debugging Tools", width=80)
    table.add_column("Name", style="bold", width=16)
    table.add_column("Module.Class", ratio=2)
    table.add_column("Capabilities", ratio=2)
    table.add_column("Status", width=12)

    for name, tool_cfg in debug_cfg.tools.items():
        module_class = f"{tool_cfg.module}.{tool_cfg.class_name}"

        # Try loading tool to check status
        status_text = "[dim]unknown[/dim]"
        capabilities_text = ""
        try:
            from autopilot.core.config import DebuggingConfig

            single_cfg = DebuggingConfig(enabled=True, tool=name, tools={name: tool_cfg})

            from autopilot.debugging.loader import load_debugging_tool

            instance = load_debugging_tool(single_cfg)
            provision = instance.check_provisioned()
            if provision.provisioned and provision.ready:
                status_text = "[success]ready[/success]"
            elif provision.provisioned:
                status_text = "[warning]provisioned[/warning]"
            else:
                status_text = "[error]not provisioned[/error]"
            capabilities_text = ", ".join(sorted(instance.capabilities))
        except Exception:
            status_text = "[error]load error[/error]"

        active_marker = " *" if name == debug_cfg.tool else ""
        table.add_row(f"{name}{active_marker}", module_class, capabilities_text, status_text)

    console.print(table)
    console.print("\n[dim]* = active tool[/dim]")


@debug_app.command("status")
def debug_status() -> None:
    """Show debugging pipeline configuration and health."""
    from rich.panel import Panel

    from autopilot.cli.display import console

    debug_cfg, _project_root, _config_path = _resolve_debug_config()

    lines = [
        f"Enabled:          {debug_cfg.enabled}",
        f"Active tool:      {debug_cfg.tool}",
        f"Max iterations:   {debug_cfg.max_fix_iterations}",
        f"Timeout:          {debug_cfg.timeout_seconds}s",
        f"Test framework:   {debug_cfg.regression_test_framework}",
        f"UX review:        {debug_cfg.ux_review_enabled}",
        f"Registered tools: {len(debug_cfg.tools)}",
    ]

    console.print(Panel("\n".join(lines), title="Debugging Pipeline Status", width=60))


# ---------------------------------------------------------------------------
# Task 012: Plugin management commands
# ---------------------------------------------------------------------------


@debug_app.command("add-tool")
def debug_add_tool(
    name: Annotated[str, typer.Argument(help="Name for the debugging tool.")],
    module: str = typer.Option(..., "--module", "-m", help="Python module path."),
    class_name: str = typer.Option(..., "--class", "-c", help="Class name in the module."),
) -> None:
    """Register a new debugging tool plugin."""
    from autopilot.cli.display import console

    # Validate protocol compliance before writing config
    try:
        mod = importlib.import_module(module)
    except ImportError as exc:
        console.print(f"[error]Cannot import module '{module}': {exc}[/error]")
        raise typer.Exit(code=1) from None

    cls = getattr(mod, class_name, None)
    if cls is None:
        console.print(f"[error]Class '{class_name}' not found in module '{module}'.[/error]")
        raise typer.Exit(code=1)

    valid, msg = _validate_plugin(cls)
    if not valid:
        console.print(f"[error]Plugin validation failed: {msg}[/error]")
        raise typer.Exit(code=1)

    _debug_cfg, _project_root, config_path = _resolve_debug_config()

    def _add_tool(raw: dict[str, Any]) -> None:
        debugging: dict[str, Any] = raw.setdefault("debugging", {})
        tools: dict[str, Any] = debugging.setdefault("tools", {})
        tools[name] = {"module": module, "class": class_name}
        # Ensure project key exists for validation
        raw.setdefault("project", {"name": config_path.parent.parent.name})

    _load_modify_save_config(config_path, _add_tool)
    console.print(f"[success]Tool '{name}' registered successfully.[/success]")


@debug_app.command("remove-tool")
def debug_remove_tool(
    name: Annotated[str, typer.Argument(help="Name of the tool to remove.")],
) -> None:
    """Remove a debugging tool plugin from configuration."""
    from autopilot.cli.display import console

    debug_cfg, _project_root, config_path = _resolve_debug_config()

    if name not in debug_cfg.tools:
        console.print(f"[error]Tool '{name}' is not registered.[/error]")
        raise typer.Exit(code=1)

    if name == debug_cfg.tool:
        console.print(f"[warning]Warning: '{name}' is the active debugging tool.[/warning]")

    def _remove_tool(raw: dict[str, Any]) -> None:
        debugging: dict[str, Any] = raw.get("debugging", {})
        tools: dict[str, Any] = debugging.get("tools", {})
        tools.pop(name, None)
        raw.setdefault("project", {"name": config_path.parent.parent.name})

    _load_modify_save_config(config_path, _remove_tool)
    console.print(f"[success]Tool '{name}' removed.[/success]")


@debug_app.command("validate-tool")
def debug_validate_tool(
    name: Annotated[str, typer.Argument(help="Name of the tool to validate.")],
) -> None:
    """Validate a debugging tool plugin for protocol compliance."""
    from autopilot.cli.display import console

    debug_cfg, _project_root, _config_path = _resolve_debug_config()

    if name not in debug_cfg.tools:
        console.print(f"[error]Tool '{name}' is not registered.[/error]")
        raise typer.Exit(code=1)

    tool_cfg = debug_cfg.tools[name]

    try:
        mod = importlib.import_module(tool_cfg.module)
    except ImportError as exc:
        console.print(f"[error]Cannot import module '{tool_cfg.module}': {exc}[/error]")
        raise typer.Exit(code=1) from None

    cls = getattr(mod, tool_cfg.class_name, None)
    if cls is None:
        console.print(
            f"[error]Class '{tool_cfg.class_name}' not found in '{tool_cfg.module}'.[/error]"
        )
        raise typer.Exit(code=1)

    valid, msg = _validate_plugin(cls)
    if valid:
        console.print(f"[success]Tool '{name}' is valid: {msg}[/success]")
    else:
        console.print(f"[error]Tool '{name}' is invalid: {msg}[/error]")
        raise typer.Exit(code=1)


@debug_app.command("provision")
def debug_provision(
    name: Annotated[str, typer.Argument(help="Name of the tool to provision.")],
) -> None:
    """Provision a debugging tool's environment."""
    from autopilot.cli.display import console
    from autopilot.debugging.loader import load_debugging_tool

    debug_cfg, _project_root, _config_path = _resolve_debug_config()

    if name not in debug_cfg.tools:
        console.print(f"[error]Tool '{name}' is not registered.[/error]")
        raise typer.Exit(code=1)

    tool_cfg = debug_cfg.tools[name]

    try:
        from autopilot.core.config import DebuggingConfig

        single_cfg = DebuggingConfig(enabled=True, tool=name, tools={name: tool_cfg})
        instance = load_debugging_tool(single_cfg)
    except (ValueError, ImportError, TypeError) as exc:
        console.print(f"[error]Failed to load tool '{name}': {exc}[/error]")
        raise typer.Exit(code=1) from None

    result = instance.provision(dict(tool_cfg.settings))

    if result.success:
        console.print(f"[success]Tool '{name}' provisioned successfully.[/success]")
        if result.components_installed:
            for comp in result.components_installed:
                console.print(f"  Installed: {comp}")
        if result.manual_steps:
            console.print("\n[warning]Manual steps required:[/warning]")
            for step in result.manual_steps:
                console.print(f"  - {step}")
    else:
        console.print(f"[error]Provisioning failed: {result.error}[/error]")
        raise typer.Exit(code=1)


@debug_app.command("deprovision")
def debug_deprovision(
    name: Annotated[str, typer.Argument(help="Name of the tool to deprovision.")],
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
) -> None:
    """Deprovision a debugging tool's environment."""
    from autopilot.cli.display import console
    from autopilot.debugging.loader import load_debugging_tool

    debug_cfg, _project_root, _config_path = _resolve_debug_config()

    if name not in debug_cfg.tools:
        console.print(f"[error]Tool '{name}' is not registered.[/error]")
        raise typer.Exit(code=1)

    if not force:
        confirm = typer.confirm(f"Deprovision tool '{name}'?")
        if not confirm:
            console.print("[info]Cancelled.[/info]")
            raise typer.Exit()

    tool_cfg = debug_cfg.tools[name]

    try:
        from autopilot.core.config import DebuggingConfig

        single_cfg = DebuggingConfig(enabled=True, tool=name, tools={name: tool_cfg})
        instance = load_debugging_tool(single_cfg)
    except (ValueError, ImportError, TypeError) as exc:
        console.print(f"[error]Failed to load tool '{name}': {exc}[/error]")
        raise typer.Exit(code=1) from None

    instance.deprovision()
    console.print(f"[success]Tool '{name}' deprovisioned.[/success]")
