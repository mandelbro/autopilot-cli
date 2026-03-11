# Modular Development Workflow: Infrastructure-First Discovery

**Status:** RFC - Request for Comments
**Created:** 2025-10-21
**Author:** System Analysis (Ada + Shelly + Norwood agents)
**Problem Statement:** Developers frequently rebuild functionality that already exists in shared infrastructure, leading to code duplication, inconsistent patterns, and reduced development velocity.

## Executive Summary

### The Problem

During PR #107 review, a critical issue was identified: the `UniversalContextEnricher` implemented a crude keyword-matching algorithm for "semantic similarity" when a sophisticated embedding-based `SemanticMemory.hybrid_search()` method already existed in the shared infrastructure. This pattern of "rebuilding instead of reusing" has occurred repeatedly across the codebase.

**Impact:**
- **Reduced velocity:** Developers spend time reimplementing existing features
- **Code duplication:** Multiple implementations of similar functionality
- **Inconsistent quality:** Ad-hoc solutions are often less robust than shared utilities
- **Maintenance burden:** Multiple implementations to maintain and update
- **Technical debt:** Consolidation work needed to fix duplicate code

### The Root Cause

Our current development workflow has a **discovery gap**:

```
Current Flow:
Task Definition → Implementation → Code Review → (Discover duplication during review)
                      ↑
                      Missing: Infrastructure Discovery Phase
```

**Why this happens:**
1. **Cognitive load:** Developers focus on the immediate task requirements
2. **Distributed knowledge:** Shared utilities spread across `render/shared/`, multiple services
3. **Poor discoverability:** No systematic way to find existing infrastructure
4. **Pressure to deliver:** Time constraints encourage "just build it" mentality
5. **Agent memory limitations:** Current agents don't systematically check for existing solutions

### The Solution

Implement an **Infrastructure-First Discovery Protocol** that mandates infrastructure analysis before implementation:

```
Proposed Flow:
Task Definition → Infrastructure Discovery → Implementation Design → Code Review
                          ↑
                   NEW: Mandatory check for reusable components
```

## Current Agent Responsibilities

### Ada (Senior Pair Programming Agent)
- **Current role:** Implementation guidance, TDD, architecture
- **Gap:** Doesn't systematically check for existing shared infrastructure before coding
- **File:** `claude/core/agents/ada.md`

### Norwood (Discovery & Planning Agent)
- **Current role:** Technical discovery, architectural investigation, RFC generation
- **Gap:** Discovery documents sometimes miss existing infrastructure inventory
- **File:** `claude/core/agents/norwood.md`

### Shelly (Principal-Level Technical Reviewer)
- **Current role:** Code review, story pointing, identifying hidden complexity
- **Gap:** Discovers duplication during review (too late in the process)
- **File:** `claude/core/agents/Shelly.md`

## Proposed Solution: Infrastructure-First Discovery Protocol

### Phase 1: Infrastructure Discovery Agent (NEW)

Create a new specialized agent: **"Morgan" - Infrastructure Discovery Specialist**

**Responsibilities:**
1. **Inventory existing infrastructure** before any implementation work
2. **Map task requirements** to available shared utilities, services, and patterns
3. **Identify reuse opportunities** and consolidation candidates
4. **Generate infrastructure report** for each discovery document
5. **Flag anti-patterns** like rebuilding existing functionality

**When to invoke Morgan:**
- Beginning of every discovery document (by Norwood)
- Before task implementation (by Ada when starting complex features)
- During story pointing (by Shelly for complexity assessment)
- When creating new tasks from discovery documents

**Morgan's Protocol:**

