/**
 * Core Plugin Interface
 *
 * Defines the contract that all plugins must implement.
 */
import type { PluginMetadata, PluginContext, PluginLifecycleState, AgentTypeDefinition, TaskTypeDefinition, MCPToolDefinition, CLICommandDefinition, MemoryBackendFactory, HookDefinition, WorkerDefinition, LLMProviderDefinition, HealthCheckResult } from '../types/index.js';
/**
 * Core plugin interface that all plugins must implement.
 *
 * Plugins provide extensibility across multiple domains:
 * - Agent types and task definitions
 * - MCP tools for Claude interaction
 * - CLI commands for terminal interface
 * - Memory backends for storage
 * - Hooks for lifecycle events
 * - Workers for parallel execution
 * - LLM providers for model access
 */
export interface IPlugin {
    /** Plugin metadata (name, version, etc.) */
    readonly metadata: PluginMetadata;
    /** Current lifecycle state */
    readonly state: PluginLifecycleState;
    /**
     * Initialize the plugin with context.
     * Called once when the plugin is loaded.
     */
    initialize(context: PluginContext): Promise<void>;
    /**
     * Shutdown the plugin gracefully.
     * Called when the plugin is being unloaded.
     */
    shutdown(): Promise<void>;
    /**
     * Check plugin health.
     * Called periodically for monitoring.
     */
    healthCheck?(): Promise<HealthCheckResult>;
    /**
     * Register agent type definitions.
     * Called during initialization to collect agent types.
     */
    registerAgentTypes?(): AgentTypeDefinition[];
    /**
     * Register task type definitions.
     * Called during initialization to collect task types.
     */
    registerTaskTypes?(): TaskTypeDefinition[];
    /**
     * Register MCP tool definitions.
     * Called during initialization to expose tools to Claude.
     */
    registerMCPTools?(): MCPToolDefinition[];
    /**
     * Register CLI command definitions.
     * Called during initialization to extend the CLI.
     */
    registerCLICommands?(): CLICommandDefinition[];
    /**
     * Register memory backend factories.
     * Called during initialization to add storage options.
     */
    registerMemoryBackends?(): MemoryBackendFactory[];
    /**
     * Register hook definitions.
     * Called during initialization to add lifecycle hooks.
     */
    registerHooks?(): HookDefinition[];
    /**
     * Register worker definitions.
     * Called during initialization to add worker types.
     */
    registerWorkers?(): WorkerDefinition[];
    /**
     * Register LLM provider definitions.
     * Called during initialization to add model providers.
     */
    registerProviders?(): LLMProviderDefinition[];
}
/**
 * Factory function type for creating plugin instances.
 */
export type PluginFactory = () => IPlugin | Promise<IPlugin>;
/**
 * Plugin module export interface.
 * Plugins should export a default factory or plugin instance.
 */
export interface PluginModule {
    default: IPlugin | PluginFactory;
    metadata?: PluginMetadata;
}
export declare const PLUGIN_EVENTS: {
    readonly LOADING: "plugin:loading";
    readonly LOADED: "plugin:loaded";
    readonly INITIALIZING: "plugin:initializing";
    readonly INITIALIZED: "plugin:initialized";
    readonly SHUTTING_DOWN: "plugin:shutting-down";
    readonly SHUTDOWN: "plugin:shutdown";
    readonly ERROR: "plugin:error";
    readonly HEALTH_CHECK: "plugin:health-check";
};
export type PluginEvent = typeof PLUGIN_EVENTS[keyof typeof PLUGIN_EVENTS];
/**
 * Validate plugin metadata.
 */
export declare function validatePluginMetadata(metadata: unknown): metadata is PluginMetadata;
/**
 * Validate plugin interface.
 */
export declare function validatePlugin(plugin: unknown): plugin is IPlugin;
//# sourceMappingURL=plugin-interface.d.ts.map