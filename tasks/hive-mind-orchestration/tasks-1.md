## Summary (tasks-1.md)

- **Tasks in this file**: 7
- **Task IDs**: 001 - 007
- **Total Points**: 10

### Phase 1: Configuration and Models + Phase 2: Objective Template System

---

## Tasks

### Task ID: 001

- **Title**: Add HiveMindConfig to AutopilotConfig
- **File**: src/autopilot/core/config.py
- **Complete**: [x]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a project operator, I want hive-mind configuration in my project's `config.yaml`, so that I can enable/disable hive-mind orchestration, set worker counts, toggle quality passes, and configure the code review loop without code changes.
- **Outcome (what this delivers)**: `HiveMindConfig` Pydantic model added to `config.py` with all fields from the discovery document (enabled, namespace, worker_count, use_claude, batch_strategy, objective_template, quality pass toggles, review loop settings, commands, timeouts). `AutopilotConfig` extended with `hive_mind` field. Existing configs without a `hive_mind` section continue to load (defaults to `enabled: False`).

#### Prompt:

```markdown
**Objective:** Add the `HiveMindConfig` model to the existing configuration hierarchy for hive-mind orchestration.

**File to Modify:** `src/autopilot/core/config.py`

**Context:**
Follow the exact same pattern as existing config sections (e.g., `DebuggingConfig`, `WorkspaceConfig`): frozen Pydantic BaseModel with `ConfigDict(frozen=True)`. The discovery document (lines 269-317) defines all fields precisely.

**Prerequisite Requirements:**
1. Read `src/autopilot/core/config.py` to understand the existing config pattern (frozen models, Field validators, ConfigDict)
2. Read the Phase 1 section of `docs/discovery/hive-mind-orchestration.md` (lines 263-317)

**Detailed Instructions:**

1. Add `HiveMindConfig(BaseModel)` between `DebuggingConfig` and `AutopilotConfig` (to maintain alphabetical-ish ordering with other domain configs):

   ```python
   class HiveMindConfig(BaseModel):
       model_config = ConfigDict(frozen=True)

       enabled: bool = False
       namespace: str = ""  # defaults to project name if empty
       worker_count: int = Field(default=4, gt=0, le=15)
       use_claude: bool = True
       batch_strategy: Literal["auto", "manual"] = "auto"
       objective_template: str = "default"
       # Quality pass toggles
       duplication_check: bool = True
       cleanup_pass: bool = True
       security_scan: bool = True
       coverage_check: bool = True
       file_size_check: bool = True
       # Review loop
       code_review_enabled: bool = True
       code_review_label: str = "claude-review"
       max_review_rounds: int = Field(default=3, gt=0, le=10)
       auto_merge: bool = True
       # Commands
       format_command: str = "just format"
       # Timeouts
       spawn_timeout_seconds: int = Field(default=60, gt=0)
       session_timeout_seconds: int = Field(default=14400, gt=0)  # 4 hours
   ```

2. Add the `Literal` import if not already present (check the existing imports -- it is already imported).

3. Add to `AutopilotConfig`:
   ```python
   hive_mind: HiveMindConfig = Field(default_factory=HiveMindConfig)
   ```
   Place it after `debugging` to maintain consistent ordering.

**Acceptance Criteria:**
- [ ] `HiveMindConfig` uses `ConfigDict(frozen=True)` and all field defaults match the discovery spec
- [ ] `worker_count` has validators `gt=0, le=15`
- [ ] `max_review_rounds` has validators `gt=0, le=10`
- [ ] `spawn_timeout_seconds` and `session_timeout_seconds` have `gt=0`
- [ ] `AutopilotConfig` includes `hive_mind` field with `HiveMindConfig` default
- [ ] Existing config YAML files without `hive_mind` section load without error
- [ ] Config round-trip: `from_yaml()` -> `to_yaml()` preserves the `hive_mind` section
- [ ] `just all` passes (lint, typecheck, test)
```

---

### Task ID: 002

- **Title**: Add SessionType.HIVE_MIND and HiveMindResult model
- **File**: src/autopilot/core/models.py
- **Complete**: [x]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a session tracking system, I want a `HIVE_MIND` session type and a structured result model, so that hive-mind sessions are tracked alongside daemon and manual sessions with their specific outcome data.
- **Outcome (what this delivers)**: `SessionType.HIVE_MIND` enum value added. `HiveMindResult` frozen dataclass with session_id, namespace, task_file, task_ids, exit_code, duration_seconds, output, error, and optional git-derived fields (tasks_completed, prs_created, prs_merged, batches_completed).

