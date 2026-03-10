/**
 * Base Plugin Implementation
 *
 * Abstract base class that provides common plugin functionality.
 * Plugins should extend this class for easier implementation.
 */
import { EventEmitter } from 'events';
import type { PluginMetadata, PluginContext, PluginLifecycleState, PluginConfig, ILogger, IEventBus, ServiceContainer, AgentTypeDefinition, TaskTypeDefinition, MCPToolDefinition, CLICommandDefinition, MemoryBackendFactory, HookDefinition, WorkerDefinition, LLMProviderDefinition, HealthCheckResult } from '../types/index.js';
import type { IPlugin } from './plugin-interface.js';
/**
 * Abstract base class for plugins.
 *
 * Provides:
 * - Lifecycle management
 * - Logging and event emission
 * - Configuration access
 * - Service container access
 * - Default implementations for optional methods
 *
 * @example
 * ```typescript
 * class MyPlugin extends BasePlugin {
 *   constructor() {
 *     super({
 *       name: 'my-plugin',
 *       version: '1.0.0',
 *       description: 'My custom plugin'
 *     });
 *   }
 *
 *   protected async onInitialize(): Promise<void> {
 *     this.logger.info('Plugin initialized');
 *   }
 *
 *   registerMCPTools(): MCPToolDefinition[] {
 *     return [{
 *       name: 'my-tool',
 *       description: 'My custom tool',
 *       inputSchema: { type: 'object', properties: {} },
 *       handler: async (input) => ({
 *         content: [{ type: 'text', text: 'Hello!' }]
 *       })
 *     }];
 *   }
 * }
 * ```
 */
export declare abstract class BasePlugin extends EventEmitter implements IPlugin {
    readonly metadata: PluginMetadata;
    private _state;
    private _context;
    private _initTime;
    constructor(metadata: PluginMetadata);
    get state(): PluginLifecycleState;
    protected setState(state: PluginLifecycleState): void;
    protected get context(): PluginContext;
    protected get config(): PluginConfig;
    protected get logger(): ILogger;
    protected get eventBus(): IEventBus;
    protected get services(): ServiceContainer;
    protected get settings(): Record<string, unknown>;
    /**
     * Initialize the plugin.
     * Subclasses should override onInitialize() instead of this method.
     */
    initialize(context: PluginContext): Promise<void>;
    /**
     * Shutdown the plugin.
     * Subclasses should override onShutdown() instead of this method.
     */
    shutdown(): Promise<void>;
    /**
     * Health check implementation.
     * Subclasses can override onHealthCheck() for custom checks.
     */
    healthCheck(): Promise<HealthCheckResult>;
    /**
     * Called during initialization.
     * Override this in subclasses to add initialization logic.
     */
    protected onInitialize(): Promise<void>;
    /**
     * Called during shutdown.
     * Override this in subclasses to add cleanup logic.
     */
    protected onShutdown(): Promise<void>;
    /**
     * Called during health check.
     * Override this in subclasses to add custom health checks.
     */
    protected onHealthCheck(): Promise<Record<string, {
        healthy: boolean;
        message?: string;
    }>>;
    /**
     * Validate plugin dependencies are available.
     */
    protected validateDependencies(): Promise<void>;
    /**
     * Validate plugin configuration.
     * Override this in subclasses to add config validation.
     */
    protected validateConfig(): Promise<void>;
    registerAgentTypes?(): AgentTypeDefinition[];
    registerTaskTypes?(): TaskTypeDefinition[];
    registerMCPTools?(): MCPToolDefinition[];
    registerCLICommands?(): CLICommandDefinition[];
    registerMemoryBackends?(): MemoryBackendFactory[];
    registerHooks?(): HookDefinition[];
    registerWorkers?(): WorkerDefinition[];
    registerProviders?(): LLMProviderDefinition[];
    /**
     * Get setting value with type safety.
     */
    protected getSetting<T>(key: string, defaultValue?: T): T | undefined;
    /**
     * Get uptime in milliseconds.
     */
    protected getUptime(): number;
    /**
     * Create a child logger with context.
     */
    protected createChildLogger(context: Record<string, unknown>): ILogger;
}
/**
 * Configuration for creating a simple plugin.
 */
export interface SimplePluginConfig {
    metadata: PluginMetadata;
    onInitialize?: (context: PluginContext) => Promise<void>;
    onShutdown?: () => Promise<void>;
    agentTypes?: AgentTypeDefinition[];
    taskTypes?: TaskTypeDefinition[];
    mcpTools?: MCPToolDefinition[];
    cliCommands?: CLICommandDefinition[];
    hooks?: HookDefinition[];
    workers?: WorkerDefinition[];
    providers?: LLMProviderDefinition[];
}
/**
 * Create a simple plugin from configuration.
 *
 * @example
 * ```typescript
 * const myPlugin = createSimplePlugin({
 *   metadata: { name: 'my-plugin', version: '1.0.0' },
 *   mcpTools: [{
 *     name: 'hello',
 *     description: 'Say hello',
 *     inputSchema: { type: 'object', properties: {} },
 *     handler: async () => ({ content: [{ type: 'text', text: 'Hello!' }] })
 *   }]
 * });
 * ```
 */
export declare function createSimplePlugin(config: SimplePluginConfig): IPlugin;
//# sourceMappingURL=base-plugin.d.ts.map