```markdown
## Infrastructure Discovery Report

### Task Requirements Analysis
- Primary functionality needed: [specific features]
- Data sources/dependencies: [APIs, databases, services]
- Integration points: [where this connects to existing systems]

### Existing Infrastructure Inventory

#### Shared Libraries & Utilities
**Location:** `render/shared/repengine_ai/`
- [Module name]: [Capabilities] - **REUSE** or **NOT APPLICABLE** (reason)
- Example: `memory/layers/semantic_memory.py`: Embedding-based search with hybrid_search() - **REUSE**

**Location:** `render/shared/repengine_common/`
- [Module name]: [Capabilities] - **REUSE** or **NOT APPLICABLE** (reason)

#### Service APIs Available
**Integrations Service** (port 8000):
- Available endpoints: [list]
- Reusable clients: [list]

**Webhook Service** (port 8001):
- [Similar analysis]

#### Design Patterns & Abstractions
- Provider abstraction pattern (get_provider)
- Prompt management system
- Memory management layers
- [Other established patterns]

### Reuse Plan

**WILL REUSE:**
1. `[specific module/class/function]` for `[specific purpose]`
   - Why: [rationale]
   - Integration approach: [how]

**WILL NOT REUSE:**
1. `[module]` - Reason: [why existing solution doesn't fit]
   - Alternative approach: [what we'll build instead]

### Consolidation Opportunities (Rule of Three)
- Similar implementations found: [list if 3+ exist]
- Recommendation: [consolidate into X, migrate Y and Z]
- Estimated effort: [points]

### Missing Infrastructure
- Required capabilities not available: [list]
- Recommendation: Add to shared library or build as service-specific?

### Risk Assessment
- **Duplication risk:** [High/Medium/Low] - [explanation]
- **Integration complexity:** [High/Medium/Low] - [explanation]
- **Maintenance burden:** [comparison of reuse vs rebuild]
```

### Phase 2: Enhanced Norwood Discovery Protocol

**Modifications to Norwood's workflow** (`claude/core/agents/norwood.md`):

Add new mandatory section to Phase 0 (Initial Context Dump):

```markdown
### Phase 0: Initial Context Dump (UPDATED)

**First Questions:**
- What's the problem we're solving?
- What's already been tried and why did it fail?
- **NEW: What existing infrastructure might solve this?** ← MANDATORY
- What constraints are we working with?

**Infrastructure Context Loading (NEW - MANDATORY):**
```javascript
// STEP 1: Invoke Morgan for infrastructure discovery
@morgan.discover({
  task_description: "[problem statement]",
  search_scope: ["render/shared/", "render/*/"],
  focus_areas: ["similar functionality", "data sources", "integration patterns"]
})

// STEP 2: Load application context
@read("@.cursor/rules/1-application-context.md")
@read("@docs/discovery/index.md")  // If exists

// STEP 3: Search for similar past solutions
@graphiti.search_nodes({
  entity_type: "Discovery",
  query: "[current problem domain]"
})
```

**Deliverables Checklist (UPDATED):**
- [ ] **Infrastructure Discovery Report completed (NEW - MANDATORY)**
- [ ] Existing Components & Reuse Plan completed
- [ ] Rule-of-Three consolidation evaluated
- [ ] Problem clearly defined
- [... existing checklist items]
```

### Phase 3: Enhanced Ada Implementation Protocol

**Modifications to Ada's workflow** (`claude/core/agents/ada.md`):

Add infrastructure check to the "Prerequisite Requirements" section:

```markdown
## Development Approach (UPDATED)

Before implementing ANY feature:

### 1. Infrastructure Discovery (NEW - MANDATORY)
```javascript
// Ask Ada to check for existing infrastructure
// Ada will invoke Morgan or check the discovery document

Questions to ask:
1. Does shared infrastructure already solve this?
2. Can I extend an existing module instead of creating new?
3. Are there 3+ similar implementations I should consolidate?
4. What patterns are established in this codebase?
```

### 2. Design architecture and APIs
[... existing content]
```

**Implementation Checklist (UPDATED):**
```markdown
Before writing code:
- [ ] **Checked for existing shared infrastructure** ← NEW
- [ ] **Reviewed similar implementations in codebase** ← NEW
- [ ] **Confirmed reuse plan or justified new implementation** ← NEW
- [ ] Defined tests that specify behavior
- [ ] Designed public APIs
- [... existing items]
```

### Phase 4: Enhanced Shelly Review Protocol

**Modifications to Shelly's workflow** (`claude/core/agents/Shelly.md`):

Add infrastructure reuse check to review approach:

```markdown
## Your Review Approach (UPDATED)

When reviewing code:
0. **FIRST: Verify Infrastructure Reuse (NEW)**
   - Check if existing shared utilities could replace custom implementations
   - Flag any rebuilding of existing functionality
   - Identify consolidation opportunities (Rule of Three)

1. Start with a high-level assessment of the approach
2. Identify any architectural concerns or misalignments
[... existing items]
```