#### Prompt:

```markdown
**Objective:** Add the `HIVE_MIND` session type and `HiveMindResult` data model for tracking hive-mind session outcomes.

**File to Modify:** `src/autopilot/core/models.py`

**Context:**
The `SessionType` enum is used in `Session.from_json()` to deserialize session records. Adding a new value is additive and backward-compatible. The `HiveMindResult` follows the frozen dataclass pattern used by `AgentResult`, `CycleResult`, etc. See discovery lines 319-344.

**Prerequisite Requirements:**
1. Read `src/autopilot/core/models.py` to understand enum and dataclass patterns
2. Read the Phase 1 models section of `docs/discovery/hive-mind-orchestration.md` (lines 319-344)
3. Grep all `SessionType` usages to verify no switch/match statements need updating for the new value

**Detailed Instructions:**

1. Add `HIVE_MIND = "hive_mind"` to the `SessionType` StrEnum (after `MANUAL`).

2. Add `HiveMindResult` frozen dataclass after `SprintResult` (before the Enforcement types section):

   ```python
   @dataclass(frozen=True)
   class HiveMindResult:
       """Result from a hive-mind orchestration session."""

       session_id: str
       namespace: str
       task_file: str
       task_ids: tuple[str, ...]  # tuple for immutability on frozen dataclass
       exit_code: int = 0
       duration_seconds: float = 0.0
       output: str = ""
       error: str = ""
       # Git-derived (populated post-session via result collection)
       tasks_completed: int | None = None
       prs_created: int | None = None
       prs_merged: int | None = None
       batches_completed: int | None = None  # inferred from prs_merged
   ```

**Acceptance Criteria:**
- [ ] `SessionType.HIVE_MIND` has value `"hive_mind"` and is a valid `SessionType`
- [ ] `SessionType("hive_mind")` round-trips correctly
- [ ] `HiveMindResult` is frozen (raises `FrozenInstanceError` on attribute assignment)
- [ ] `task_ids` is `tuple[str, ...]` (not list)
- [ ] Git-derived fields default to `None`
- [ ] No existing tests break (verify `Session.from_json` still works with existing session types)
- [ ] `just all` passes
```

---

### Task ID: 003

- **Title**: Unit tests for HiveMindConfig and HiveMindResult
- **File**: tests/core/test_hive_config.py
- **Complete**: [x]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests verifying the hive-mind config and result models, so that I can refactor confidently knowing the data contracts are verified.
- **Outcome (what this delivers)**: Test file covering `HiveMindConfig` defaults, validators, YAML round-trip, and `HiveMindResult` construction, immutability, and `SessionType.HIVE_MIND`.

#### Prompt:

```markdown
**Objective:** Write unit tests for the Phase 1 config and model additions.

**File to Create:** `tests/core/test_hive_config.py`

**Context:**
Follow test patterns from `tests/core/test_config.py` (existing config tests). Use `tmp_path` for YAML round-trip tests.

**Prerequisite Requirements:**
1. Tasks 001-002 must be complete
2. Read `tests/core/test_config.py` for style conventions and fixture patterns

**Detailed Instructions:**

1. `TestHiveMindConfig` class:
   - Test default values: `enabled=False`, `namespace=""`, `worker_count=4`, `use_claude=True`, etc.
   - Test `worker_count` validator: 0 raises `ValidationError`, 15 is valid, 16 raises
   - Test `max_review_rounds` validator: 0 raises, 10 is valid, 11 raises
   - Test YAML round-trip: create `AutopilotConfig` with custom `hive_mind`, serialize via `to_yaml()`, reload via `from_yaml()`, assert values match
   - Test that `AutopilotConfig` without `hive_mind` in YAML loads with defaults

2. `TestHiveMindResult` class:
   - Test construction with required fields (session_id, namespace, task_file, task_ids)
   - Test frozen immutability
   - Test `task_ids` is tuple
   - Test git-derived fields default to `None`
   - Test `SessionType.HIVE_MIND` exists and round-trips via `SessionType("hive_mind")`

**Acceptance Criteria:**
- [ ] All validator edge cases tested (boundary values)
- [ ] YAML round-trip test uses `tmp_path` and `to_yaml`/`from_yaml`
- [ ] Frozen immutability tested on `HiveMindResult`
- [ ] `just all` passes
```

