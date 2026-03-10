/**
 * Attention Bridge
 *
 * Bridge to ruvector-attention-wasm for multi-head attention computation.
 * Enables agent-to-agent communication weighting and focus management.
 */
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * Attention configuration
 */
export interface AttentionConfig {
    /** Dimension of each attention head */
    headDim: number;
    /** Number of attention heads */
    numHeads: number;
    /** Sequence length */
    seqLength: number;
    /** Whether to use causal masking */
    causal: boolean;
    /** Dropout rate (0-1) */
    dropout: number;
    /** Temperature for softmax scaling */
    temperature: number;
}
/**
 * Attention output
 */
export interface AttentionOutput {
    values: Float32Array;
    weights: Float32Array;
    attended: string[];
}
/**
 * WASM attention module interface
 */
interface AttentionModule {
    flashAttention(query: Float32Array, key: Float32Array, value: Float32Array, config: AttentionConfig): Float32Array;
    multiHeadAttention(query: Float32Array, key: Float32Array, value: Float32Array, config: AttentionConfig): Float32Array;
    selfAttention(input: Float32Array, config: AttentionConfig): Float32Array;
    computeWeights(query: Float32Array, keys: Float32Array[], config: AttentionConfig): Float32Array;
}
/**
 * Attention Bridge implementation
 */
export declare class AttentionBridge {
    readonly name = "ruvector-attention-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<AttentionConfig>);
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): AttentionModule | null;
    /**
     * Compute flash attention (optimized for long sequences)
     * Achieves 2.49x-7.47x speedup over standard attention
     */
    flashAttention(query: Float32Array, key: Float32Array, value: Float32Array, config?: Partial<AttentionConfig>): Float32Array;
    /**
     * Compute multi-head attention
     */
    multiHeadAttention(query: Float32Array, key: Float32Array, value: Float32Array, config?: Partial<AttentionConfig>): Float32Array;
    /**
     * Compute self-attention
     */
    selfAttention(input: Float32Array, config?: Partial<AttentionConfig>): Float32Array;
    /**
     * Compute attention weights for agent-to-agent communication
     * Returns normalized weights indicating how much each key should be attended to
     */
    computeWeights(query: Float32Array, keys: Float32Array[], config?: Partial<AttentionConfig>): number[];
    /**
     * Compute attention-weighted aggregation of agent states
     */
    aggregateWithAttention(query: Float32Array, agentStates: Float32Array[], agentValues: Float32Array[]): Float32Array;
    /**
     * Find top-k most relevant agents based on attention
     */
    findMostRelevant(query: Float32Array, agentStates: Float32Array[], k: number): Array<{
        index: number;
        weight: number;
    }>;
    /**
     * Create mock module for development without WASM
     */
    private createMockModule;
}
/**
 * Create a new attention bridge
 */
export declare function createAttentionBridge(config?: Partial<AttentionConfig>): AttentionBridge;
export default AttentionBridge;
//# sourceMappingURL=attention-bridge.d.ts.map