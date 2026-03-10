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
import { HookEvent, HookPriority, } from '../types/index.js';
import { BasePlugin, createSimplePlugin } from '../core/base-plugin.js';
import { validatePlugin, validatePluginMetadata, PLUGIN_EVENTS } from '../core/plugin-interface.js';
import { PluginRegistry, getDefaultRegistry, setDefaultRegistry } from '../registry/plugin-registry.js';
// ============================================================================
// SDK Builder Pattern
// ============================================================================
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
export class PluginBuilder {
    metadata;
    agentTypes = [];
    taskTypes = [];
    mcpTools = [];
    cliCommands = [];
    hooks = [];
    workers = [];
    providers = [];
    initHandler;
    shutdownHandler;
    constructor(name, version) {
        this.metadata = { name, version };
    }
    // =========================================================================
    // Metadata Configuration
    // =========================================================================
    withDescription(description) {
        this.metadata = { ...this.metadata, description };
        return this;
    }
    withAuthor(author) {
        this.metadata = { ...this.metadata, author };
        return this;
    }
    withLicense(license) {
        this.metadata = { ...this.metadata, license };
        return this;
    }
    withRepository(repository) {
        this.metadata = { ...this.metadata, repository };
        return this;
    }
    withDependencies(dependencies) {
        this.metadata = { ...this.metadata, dependencies };
        return this;
    }
    withTags(tags) {
        this.metadata = { ...this.metadata, tags };
        return this;
    }
    withMinCoreVersion(minCoreVersion) {
        this.metadata = { ...this.metadata, minCoreVersion };
        return this;
    }
    // =========================================================================
    // Extension Points
    // =========================================================================
    withAgentTypes(types) {
        this.agentTypes.push(...types);
        return this;
    }
    withTaskTypes(types) {
        this.taskTypes.push(...types);
        return this;
    }
    withMCPTools(tools) {
        this.mcpTools.push(...tools);
        return this;
    }
    withCLICommands(commands) {
        this.cliCommands.push(...commands);
        return this;
    }
    withHooks(hooks) {
        this.hooks.push(...hooks);
        return this;
    }
    withWorkers(workers) {
        this.workers.push(...workers);
        return this;
    }
    withProviders(providers) {
        this.providers.push(...providers);
        return this;
    }
    // =========================================================================
    // Lifecycle Handlers
    // =========================================================================
    onInitialize(handler) {
        this.initHandler = handler;
        return this;
    }
    onShutdown(handler) {
        this.shutdownHandler = handler;
        return this;
    }
    // =========================================================================
    // Build
    // =========================================================================
    build() {
        return createSimplePlugin({
            metadata: this.metadata,
            onInitialize: this.initHandler,
            onShutdown: this.shutdownHandler,
            agentTypes: this.agentTypes.length > 0 ? this.agentTypes : undefined,
            taskTypes: this.taskTypes.length > 0 ? this.taskTypes : undefined,
            mcpTools: this.mcpTools.length > 0 ? this.mcpTools : undefined,
            cliCommands: this.cliCommands.length > 0 ? this.cliCommands : undefined,
            hooks: this.hooks.length > 0 ? this.hooks : undefined,
            workers: this.workers.length > 0 ? this.workers : undefined,
            providers: this.providers.length > 0 ? this.providers : undefined,
        });
    }
    /**
     * Build and automatically register with the default registry.
     */
    async buildAndRegister(config) {
        const plugin = this.build();
        await getDefaultRegistry().register(plugin, config);
        return plugin;
    }
}
// ============================================================================
// Quick Plugin Creation Helpers
// ============================================================================
/**
 * Create a tool-only plugin quickly.
 */
export function createToolPlugin(name, version, tools) {
    return new PluginBuilder(name, version)
        .withMCPTools(tools)
        .build();
}
/**
 * Create a hooks-only plugin quickly.
 */
export function createHooksPlugin(name, version, hooks) {
    return new PluginBuilder(name, version)
        .withHooks(hooks)
        .build();
}
/**
 * Create a worker plugin quickly.
 */
export function createWorkerPlugin(name, version, workers) {
    return new PluginBuilder(name, version)
        .withWorkers(workers)
        .build();
}
/**
 * Create a provider plugin quickly.
 */
export function createProviderPlugin(name, version, providers) {
    return new PluginBuilder(name, version)
        .withProviders(providers)
        .build();
}
// ============================================================================
// Tool Builder
// ============================================================================
/**
 * Builder for creating MCP tools with validation.
 */