---

### Task ID: 004

- **Title**: Add render_to_string method to TemplateRenderer
- **File**: src/autopilot/core/templates.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As the objective builder, I want to render Jinja2 templates to strings (not just files), so that I can construct hive-mind objective prompts from templates without writing to the filesystem.
- **Outcome (what this delivers)**: A `render_to_string(template_name, context)` method on `TemplateRenderer` that returns the rendered template as a string.

#### Prompt:

```markdown
**Objective:** Add a `render_to_string` method to `TemplateRenderer` so that objective templates can be rendered to strings rather than files.

**File to Modify:** `src/autopilot/core/templates.py`

**Context:**
The existing `render_to()` method writes rendered output to the filesystem. The `HiveObjectiveBuilder` (Task 006) needs string output. Rather than building a parallel Jinja2 environment, we add `render_to_string()` to reuse the same rendering infrastructure. See discovery line 89.

**Prerequisite Requirements:**
1. Read `src/autopilot/core/templates.py` to understand the existing rendering logic
2. Note how `render_to()` builds the Jinja2 `Environment` with `FileSystemLoader` and `StrictUndefined`

**Detailed Instructions:**

1. Extract the Jinja2 `Environment` creation logic from `render_to()` into a private `_build_env()` method to avoid duplication:

   ```python
   def _build_env(self) -> Environment:
       """Build Jinja2 environment with user-override and package search paths."""
       search_paths: list[str] = []
       if self._user_dir.is_dir():
           search_paths.append(str(self._user_dir))
       if self._package_dir.is_dir():
           search_paths.append(str(self._package_dir))

       if not search_paths:
           msg = f"No templates found for project type '{self._project_type}'"
           raise ValueError(msg)

       return Environment(
           loader=FileSystemLoader(search_paths),
           keep_trailing_newline=True,
           undefined=StrictUndefined,
       )
   ```

2. Refactor `render_to()` to use `self._build_env()`.

3. Add `render_to_string()`:

   ```python
   def render_to_string(self, template_name: str, context: dict[str, Any]) -> str:
       """Render a single template to a string."""
       env = self._build_env()
       template = env.get_template(template_name)
       return template.render(**context)
   ```

**Acceptance Criteria:**
- [ ] `render_to_string("template.j2", context)` returns the rendered string
- [ ] `render_to()` still works exactly as before (no behavioral change)
- [ ] `_build_env()` is private and handles missing template dirs with `ValueError`
- [ ] `StrictUndefined` is used (missing variables raise `UndefinedError`)
- [ ] `just all` passes
```

---

### Task ID: 005

- **Title**: Create hive-objective default template and metadata
- **File**: templates/hive-objective/default.j2
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As a hive-mind operator, I want a well-structured default objective template, so that hive-mind sessions automatically include batch grouping, quality passes, code review loops, and task status updates without manual prompt construction.
- **Outcome (what this delivers)**: The `templates/hive-objective/default.j2` Jinja2 template and `templates/hive-objective/_template.yaml` metadata file. The template encodes the complete workflow: task reading, batch grouping, implementation, quality passes (duplication, cleanup, security, coverage, file size), PR creation, code review loop, merge, and task status updates.

#### Prompt:

```markdown
**Objective:** Create the default hive-mind objective Jinja2 template and its metadata file.

**Files to Create:**
- `templates/hive-objective/default.j2`
- `templates/hive-objective/_template.yaml`

**Context:**
The template system uses `TemplateRenderer` from `src/autopilot/core/templates.py`. Templates live in `templates/{type}/` with a `_template.yaml` metadata file. The `_template.yaml` lists expected files and template variables. The template content is defined in the discovery document (lines 354-427).

**Prerequisite Requirements:**
1. Read the Phase 2 section of `docs/discovery/hive-mind-orchestration.md` (lines 346-498)
2. Read existing template examples in `templates/` directory to understand the structure
3. Read `src/autopilot/core/templates.py` to understand how `_template.yaml` is loaded

**Detailed Instructions:**

1. Create `templates/hive-objective/default.j2` with the objective template from the discovery (lines 354-427). The template uses these Jinja2 features:
   - `{{ task_ids | join(', ') }}` for task ID list
   - `{{ task_file }}` for task file path reference
   - `{{ quality_command }}` for the all-in-one quality check command
   - `{% if code_review_enabled %}` conditional block for PR review loop
   - `{% if auto_merge %}` nested conditional for auto-merge
   - `{% if duplication_check %}` conditional block for duplication detection
   - `{% if cleanup_pass %}` conditional block for cleanup pass with `{{ format_command }}`
   - `{% if security_scan %}` conditional block for security analysis
   - `{% if coverage_check %}` conditional block for test coverage
   - `{% if file_size_check %}` conditional block for file size optimization
   - `{% if sprint_record %}` conditional for sprint record updates
   - `{{ quality_gates }}` for formatted quality gate commands

2. Create `templates/hive-objective/_template.yaml` with:
   ```yaml
   expected_files:
     - default.j2
   variables:
     - task_ids
     - task_file
     - quality_command
     - format_command
     - code_review_enabled
     - max_review_rounds
     - auto_merge
     - duplication_check
     - cleanup_pass
     - security_scan
     - coverage_check
     - file_size_check
     - quality_gates
     - sprint_record
   ```

**Acceptance Criteria:**
- [ ] `templates/hive-objective/default.j2` renders without errors when all variables are provided
- [ ] All conditional sections are properly guarded with `{% if ... %}`
- [ ] `_template.yaml` lists all 14 template variables
- [ ] Template content matches the discovery document (lines 354-427)
- [ ] Template produces clean output (no extra blank lines when sections are disabled)
- [ ] `just all` passes
```

---

### Task ID: 006

- **Title**: Create HiveObjectiveBuilder
- **File**: src/autopilot/orchestration/objective_builder.py
- **Complete**: [ ]
- **Sprint Points**: 2

- **User Story (business-facing)**: As the hive-mind spawn command, I want a builder that constructs parameterized objective prompts from templates and config, so that I can generate rich, config-driven objectives without manual string construction.
- **Outcome (what this delivers)**: `HiveObjectiveBuilder` class with `build(task_file, task_ids)` and `_build_context()` methods. Uses `TemplateRenderer.render_to_string()` to render the `hive-objective/default.j2` template with config-driven context. Includes objective length warning at 4000 characters.

#### Prompt:

```markdown
**Objective:** Create the `HiveObjectiveBuilder` that constructs parameterized hive-mind objective prompts from Jinja2 templates.

**File to Create:** `src/autopilot/orchestration/objective_builder.py`

**Context:**
This module bridges the config system and the template system to produce objective strings for `hive-mind spawn`. It uses `TemplateRenderer` (Task 004's `render_to_string` method) with the `hive-objective` template type. See discovery lines 452-498.

**Prerequisite Requirements:**
1. Tasks 001, 004, 005 must be complete (config, render_to_string, template files)
2. Read `src/autopilot/core/templates.py` for `TemplateRenderer` API
3. Read `src/autopilot/core/config.py` for `HiveMindConfig` and `QualityGatesConfig` fields
4. Read the Phase 2 objective builder section of the discovery (lines 452-498)

**Detailed Instructions:**

1. Create `src/autopilot/orchestration/objective_builder.py` (~100 lines):

   ```python
   """Hive-mind objective prompt builder.

   Constructs parameterized objective prompts from Jinja2 templates
   using project configuration to drive template context.
   """

   from __future__ import annotations

   import logging
   from pathlib import Path
   from typing import TYPE_CHECKING, Any

   from autopilot.core.templates import TemplateRenderer

   if TYPE_CHECKING:
       from autopilot.core.config import AutopilotConfig

   _log = logging.getLogger(__name__)

   _PACKAGE_TEMPLATES = Path(__file__).resolve().parents[3] / "templates"
   ```

2. Implement `HiveObjectiveBuilder`:

   a. `__init__(self, config: AutopilotConfig)`:
      - Store config reference
      - Create `TemplateRenderer("hive-objective", package_templates_dir=_PACKAGE_TEMPLATES)`

   b. `build(self, task_file: str, task_ids: list[str], *, template_name: str = "default") -> str`:
      - Build context via `_build_context()`
      - Render via `self._renderer.render_to_string(f"{template_name}.j2", context)`
      - Log warning if rendered length > 4000 characters
      - Return the rendered string

   c. `_build_context(self, task_file: str, task_ids: list[str]) -> dict[str, Any]`:
      - Pull values from `self._config.hive_mind` and `self._config.quality_gates`
      - Return dict with all 14 template variables (see discovery lines 479-497)
      - `quality_command` = `gates.all or "just"`
      - `sprint_record` = `""` (placeholder for future sprint integration)

   d. `_format_quality_gates(self, gates: QualityGatesConfig) -> str`:
      - Reuse the same formatting logic as `HiveMindManager._build_quality_gates()`
      - Format as bulleted list: `- pre-commit: ...`, `- type-check: ...`, etc.
      - Return empty string if no gates configured

**Acceptance Criteria:**
- [ ] `HiveObjectiveBuilder(config).build("tasks/tasks-1.md", ["001", "002"])` returns a non-empty string
- [ ] All 14 template variables are populated from config
- [ ] Objective length > 4000 chars logs a warning (use `_log.warning`)
- [ ] `_format_quality_gates()` produces the same format as the existing `HiveMindManager._build_quality_gates()`
- [ ] Module uses `from __future__ import annotations` and `TYPE_CHECKING` for config import
- [ ] File is under 120 lines
- [ ] `just all` passes
```

