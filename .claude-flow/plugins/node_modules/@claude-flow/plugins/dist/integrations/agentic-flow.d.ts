/**
 * Agentic Flow Integration
 *
 * Provides integration with agentic-flow@alpha for:
 * - Swarm coordination
 * - Agent spawning
 * - Task orchestration
 * - Memory management
 */
import { EventEmitter } from 'events';
import type { AgentTypeDefinition, WorkerDefinition, ILogger, IEventBus } from '../types/index.js';
export interface AgenticFlowConfig {
    readonly baseUrl?: string;
    readonly version?: string;
    readonly timeout?: number;
    readonly maxConcurrentAgents?: number;
    readonly logger?: ILogger;
    readonly eventBus?: IEventBus;
}
export interface SwarmTopology {
    readonly type: 'hierarchical' | 'mesh' | 'ring' | 'star' | 'custom';
    readonly maxAgents: number;
    readonly coordinatorId?: string;
    readonly metadata?: Record<string, unknown>;
}
export interface AgentSpawnOptions {
    readonly type: string;
    readonly id?: string;
    readonly capabilities?: string[];
    readonly priority?: number;
    readonly parentId?: string;
    readonly metadata?: Record<string, unknown>;
}
export interface SpawnedAgent {
    readonly id: string;
    readonly type: string;
    readonly status: 'spawning' | 'active' | 'busy' | 'idle' | 'terminated';
    readonly capabilities: string[];
    readonly parentId?: string;
    readonly spawnedAt: Date;
}
export interface TaskOrchestrationOptions {
    readonly taskType: string;
    readonly input: unknown;
    readonly agentId?: string;
    readonly priority?: number;
    readonly timeout?: number;
    readonly retries?: number;
    readonly dependencies?: string[];
}
export interface OrchestrationResult {
    readonly taskId: string;
    readonly status: 'pending' | 'running' | 'completed' | 'failed';
    readonly result?: unknown;
    readonly error?: string;
    readonly agentId: string;
    readonly startedAt: Date;
    readonly completedAt?: Date;
    readonly duration?: number;
}
export declare const AGENTIC_FLOW_EVENTS: {
    readonly SWARM_INITIALIZED: "agentic:swarm-initialized";
    readonly AGENT_SPAWNED: "agentic:agent-spawned";
    readonly AGENT_TERMINATED: "agentic:agent-terminated";
    readonly TASK_STARTED: "agentic:task-started";
    readonly TASK_COMPLETED: "agentic:task-completed";
    readonly TASK_FAILED: "agentic:task-failed";
    readonly MEMORY_STORED: "agentic:memory-stored";
    readonly MEMORY_RETRIEVED: "agentic:memory-retrieved";
};
export type AgenticFlowEvent = typeof AGENTIC_FLOW_EVENTS[keyof typeof AGENTIC_FLOW_EVENTS];
/**
 * Bridge to agentic-flow@alpha functionality.
 * Provides a unified interface for swarm coordination, agent spawning, and task orchestration.
 */
export declare class AgenticFlowBridge extends EventEmitter {
    private readonly config;
    private readonly agents;
    private readonly tasks;
    private swarmInitialized;
    private swarmTopology?;
    private nextAgentId;
    private nextTaskId;
    constructor(config?: AgenticFlowConfig);
    /**
     * Initialize a swarm with the specified topology.
     */
    initializeSwarm(topology: SwarmTopology): Promise<void>;
    /**
     * Get current swarm status.
     */
    getSwarmStatus(): {
        initialized: boolean;
        topology?: SwarmTopology;
        activeAgents: number;
        pendingTasks: number;
    };
    /**
     * Shutdown the swarm.
     */
    shutdownSwarm(): Promise<void>;
    /**
     * Spawn a new agent.
     */
    spawnAgent(options: AgentSpawnOptions): Promise<SpawnedAgent>;
    /**
     * Terminate an agent.
     */
    terminateAgent(agentId: string): Promise<void>;
    /**
     * Get agent by ID.
     */
    getAgent(agentId: string): SpawnedAgent | undefined;
    /**
     * List all agents.
     */
    listAgents(): SpawnedAgent[];
    /**
     * Find agents by capability.
     */
    findAgentsByCapability(capability: string): SpawnedAgent[];
    /**
     * Orchestrate a task.
     */
    orchestrateTask(options: TaskOrchestrationOptions): Promise<OrchestrationResult>;
    private executeTask;
    /**
     * Get task result.
     */
    getTaskResult(taskId: string): OrchestrationResult | undefined;
    /**
     * List all tasks.
     */
    listTasks(): OrchestrationResult[];
    /**
     * Convert plugin agent type to agentic-flow format.
     */
    convertAgentType(agentType: AgentTypeDefinition): AgentSpawnOptions;
    /**
     * Convert plugin worker to agent spawn options.
     */
    convertWorkerToAgent(worker: WorkerDefinition): AgentSpawnOptions;
}
export interface AgentDBConfig {
    readonly path?: string;
    readonly dimensions?: number;
    readonly indexType?: 'hnsw' | 'flat' | 'ivf';
    readonly efConstruction?: number;
    readonly efSearch?: number;
    readonly m?: number;
}
export interface VectorEntry {
    readonly id: string;
    readonly vector: Float32Array;
    readonly metadata?: Record<string, unknown>;
    readonly timestamp: Date;
}
export interface VectorSearchOptions {
    readonly limit?: number;
    readonly threshold?: number;
    readonly filter?: Record<string, unknown>;
}
export interface VectorSearchResult {
    readonly id: string;
    readonly score: number;
    readonly metadata?: Record<string, unknown>;
}
/**
 * Bridge to AgentDB for vector storage and similarity search.
 * Provides 150x-12,500x faster search compared to traditional methods.
 */
export declare class AgentDBBridge extends EventEmitter {
    private readonly config;
    private readonly vectors;
    private initialized;
    constructor(config?: AgentDBConfig);
    /**
     * Initialize AgentDB.
     */
    initialize(): Promise<void>;
    /**
     * Shutdown AgentDB.
     */
    shutdown(): Promise<void>;
    /**
     * Store a vector.
     */
    store(id: string, vector: Float32Array, metadata?: Record<string, unknown>): Promise<void>;
    /**
     * Retrieve a vector by ID.
     */
    retrieve(id: string): Promise<VectorEntry | null>;
    /**
     * Search for similar vectors.
     */
    search(query: Float32Array, options?: VectorSearchOptions): Promise<VectorSearchResult[]>;
    /**
     * Delete a vector.
     */
    delete(id: string): Promise<boolean>;
    /**
     * Get database statistics.
     */
    getStats(): {
        vectorCount: number;
        dimensions: number;
        indexType: string;
        memoryUsage: number;
    };
    /**
     * Calculate cosine similarity between two vectors.
     */
    private cosineSimilarity;
}
/**
 * Get the default AgenticFlow bridge instance.
 */
export declare function getAgenticFlowBridge(config?: AgenticFlowConfig): AgenticFlowBridge;
/**
 * Get the default AgentDB bridge instance.
 */
export declare function getAgentDBBridge(config?: AgentDBConfig): AgentDBBridge;
/**
 * Reset the default bridges (for testing).
 */
export declare function resetBridges(): void;
//# sourceMappingURL=agentic-flow.d.ts.map