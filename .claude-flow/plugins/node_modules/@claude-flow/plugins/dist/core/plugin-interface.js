/**
 * Core Plugin Interface
 *
 * Defines the contract that all plugins must implement.
 */
// ============================================================================
// Plugin Events
// ============================================================================
export const PLUGIN_EVENTS = {
    LOADING: 'plugin:loading',
    LOADED: 'plugin:loaded',
    INITIALIZING: 'plugin:initializing',
    INITIALIZED: 'plugin:initialized',
    SHUTTING_DOWN: 'plugin:shutting-down',
    SHUTDOWN: 'plugin:shutdown',
    ERROR: 'plugin:error',
    HEALTH_CHECK: 'plugin:health-check',
};
// ============================================================================
// Plugin Validation
// ============================================================================
/**
 * Validate plugin metadata.
 */
export function validatePluginMetadata(metadata) {
    if (!metadata || typeof metadata !== 'object')
        return false;
    const m = metadata;
    if (typeof m.name !== 'string' || m.name.length === 0)
        return false;
    if (typeof m.version !== 'string' || !/^\d+\.\d+\.\d+/.test(m.version))
        return false;
    if (m.description !== undefined && typeof m.description !== 'string')
        return false;
    if (m.author !== undefined && typeof m.author !== 'string')
        return false;
    if (m.dependencies !== undefined) {
        if (!Array.isArray(m.dependencies))
            return false;
        if (!m.dependencies.every(d => typeof d === 'string'))
            return false;
    }
    return true;
}
/**
 * Validate plugin interface.
 */
export function validatePlugin(plugin) {
    if (!plugin || typeof plugin !== 'object')
        return false;
    const p = plugin;
    // Check required properties
    if (!validatePluginMetadata(p.metadata))
        return false;
    if (typeof p.state !== 'string')
        return false;
    if (typeof p.initialize !== 'function')
        return false;
    if (typeof p.shutdown !== 'function')
        return false;
    // Check optional methods are functions if present
    const optionalMethods = [
        'healthCheck',
        'registerAgentTypes',
        'registerTaskTypes',
        'registerMCPTools',
        'registerCLICommands',
        'registerMemoryBackends',
        'registerHooks',
        'registerWorkers',
        'registerProviders',
    ];
    for (const method of optionalMethods) {
        if (p[method] !== undefined && typeof p[method] !== 'function') {
            return false;
        }
    }
    return true;
}
//# sourceMappingURL=plugin-interface.js.map