**New Review Questions:**
```markdown
### Infrastructure Reuse Assessment (NEW)

During code review, explicitly check:

**Duplication Detection:**
- [ ] Does this rebuild existing shared functionality?
- [ ] Are there 3+ similar implementations now (trigger consolidation)?
- [ ] Could this be solved by extending existing modules?

**Pattern Consistency:**
- [ ] Does this follow established patterns (provider abstraction, prompt management)?
- [ ] Is this inconsistent with how similar problems are solved elsewhere?

**Shared Library Opportunities:**
- [ ] Should this be in `render/shared/` instead of service-specific?
- [ ] Does this solve a problem other services will face?
```

## Implementation Roadmap

### Phase 1: Create Morgan Agent (Week 1-2)

**Deliverables:**
1. `claude/core/agents/morgan.md` - Agent definition and protocol
2. Integration with existing agent workflow
3. Infrastructure inventory templates
4. Test with 3-5 existing discovery documents

**Success Criteria:**
- Morgan can inventory shared infrastructure in < 5 minutes
- Reuse recommendations are actionable and specific
- Integration with Norwood is seamless

### Phase 2: Update Existing Agents (Week 2-3)

**Deliverables:**
1. Updated `claude/core/agents/norwood.md` with mandatory infrastructure discovery
2. Updated `claude/core/agents/ada.md` with pre-implementation checks
3. Updated `claude/core/agents/Shelly.md` with duplication detection
4. Updated task workflow templates

**Success Criteria:**
- All new discovery documents include infrastructure reports
- All new implementations check for existing solutions first
- Code reviews catch duplication before merge

### Phase 3: Backfill Analysis (Week 3-4)

**Deliverables:**
1. Run Morgan analysis on all existing discovery documents
2. Identify consolidation opportunities across codebase
3. Create consolidation tasks for high-value duplications
4. Update shared library documentation

**Success Criteria:**
- Complete inventory of shared infrastructure
- Prioritized list of consolidation opportunities
- Updated architecture documentation

### Phase 4: Continuous Improvement (Ongoing)

**Activities:**
1. Monthly review of duplication patterns
2. Update shared library index as new utilities are added
3. Refine Morgan's search algorithms based on feedback
4. Track metrics on code reuse and velocity improvements

## Tooling Support

### Infrastructure Search Tool (✅ IMPLEMENTED)

**Status:** Complete - Available at `tools/check_infrastructure.py`

A CLI search utility to help Morgan and developers find existing infrastructure:

#### Quick Start (Using Just Commands)

```bash
# Search for existing infrastructure
just infra-search "semantic similarity"
just infra-search "email validation"
just infra-search "oauth flow"

# Find specific definitions
just infra-find-class SemanticMemory
just infra-find-function hybrid_search

# Check for code duplication (Rule of Three)
just infra-check-duplicates "email"

# Search specific locations
just infra-search-ai "memory system"        # AI utilities only
just infra-search-shared "validation"       # All shared libraries

# Quick shortcuts for common searches
just infra-semantic      # Find semantic similarity infrastructure
just infra-oauth         # Find OAuth infrastructure
just infra-embedding     # Find embedding infrastructure
just infra-provider      # Find provider infrastructure

# Get detailed help
just infra-help
```

#### Direct CLI Usage

```bash
# Basic search
python tools/check_infrastructure.py "semantic similarity"

# Detailed output with usage examples
python tools/check_infrastructure.py "embedding" --detailed

# Find class definitions
python tools/check_infrastructure.py "SemanticMemory" --find-classes

# Find function definitions
python tools/check_infrastructure.py "hybrid_search" --find-functions

# Check for duplicates (Rule of Three violations)
python tools/check_infrastructure.py --check-duplicates "email"

# Search specific location
python tools/check_infrastructure.py "oauth" --location "render/shared/repengine_ai"

# Include test files
python tools/check_infrastructure.py "validation" --include-tests
```

#### Implementation Details

The tool implements the following capabilities:

