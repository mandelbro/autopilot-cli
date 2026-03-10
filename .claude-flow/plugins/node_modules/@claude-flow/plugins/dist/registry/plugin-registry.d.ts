/**
 * Plugin Registry
 *
 * Manages plugin lifecycle, dependency resolution, and extension point collection.
 */
import { EventEmitter } from 'events';
import type { PluginConfig, PluginMetadata, IEventBus, ILogger, AgentTypeDefinition, TaskTypeDefinition, MCPToolDefinition, CLICommandDefinition, MemoryBackendFactory, HookDefinition, WorkerDefinition, LLMProviderDefinition, HealthCheckResult } from '../types/index.js';
import type { IPlugin, PluginFactory } from '../core/plugin-interface.js';
export interface PluginRegistryConfig {
    coreVersion: string;
    dataDir: string;
    logger?: ILogger;
    eventBus?: IEventBus;
    defaultConfig?: Partial<PluginConfig>;
    maxPlugins?: number;
    loadTimeout?: number;
}
export interface PluginEntry {
    plugin: IPlugin;
    config: PluginConfig;
    loadTime: Date;
    initTime?: Date;
    error?: string;
}
export interface RegistryStats {
    total: number;
    initialized: number;
    failed: number;
    agentTypes: number;
    taskTypes: number;
    mcpTools: number;
    cliCommands: number;
    hooks: number;
    workers: number;
    providers: number;
}
/**
 * Central registry for plugin management.
 *
 * Features:
 * - Plugin loading and unloading
 * - Dependency resolution
 * - Extension point collection
 * - Health monitoring
 * - Lifecycle management
 */
export declare class PluginRegistry extends EventEmitter {
    private readonly plugins;
    private readonly config;
    private readonly logger;
    private readonly eventBus;
    private readonly services;
    private initialized;
    private agentTypesCache;
    private taskTypesCache;
    private mcpToolsCache;
    private cliCommandsCache;
    private memoryBackendsCache;
    private hooksCache;
    private workersCache;
    private providersCache;
    constructor(config: PluginRegistryConfig);
    /**
     * Register a plugin.
     */
    register(plugin: IPlugin | PluginFactory, config?: Partial<PluginConfig>): Promise<void>;
    /**
     * Unregister a plugin.
     */
    unregister(name: string): Promise<void>;
    /**
     * Initialize all registered plugins.
     */
    initialize(): Promise<void>;
    /**
     * Shutdown all plugins.
     */
    shutdown(): Promise<void>;
    /**
     * Resolve dependencies and return load order.
     */
    private resolveDependencies;
    /**
     * Collect extension points from a plugin.
     */
    private collectExtensionPoints;
    /**
     * Invalidate extension point caches.
     */
    private invalidateCaches;
    getAgentTypes(): AgentTypeDefinition[];
    getTaskTypes(): TaskTypeDefinition[];
    getMCPTools(): MCPToolDefinition[];
    getCLICommands(): CLICommandDefinition[];
    getMemoryBackends(): MemoryBackendFactory[];
    getHooks(): HookDefinition[];
    getWorkers(): WorkerDefinition[];
    getProviders(): LLMProviderDefinition[];
    getPlugin(name: string): IPlugin | undefined;
    getPluginEntry(name: string): PluginEntry | undefined;
    listPlugins(): PluginMetadata[];
    /**
     * Run health checks on all plugins.
     */
    healthCheck(): Promise<Map<string, HealthCheckResult>>;
    getStats(): RegistryStats;
    private createPluginContext;
    private initializeWithTimeout;
}
export declare function getDefaultRegistry(): PluginRegistry;
export declare function setDefaultRegistry(registry: PluginRegistry): void;
//# sourceMappingURL=plugin-registry.d.ts.map