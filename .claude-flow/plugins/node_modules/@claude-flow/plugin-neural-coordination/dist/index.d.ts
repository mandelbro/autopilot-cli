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
export * from './types.js';
export { neuralConsensusTool, topologyOptimizeTool, collectiveMemoryTool, emergentProtocolTool, swarmBehaviorTool, neuralCoordinationTools, toolHandlers, getTool, getToolNames, } from './mcp-tools.js';
export { NervousSystemBridge, createNervousSystemBridge, AttentionBridge, createAttentionBridge, } from './bridges/index.js';
export type { NervousSystemConfig, NeuralSignal, CoordinationResult, } from './bridges/nervous-system-bridge.js';
export type { AttentionConfig, AttentionOutput, } from './bridges/attention-bridge.js';
import type { MCPTool } from './types.js';
import { NervousSystemBridge } from './bridges/nervous-system-bridge.js';
import { AttentionBridge } from './bridges/attention-bridge.js';
/**
 * Neural Coordination Plugin metadata
 */
export declare const PLUGIN_METADATA: {
    readonly name: "@claude-flow/plugin-neural-coordination";
    readonly version: "3.0.0-alpha.1";
    readonly description: "Neural coordination plugin for multi-agent swarm intelligence";
    readonly author: "Claude Flow Team";
    readonly keywords: readonly ["neural-coordination", "multi-agent", "swarm", "consensus", "topology", "sona", "gnn", "attention"];
};
/**
 * Plugin state
 */
export interface NeuralCoordinationPluginState {
    initialized: boolean;
    nervousSystemBridge: NervousSystemBridge | null;
    attentionBridge: AttentionBridge | null;
}
/**
 * Initialize the neural coordination plugin
 */
export declare function initializePlugin(): Promise<void>;
/**
 * Shutdown the neural coordination plugin
 */
export declare function shutdownPlugin(): Promise<void>;
/**
 * Get plugin state
 */
export declare function getPluginState(): NeuralCoordinationPluginState;
/**
 * Get all MCP tools provided by this plugin
 */
export declare function getMCPTools(): MCPTool[];
/**
 * Plugin interface for registration with Claude Flow
 */
export declare const neuralCoordinationPlugin: {
    metadata: {
        readonly name: "@claude-flow/plugin-neural-coordination";
        readonly version: "3.0.0-alpha.1";
        readonly description: "Neural coordination plugin for multi-agent swarm intelligence";
        readonly author: "Claude Flow Team";
        readonly keywords: readonly ["neural-coordination", "multi-agent", "swarm", "consensus", "topology", "sona", "gnn", "attention"];
    };
    state: "uninitialized" | "initializing" | "ready" | "error";
    initialize(): Promise<void>;
    shutdown(): Promise<void>;
    getMCPTools(): MCPTool[];
    getAgentTypes(): string[];
};
export default neuralCoordinationPlugin;
//# sourceMappingURL=index.d.ts.map