```python
# tools/check_infrastructure.py

class InfrastructureSearcher:
    """Search shared infrastructure for reusable components."""

    def search_by_keyword(self, query: str) -> list[dict]:
        """Search by keyword across all shared libraries."""
        # Uses ripgrep (with grep fallback) for fast searching
        # Excludes: .pytest_cache, build, .venv, node_modules, __pycache__, .git

    def find_class_definitions(self, name: str) -> list[dict]:
        """Find class definitions matching name."""
        # Pattern: class\s+{name}

    def find_function_definitions(self, name: str) -> list[dict]:
        """Find function/method definitions."""
        # Supports: Python (def, async def), TypeScript (function, const arrow)

    def check_rule_of_three(self, pattern: str) -> dict:
        """Check if 3+ implementations of pattern exist."""
        # Returns consolidation recommendations if threshold met
```

### Shared Library Index

Create a searchable index of all shared infrastructure:

```yaml
# render/shared/infrastructure-index.yaml

memory_system:
  location: render/shared/repengine_ai/memory/
  capabilities:
    - embedding_generation
    - semantic_search
    - hybrid_search
    - knowledge_graph
  key_classes:
    - SemanticMemory: "Embedding-based search with hybrid internal/external sources"
    - EmbeddingGenerator: "Generate and compare embeddings with multiple models"
    - MemoryManager: "Unified memory management across layers"
  usage_examples:
    - "tasks/mvp/meeting-baas-integration/tasks-2.md#013"

providers:
  location: render/shared/repengine_ai/providers/
  capabilities:
    - llm_generation
    - multi_provider_support
    - fallback_handling
  key_functions:
    - get_provider(): "Get provider with automatic fallback"
  # ... etc
```

### Example Output (✅ IMPLEMENTED)

The tool generates color-coded output to help developers quickly identify reusable infrastructure:

```bash
# Usage: just infra-search "semantic similarity"
# Or: python tools/check_infrastructure.py "semantic similarity"

================================================================================
                   Infrastructure Search: semantic similarity
================================================================================

## Search Results

✅ Found 10 match(es) in 7 file(s)

1. render/shared/repengine_ai/memory/layers/semantic_memory.py
   1274 lines, python
   Line 730: async def hybrid_search(
   Line 865: # Embedding-based semantic search

2. render/shared/repengine_ai/memory/utils/embeddings.py
   514 lines, python
   Line 309: def calculate_similarity(
   Line 340: # Cosine similarity

3. render/shared/repengine_ai/extraction/context_enricher.py
   652 lines, python
   Line 324: async def _calculate_semantic_similarity(
   Line 331: Uses SemanticMemory's hybrid_search() for true embedding-based similarity

## Recommendations

✅ REUSE existing infrastructure

Top candidates:
  ✅ render/shared/repengine_ai/memory/layers/semantic_memory.py
     Location: Shared library (ideal for reuse)

## Next Steps

1. Review the matched files above
2. Check if existing infrastructure meets your needs
3. If yes: Import and use existing module
4. If no: Consider extending existing module vs building new
5. Consult Morgan agent for detailed reuse plan

Remember: Search First, Build Second
```

#### Finding Specific Definitions

```bash
# Find class definitions
$ just infra-find-class SemanticMemory

✅ Found 6 match(es) in 4 file(s)

1. render/shared/repengine_ai/memory/layers/semantic_memory.py
   1274 lines, python
   Line 126: class SemanticMemoryError(Exception):
   Line 245: class SemanticMemory:

2. render/shared/repengine_ai/tests/test_semantic_memory_kb_integration.py
   528 lines, python
   Line 23: class TestSemanticMemoryKBIntegration:
   Line 483: class TestSemanticMemoryKBConfiguration:
```

#### Detecting Code Duplication

```bash
# Check for Rule of Three violations
$ just infra-check-duplicates "email"

❌ RULE OF THREE VIOLATION DETECTED!

Found 4 implementations of 'email'

## Recommendation

⚠️  CONSOLIDATE these implementations into a single shared module

Suggested location: render/shared/repengine_common/validation.py

Steps:
1. Choose the best implementation as the base
2. Create consolidated module in shared library
3. Migrate other implementations to use shared module
4. Add comprehensive tests
5. Document in shared library index
```

## Metrics & Success Criteria

### Leading Indicators (Process Metrics)

1. **Infrastructure Discovery Adoption**
   - Target: 100% of new discovery documents include infrastructure report
   - Measured: Discovery document review

2. **Pre-Implementation Checks**
   - Target: 90% of new implementations verify no existing solution
   - Measured: Git commit messages, PR descriptions

