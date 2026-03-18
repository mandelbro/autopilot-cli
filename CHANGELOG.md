# Changelog

## [1.1.1](https://github.com/mandelbro/autopilot-cli/compare/v1.1.0...v1.1.1) (2026-03-18)


### Bug Fixes

* **build:** Exclude .claude/ from sdist to prevent symlink build failure ([c079822](https://github.com/mandelbro/autopilot-cli/commit/c0798228f61bca4315d8b9455b11a2dd9559b302))

## [1.1.0](https://github.com/mandelbro/autopilot-cli/compare/v1.0.0...v1.1.0) (2026-03-18)


### Features

* Add project discover/register for external task projects ([#55](https://github.com/mandelbro/autopilot-cli/issues/55)) ([a8c223f](https://github.com/mandelbro/autopilot-cli/commit/a8c223fd347eaecb2f051b9f8c937db19768de74))


### Bug Fixes

* **ci:** Fix publish job skipped on workflow_dispatch ([cee02e6](https://github.com/mandelbro/autopilot-cli/commit/cee02e6f282db7cfb3b166b471383d5b58bcc7b0))
* **ci:** Update action SHAs to latest releases, force Node 24 ([dc29f57](https://github.com/mandelbro/autopilot-cli/commit/dc29f57eec0591bf9f132788ed74838191334b3c))
* Move templates into package source tree for editable install compat ([4ebe50d](https://github.com/mandelbro/autopilot-cli/commit/4ebe50da78e2b1ef278f38cac4d4f3a49224f181))


### Documentation

* Add local development run instructions to README ([b46ebc7](https://github.com/mandelbro/autopilot-cli/commit/b46ebc7e4c52869207ef7ee61de8b2dbe33fc40e))

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
