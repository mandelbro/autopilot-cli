/**
 * GNN Bridge for Code Graph Analysis
 *
 * Provides graph neural network operations for code structure analysis
 * using ruvector-gnn-wasm for high-performance graph algorithms.
 *
 * Features:
 * - Code graph construction
 * - Node embedding computation
 * - Impact prediction using graph propagation
 * - Community detection for module discovery
 * - Pattern matching in code graphs
 *
 * Based on ADR-035: Advanced Code Intelligence Plugin
 *
 * @module v3/plugins/code-intelligence/bridges/gnn-bridge
 */
import type { IGNNBridge, DependencyGraph } from '../types.js';
/**
 * GNN Bridge Implementation
 */
export declare class GNNBridge implements IGNNBridge {
    private wasmModule;
    private initialized;
    private readonly embeddingDim;
    constructor(embeddingDim?: number);
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
    /**
     * Build code graph from files
     */
    buildCodeGraph(files: string[], _includeCallGraph: boolean): Promise<DependencyGraph>;
    /**
     * Compute node embeddings using GNN
     */
    computeNodeEmbeddings(graph: DependencyGraph, embeddingDim: number): Promise<Map<string, Float32Array>>;
    /**
     * Predict impact of changes using GNN
     */
    predictImpact(graph: DependencyGraph, changedNodes: string[], depth: number): Promise<Map<string, number>>;
    /**
     * Detect communities in code graph
     */
    detectCommunities(graph: DependencyGraph): Promise<Map<string, number>>;
    /**
     * Find similar code patterns
     */
    findSimilarPatterns(graph: DependencyGraph, patternGraph: DependencyGraph, threshold: number): Promise<Array<{
        matchId: string;
        score: number;
    }>>;
    /**
     * Load WASM module dynamically
     */
    private loadWasmModule;
    /**
     * Detect language from file extension
     */
    private detectLanguage;
    /**
     * Extract imports from file (simplified)
     */
    private extractImports;
    /**
     * Calculate max depth of dependency graph
     */
    private calculateMaxDepth;
    /**
     * Encode node type as number
     */
    private encodeNodeType;
    /**
     * Encode language as number
     */
    private encodeLanguage;
    /**
     * Compute embeddings using JS (fallback)
     */
    private computeEmbeddingsJS;
    /**
     * Compute cosine similarity
     */
    private cosineSimilarity;
}
/**
 * Create and export default bridge instance
 */
export declare function createGNNBridge(embeddingDim?: number): IGNNBridge;
export default GNNBridge;
//# sourceMappingURL=gnn-bridge.d.ts.map