---

### Task ID: 007

- **Title**: Unit tests for TemplateRenderer.render_to_string and HiveObjectiveBuilder
- **File**: tests/orchestration/test_objective_builder.py
- **Complete**: [ ]
- **Sprint Points**: 1

- **User Story (business-facing)**: As a developer, I want tests verifying that templates render correctly with various config combinations, so that I can change templates or config without breaking objective generation.
- **Outcome (what this delivers)**: Test file covering `render_to_string` on `TemplateRenderer`, `HiveObjectiveBuilder.build()` with default and custom configs, quality gate formatting, objective length warning, and template variable completeness.

#### Prompt:

```markdown
**Objective:** Write unit tests for the template rendering and objective builder components.

**Files to Create:**
- `tests/core/test_render_to_string.py` (TemplateRenderer.render_to_string tests)
- `tests/orchestration/test_objective_builder.py` (HiveObjectiveBuilder tests)

**Context:**
Use `tmp_path` to create temporary template files for `render_to_string` tests. For `HiveObjectiveBuilder` tests, the real template files in `templates/hive-objective/` should be used (they exist from Task 005).

**Prerequisite Requirements:**
1. Tasks 004-006 must be complete
2. Read existing test files for style conventions (`tests/core/test_config.py`, `tests/orchestration/test_hive.py`)

**Detailed Instructions:**

1. `tests/core/test_render_to_string.py`:
   - Test `render_to_string` with a simple template (`{{ name }}`) in a tmp directory
   - Test `render_to_string` raises `UndefinedError` for missing variables (StrictUndefined)
   - Test `render_to_string` with template inheritance (user override)
   - Test that `render_to` still works after refactoring (regression test)

2. `tests/orchestration/test_objective_builder.py`:
   - Fixture: `hive_config` returning `AutopilotConfig` with `HiveMindConfig` defaults
   - Test `build()` returns non-empty string with valid task_file and task_ids
   - Test rendered output contains task IDs and task file path
   - Test with `code_review_enabled=False` -- output should NOT contain "code review" section
   - Test with all quality passes disabled -- output should be shorter (no quality sections)
   - Test `_format_quality_gates()` with configured gates (pre_commit, type_check, test)
   - Test `_format_quality_gates()` with empty gates returns empty string
   - Test objective length warning is logged when content > 4000 chars (use `caplog` fixture)
   - Test `template_name` parameter uses correct template file

**Acceptance Criteria:**
- [ ] `render_to_string` tests use `tmp_path` with temporary .j2 files
- [ ] `HiveObjectiveBuilder` tests use the real `templates/hive-objective/default.j2`
- [ ] Config-driven conditional sections are tested (at least code_review and one quality pass)
- [ ] Quality gate formatting matches existing `HiveMindManager._build_quality_gates()` output
- [ ] Length warning test uses `caplog` to assert warning was logged
- [ ] `just all` passes
```
