/**
 * Nervous System Bridge
 *
 * Bridge to ruvector-nervous-system-wasm for neural coordination layer.
 * Provides signal propagation, state synchronization, and agent coordination.
 */
import type { Agent } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * Nervous system configuration
 */
export interface NervousSystemConfig {
    /** Number of neurons in the network */
    neuronCount: number;
    /** Signal propagation speed (0-1) */
    propagationSpeed: number;
    /** Signal decay rate (0-1) */
    decayRate: number;
    /** Synchronization threshold (0-1) */
    syncThreshold: number;
    /** Maximum coordination attempts */
    maxCoordinationAttempts: number;
}
/**
 * Signal in the nervous system
 */
export interface NeuralSignal {
    source: string;
    target: string;
    strength: number;
    type: 'excitatory' | 'inhibitory';
    payload?: Float32Array;
}
/**
 * Coordination result
 */
export interface CoordinationResult {
    success: boolean;
    assignments: Map<string, string>;
    synchronizationLevel: number;
    convergenceRounds: number;
}
/**
 * WASM nervous system module interface
 */
interface NervousSystemModule {
    propagate(signals: Float32Array[], config: NervousSystemConfig): Float32Array[];
    synchronize(states: Float32Array[], threshold: number): Float32Array;
    coordinate(agents: number, capabilities: Uint8Array, tasks: Uint8Array): Uint32Array;
    measureSynchrony(states: Float32Array[]): number;
}
/**
 * Nervous System Bridge implementation
 */
export declare class NervousSystemBridge {
    readonly name = "ruvector-nervous-system-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<NervousSystemConfig>);
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): NervousSystemModule | null;
    /**
     * Propagate signals through the neural network
     */
    propagate(signals: Float32Array[]): Promise<Float32Array[]>;
    /**
     * Synchronize agent states to achieve collective coherence
     */
    synchronize(states: Float32Array[]): Promise<Float32Array>;
    /**
     * Coordinate agents for task assignment
     */
    coordinate(agents: Agent[]): Promise<CoordinationResult>;
    /**
     * Create mock module for development without WASM
     */
    private createMockModule;
}
/**
 * Create a new nervous system bridge
 */
export declare function createNervousSystemBridge(config?: Partial<NervousSystemConfig>): NervousSystemBridge;
export default NervousSystemBridge;
//# sourceMappingURL=nervous-system-bridge.d.ts.map