export class MCPToolBuilder {
    name;
    description = '';
    properties = {};
    required = [];
    handler;
    constructor(name) {
        this.name = name;
    }
    withDescription(description) {
        this.description = description;
        return this;
    }
    addStringParam(name, description, options) {
        this.properties[name] = {
            type: 'string',
            description,
            default: options?.default,
            enum: options?.enum,
        };
        if (options?.required) {
            this.required.push(name);
        }
        return this;
    }
    addNumberParam(name, description, options) {
        this.properties[name] = {
            type: 'number',
            description,
            default: options?.default,
            minimum: options?.minimum,
            maximum: options?.maximum,
        };
        if (options?.required) {
            this.required.push(name);
        }
        return this;
    }
    addBooleanParam(name, description, options) {
        this.properties[name] = {
            type: 'boolean',
            description,
            default: options?.default,
        };
        if (options?.required) {
            this.required.push(name);
        }
        return this;
    }
    addObjectParam(name, description, schema, options) {
        this.properties[name] = {
            ...schema,
            description,
        };
        if (options?.required) {
            this.required.push(name);
        }
        return this;
    }
    addArrayParam(name, description, itemsSchema, options) {
        this.properties[name] = {
            type: 'array',
            description,
            items: itemsSchema,
        };
        if (options?.required) {
            this.required.push(name);
        }
        return this;
    }
    withHandler(handler) {
        this.handler = handler;
        return this;
    }
    build() {
        if (!this.handler) {
            throw new Error(`Tool ${this.name} requires a handler`);
        }
        return {
            name: this.name,
            description: this.description,
            inputSchema: {
                type: 'object',
                properties: this.properties,
                required: this.required.length > 0 ? this.required : undefined,
            },
            handler: this.handler,
        };
    }
}
// ============================================================================
// Hook Builder
// ============================================================================
/**
 * Builder for creating hooks with validation.
 */
export class HookBuilder {
    event;
    name;
    description;
    priority = HookPriority.Normal;
    async = true;
    handler;
    constructor(event) {
        this.event = event;
    }
    withName(name) {
        this.name = name;
        return this;
    }
    withDescription(description) {
        this.description = description;
        return this;
    }
    withPriority(priority) {
        this.priority = priority;
        return this;
    }
    synchronous() {
        this.async = false;
        return this;
    }
    withHandler(handler) {
        this.handler = handler;
        return this;
    }
    build() {
        if (!this.handler) {
            throw new Error(`Hook for event ${this.event} requires a handler`);
        }
        return {
            event: this.event,
            handler: this.handler,
            priority: this.priority,
            name: this.name,
            description: this.description,
            async: this.async,
        };
    }
}
// ============================================================================
// Worker Builder
// ============================================================================
/**
 * Builder for creating workers with validation.
 */
export class WorkerBuilder {
    type;
    name;
    description;
    capabilities = [];
    specialization;
    maxConcurrentTasks = 5;
    timeout = 30000;
    priority = 50;
    metadata = {};
    constructor(type, name) {
        this.type = type;
        this.name = name;
    }
    withDescription(description) {
        this.description = description;
        return this;
    }
    withCapabilities(capabilities) {
        this.capabilities.push(...capabilities);
        return this;
    }
    withSpecialization(vector) {
        this.specialization = vector;
        return this;
    }
    withMaxConcurrentTasks(max) {
        this.maxConcurrentTasks = max;
        return this;
    }
    withTimeout(timeout) {
        this.timeout = timeout;
        return this;
    }
    withPriority(priority) {
        this.priority = priority;
        return this;
    }
    withMetadata(metadata) {
        this.metadata = { ...this.metadata, ...metadata };
        return this;
    }
    build() {
        return {
            type: this.type,
            name: this.name,
            description: this.description,
            capabilities: this.capabilities,
            specialization: this.specialization,
            maxConcurrentTasks: this.maxConcurrentTasks,
            timeout: this.timeout,
            priority: this.priority,
            metadata: Object.keys(this.metadata).length > 0 ? this.metadata : undefined,
        };
    }
}
// ============================================================================
// Exports
// ============================================================================
// Re-export core types and interfaces
export { HookEvent, HookPriority, validatePlugin, validatePluginMetadata, PLUGIN_EVENTS, 
// Base plugin
BasePlugin, createSimplePlugin, 
// Registry
PluginRegistry, getDefaultRegistry, setDefaultRegistry, };
//# sourceMappingURL=index.js.map