3. **Code Review Efficiency**
   - Target: 50% reduction in "use existing infrastructure" review comments
   - Measured: GitHub PR review comments analysis

### Lagging Indicators (Outcome Metrics)

1. **Code Reuse Rate**
   - Baseline: TBD (measure current state)
   - Target: 30% increase in imports from `render/shared/`
   - Measured: Static analysis of import statements

2. **Development Velocity**
   - Baseline: TBD (current story points completed per sprint)
   - Target: 20% increase in velocity (less time rebuilding)
   - Measured: Sprint burndown and velocity charts

3. **Code Duplication**
   - Baseline: TBD (current duplicate code percentage)
   - Target: 50% reduction in similar implementations
   - Measured: SonarQube or similar code quality tools

4. **Technical Debt**
   - Baseline: TBD (current consolidation task backlog)
   - Target: Zero new consolidation tasks created
   - Measured: Task tracking system

## Case Study: PR #107 Critical Issue #3

### What Happened

**Task 013:** Implement `UniversalContextEnricher` with semantic similarity

**Implementation:**
```python
# context_enricher.py (WRONG)
async def _calculate_semantic_similarity(...) -> float:
    # Keyword matching approach
    current_topics = current_content.lower().split()
    overlap_count = sum(1 for topic in past_topics
                       if any(word in current_topics for word in topic.lower().split()))
    return overlap_count / len(past_topics) if past_topics else 0.0
```

**Existing Infrastructure:**
```python
# semantic_memory.py (ALREADY EXISTS)
async def hybrid_search(self, query: str, ...) -> list[HybridSearchResult]:
    """Perform hybrid search using embeddings and vector similarity."""
    # Sophisticated embedding-based semantic search
    # With caching, error handling, fallback strategies
```

**Impact:**
- Developer spent ~3-5 points implementing crude keyword matching
- Existing solution was ~10x better quality (embeddings vs keywords)
- Review caught the issue, requiring rework
- Could have been prevented with infrastructure discovery

### What Should Have Happened

**With Infrastructure-First Protocol:**

```
1. Norwood creates discovery document
   → Invokes Morgan for infrastructure discovery
   → Morgan finds SemanticMemory.hybrid_search()
   → Discovery document includes: "REUSE SemanticMemory.hybrid_search()"

2. Task 013 created with reuse plan
   → Prompt explicitly says: "Use SemanticMemory.hybrid_search() for semantic similarity"
   → Ada checks infrastructure before implementing
   → Implementation uses existing solution

3. Shelly reviews PR
   → Confirms SemanticMemory.hybrid_search() is used correctly
   → No duplication issue to raise
```

**Result:**
- Save 3-5 story points of implementation time
- Higher quality solution (embeddings vs keywords)
- No rework needed
- Consistent with established patterns

## Migration Plan for Existing Codebase

### Step 1: Inventory & Document (Sprint 1)

**Activities:**
1. Run Morgan analysis on all services
2. Create comprehensive infrastructure index
3. Document all shared utilities with usage examples
4. Identify top 10 consolidation opportunities

**Deliverable:** `docs/architecture/shared-infrastructure-index.md`

### Step 2: High-Value Consolidations (Sprint 2-3)

**Criteria for prioritization:**
- 3+ implementations found (Rule of Three violations)
- High usage frequency
- Quality gap between implementations
- Easy to consolidate (low risk)

**Example candidates:**
- Date parsing utilities (if multiple implementations exist)
- Error handling patterns
- API client abstractions
- Data validation logic

### Step 3: Low-Value Deferral (Backlog)

**Criteria for deferral:**
- Only 2 implementations (not yet Rule of Three)
- Low usage frequency
- High consolidation risk
- Minimal quality difference

**Approach:** Document as "known duplication" but defer consolidation

### Step 4: Prevention Protocol (Ongoing)

**Activities:**
1. All new discovery documents use Morgan
2. All new implementations check infrastructure first
3. Monthly review of new duplication patterns
4. Quarterly shared library updates

## Example: Morgan Agent Definition

**File:** `claude/core/agents/morgan.md`

