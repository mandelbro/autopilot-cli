/**
 * Plugin SDK - Unified API for Claude Flow Plugin Development
 *
 * Provides a comprehensive SDK for building plugins with full access to:
 * - Plugin lifecycle management
 * - Worker capabilities
 * - Hook system
 * - Memory backends (AgentDB integration)
 * - LLM providers
 * - MCP tools
 */
import { HookEvent, HookPriority, type PluginMetadata, type PluginContext, type PluginConfig, type ILogger, type IEventBus, type ServiceContainer, type AgentTypeDefinition, type TaskTypeDefinition, type MCPToolDefinition, type CLICommandDefinition, type MemoryBackendFactory, type HookDefinition, type HookHandler, type WorkerDefinition, type WorkerType, type LLMProviderDefinition, type HealthCheckResult, type JSONSchema } from '../types/index.js';
import { BasePlugin, createSimplePlugin } from '../core/base-plugin.js';
import type { IPlugin, PluginFactory } from '../core/plugin-interface.js';
import { validatePlugin, validatePluginMetadata, PLUGIN_EVENTS } from '../core/plugin-interface.js';
import { PluginRegistry, getDefaultRegistry, setDefaultRegistry } from '../registry/plugin-registry.js';
/**
 * Plugin builder for fluent plugin creation.
 *
 * @example
 * ```typescript
 * const myPlugin = new PluginBuilder('my-plugin', '1.0.0')
 *   .withDescription('My awesome plugin')
 *   .withMCPTools([{
 *     name: 'my-tool',
 *     description: 'Does something useful',
 *     inputSchema: { type: 'object', properties: {} },
 *     handler: async (input) => ({ content: [{ type: 'text', text: 'Done!' }] })
 *   }])
 *   .withHooks([{
 *     event: HookEvent.PostTaskComplete,
 *     handler: async (ctx) => ({ success: true })
 *   }])
 *   .onInitialize(async (ctx) => {
 *     console.log('Plugin initialized!');
 *   })
 *   .build();
 * ```
 */
export declare class PluginBuilder {
    private metadata;
    private agentTypes;
    private taskTypes;
    private mcpTools;
    private cliCommands;
    private hooks;
    private workers;
    private providers;
    private initHandler?;
    private shutdownHandler?;
    constructor(name: string, version: string);
    withDescription(description: string): this;
    withAuthor(author: string): this;
    withLicense(license: string): this;
    withRepository(repository: string): this;
    withDependencies(dependencies: string[]): this;
    withTags(tags: string[]): this;
    withMinCoreVersion(minCoreVersion: string): this;
    withAgentTypes(types: AgentTypeDefinition[]): this;
    withTaskTypes(types: TaskTypeDefinition[]): this;
    withMCPTools(tools: MCPToolDefinition[]): this;
    withCLICommands(commands: CLICommandDefinition[]): this;
    withHooks(hooks: HookDefinition[]): this;
    withWorkers(workers: WorkerDefinition[]): this;
    withProviders(providers: LLMProviderDefinition[]): this;
    onInitialize(handler: (context: PluginContext) => Promise<void>): this;
    onShutdown(handler: () => Promise<void>): this;
    build(): IPlugin;
    /**
     * Build and automatically register with the default registry.
     */
    buildAndRegister(config?: Partial<PluginConfig>): Promise<IPlugin>;
}
/**
 * Create a tool-only plugin quickly.
 */
export declare function createToolPlugin(name: string, version: string, tools: MCPToolDefinition[]): IPlugin;
/**
 * Create a hooks-only plugin quickly.
 */
export declare function createHooksPlugin(name: string, version: string, hooks: HookDefinition[]): IPlugin;
/**
 * Create a worker plugin quickly.
 */
export declare function createWorkerPlugin(name: string, version: string, workers: WorkerDefinition[]): IPlugin;
/**
 * Create a provider plugin quickly.
 */
export declare function createProviderPlugin(name: string, version: string, providers: LLMProviderDefinition[]): IPlugin;
/**
 * Builder for creating MCP tools with validation.
 */
export declare class MCPToolBuilder {
    private name;
    private description;
    private properties;
    private required;
    private handler?;
    constructor(name: string);
    withDescription(description: string): this;
    addStringParam(name: string, description: string, options?: {
        required?: boolean;
        default?: string;
        enum?: string[];
    }): this;
    addNumberParam(name: string, description: string, options?: {
        required?: boolean;
        default?: number;
        minimum?: number;
        maximum?: number;
    }): this;
    addBooleanParam(name: string, description: string, options?: {
        required?: boolean;
        default?: boolean;
    }): this;
    addObjectParam(name: string, description: string, schema: JSONSchema, options?: {
        required?: boolean;
    }): this;
    addArrayParam(name: string, description: string, itemsSchema: JSONSchema, options?: {
        required?: boolean;
    }): this;
    withHandler(handler: MCPToolDefinition['handler']): this;
    build(): MCPToolDefinition;
}
/**
 * Builder for creating hooks with validation.
 */
export declare class HookBuilder {
    private event;
    private name?;
    private description?;
    private priority;
    private async;
    private handler?;
    constructor(event: HookEvent);
    withName(name: string): this;
    withDescription(description: string): this;
    withPriority(priority: HookPriority): this;
    synchronous(): this;
    withHandler(handler: HookHandler): this;
    build(): HookDefinition;
}
/**
 * Builder for creating workers with validation.
 */
export declare class WorkerBuilder {
    private type;
    private name;
    private description?;
    private capabilities;
    private specialization?;
    private maxConcurrentTasks;
    private timeout;
    private priority;
    private metadata;
    constructor(type: WorkerType, name: string);
    withDescription(description: string): this;
    withCapabilities(capabilities: string[]): this;
    withSpecialization(vector: Float32Array): this;
    withMaxConcurrentTasks(max: number): this;
    withTimeout(timeout: number): this;
    withPriority(priority: number): this;
    withMetadata(metadata: Record<string, unknown>): this;
    build(): WorkerDefinition;
}
export { type PluginMetadata, type PluginContext, type PluginConfig, type ILogger, type IEventBus, type ServiceContainer, type AgentTypeDefinition, type TaskTypeDefinition, type MCPToolDefinition, type CLICommandDefinition, type MemoryBackendFactory, type HookDefinition, type HookHandler, type WorkerDefinition, type LLMProviderDefinition, type HealthCheckResult, type JSONSchema, HookEvent, HookPriority, type WorkerType, type IPlugin, type PluginFactory, validatePlugin, validatePluginMetadata, PLUGIN_EVENTS, BasePlugin, createSimplePlugin, PluginRegistry, getDefaultRegistry, setDefaultRegistry, };
//# sourceMappingURL=index.d.ts.map