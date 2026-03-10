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
// ============================================================================
// Core Types
// ============================================================================
export * from './types/index.js';
// ============================================================================
// Plugin Interface & Base
// ============================================================================
export { validatePlugin, validatePluginMetadata, PLUGIN_EVENTS, } from './core/plugin-interface.js';
export { BasePlugin, createSimplePlugin, } from './core/base-plugin.js';
// ============================================================================
// Plugin Registry
// ============================================================================
export { PluginRegistry, getDefaultRegistry, setDefaultRegistry, } from './registry/plugin-registry.js';
// ============================================================================
// SDK Builders
// ============================================================================
export { PluginBuilder, MCPToolBuilder, HookBuilder, WorkerBuilder, createToolPlugin, createHooksPlugin, createWorkerPlugin, createProviderPlugin, } from './sdk/index.js';
// ============================================================================
// Workers
// ============================================================================
export { WorkerPool, WorkerInstance, WorkerFactory, WORKER_EVENTS, } from './workers/index.js';
// ============================================================================
// Hooks
// ============================================================================
export { HookRegistry, HookBuilder as HookBuilderAdvanced, HookFactory, HookExecutor, HookEvent, HookPriority, } from './hooks/index.js';
// ============================================================================
// Providers
// ============================================================================
export { ProviderRegistry, BaseLLMProvider, ProviderFactory, PROVIDER_EVENTS, } from './providers/index.js';
// ============================================================================
// Integrations
// ============================================================================
export { 
// Agentic Flow
AgenticFlowBridge, getAgenticFlowBridge, AGENTIC_FLOW_EVENTS, 
// AgentDB
AgentDBBridge, getAgentDBBridge, resetBridges, } from './integrations/index.js';
// ============================================================================
// Security
// ============================================================================
export { Security, validateString, validateNumber, validateBoolean, validateArray, validateEnum, validatePath, validateCommand, safePath, safePathAsync, safeJsonParse, safeJsonStringify, escapeShellArg, sanitizeError, sanitizeErrorMessage, createRateLimiter, createResourceLimiter, generateSecureId, generateSecureToken, hashString, constantTimeCompare, } from './security/index.js';
// ============================================================================
// Version
// ============================================================================
export const VERSION = '3.0.0-alpha.1';
export const SDK_VERSION = '1.0.0';
// ============================================================================
// Quick Start Utilities
// ============================================================================
import { PluginBuilder } from './sdk/index.js';
import { getDefaultRegistry } from './registry/plugin-registry.js';
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
export async function quickPlugin(name, version, configure, config) {
    const builder = new PluginBuilder(name, version);
    configure(builder);
    return builder.buildAndRegister(config);
}
/**
 * Load and register a plugin module dynamically.
 *
 * @example
 * ```typescript
 * const plugin = await loadPlugin('./my-plugin.js');
 * ```
 */
export async function loadPlugin(modulePath, config) {
    const module = await import(modulePath);
    const pluginOrFactory = module.default ?? module.plugin;
    if (!pluginOrFactory) {
        throw new Error(`Module ${modulePath} does not export a plugin`);
    }
    const plugin = typeof pluginOrFactory === 'function'
        ? await pluginOrFactory()
        : pluginOrFactory;
    await getDefaultRegistry().register(plugin, config);
    return plugin;
}
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
export async function initializePlugins(_options) {
    const registry = getDefaultRegistry();
    await registry.initialize();
}
/**
 * Shutdown the plugin system.
 */
export async function shutdownPlugins() {
    const registry = getDefaultRegistry();
    await registry.shutdown();
}
//# sourceMappingURL=index.js.map