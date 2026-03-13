## Summary (tasks-6.md)

- **Tasks in this file**: 10
- **Task IDs**: 051 - 060
- **Total Points**: 41

### Main Phase 4: DevOps Agent + Phase 5: Enforcement Engine Start

---

## Tasks

### Task ID: 051

- **Title**: DevOps Agent system prompt
- **File**: templates/python/agents/devops-agent.md
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a PL agent, I want a DevOps Agent that monitors deployment health, so that deploy failures are detected and routed to remediation within one cycle.
- **Outcome (what this delivers)**: DA system prompt template with three workflows: check_deploys (every cycle), verify_deploy (after merges), investigate_failure (on failure detection).

#### Prompt:

```markdown
**Objective:** Create the DevOps Agent system prompt with monitoring workflows.

**File to Create/Modify:** `templates/python/agents/devops-agent.md`

**Specification References:**
- Discovery Phase 4: DA system prompt with monitoring workflows
- Discovery: DevOps Agent monitoring section
- Discovery: Agent Orchestration Strategy (DA in dispatch flow)

**Prerequisite Requirements:**
1. Task 007 must be complete (template structure)
2. Review existing RepEngine agent prompts for style consistency

**Detailed Instructions:**
1. Write DA system prompt with three workflows:
   - `check_deploys`: Read Render deploy statuses, curl health endpoints, write status to board
   - `verify_deploy`: After PR merge, verify feature is live on staging
   - `investigate_failure`: Correlate failed deploy with recent commits, classify failure type, route remediation
2. Include: tool usage (gh, curl, git log), output format, board section update instructions
3. Use sonnet model (cheaper/faster), 30 max turns, 900s timeout
4. Failure classification: git_auth_expired -> human escalation, broken_imports/missing_deps/crash_loop -> EM dispatch

**Acceptance Criteria:**
- [ ] DA prompt covers all three workflows
- [ ] Failure classification routes correctly
- [ ] Board section update format is specified
- [ ] Prompt is project-agnostic (template variables for service config)
```

---

### Task ID: 052

- **Title**: Render service registry in config model
- **File**: src/autopilot/core/config.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a system operator, I want to configure monitored services in the project config, so that the DA knows which services to check and where their health endpoints are.
- **Outcome (what this delivers)**: RenderServiceConfig and DeploymentMonitoringConfig Pydantic models added to the project config.

#### Prompt:

```markdown
**Objective:** Add deployment monitoring configuration to the config model.

**File to Create/Modify:** `src/autopilot/core/config.py`

**Specification References:**
- Discovery: Render services config section (service IDs, health endpoints, staging URLs)
- Discovery: Deployment monitoring config (check frequency, failure patterns, GitHub issues)

**Prerequisite Requirements:**
1. Task 002 must be complete (config model)
2. Update tests in `tests/core/test_config.py`

**Detailed Instructions:**
1. Add `RenderServiceConfig`: id, name, health_endpoints (list[str]), staging_url
2. Add `DeploymentMonitoringConfig`: enabled, check_frequency (every_cycle/every_nth_cycle/manual_only), health_check_timeout_seconds, failure_patterns (dict mapping pattern to remediation), github_issues config
3. Add `render_services: dict[str, RenderServiceConfig]` to AutopilotConfig
4. Add `deployment_monitoring: DeploymentMonitoringConfig` to AutopilotConfig
5. Update YAML template with monitoring section

**Acceptance Criteria:**
- [ ] Config models validate service registry entries
- [ ] Failure pattern mapping is configurable
- [ ] YAML round-trip preserves monitoring config
- [ ] All tests pass
```

---

### Task ID: 053

- **Title**: Health checker and deploy status writer
- **File**: src/autopilot/monitoring/health_checker.py, src/autopilot/monitoring/deploy_status.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a DA agent, I want to check service health endpoints and write deployment status to the project board, so that the PL can gate feature verification on deployment health.
- **Outcome (what this delivers)**: HTTP health endpoint checker and board section writer for deployment status.

