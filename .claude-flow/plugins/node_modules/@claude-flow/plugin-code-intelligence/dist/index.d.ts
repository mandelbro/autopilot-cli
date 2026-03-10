/**
 * Code Intelligence Plugin for Claude Flow V3
 *
 * A comprehensive code intelligence plugin combining graph neural networks
 * for code structure analysis with ultra-fast vector search for semantic
 * code similarity.
 *
 * Features:
 * - Semantic code search
 * - Architecture analysis and drift detection
 * - Refactoring impact prediction using GNN
 * - Module splitting suggestions using MinCut
 * - Pattern learning from code history
 *
 * Based on ADR-035: Advanced Code Intelligence Plugin
 *
 * @module @claude-flow/plugin-code-intelligence
 */
export * from './types.js';
export { GNNBridge, createGNNBridge } from './bridges/gnn-bridge.js';
export { MinCutBridge, createMinCutBridge } from './bridges/mincut-bridge.js';
export { semanticSearchTool, architectureAnalyzeTool, refactorImpactTool, splitSuggestTool, learnPatternsTool, codeIntelligenceTools, toolHandlers, createToolContext, } from './mcp-tools.js';
export type { MCPTool, ToolContext, MCPToolResult } from './mcp-tools.js';
import type { CodeIntelligenceConfig, IGNNBridge, IMinCutBridge } from './types.js';
/**
 * Plugin metadata
 */
export declare const pluginMetadata: {
    name: string;
    version: string;
    description: string;
    author: string;
    category: string;
    keywords: string[];
    homepage: string;
    repository: string;
};
/**
 * Plugin state
 */
export type PluginState = 'uninitialized' | 'initializing' | 'ready' | 'error' | 'shutdown';
/**
 * Code Intelligence Plugin Class
 */
export declare class CodeIntelligencePlugin {
    private state;
    private config;
    private gnnBridge;
    private mincutBridge;
    constructor(config?: Partial<CodeIntelligenceConfig>);
    /**
     * Get plugin metadata
     */
    getMetadata(): {
        name: string;
        version: string;
        description: string;
        author: string;
        category: string;
        keywords: string[];
        homepage: string;
        repository: string;
    };
    /**
     * Get current state
     */
    getState(): PluginState;
    /**
     * Initialize the plugin
     */
    initialize(): Promise<void>;
    /**
     * Shutdown the plugin
     */
    shutdown(): Promise<void>;
    /**
     * Get MCP tools provided by this plugin
     */
    getMCPTools(): import("./mcp-tools.js").MCPTool<unknown, unknown>[];
    /**
     * Get tool context for execution
     */
    getToolContext(): {
        get: <T>(key: string) => T | undefined;
        set: <T>(key: string, value: T) => void;
        bridges: {
            gnn: IGNNBridge;
            mincut: IMinCutBridge;
        };
        config: {
            allowedRoots: string[];
            blockedPatterns: RegExp[];
            maskSecrets: boolean;
        };
    };
    /**
     * Get configuration
     */
    getConfig(): CodeIntelligenceConfig;
    /**
     * Update configuration
     */
    updateConfig(config: Partial<CodeIntelligenceConfig>): void;
}
/**
 * Create plugin instance
 */
export declare function createPlugin(config?: Partial<CodeIntelligenceConfig>): CodeIntelligencePlugin;
/**
 * Default export
 */
export default CodeIntelligencePlugin;
//# sourceMappingURL=index.d.ts.map