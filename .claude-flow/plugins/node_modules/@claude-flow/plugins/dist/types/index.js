/**
 * @claude-flow/plugins - Core Type Definitions
 *
 * Unified type system for plugins, workers, hooks, and providers.
 */
// ============================================================================
// Hook Types
// ============================================================================
export var HookEvent;
(function (HookEvent) {
    // Tool lifecycle
    HookEvent["PreToolUse"] = "hook:pre-tool-use";
    HookEvent["PostToolUse"] = "hook:post-tool-use";
    // Session lifecycle
    HookEvent["SessionStart"] = "hook:session-start";
    HookEvent["SessionEnd"] = "hook:session-end";
    HookEvent["SessionRestore"] = "hook:session-restore";
    // Task execution
    HookEvent["PreTaskExecute"] = "hook:pre-task-execute";
    HookEvent["PostTaskComplete"] = "hook:post-task-complete";
    HookEvent["TaskFailed"] = "hook:task-failed";
    // File operations
    HookEvent["PreFileWrite"] = "hook:pre-file-write";
    HookEvent["PostFileWrite"] = "hook:post-file-write";
    HookEvent["PreFileDelete"] = "hook:pre-file-delete";
    // Command execution
    HookEvent["PreCommand"] = "hook:pre-command";
    HookEvent["PostCommand"] = "hook:post-command";
    // Agent operations
    HookEvent["AgentSpawned"] = "hook:agent-spawned";
    HookEvent["AgentTerminated"] = "hook:agent-terminated";
    // Memory operations
    HookEvent["PreMemoryStore"] = "hook:pre-memory-store";
    HookEvent["PostMemoryStore"] = "hook:post-memory-store";
    // Learning
    HookEvent["PatternDetected"] = "hook:pattern-detected";
    HookEvent["StrategyUpdated"] = "hook:strategy-updated";
    // Plugin lifecycle
    HookEvent["PluginLoaded"] = "hook:plugin-loaded";
    HookEvent["PluginUnloaded"] = "hook:plugin-unloaded";
})(HookEvent || (HookEvent = {}));
export var HookPriority;
(function (HookPriority) {
    HookPriority[HookPriority["Critical"] = 100] = "Critical";
    HookPriority[HookPriority["High"] = 75] = "High";
    HookPriority[HookPriority["Normal"] = 50] = "Normal";
    HookPriority[HookPriority["Low"] = 25] = "Low";
    HookPriority[HookPriority["Deferred"] = 0] = "Deferred";
})(HookPriority || (HookPriority = {}));
//# sourceMappingURL=index.js.map