#### Prompt:

```markdown
**Objective:** Implement deployment health checking and status board writing.

**File to Create/Modify:**
- `src/autopilot/monitoring/health_checker.py`
- `src/autopilot/monitoring/deploy_status.py`

**Specification References:**
- Discovery: Deployment health monitoring (health checker, deploy status board section)
- Discovery: Render service registry

**Prerequisite Requirements:**
1. Tasks 002, 017, 052 must be complete (config, board, monitoring config)
2. Write tests in `tests/monitoring/test_health_checker.py`, `tests/monitoring/test_deploy_status.py`

**Detailed Instructions:**
1. `health_checker.py`: Implement `HealthChecker`:
   - `check_service(service: RenderServiceConfig) -> HealthCheckResult`
   - HTTP GET to each health endpoint with configurable timeout
   - Result: service_name, endpoint, status_code, response_time, healthy (bool), error
   - `check_all(services: dict) -> list[HealthCheckResult]`
2. `deploy_status.py`: Implement `DeployStatusWriter`:
   - `update_board(board_path: Path, results: list[HealthCheckResult])`
   - Write "Deployment Status" section to project-board.md
   - Table format: Service | Status | Last Check | Health Endpoints | Notes
   - PL reads this section to decide whether to dispatch PD for verification

**Acceptance Criteria:**
- [ ] Health checker calls endpoints with timeout
- [ ] Unhealthy services are correctly identified
- [ ] Board section is written with status table
- [ ] PL can read deployment status from board
- [ ] All tests pass with mocked HTTP responses
```

---

### Task ID: 054

- **Title**: Failure pattern catalog and remediation routing
- **File**: src/autopilot/monitoring/failure_patterns.py
- **Complete**: [x]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a DA agent, I want to classify deployment failures and route them to appropriate remediation, so that code issues trigger EM fixes and infrastructure issues trigger human escalation.
- **Outcome (what this delivers)**: Failure pattern classifier mapping known failure types to remediation actions (EM dispatch vs human escalation).

#### Prompt:

```markdown
**Objective:** Implement failure pattern classification and remediation routing.

**File to Create/Modify:** `src/autopilot/monitoring/failure_patterns.py`

**Specification References:**
- Discovery Phase 4: Known failure pattern catalog
- Discovery: Failure pattern -> remediation mapping (git_auth -> human, broken_imports -> EM)

**Prerequisite Requirements:**
1. Tasks 003, 052 must be complete (models, monitoring config)
2. Write tests in `tests/monitoring/test_failure_patterns.py`

**Detailed Instructions:**
1. Implement `FailureClassifier`:
   - `classify(error_output: str) -> FailureClassification`
   - Known patterns: git_auth_expired, broken_imports, missing_dependency, crash_loop
   - Each pattern has: regex_patterns, classification, remediation_action, severity
2. Remediation routing:
   - `route_remediation(classification) -> RemediationAction`
   - Actions: em_dispatch (code fix), human_escalation (infra issue), da_retry (transient)
3. Support custom patterns from config.deployment_monitoring.failure_patterns
4. `FailureClassification`: pattern_name, matched_text, remediation, confidence

**Acceptance Criteria:**
- [ ] Known failure patterns are correctly classified
- [ ] Remediation routing maps to correct actions
- [ ] Custom patterns from config are loaded
- [ ] Unknown failures default to human escalation
- [ ] All tests pass
```

---

### Task ID: 055

- **Title**: GitHub issue creation for deploy failures
- **File**: src/autopilot/monitoring/render_registry.py
- **Complete**: [x]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a system operator, I want automated GitHub issues for deploy failures, so that infrastructure problems are tracked with full diagnostic context.
- **Outcome (what this delivers)**: GitHub issue creator that posts structured deploy failure diagnostics with labels, commit correlation, and remediation recommendations.