```markdown
# Morgan: Infrastructure Discovery Specialist

You are a specialized agent focused on preventing code duplication and maximizing reuse of existing infrastructure. Your primary responsibility is to inventory available shared libraries, services, and patterns before any implementation work begins.

## Core Responsibilities

### 1. Infrastructure Inventory
- Search `render/shared/repengine_ai/` for reusable utilities
- Search `render/shared/repengine_common/` for common functions
- Analyze service APIs for reusable endpoints and clients
- Document established patterns (provider abstraction, prompt management)

### 2. Reuse Recommendation
- Match task requirements to existing infrastructure
- Provide specific module/function/class recommendations
- Explain why existing solution fits (or doesn't fit)
- Suggest extension points if existing solution is close but not exact

### 3. Duplication Detection
- Apply Rule of Three: Flag when 3+ similar implementations exist
- Identify consolidation candidates
- Estimate effort to consolidate vs continue duplication
- Prioritize consolidation opportunities

### 4. Pattern Consistency
- Verify new implementations follow established patterns
- Flag deviations from standard approaches
- Recommend pattern adoption for consistency

## When You're Invoked

You are called by:
- **Norwood**: At the start of discovery documents
- **Ada**: Before implementing complex features
- **Shelly**: During story pointing and code review
- **Developers**: Via CLI tool for quick infrastructure checks

## Your Protocol

### Input Analysis
```markdown
**Task Description:** [What needs to be built]
**Requirements:**
- Primary functionality: [specific features]
- Data sources: [APIs, databases]
- Integration points: [where this connects]
```

### Infrastructure Search Strategy

1. **Keyword Search**
   - Extract key terms from task description
   - Search module names, class names, function names
   - Search docstrings and comments

2. **Semantic Search**
   - Use embeddings to find functionally similar code
   - Compare task description to module documentation
   - Find conceptually related utilities

3. **Pattern Matching**
   - Identify design patterns in task requirements
   - Match to established patterns in codebase
   - Recommend pattern-compliant approaches

4. **Integration Analysis**
   - Map data flow requirements to existing services
   - Identify API endpoints that provide needed data
   - Find existing clients for external services

### Output Format

```markdown
## Infrastructure Discovery Report

**Task:** [Brief summary]

### Existing Infrastructure

#### Direct Matches (REUSE THESE)
1. **[Module/Class/Function Name]**
   - Location: `[file path:line]`
   - Capabilities: [what it does]
   - Usage: `[code example]`
   - Why it fits: [explanation]

