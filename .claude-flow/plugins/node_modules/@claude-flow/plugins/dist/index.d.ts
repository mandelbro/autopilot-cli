/**
 * @claude-flow/plugins
 *
 * Unified Plugin SDK for Claude Flow v3
 *
 * This package provides a comprehensive plugin development framework including:
 * - Plugin lifecycle management
 * - Worker capabilities
 * - Hook system
 * - LLM provider integration
 * - Security utilities
 * - MCP tool development
 *
 * @example
 * ```typescript
 * import {
 *   PluginBuilder,
 *   HookEvent,
 *   HookPriority,
 *   WorkerFactory,
 *   ProviderFactory,
 *   Security,
 * } from '@claude-flow/plugins';
 *
 * // Create a plugin with the builder
 * const myPlugin = new PluginBuilder('my-plugin', '1.0.0')
 *   .withDescription('My awesome plugin')
 *   .withMCPTools([...])
 *   .withHooks([...])
 *   .withWorkers([...])
 *   .build();
 *
 * // Register with the default registry
 * await getDefaultRegistry().register(myPlugin);
 * ```
 *
 * @packageDocumentation
 */
export * from './types/index.js';
export { type IPlugin, type PluginFactory, type PluginModule, type PluginEvent, validatePlugin, validatePluginMetadata, PLUGIN_EVENTS, } from './core/plugin-interface.js';
export { BasePlugin, createSimplePlugin, type SimplePluginConfig, } from './core/base-plugin.js';
export { PluginRegistry, getDefaultRegistry, setDefaultRegistry, type PluginRegistryConfig, type PluginEntry, type RegistryStats, } from './registry/plugin-registry.js';
export { PluginBuilder, MCPToolBuilder, HookBuilder, WorkerBuilder, createToolPlugin, createHooksPlugin, createWorkerPlugin, createProviderPlugin, } from './sdk/index.js';
export { WorkerPool, WorkerInstance, WorkerFactory, WORKER_EVENTS, type IWorkerPool, type IWorkerInstance, type WorkerTask, type WorkerTaskResult, type WorkerPoolConfig, type PoolMetrics, type WorkerEvent, } from './workers/index.js';
export { HookRegistry, HookBuilder as HookBuilderAdvanced, HookFactory, HookExecutor, HookEvent, HookPriority, type HookRegistryConfig, type HookEntry, type HookRegistryStats, } from './hooks/index.js';
export { ProviderRegistry, BaseLLMProvider, ProviderFactory, PROVIDER_EVENTS, type ILLMProvider, type RateLimitStatus, type ProviderRegistryConfig, type ProviderEntry, type ProviderRegistryStats, type RetryConfig, type ProviderEvent, } from './providers/index.js';
export { AgenticFlowBridge, getAgenticFlowBridge, AGENTIC_FLOW_EVENTS, type AgenticFlowConfig, type SwarmTopology, type AgentSpawnOptions, type SpawnedAgent, type TaskOrchestrationOptions, type OrchestrationResult, type AgenticFlowEvent, AgentDBBridge, getAgentDBBridge, resetBridges, type AgentDBConfig, type VectorEntry, type VectorSearchOptions, type VectorSearchResult, } from './integrations/index.js';
export { Security, validateString, validateNumber, validateBoolean, validateArray, validateEnum, validatePath, validateCommand, safePath, safePathAsync, safeJsonParse, safeJsonStringify, escapeShellArg, sanitizeError, sanitizeErrorMessage, createRateLimiter, createResourceLimiter, generateSecureId, generateSecureToken, hashString, constantTimeCompare, type RateLimiter, type ResourceLimits, } from './security/index.js';
export declare const VERSION = "3.0.0-alpha.1";
export declare const SDK_VERSION = "1.0.0";
import { PluginBuilder } from './sdk/index.js';
import type { IPlugin } from './core/plugin-interface.js';
import type { PluginConfig } from './types/index.js';
/**
 * Quick start: Create and register a plugin in one call.
 *
 * @example
 * ```typescript
 * const plugin = await quickPlugin('my-plugin', '1.0.0', (builder) => {
 *   builder
 *     .withDescription('Quick plugin')
 *     .withMCPTools([...]);
 * });
 * ```
 */
export declare function quickPlugin(name: string, version: string, configure: (builder: PluginBuilder) => void, config?: Partial<PluginConfig>): Promise<IPlugin>;
/**
 * Load and register a plugin module dynamically.
 *
 * @example
 * ```typescript
 * const plugin = await loadPlugin('./my-plugin.js');
 * ```
 */
export declare function loadPlugin(modulePath: string, config?: Partial<PluginConfig>): Promise<IPlugin>;
/**
 * Initialize the plugin system.
 *
 * @example
 * ```typescript
 * await initializePlugins({
 *   coreVersion: '3.0.0',
 *   dataDir: './data',
 * });
 * ```
 */
export declare function initializePlugins(_options?: {
    coreVersion?: string;
    dataDir?: string;
}): Promise<void>;
/**
 * Shutdown the plugin system.
 */
export declare function shutdownPlugins(): Promise<void>;
//# sourceMappingURL=index.d.ts.map