#### Prompt:

```markdown
**Objective:** Implement GitHub issue creation for deployment failures.

**File to Create/Modify:** `src/autopilot/monitoring/render_registry.py`

**Specification References:**
- Discovery Phase 4: GitHub issue creation for deploy failures
- Discovery: DA writes deploy status to board, creates GitHub issues

**Prerequisite Requirements:**
1. Tasks 005, 054 must be complete (git utils, failure patterns)
2. Write tests in `tests/monitoring/test_render_registry.py`

**Detailed Instructions:**
1. Implement `GitHubIssueCreator`:
   - `create_deploy_failure_issue(failure: FailureClassification, service: str, context: dict) -> str`
   - Uses `gh issue create` subprocess
   - Issue body includes: service name, failure type, error output, recent commits (git log), deploy timestamp, remediation suggestion
   - Labels from config: ["deploy-failure", "autopilot"]
2. Only create issues when config.deployment_monitoring.github_issues.create_on_failure is True
3. Deduplication: check for existing open issue with same failure pattern before creating new one

**Acceptance Criteria:**
- [ ] Issues are created via gh CLI with correct content
- [ ] Duplicate issues are detected and avoided
- [ ] Issue content includes diagnostic context
- [ ] Config controls issue creation
- [ ] All tests pass with mocked gh calls
```

---

### Task ID: 056

- **Title**: Enforcement engine orchestrator
- **File**: src/autopilot/enforcement/engine.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a technical architect, I want a unified enforcement engine, so that all 5 enforcement layers are coordinated from a single interface for setup, checking, and reporting.
- **Outcome (what this delivers)**: Enforcement engine orchestrator that coordinates setup, check, and report operations across all 5 enforcement layers.

#### Prompt:

```markdown
**Objective:** Implement the enforcement engine orchestrator per RFC Section 3.5.

**File to Create/Modify:** `src/autopilot/enforcement/engine.py`

**Specification References:**
- RFC Section 3.5: Anti-Pattern Enforcement Engine
- RFC Section 3.5.3: Integration with autonomous pipeline (5 integration points)
- Discovery: EnforcementEngine class (setup, check, report methods)

**Prerequisite Requirements:**
1. Tasks 002, 003 must be complete (config, models)
2. Write tests in `tests/enforcement/test_engine.py`

**Detailed Instructions:**
1. Implement `EnforcementEngine` class per Discovery specification:
   - `setup(project: ProjectConfig) -> SetupResult` configures all layers
   - `check(project_root: Path) -> CheckResult` runs all rule checks
   - `report(project_id: str) -> EnforcementReport` generates trend analysis
   - `build_quality_gate_prompt() -> str` generates quality gate instructions
2. Load rules dynamically from enforcement/rules/ and custom rules from .autopilot/enforcement/rules/
3. `EnforcementRule` protocol: category, severity, name, check(), fix()
4. Coordinate layers: editor config, pre-commit, CI, guardrails, protected regions
5. Metrics collection to SQLite after each check run

**Acceptance Criteria:**
- [ ] Engine coordinates all 5 layers
- [ ] Rules load dynamically from package and project
- [ ] Check returns categorized violations
- [ ] Quality gate prompt generation works
- [ ] Metrics are stored in SQLite
- [ ] All tests pass
```

---

### Task ID: 057

- **Title**: Enforcement rules -- base protocol and Categories 1-3
- **File**: src/autopilot/enforcement/rules/base.py, rules/duplication.py, rules/conventions.py, rules/overengineering.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a code quality enforcer, I want rules for infrastructure duplication, convention violations, and over-engineering, so that the three most common AI anti-patterns are automatically detected.
- **Outcome (what this delivers)**: EnforcementRule protocol definition and implementations for Categories 1 (Infrastructure Duplication, 80-90%), 2 (Ignored Conventions, 90-100%), 3 (Over-engineering, 80-90%).