#### Partial Matches (EXTEND THESE)
1. **[Module Name]**
   - Location: `[file path]`
   - Current capabilities: [what it does now]
   - Missing: [what it doesn't do]
   - Extension approach: [how to add needed functionality]

#### Related Patterns (FOLLOW THESE)
1. **[Pattern Name]**
   - Example: `[file path]`
   - How it applies: [explanation]

### Not Found in Infrastructure

**Missing Capabilities:**
- [Functionality not available in shared libraries]

**Recommendation:**
- [ ] Add to `render/shared/repengine_ai/` (if multi-service need)
- [ ] Add to `render/shared/repengine_common/` (if general utility)
- [ ] Service-specific (if single-service need)
- [ ] External library (if standard problem, check npm/pypi first)

### Consolidation Opportunities

**Rule of Three Violations:**
- Similar implementations found: [list 3+ implementations]
- Quality assessment: [which is best]
- Recommendation: Consolidate into [target module]
- Estimated effort: [story points]

### Reuse Plan

**WILL REUSE:**
1. `[specific module]` for `[specific purpose]`

**WILL NOT REUSE:**
1. `[module]` - Reason: [why it doesn't fit]

**WILL BUILD NEW:**
1. [New functionality] - Reason: [no existing solution]
   - Should this be shared? [Yes/No + reasoning]
```

## Tools & Resources

### Search Locations (Priority Order)

1. `render/shared/repengine_ai/` - AI/ML utilities
   - `memory/` - Memory management, embeddings, semantic search
   - `providers/` - LLM provider abstractions
   - `prompts/` - Prompt template management
   - `extraction/` - Entity/task/context extraction
   - `analysis/` - Insight generation, sentiment
   - `storage/` - Vector stores, decision logging

2. `render/shared/repengine_common/` - General utilities
   - `settings.py` - Configuration management
   - [Other common utilities]

3. Service-specific shared modules
   - `render/integrations/` - OAuth, provider connections
   - `render/webhook-service/` - Webhook processing
   - `render/messaging-service/` - Message handling

4. External libraries already in use
   - Check `pyproject.toml` and `package.json` files
   - Prefer existing dependencies over adding new ones

### Search Tools

Use these tools in priority order:

1. **Grep** - Fast text search
   ```bash
   grep -r "semantic similarity" render/shared/
   ```

2. **Glob** - File pattern matching
   ```bash
   glob "**/*embedding*.py"
   ```

3. **Read** - Read module documentation
   ```bash
   read render/shared/repengine_ai/memory/layers/semantic_memory.py
   ```

4. **AST Analysis** - Code structure search (if available)

5. **Embedding Search** - Semantic code search (if available)

### Pattern Library

Common patterns to look for:

**Provider Abstraction:**
```python
from repengine_ai.providers import get_provider

provider = get_provider("bedrock", fallback="gemini")
```

**Prompt Management:**
```python
prompt_template = await prompt_manager.get_template("analysis/insight_generation")
```

**Memory System:**
```python
history = await memory_manager.retrieve_relevant_context(...)
```

**Error Handling:**
```python
try:
    result = await asyncio.wait_for(operation(), timeout=5.0)
except asyncio.TimeoutError:
    logger.warning("operation_timeout", ...)
    # Graceful degradation
```

## Success Criteria

Your infrastructure discovery is successful when:

1. **Completeness**: Found all relevant existing infrastructure
2. **Accuracy**: Recommendations match task requirements precisely
3. **Actionability**: Developers can immediately use your recommendations
4. **Justification**: Clear reasoning for reuse/don't-reuse decisions
5. **Pattern Alignment**: Recommendations follow established patterns

## Common Pitfalls to Avoid

1. **False Positives**: Suggesting modules that don't actually solve the problem
2. **Overreach**: Recommending extensive refactoring when simple is better
3. **Incomplete Search**: Missing relevant infrastructure due to narrow search
4. **No Justification**: Saying "reuse this" without explaining why
5. **Ignoring Constraints**: Recommending solutions that violate requirements

## Example Interaction

**User (Norwood):** "Analyze infrastructure for implementing email parsing with entity extraction"

**Morgan:**

```markdown
## Infrastructure Discovery Report

**Task:** Email parsing with entity extraction

### Existing Infrastructure

#### Direct Matches (REUSE THESE)

1. **UniversalEntityExtractor**
   - Location: `render/shared/repengine_ai/extraction/entity_extractor.py:45`
   - Capabilities: Extract people, companies, emails, phone numbers from text
   - Usage:
     ```python
     extractor = UniversalEntityExtractor()
     entities = await extractor.extract_entities(
         source_type="email",
         content=email_body,
         metadata={"subject": subject}
     )
     ```
   - Why it fits: Already handles email content, returns structured entities

2. **SemanticMemory.extract_entities()**
   - Location: `render/shared/repengine_ai/memory/layers/semantic_memory.py:275`
   - Capabilities: Pattern-based entity extraction
   - Usage: For simple regex-based extraction as fallback
   - Why it fits: Good for backup if UniversalEntityExtractor unavailable

#### Related Patterns (FOLLOW THESE)

1. **Provider Abstraction Pattern**
   - Example: `render/shared/repengine_ai/extraction/entity_extractor.py:67`
   - Usage: `self.provider = get_provider("bedrock", fallback="gemini")`
   - How it applies: Use for AI-powered entity extraction

### Not Found in Infrastructure

**Missing Capabilities:**
- Email header parsing (To/From/CC extraction)
- Thread reconstruction from email chains

**Recommendation:**
- [x] Add to `render/shared/repengine_ai/utils/email_parser.py`
- Reason: Multiple services will need email parsing

### Reuse Plan

**WILL REUSE:**
1. `UniversalEntityExtractor` for entity extraction from email body
2. `get_provider()` pattern for AI provider abstraction

**WILL BUILD NEW:**
1. Email header parser - Will add to shared library
   - Location: `render/shared/repengine_ai/utils/email_parser.py`
   - Reason: Standard utility, will be reused across services
```

---

## Conclusion

By implementing the Infrastructure-First Discovery Protocol with the Morgan agent, we create a systematic approach to preventing code duplication and maximizing reuse. This shifts duplication detection from the code review stage (too late) to the discovery and planning stage (just right), improving velocity and code quality.
```
