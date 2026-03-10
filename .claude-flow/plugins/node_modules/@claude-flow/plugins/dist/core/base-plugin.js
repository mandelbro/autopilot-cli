/**
 * Base Plugin Implementation
 *
 * Abstract base class that provides common plugin functionality.
 * Plugins should extend this class for easier implementation.
 */
import { EventEmitter } from 'events';
import { PLUGIN_EVENTS } from './plugin-interface.js';
// ============================================================================
// Base Plugin
// ============================================================================
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
export class BasePlugin extends EventEmitter {
    // =========================================================================
    // Properties
    // =========================================================================
    metadata;
    _state = 'uninitialized';
    _context = null;
    _initTime = null;
    // =========================================================================
    // Constructor
    // =========================================================================
    constructor(metadata) {
        super();
        this.metadata = Object.freeze(metadata);
    }
    // =========================================================================
    // State Management
    // =========================================================================
    get state() {
        return this._state;
    }
    setState(state) {
        const previousState = this._state;
        this._state = state;
        this.emit('stateChange', { previousState, currentState: state });
    }
    // =========================================================================
    // Context Accessors
    // =========================================================================
    get context() {
        if (!this._context) {
            throw new Error(`Plugin ${this.metadata.name} not initialized`);
        }
        return this._context;
    }
    get config() {
        return this.context.config;
    }
    get logger() {
        return this.context.logger;
    }
    get eventBus() {
        return this.context.eventBus;
    }
    get services() {
        return this.context.services;
    }
    get settings() {
        return this.config.settings;
    }
    // =========================================================================
    // Lifecycle Implementation
    // =========================================================================
    /**
     * Initialize the plugin.
     * Subclasses should override onInitialize() instead of this method.
     */
    async initialize(context) {
        if (this._state !== 'uninitialized') {
            throw new Error(`Plugin ${this.metadata.name} already initialized`);
        }
        this.setState('initializing');
        this._context = context;
        this._initTime = new Date();
        try {
            // Validate dependencies
            await this.validateDependencies();
            // Validate configuration
            await this.validateConfig();
            // Call subclass initialization
            await this.onInitialize();
            this.setState('initialized');
            this.eventBus.emit(PLUGIN_EVENTS.INITIALIZED, { plugin: this.metadata.name });
        }
        catch (error) {
            this.setState('error');
            this.eventBus.emit(PLUGIN_EVENTS.ERROR, {
                plugin: this.metadata.name,
                error: error instanceof Error ? error.message : String(error),
            });
            throw error;
        }
    }
    /**
     * Shutdown the plugin.
     * Subclasses should override onShutdown() instead of this method.
     */
    async shutdown() {
        if (this._state !== 'initialized' && this._state !== 'error') {
            return; // Already shutdown or never initialized
        }
        this.setState('shutting-down');
        try {
            await this.onShutdown();
            this.setState('shutdown');
            this.eventBus.emit(PLUGIN_EVENTS.SHUTDOWN, { plugin: this.metadata.name });
        }
        catch (error) {
            this.setState('error');
            throw error;
        }
        finally {
            this._context = null;
        }
    }
    /**
     * Health check implementation.
     * Subclasses can override onHealthCheck() for custom checks.
     */
    async healthCheck() {
        const checks = {};
        // Check state
        const stateHealthy = this._state === 'initialized';
        checks['state'] = {
            healthy: stateHealthy,
            message: stateHealthy ? 'Plugin initialized' : `State: ${this._state}`,
        };
        // Run custom health checks
        const startTime = Date.now();
        try {
            const customChecks = await this.onHealthCheck();
            Object.assign(checks, customChecks);
        }
        catch (error) {
            checks['custom'] = {
                healthy: false,
                message: error instanceof Error ? error.message : 'Health check failed',
                latencyMs: Date.now() - startTime,
            };
        }
        const allHealthy = Object.values(checks).every(c => c.healthy);
        return {
            healthy: allHealthy,
            status: allHealthy ? 'healthy' : 'unhealthy',
            checks,
            timestamp: new Date(),
        };
    }
    // =========================================================================
    // Lifecycle Hooks (Override in subclasses)
    // =========================================================================
    /**
     * Called during initialization.
     * Override this in subclasses to add initialization logic.
     */
    async onInitialize() {
        // Default: no-op
    }
    /**
     * Called during shutdown.
     * Override this in subclasses to add cleanup logic.
     */
    async onShutdown() {
        // Default: no-op
    }
    /**
     * Called during health check.
     * Override this in subclasses to add custom health checks.
     */
    async onHealthCheck() {
        return {};
    }
    // =========================================================================
    // Validation
    // =========================================================================
    /**
     * Validate plugin dependencies are available.
     */
    async validateDependencies() {
        const deps = this.metadata.dependencies ?? [];
        for (const dep of deps) {
            // Dependencies are validated by the PluginManager
            // This hook allows plugins to do additional checks
            this.logger.debug(`Dependency validated: ${dep}`);
        }
    }
    /**
     * Validate plugin configuration.
     * Override this in subclasses to add config validation.
     */
    async validateConfig() {
        // Default: no-op
    }
    // =========================================================================
    // Utility Methods
    // =========================================================================
    /**
     * Get setting value with type safety.
     */
    getSetting(key, defaultValue) {
        const value = this.settings[key];
        if (value === undefined)
            return defaultValue;
        return value;
    }
    /**
     * Get uptime in milliseconds.
     */
    getUptime() {
        if (!this._initTime)
            return 0;
        return Date.now() - this._initTime.getTime();
    }
    /**
     * Create a child logger with context.
     */
    createChildLogger(context) {
        return this.logger.child({ plugin: this.metadata.name, ...context });
    }
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
export function createSimplePlugin(config) {
    return new SimplePlugin(config);
}
class SimplePlugin extends BasePlugin {
    _config;
    constructor(config) {
        super(config.metadata);
        this._config = config;
    }
    async onInitialize() {
        if (this._config.onInitialize) {
            await this._config.onInitialize(this.context);
        }
    }
    async onShutdown() {
        if (this._config.onShutdown) {
            await this._config.onShutdown();
        }
    }
    registerAgentTypes() {
        return this._config.agentTypes ?? [];
    }
    registerTaskTypes() {
        return this._config.taskTypes ?? [];
    }
    registerMCPTools() {
        return this._config.mcpTools ?? [];
    }
    registerCLICommands() {
        return this._config.cliCommands ?? [];
    }
    registerHooks() {
        return this._config.hooks ?? [];
    }
    registerWorkers() {
        return this._config.workers ?? [];
    }
    registerProviders() {
        return this._config.providers ?? [];
    }
}
//# sourceMappingURL=base-plugin.js.map