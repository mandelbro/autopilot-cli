/**
 * Plugin Registry
 *
 * Manages plugin lifecycle, dependency resolution, and extension point collection.
 */
import { EventEmitter } from 'events';
import { validatePlugin, PLUGIN_EVENTS } from '../core/plugin-interface.js';
// ============================================================================
// Default Implementations
// ============================================================================
class DefaultEventBus {
    emitter = new EventEmitter();
    emit(event, data) {
        this.emitter.emit(event, data);
    }
    on(event, handler) {
        this.emitter.on(event, handler);
        return () => this.off(event, handler);
    }
    off(event, handler) {
        this.emitter.off(event, handler);
    }
    once(event, handler) {
        this.emitter.once(event, handler);
        return () => this.off(event, handler);
    }
}
class DefaultLogger {
    context = {};
    constructor(context) {
        if (context)
            this.context = context;
    }
    debug(message, ...args) {
        console.debug(`[DEBUG]`, message, ...args, this.context);
    }
    info(message, ...args) {
        console.info(`[INFO]`, message, ...args, this.context);
    }
    warn(message, ...args) {
        console.warn(`[WARN]`, message, ...args, this.context);
    }
    error(message, ...args) {
        console.error(`[ERROR]`, message, ...args, this.context);
    }
    child(context) {
        return new DefaultLogger({ ...this.context, ...context });
    }
}
class DefaultServiceContainer {
    services = new Map();
    get(key) {
        return this.services.get(key);
    }
    set(key, value) {
        this.services.set(key, value);
    }
    has(key) {
        return this.services.has(key);
    }
    delete(key) {
        return this.services.delete(key);
    }
}
// ============================================================================
// Plugin Registry
// ============================================================================
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
export class PluginRegistry extends EventEmitter {
    // =========================================================================
    // Properties
    // =========================================================================
    plugins = new Map();
    config;
    logger;
    eventBus;
    services;
    initialized = false;
    // Extension point caches
    agentTypesCache = [];
    taskTypesCache = [];
    mcpToolsCache = [];
    cliCommandsCache = [];
    memoryBackendsCache = [];
    hooksCache = [];
    workersCache = [];
    providersCache = [];
    // =========================================================================
    // Constructor
    // =========================================================================
    constructor(config) {
        super();
        this.config = config;
        this.logger = config.logger ?? new DefaultLogger({ component: 'PluginRegistry' });
        this.eventBus = config.eventBus ?? new DefaultEventBus();
        this.services = new DefaultServiceContainer();
        // Register self in services
        this.services.set('pluginRegistry', this);
    }
    // =========================================================================
    // Plugin Loading
    // =========================================================================
    /**
     * Register a plugin.
     */
    async register(plugin, config) {
        // Resolve factory if needed
        const resolvedPlugin = typeof plugin === 'function' ? await plugin() : plugin;
        // Validate plugin
        if (!validatePlugin(resolvedPlugin)) {
            throw new Error('Invalid plugin: does not implement IPlugin interface');
        }
        const name = resolvedPlugin.metadata.name;
        // Check for duplicates
        if (this.plugins.has(name)) {
            throw new Error(`Plugin ${name} already registered`);
        }
        // Check max plugins
        if (this.config.maxPlugins && this.plugins.size >= this.config.maxPlugins) {
            throw new Error(`Maximum plugin limit (${this.config.maxPlugins}) reached`);
        }
        // Create config
        const pluginConfig = {
            enabled: true,
            priority: 50,
            settings: {},
            ...this.config.defaultConfig,
            ...config,
        };
        // Store entry
        const entry = {
            plugin: resolvedPlugin,
            config: pluginConfig,
            loadTime: new Date(),
        };
        this.plugins.set(name, entry);
        this.eventBus.emit(PLUGIN_EVENTS.LOADED, { plugin: name });
        this.logger.info(`Plugin registered: ${name} v${resolvedPlugin.metadata.version}`);
    }
    /**
     * Unregister a plugin.
     */
    async unregister(name) {
        const entry = this.plugins.get(name);
        if (!entry) {
            throw new Error(`Plugin ${name} not found`);
        }
        // Shutdown if initialized
        if (entry.plugin.state === 'initialized') {
            await entry.plugin.shutdown();
        }
        this.plugins.delete(name);
        this.invalidateCaches();
        this.logger.info(`Plugin unregistered: ${name}`);
    }
    // =========================================================================
    // Initialization
    // =========================================================================
    /**
     * Initialize all registered plugins.
     */
    async initialize() {
        if (this.initialized) {
            throw new Error('Registry already initialized');
        }
        // Resolve dependencies and get load order
        const loadOrder = this.resolveDependencies();
        // Initialize plugins in order
        for (const name of loadOrder) {
            const entry = this.plugins.get(name);
            if (!entry.config.enabled) {
                this.logger.info(`Plugin ${name} is disabled, skipping initialization`);
                continue;
            }
            try {
                const context = this.createPluginContext(entry);
                await this.initializeWithTimeout(entry.plugin, context);
                entry.initTime = new Date();
                this.collectExtensionPoints(entry.plugin);
                this.logger.info(`Plugin initialized: ${name}`);
            }
            catch (error) {
                entry.error = error instanceof Error ? error.message : String(error);
                this.logger.error(`Failed to initialize plugin ${name}: ${entry.error}`);
                // Continue with other plugins
            }
        }
        this.initialized = true;
        this.logger.info(`Registry initialized with ${this.plugins.size} plugins`);
    }
    /**
     * Shutdown all plugins.
     */
    async shutdown() {
        // Shutdown in reverse order
        const names = Array.from(this.plugins.keys()).reverse();
        for (const name of names) {
            const entry = this.plugins.get(name);
            if (entry.plugin.state === 'initialized') {
                try {
                    await entry.plugin.shutdown();
                    this.logger.info(`Plugin shutdown: ${name}`);
                }
                catch (error) {
                    this.logger.error(`Error shutting down plugin ${name}: ${error}`);
                }
            }
        }
        this.invalidateCaches();
        this.initialized = false;
    }
    // =========================================================================
    // Dependency Resolution
    // =========================================================================
    /**
     * Resolve dependencies and return load order.
     */
    resolveDependencies() {
        const visited = new Set();
        const visiting = new Set();
        const order = [];
        const visit = (name) => {
            if (visited.has(name))
                return;
            if (visiting.has(name)) {
                throw new Error(`Circular dependency detected: ${name}`);
            }
            const entry = this.plugins.get(name);
            if (!entry) {
                throw new Error(`Missing dependency: ${name}`);
            }
            visiting.add(name);
            const deps = entry.plugin.metadata.dependencies ?? [];
            for (const dep of deps) {
                visit(dep);
            }
            visiting.delete(name);
            visited.add(name);
            order.push(name);
        };
        for (const name of this.plugins.keys()) {
            visit(name);
        }
        return order;
    }
    // =========================================================================
    // Extension Points
    // =========================================================================
    /**
     * Collect extension points from a plugin.
     */
    collectExtensionPoints(plugin) {
        if (plugin.registerAgentTypes) {
            const types = plugin.registerAgentTypes();
            if (types)
                this.agentTypesCache.push(...types);
        }
        if (plugin.registerTaskTypes) {
            const types = plugin.registerTaskTypes();
            if (types)
                this.taskTypesCache.push(...types);
        }
        if (plugin.registerMCPTools) {
            const tools = plugin.registerMCPTools();
            if (tools)
                this.mcpToolsCache.push(...tools);
        }
        if (plugin.registerCLICommands) {
            const commands = plugin.registerCLICommands();
            if (commands)
                this.cliCommandsCache.push(...commands);
        }
        if (plugin.registerMemoryBackends) {
            const backends = plugin.registerMemoryBackends();
            if (backends)
                this.memoryBackendsCache.push(...backends);
        }
        if (plugin.registerHooks) {
            const hooks = plugin.registerHooks();
            if (hooks)
                this.hooksCache.push(...hooks);
        }
        if (plugin.registerWorkers) {
            const workers = plugin.registerWorkers();
            if (workers)
                this.workersCache.push(...workers);
        }
        if (plugin.registerProviders) {
            const providers = plugin.registerProviders();
            if (providers)
                this.providersCache.push(...providers);
        }
    }
    /**
     * Invalidate extension point caches.
     */
    invalidateCaches() {
        this.agentTypesCache = [];
        this.taskTypesCache = [];
        this.mcpToolsCache = [];
        this.cliCommandsCache = [];
        this.memoryBackendsCache = [];
        this.hooksCache = [];
        this.workersCache = [];
        this.providersCache = [];
        // Recollect from initialized plugins
        for (const entry of this.plugins.values()) {
            if (entry.plugin.state === 'initialized') {
                this.collectExtensionPoints(entry.plugin);
            }
        }
    }
    // =========================================================================
    // Getters
    // =========================================================================
    getAgentTypes() {
        return [...this.agentTypesCache];
    }
    getTaskTypes() {
        return [...this.taskTypesCache];
    }
    getMCPTools() {
        return [...this.mcpToolsCache];
    }
    getCLICommands() {
        return [...this.cliCommandsCache];
    }
    getMemoryBackends() {
        return [...this.memoryBackendsCache];
    }
    getHooks() {
        return [...this.hooksCache];
    }
    getWorkers() {
        return [...this.workersCache];
    }
    getProviders() {
        return [...this.providersCache];
    }
    getPlugin(name) {
        return this.plugins.get(name)?.plugin;
    }
    getPluginEntry(name) {
        return this.plugins.get(name);
    }
    listPlugins() {
        return Array.from(this.plugins.values()).map(e => e.plugin.metadata);
    }
    // =========================================================================
    // Health Check
    // =========================================================================
    /**
     * Run health checks on all plugins.
     */
    async healthCheck() {
        const results = new Map();
        for (const [name, entry] of this.plugins) {
            if (entry.plugin.state !== 'initialized') {
                results.set(name, {
                    healthy: false,
                    status: 'unhealthy',
                    message: `Plugin not initialized: ${entry.plugin.state}`,
                    checks: {},
                    timestamp: new Date(),
                });
                continue;
            }
            try {
                if (entry.plugin.healthCheck) {
                    results.set(name, await entry.plugin.healthCheck());
                }
                else {
                    results.set(name, {
                        healthy: true,
                        status: 'healthy',
                        checks: {},
                        timestamp: new Date(),
                    });
                }
            }
            catch (error) {
                results.set(name, {
                    healthy: false,
                    status: 'unhealthy',
                    message: error instanceof Error ? error.message : String(error),
                    checks: {},
                    timestamp: new Date(),
                });
            }
        }
        return results;
    }
    // =========================================================================
    // Stats
    // =========================================================================
    getStats() {
        let initialized = 0;
        let failed = 0;
        for (const entry of this.plugins.values()) {
            if (entry.plugin.state === 'initialized')
                initialized++;
            if (entry.plugin.state === 'error' || entry.error)
                failed++;
        }
        return {
            total: this.plugins.size,
            initialized,
            failed,
            agentTypes: this.agentTypesCache.length,
            taskTypes: this.taskTypesCache.length,
            mcpTools: this.mcpToolsCache.length,
            cliCommands: this.cliCommandsCache.length,
            hooks: this.hooksCache.length,
            workers: this.workersCache.length,
            providers: this.providersCache.length,
        };
    }
    // =========================================================================
    // Helpers
    // =========================================================================
    createPluginContext(entry) {
        return {
            config: entry.config,
            eventBus: this.eventBus,
            logger: this.logger.child({ plugin: entry.plugin.metadata.name }),
            services: this.services,
            coreVersion: this.config.coreVersion,
            dataDir: this.config.dataDir,
        };
    }
    async initializeWithTimeout(plugin, context) {
        const timeout = this.config.loadTimeout ?? 30000;
        await Promise.race([
            plugin.initialize(context),
            new Promise((_, reject) => setTimeout(() => reject(new Error('Initialization timeout')), timeout)),
        ]);
    }
}
// ============================================================================
// Default Registry Instance
// ============================================================================
let defaultRegistry = null;
export function getDefaultRegistry() {
    if (!defaultRegistry) {
        defaultRegistry = new PluginRegistry({
            coreVersion: '3.0.0',
            dataDir: process.cwd(),
        });
    }
    return defaultRegistry;
}
export function setDefaultRegistry(registry) {
    defaultRegistry = registry;
}
//# sourceMappingURL=plugin-registry.js.map