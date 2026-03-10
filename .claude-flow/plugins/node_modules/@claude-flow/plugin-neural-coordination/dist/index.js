/**
 * Neural Coordination Plugin
 *
 * Multi-agent neural coordination for swarm intelligence using
 * SONA, GNN, and attention mechanisms.
 *
 * Features:
 * - Neural consensus protocols (neural voting, iterative refinement, auction, contract net)
 * - GNN-based topology optimization (mesh, tree, ring, star, hybrid)
 * - Collective memory with EWC consolidation
 * - Emergent communication protocol learning
 * - Swarm behavior orchestration (flocking, foraging, formation, etc.)
 *
 * @packageDocumentation
 */
// Export types
export * from './types.js';
// Export MCP tools
export { neuralConsensusTool, topologyOptimizeTool, collectiveMemoryTool, emergentProtocolTool, swarmBehaviorTool, neuralCoordinationTools, toolHandlers, getTool, getToolNames, } from './mcp-tools.js';
// Export bridges
export { NervousSystemBridge, createNervousSystemBridge, AttentionBridge, createAttentionBridge, } from './bridges/index.js';
import { neuralCoordinationTools } from './mcp-tools.js';
import { createNervousSystemBridge } from './bridges/nervous-system-bridge.js';
import { createAttentionBridge } from './bridges/attention-bridge.js';
/**
 * Neural Coordination Plugin metadata
 */
export const PLUGIN_METADATA = {
    name: '@claude-flow/plugin-neural-coordination',
    version: '3.0.0-alpha.1',
    description: 'Neural coordination plugin for multi-agent swarm intelligence',
    author: 'Claude Flow Team',
    keywords: [
        'neural-coordination',
        'multi-agent',
        'swarm',
        'consensus',
        'topology',
        'sona',
        'gnn',
        'attention',
    ],
};
let pluginState = {
    initialized: false,
    nervousSystemBridge: null,
    attentionBridge: null,
};
/**
 * Initialize the neural coordination plugin
 */
export async function initializePlugin() {
    if (pluginState.initialized)
        return;
    // Initialize bridges
    pluginState.nervousSystemBridge = createNervousSystemBridge();
    pluginState.attentionBridge = createAttentionBridge();
    await Promise.all([
        pluginState.nervousSystemBridge.init(),
        pluginState.attentionBridge.init(),
    ]);
    pluginState.initialized = true;
}
/**
 * Shutdown the neural coordination plugin
 */
export async function shutdownPlugin() {
    if (!pluginState.initialized)
        return;
    await Promise.all([
        pluginState.nervousSystemBridge?.destroy(),
        pluginState.attentionBridge?.destroy(),
    ]);
    pluginState = {
        initialized: false,
        nervousSystemBridge: null,
        attentionBridge: null,
    };
}
/**
 * Get plugin state
 */
export function getPluginState() {
    return { ...pluginState };
}
/**
 * Get all MCP tools provided by this plugin
 */
export function getMCPTools() {
    return neuralCoordinationTools;
}
/**
 * Plugin interface for registration with Claude Flow
 */
export const neuralCoordinationPlugin = {
    metadata: PLUGIN_METADATA,
    state: 'uninitialized',
    async initialize() {
        this.state = 'initializing';
        try {
            await initializePlugin();
            this.state = 'ready';
        }
        catch (error) {
            this.state = 'error';
            throw error;
        }
    },
    async shutdown() {
        await shutdownPlugin();
        this.state = 'uninitialized';
    },
    getMCPTools() {
        return neuralCoordinationTools;
    },
    getAgentTypes() {
        return [
            'neural-coordinator',
            'topology-optimizer',
            'collective-memory-manager',
            'protocol-learner',
            'swarm-orchestrator',
        ];
    },
};
export default neuralCoordinationPlugin;
//# sourceMappingURL=index.js.map