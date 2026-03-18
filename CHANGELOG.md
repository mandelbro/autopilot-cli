# Changelog

## [1.1.0](https://github.com/mandelbro/autopilot-cli/compare/v1.0.0...v1.1.0) (2026-03-18)


### Features

* Add debugging agent discovery and plugin architecture documentation ([40b091a](https://github.com/mandelbro/autopilot-cli/commit/40b091ad60e7370cef4c546645c56ef173911cf7))
* AgentInvoker cwd validation + stale workspace detection — Tasks 100, 103 ([#43](https://github.com/mandelbro/autopilot-cli/issues/43)) ([b98f5ef](https://github.com/mandelbro/autopilot-cli/commit/b98f5ef86a427708f84ad1d76cbc7f9d8c700bee))
* Coordination module — Tasks 017-020 ([#10](https://github.com/mandelbro/autopilot-cli/issues/10)) ([cdf557d](https://github.com/mandelbro/autopilot-cli/commit/cdf557dc90466b1e0faf0090173135e647da2797))
* Daemon and hive-mind integration — Tasks 036, 037 ([#19](https://github.com/mandelbro/autopilot-cli/issues/19)) ([3411f64](https://github.com/mandelbro/autopilot-cli/commit/3411f643214bfa52c9ac7ca42a8be9d28a5fdad2))
* Dashboard and CLI convenience commands — Tasks 044, 045 ([#22](https://github.com/mandelbro/autopilot-cli/issues/22)) ([b7f4988](https://github.com/mandelbro/autopilot-cli/commit/b7f498802d6a18154d6047c5fbd8bfd9a4bb6c5a))
* Data layer — Tasks 034, 038, 040 ([#17](https://github.com/mandelbro/autopilot-cli/issues/17)) ([5281d4b](https://github.com/mandelbro/autopilot-cli/commit/5281d4b7607d3cee34c8caab57d33071807d1f22))
* **debugging:** BrowserMCPTool plugin + tests — Tasks 008-010b ([#47](https://github.com/mandelbro/autopilot-cli/issues/47)) ([f315a87](https://github.com/mandelbro/autopilot-cli/commit/f315a877215b0c8d4772f59d38c5cfea07f64fea))
* **debugging:** CLI debug commands + tests — Tasks 011-013 ([#50](https://github.com/mandelbro/autopilot-cli/issues/50)) ([982b83c](https://github.com/mandelbro/autopilot-cli/commit/982b83c084a54958705589374f91ee5345dd09f8))
* **debugging:** DebuggingTool protocol, models, config, pipeline — Tasks 001-005 ([#45](https://github.com/mandelbro/autopilot-cli/issues/45)) ([f294efb](https://github.com/mandelbro/autopilot-cli/commit/f294efb67f6876126d293f4bb7130d61f7c68410))
* **debugging:** Desktop Agent plugin, orchestration hooks, and docs — Tasks 015-019 ([#51](https://github.com/mandelbro/autopilot-cli/issues/51)) ([89255da](https://github.com/mandelbro/autopilot-cli/commit/89255da0b5837f8090d123e9a370c4b45ee5d35e))
* **debugging:** Plugin loader + tests — Tasks 006-007 ([#46](https://github.com/mandelbro/autopilot-cli/issues/46)) ([e97b974](https://github.com/mandelbro/autopilot-cli/commit/e97b97498ab32beffd54e8db8666582d5b63dfb9))
* DevOps Agent and deployment monitoring — Tasks 051-055 ([#24](https://github.com/mandelbro/autopilot-cli/issues/24)) ([4d6717f](https://github.com/mandelbro/autopilot-cli/commit/4d6717ffa10fd1f205ac0a3b0a9773797ff8255d))
* Discovery pipeline and estimation agent — Tasks 079-080 ([#32](https://github.com/mandelbro/autopilot-cli/issues/32)) ([34e13a1](https://github.com/mandelbro/autopilot-cli/commit/34e13a1e2f813d6b95a8afcb31422f159f570183))
* Enforcement engine and all 11 rule categories — Tasks 056-060 ([#25](https://github.com/mandelbro/autopilot-cli/issues/25)) ([2a319ef](https://github.com/mandelbro/autopilot-cli/commit/2a319ef662746bd74f22e58e27f1243dfe180469))
* Enforcement layers 2-5 — Tasks 061-064 ([#26](https://github.com/mandelbro/autopilot-cli/issues/26)) ([36be462](https://github.com/mandelbro/autopilot-cli/commit/36be462c40e2ca2e724859397a9c3fb2aba313e4))
* Enforcement support and CLI — Tasks 065-067 ([#27](https://github.com/mandelbro/autopilot-cli/issues/27)) ([37a9b93](https://github.com/mandelbro/autopilot-cli/commit/37a9b93b98123cbe2e400022e1ea36f1be0c748c))
* Event-driven triggers, workflow hooks — Tasks 087-088 ([#35](https://github.com/mandelbro/autopilot-cli/issues/35)) ([b72f0fb](https://github.com/mandelbro/autopilot-cli/commit/b72f0fbdd866e5f833ffa23d928fddc225ae273a))
* Foundation tasks 001-003 — package, config, data models ([#1](https://github.com/mandelbro/autopilot-cli/issues/1)) ([f27217d](https://github.com/mandelbro/autopilot-cli/commit/f27217d1352cce8b63ab7ab3c3d5503dd3737c12))
* **hive-mind:** Config, models, and objective template system — Tasks 001-007 ([#48](https://github.com/mandelbro/autopilot-cli/issues/48)) ([bcc0297](https://github.com/mandelbro/autopilot-cli/commit/bcc029731f7689682db893029db5d483d03121fc))
* **hive-mind:** HiveMindManager evolution, CLI commands, integration wiring — Tasks 008-013 ([#49](https://github.com/mandelbro/autopilot-cli/issues/49)) ([7f1eaf8](https://github.com/mandelbro/autopilot-cli/commit/7f1eaf8521aa46989520fec9c4172e1630ad57a5))
* Norwood discovery template and discover CLI commands — Tasks 077-078 ([#31](https://github.com/mandelbro/autopilot-cli/issues/31)) ([7f1801b](https://github.com/mandelbro/autopilot-cli/commit/7f1801b93d01bd250d6218f2c4cc0d7e65d51632))
* Orchestration primitives — Tasks 031, 032, 033 ([#16](https://github.com/mandelbro/autopilot-cli/issues/16)) ([d2c4b7d](https://github.com/mandelbro/autopilot-cli/commit/d2c4b7d43d24600c658738d209f28f55c3b6cb49))
* REPL skeleton with context management — Tasks 013-014 ([#11](https://github.com/mandelbro/autopilot-cli/issues/11)) ([1603f0d](https://github.com/mandelbro/autopilot-cli/commit/1603f0d2ad46390d00d4ac52b8de91dd6a0a31fe))
* Reporting modules — Tasks 041, 042, 043 ([#21](https://github.com/mandelbro/autopilot-cli/issues/21)) ([051cbd2](https://github.com/mandelbro/autopilot-cli/commit/051cbd2f10e0e83eb5a4ef1ccab89e81950f1fc9))
* Resource broker, usage limits, quality reporting — Tasks 084-086 ([#34](https://github.com/mandelbro/autopilot-cli/issues/34)) ([feb1044](https://github.com/mandelbro/autopilot-cli/commit/feb1044f47bddc0ae6536af94e1e1006ae761787))
* Scheduler core — cycle orchestration — Task 035 ([#18](https://github.com/mandelbro/autopilot-cli/issues/18)) ([9e6633f](https://github.com/mandelbro/autopilot-cli/commit/9e6633f08fd47af067a4f63ef546263f4b979ce5))
* Scheduler workspace integration — Task 099 ([#42](https://github.com/mandelbro/autopilot-cli/issues/42)) ([f29bef4](https://github.com/mandelbro/autopilot-cli/commit/f29bef4a39e5ca8429836f3361785cc170ef4546))
* Session CLI commands — Task 039 ([#20](https://github.com/mandelbro/autopilot-cli/issues/20)) ([557d9ef](https://github.com/mandelbro/autopilot-cli/commit/557d9efdb50eb57a13e9cc5f614d354dcdb15c90))
* Sprint CLI, UAT context loader, spec engine — Tasks 026, 029, 030 ([#15](https://github.com/mandelbro/autopilot-cli/issues/15)) ([2b4fac7](https://github.com/mandelbro/autopilot-cli/commit/2b4fac7a7eaf990c62e1360c6cd9b13259955449))
* Sprint planning, discovery pipeline, estimation — Tasks 024, 025, 027 ([#14](https://github.com/mandelbro/autopilot-cli/issues/14)) ([eacc6c7](https://github.com/mandelbro/autopilot-cli/commit/eacc6c799f0faaf8dadebea7e926623a63976b5c))
* Strict pyright, pydantic-settings — Tasks 092, 094 ([#39](https://github.com/mandelbro/autopilot-cli/issues/39)) ([6035698](https://github.com/mandelbro/autopilot-cli/commit/60356980062ab0002ce2474997d4720f79f404c7))
* Structured logging, pre-commit hooks — Tasks 091, 093 ([#37](https://github.com/mandelbro/autopilot-cli/issues/37)) ([4c5fb91](https://github.com/mandelbro/autopilot-cli/commit/4c5fb916cf8cfe9aa3298978377f4dc6dfe1af37))
* Task 010 — Project initialization ([#5](https://github.com/mandelbro/autopilot-cli/issues/5)) ([d53829f](https://github.com/mandelbro/autopilot-cli/commit/d53829f69e9df9228a13153188039c24e68a05c4))
* Task create and list CLI commands — Tasks 022, 023 ([#13](https://github.com/mandelbro/autopilot-cli/issues/13)) ([ba98b63](https://github.com/mandelbro/autopilot-cli/commit/ba98b63aef4cde32c0b10837a96e38e73530eede))
* Task parser and UAT skill directory — Tasks 021, 028 ([#12](https://github.com/mandelbro/autopilot-cli/issues/12)) ([1e07e79](https://github.com/mandelbro/autopilot-cli/commit/1e07e79ae12bf48b3737a4407dd2987e4e590cb1))
* Tasks 004-005 — shared utilities ([#2](https://github.com/mandelbro/autopilot-cli/issues/2)) ([28c9bcb](https://github.com/mandelbro/autopilot-cli/commit/28c9bcb294eb36301b05b476a7c4b7fea83327dc))
* Tasks 006-007 — SQLite database and Python templates ([#3](https://github.com/mandelbro/autopilot-cli/issues/3)) ([3dffc1e](https://github.com/mandelbro/autopilot-cli/commit/3dffc1eb188e78512f42f2767172688ba136eb96))
* Tasks 008-009 — CLI skeleton and Rich display ([#4](https://github.com/mandelbro/autopilot-cli/issues/4)) ([94d2434](https://github.com/mandelbro/autopilot-cli/commit/94d2434c68d71f8028cd6775c46f7ff6e713e97e))
* Tasks 011-012 — Project registry and CLI commands ([#8](https://github.com/mandelbro/autopilot-cli/issues/8)) ([0d0b915](https://github.com/mandelbro/autopilot-cli/commit/0d0b915d52ff8064ef6ef01cd936456e93d66a18))
* Tasks 015-016 — Agent registry and template renderer ([#9](https://github.com/mandelbro/autopilot-cli/issues/9)) ([779e330](https://github.com/mandelbro/autopilot-cli/commit/779e330da83010b423e1ddfda722ae7e032c8954))
* TypeScript template, migration engine, shell completions — Tasks 081-083 ([#33](https://github.com/mandelbro/autopilot-cli/issues/33)) ([f2f3b56](https://github.com/mandelbro/autopilot-cli/commit/f2f3b56af2f6b493c7ec26fa2f4458af179cf643))
* UAT batch execution, triggers, and feedback loop — Tasks 074-076 ([#30](https://github.com/mandelbro/autopilot-cli/issues/30)) ([9c9c521](https://github.com/mandelbro/autopilot-cli/commit/9c9c52116d33e76463d8548d0656e798ee509d01))
* UAT framework — Tasks 046, 047, 048, 049, 050 ([#23](https://github.com/mandelbro/autopilot-cli/issues/23)) ([086bb6d](https://github.com/mandelbro/autopilot-cli/commit/086bb6d0248d4cc461e5ed876adf9f157f959ebc))
* UAT memory integration, optimization engine — Tasks 089-090 ([#36](https://github.com/mandelbro/autopilot-cli/issues/36)) ([68d005c](https://github.com/mandelbro/autopilot-cli/commit/68d005c69bb1fa1df87bf46b9cb51181ff3d2fc6))
* UAT Phase 2 spec coverage — Tasks 068-070 ([#28](https://github.com/mandelbro/autopilot-cli/issues/28)) ([75d177a](https://github.com/mandelbro/autopilot-cli/commit/75d177a7881bcca65bf11cd2c15fc1121c26417a))
* UAT test generators (behavioral, compliance, UX) — Tasks 071-073 ([#29](https://github.com/mandelbro/autopilot-cli/issues/29)) ([73e0cdb](https://github.com/mandelbro/autopilot-cli/commit/73e0cdb23cfbe4548b0430fc780674f1a372375b))
* Workspace isolation foundations — Tasks 095, 096, 098 ([#40](https://github.com/mandelbro/autopilot-cli/issues/40)) ([43b913c](https://github.com/mandelbro/autopilot-cli/commit/43b913cde42fba60c97c3b1d5d9e518b4521f542))
* Workspace lifecycle, CLI commands, and init wiring — Tasks 101, 102, 104 ([#44](https://github.com/mandelbro/autopilot-cli/issues/44)) ([63882fe](https://github.com/mandelbro/autopilot-cli/commit/63882fe07772e9f577e5bc19c6ab6e476a265984))
* WorkspaceManager core class — Task 097 ([#41](https://github.com/mandelbro/autopilot-cli/issues/41)) ([5cdff8c](https://github.com/mandelbro/autopilot-cli/commit/5cdff8c16ff015ac11ea0498192bb2316a422304))


### Bug Fixes

* Address PR review feedback items 2-9 ([#7](https://github.com/mandelbro/autopilot-cli/issues/7)) ([4ecd45b](https://github.com/mandelbro/autopilot-cli/commit/4ecd45b028a7d577ddc871587cec557b088443ea))


### Documentation

* **discovery:** Introduce Hive-Mind Orchestration Integration ([d6e929c](https://github.com/mandelbro/autopilot-cli/commit/d6e929c677776f1e46e1e60931dce0b449632eb6))
* Plan for workspace isolation with WorkspaceManager — ADR-011 and related tasks ([dd3b10d](https://github.com/mandelbro/autopilot-cli/commit/dd3b10d62b19d2d38810257f707ccf778641187d))
* Updates product ideation docs ([2a6156d](https://github.com/mandelbro/autopilot-cli/commit/2a6156d800f3975b855c8db522a7bda991f9d087))

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