#### Prompt:

```markdown
**Objective:** Define the rule protocol and implement the first 3 enforcement categories.

**File to Create/Modify:**
- `src/autopilot/enforcement/rules/base.py`
- `src/autopilot/enforcement/rules/duplication.py`
- `src/autopilot/enforcement/rules/conventions.py`
- `src/autopilot/enforcement/rules/overengineering.py`

**Specification References:**
- RFC Section 3.5.1: Categories 1-3 with AI prevalence rates
- RFC Section 3.5.4: EnforcementRule protocol
- Discovery: Custom Enforcement Rules (Protocol class)

**Prerequisite Requirements:**
1. Task 003 must be complete (models with Violation, Fix)
2. Write tests in `tests/enforcement/rules/test_categories_1_3.py`

**Detailed Instructions:**
1. `base.py`: Define `EnforcementRule` Protocol per RFC 3.5.4
2. `duplication.py` (Cat 1): Detect infrastructure duplication via ruff TID251 analysis, semgrep patterns. Check for duplicated utility functions, repeated config patterns
3. `conventions.py` (Cat 2): Check naming conventions via ruff I/N rules, file organization, import ordering
4. `overengineering.py` (Cat 3): Check cyclomatic complexity via ruff C901, unnecessary abstractions via SIM rules
5. Each rule implements check() returning list[Violation] and optional fix()

**Acceptance Criteria:**
- [ ] EnforcementRule protocol is defined with check/fix methods
- [ ] Category 1 detects common duplication patterns
- [ ] Category 2 checks naming and import conventions
- [ ] Category 3 flags overly complex code
- [ ] All rules return properly structured Violations
- [ ] All tests pass
```

---

### Task ID: 058

- **Title**: Enforcement rules Categories 4-7
- **File**: src/autopilot/enforcement/rules/security.py, error_handling.py, dead_code.py, type_safety.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a code quality enforcer, I want rules for security, error handling, dead code, and type safety, so that critical vulnerability patterns and code hygiene issues are caught automatically.
- **Outcome (what this delivers)**: Rule implementations for Categories 4 (Security, 36-62%), 5 (Error Handling, ~2x human), 6 (Dead Code), 7 (Type Safety).

#### Prompt:

```markdown
**Objective:** Implement enforcement rules for Categories 4-7.

**File to Create/Modify:**
- `src/autopilot/enforcement/rules/security.py`
- `src/autopilot/enforcement/rules/error_handling.py`
- `src/autopilot/enforcement/rules/dead_code.py`
- `src/autopilot/enforcement/rules/type_safety.py`

**Specification References:**
- RFC Section 3.5.1: Categories 4-7 with detection methods
- RFC Section 7.1: Security (detect-secrets, credential scanning)

**Prerequisite Requirements:**
1. Task 057 must be complete (base protocol)
2. Write tests in `tests/enforcement/rules/test_categories_4_7.py`

**Detailed Instructions:**
1. `security.py` (Cat 4): Check for hardcoded secrets (ruff S rules), credential patterns, unsafe subprocess usage
2. `error_handling.py` (Cat 5): Check for bare except, swallowed errors (ruff BLE/TRY), missing error types
3. `dead_code.py` (Cat 6): Detect unused imports (F401), unused variables (F841), commented code (ERA001)
4. `type_safety.py` (Cat 7): Check for Any abuse (ANN401), missing type annotations, unsafe casts
5. Each uses ruff output parsing where possible for consistency

**Acceptance Criteria:**
- [ ] Security rules detect common credential patterns
- [ ] Error handling rules flag bare except and swallowed errors
- [ ] Dead code rules find unused imports and variables
- [ ] Type safety rules check annotation completeness
- [ ] All tests pass
```

---

### Task ID: 059

