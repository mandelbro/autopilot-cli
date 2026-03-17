# Changelog

## [1.0.0](https://github.com/mandelbro/autopilot-cli/releases/tag/v1.0.0) (2026-03-17)

### Features

* **cli**: Typer + Rich CLI with interactive REPL, subcommand groups (task, session, enforce, hive, project, config, report)
* **core**: Pydantic v2 configuration with three-level YAML merge (global, project, CLI), frozen models
* **enforcement**: 11-category anti-pattern detection engine across 5 enforcement layers
* **orchestration**: Scheduler with interval/event/hybrid strategies, daemon-based sessions, circuit breaker, usage tracking
* **hive-mind**: Hive-mind orchestration with Jinja2 objective templates, `spawn_hive`/`stop_hive` lifecycle, resource broker and session manager integration
* **coordination**: Document-mediated agent communication via markdown board files
* **monitoring**: Deployment health checking with Render integration
* **uat**: User acceptance testing pipeline with spec indexing, test generation, and traceability matrix
* **reporting**: Cycle reports, velocity metrics, daily summaries, decision logs
* **debugging**: Debugging tool protocol with plugin architecture and BrowserMCP integration
