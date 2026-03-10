/**
 * MinCut Bridge for Module Splitting
 *
 * Provides graph min-cut operations for optimal module boundary detection
 * using ruvector-mincut-wasm for high-performance graph partitioning.
 *
 * Features:
 * - Optimal module boundary detection
 * - Multi-way graph partitioning
 * - Constraint-aware splitting
 * - Cut weight optimization
 *
 * Based on ADR-035: Advanced Code Intelligence Plugin
 *
 * @module v3/plugins/code-intelligence/bridges/mincut-bridge
 */
import type { IMinCutBridge, DependencyGraph, SplitConstraints } from '../types.js';
/**
 * MinCut Bridge Implementation
 */
export declare class MinCutBridge implements IMinCutBridge {
    private wasmModule;
    private initialized;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
    /**
     * Find optimal module boundaries using MinCut
     */
    findOptimalCuts(graph: DependencyGraph, numModules: number, constraints: SplitConstraints): Promise<Map<string, number>>;
    /**
     * Calculate cut weight for a given partition
     */
    calculateCutWeight(graph: DependencyGraph, partition: Map<string, number>): Promise<number>;
    /**
     * Find minimum s-t cut
     */
    minSTCut(graph: DependencyGraph, source: string, sink: string): Promise<{
        cutValue: number;
        cutEdges: Array<{
            from: string;
            to: string;
        }>;
        sourceSet: string[];
        sinkSet: string[];
    }>;
    /**
     * Multi-way cut for module splitting
     */
    multiWayCut(graph: DependencyGraph, terminals: string[], _weights: Map<string, number>): Promise<{
        cutValue: number;
        partitions: Map<string, number>;
    }>;
    /**
     * Load WASM module dynamically
     */
    private loadWasmModule;
    /**
     * Spectral partitioning using Fiedler vector
     */
    private spectralPartition;
    /**
     * Edmonds-Karp algorithm (Ford-Fulkerson with BFS)
     */
    private edmondsKarp;
    /**
     * Compute distances from terminals to all nodes
     */
    private computeDistances;
}
/**
 * Create and export default bridge instance
 */
export declare function createMinCutBridge(): IMinCutBridge;
export default MinCutBridge;
//# sourceMappingURL=mincut-bridge.d.ts.map