- **Title**: Enforcement rules Categories 8-11
- **File**: src/autopilot/enforcement/rules/test_quality.py, comments.py, deprecated.py, async_misuse.py
- **Complete**: [ ]
- **Sprint Points**: 5

- **User Story (business-facing)**: As a code quality enforcer, I want rules for test anti-patterns, excessive comments, deprecated APIs, and async misuse, so that all 11 anti-pattern categories are covered.
- **Outcome (what this delivers)**: Rule implementations for Categories 8 (Test Anti-Patterns, 40-70%), 9 (Excessive Comments, 90-100%), 10 (Deprecated APIs), 11 (Async Misuse, 2x human).

#### Prompt:

```markdown
**Objective:** Implement enforcement rules for Categories 8-11.

**File to Create/Modify:**
- `src/autopilot/enforcement/rules/test_quality.py`
- `src/autopilot/enforcement/rules/comments.py`
- `src/autopilot/enforcement/rules/deprecated.py`
- `src/autopilot/enforcement/rules/async_misuse.py`

**Specification References:**
- RFC Section 3.5.1: Categories 8-11 with detection methods

**Prerequisite Requirements:**
1. Task 057 must be complete (base protocol)
2. Write tests in `tests/enforcement/rules/test_categories_8_11.py`

**Detailed Instructions:**
1. `test_quality.py` (Cat 8): Check for assertion-free tests (ruff PT), over-mocking, test naming conventions
2. `comments.py` (Cat 9): Detect excessive inline comments (ERA001), comment density analysis, TODO/FIXME tracking
3. `deprecated.py` (Cat 10): Check for deprecated API usage (ruff TID251/UP), outdated patterns
4. `async_misuse.py` (Cat 11): Detect async function misuse (ruff ASYNC100-102), blocking calls in async, unawaited coroutines
5. Each rule returns violations with severity and auto-fix availability

**Acceptance Criteria:**
- [ ] All 4 categories produce accurate violations
- [ ] Auto-fix is available where applicable
- [ ] All 11 categories are now implemented
- [ ] All tests pass
```

---

### Task ID: 060

- **Title**: Layer 1 -- Editor-time configuration generation
- **File**: src/autopilot/enforcement/editor_config.py
- **Complete**: [ ]
- **Sprint Points**: 3

- **User Story (business-facing)**: As a developer, I want enforcement rules baked into my editor config, so that anti-patterns are flagged in real-time as I type, not just at commit time.
- **Outcome (what this delivers)**: Editor config generator that extends pyproject.toml with ruff rules covering all 11 categories and configures pyright strict mode.

#### Prompt:

```markdown
**Objective:** Implement Layer 1 editor-time configuration generation.

**File to Create/Modify:** `src/autopilot/enforcement/editor_config.py`

**Specification References:**
- RFC Section 3.5.2: Layer 1 (Editor-Time Configuration, <100ms feedback)
- RFC Section 3.5.1: Rule codes per category

**Prerequisite Requirements:**
1. Tasks 002, 056 must be complete (config, engine)
2. Write tests in `tests/enforcement/test_editor_config.py`

**Detailed Instructions:**
1. Implement `EditorConfigGenerator`:
   - `generate_ruff_config(project_type: str) -> dict` produces ruff config sections
   - `generate_pyright_config(project_type: str) -> dict` produces pyright strict settings
   - `apply_to_pyproject(pyproject_path: Path, config: dict)` merges into existing pyproject.toml
   - Covers all 11 categories with appropriate ruff rule codes
2. For Python: ruff rules (TID, I, N, C901, SIM, S, BLE, TRY, F, ANN, PT, ERA, UP, ASYNC)
3. For TypeScript: generate eslint config additions (placeholder for Phase 6)

**Acceptance Criteria:**
- [ ] Ruff config covers all 11 enforcement categories
- [ ] Config merges into existing pyproject.toml without overwriting
- [ ] Pyright strict mode is configured
- [ ] All tests pass
```
