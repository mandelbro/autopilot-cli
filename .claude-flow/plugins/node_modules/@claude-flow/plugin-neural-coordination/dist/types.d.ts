/**
 * Neural Coordination Plugin - Type Definitions
 *
 * Types for multi-agent neural coordination including consensus mechanisms,
 * topology optimization, collective memory, emergent protocols, and swarm behavior.
 */
import { z } from 'zod';
export interface MCPToolInputSchema {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
}
export interface MCPToolResult {
    content: Array<{
        type: 'text' | 'image' | 'resource';
        text?: string;
        data?: string;
        mimeType?: string;
    }>;
    isError?: boolean;
}
export interface MCPTool {
    name: string;
    description: string;
    inputSchema: MCPToolInputSchema;
    category?: string;
    tags?: string[];
    version?: string;
    cacheable?: boolean;
    cacheTTL?: number;
    handler: (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>;
}
export interface ToolContext {
    nervousSystemBridge?: NervousSystemBridgeInterface;
    attentionBridge?: AttentionBridgeInterface;
    config?: NeuralCoordinationConfig;
    logger?: Logger;
}
export interface Logger {
    debug(message: string, meta?: Record<string, unknown>): void;
    info(message: string, meta?: Record<string, unknown>): void;
    warn(message: string, meta?: Record<string, unknown>): void;
    error(message: string, meta?: Record<string, unknown>): void;
}
export declare const AgentSchema: z.ZodObject<{
    id: z.ZodString;
    preferences: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
    constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    capabilities: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    location: z.ZodOptional<z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
        z: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
        z?: number | undefined;
    }, {
        x: number;
        y: number;
        z?: number | undefined;
    }>>;
    embedding: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
}, "strip", z.ZodTypeAny, {
    id: string;
    preferences?: Record<string, number> | undefined;
    constraints?: Record<string, unknown> | undefined;
    capabilities?: string[] | undefined;
    location?: {
        x: number;
        y: number;
        z?: number | undefined;
    } | undefined;
    embedding?: number[] | undefined;
}, {
    id: string;
    preferences?: Record<string, number> | undefined;
    constraints?: Record<string, unknown> | undefined;
    capabilities?: string[] | undefined;
    location?: {
        x: number;
        y: number;
        z?: number | undefined;
    } | undefined;
    embedding?: number[] | undefined;
}>;
export type Agent = z.infer<typeof AgentSchema>;
export declare const AgentStateSchema: z.ZodObject<{
    agentId: z.ZodString;
    embedding: z.ZodArray<z.ZodNumber, "many">;
    vote: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodBoolean]>>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    embedding: number[];
    agentId: string;
    vote?: string | boolean | undefined;
    metadata?: Record<string, unknown> | undefined;
}, {
    embedding: number[];
    agentId: string;
    vote?: string | boolean | undefined;
    metadata?: Record<string, unknown> | undefined;
}>;
export type AgentState = z.infer<typeof AgentStateSchema>;
export declare const ConsensusProtocolSchema: z.ZodEnum<["neural_voting", "iterative_refinement", "auction", "contract_net"]>;
export type ConsensusProtocol = z.infer<typeof ConsensusProtocolSchema>;
export declare const ProposalSchema: z.ZodObject<{
    topic: z.ZodString;
    options: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        value: z.ZodUnknown;
    }, "strip", z.ZodTypeAny, {
        id: string;
        value?: unknown;
    }, {
        id: string;
        value?: unknown;
    }>, "many">;
    constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    options: {
        id: string;
        value?: unknown;
    }[];
    topic: string;
    constraints?: Record<string, unknown> | undefined;
}, {
    options: {
        id: string;
        value?: unknown;
    }[];
    topic: string;
    constraints?: Record<string, unknown> | undefined;
}>;
export type Proposal = z.infer<typeof ProposalSchema>;
export declare const NeuralConsensusInputSchema: z.ZodObject<{
    proposal: z.ZodObject<{
        topic: z.ZodString;
        options: z.ZodArray<z.ZodObject<{
            id: z.ZodString;
            value: z.ZodUnknown;
        }, "strip", z.ZodTypeAny, {
            id: string;
            value?: unknown;
        }, {
            id: string;
            value?: unknown;
        }>, "many">;
        constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        options: {
            id: string;
            value?: unknown;
        }[];
        topic: string;
        constraints?: Record<string, unknown> | undefined;
    }, {
        options: {
            id: string;
            value?: unknown;
        }[];
        topic: string;
        constraints?: Record<string, unknown> | undefined;
    }>;
    agents: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        preferences: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
        capabilities: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        location: z.ZodOptional<z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
            z: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
            z?: number | undefined;
        }, {
            x: number;
            y: number;
            z?: number | undefined;
        }>>;
        embedding: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }, {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }>, "many">;
    protocol: z.ZodDefault<z.ZodEnum<["neural_voting", "iterative_refinement", "auction", "contract_net"]>>;
    maxRounds: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    proposal: {
        options: {
            id: string;
            value?: unknown;
        }[];
        topic: string;
        constraints?: Record<string, unknown> | undefined;
    };
    agents: {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }[];
    protocol: "neural_voting" | "iterative_refinement" | "auction" | "contract_net";
    maxRounds: number;
}, {
    proposal: {
        options: {
            id: string;
            value?: unknown;
        }[];
        topic: string;
        constraints?: Record<string, unknown> | undefined;
    };
    agents: {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }[];
    protocol?: "neural_voting" | "iterative_refinement" | "auction" | "contract_net" | undefined;
    maxRounds?: number | undefined;
}>;
export type NeuralConsensusInput = z.infer<typeof NeuralConsensusInputSchema>;
export interface ConsensusVote {
    agentId: string;
    optionId: string;
    weight: number;
    confidence: number;
}
export interface ConsensusResult {
    consensusReached: boolean;
    selectedOption: string | null;
    votes: ConsensusVote[];
    agreementRatio: number;
    roundsUsed: number;
    divergentAgents: string[];
}
export interface NeuralConsensusOutput {
    consensusReached: boolean;
    selectedOption: string | null;
    agreementRatio: number;
    details: {
        protocol: ConsensusProtocol;
        roundsUsed: number;
        agentCount: number;
        divergentAgents: string[];
        interpretation: string;
    };
}
export declare const TopologyObjectiveSchema: z.ZodEnum<["minimize_latency", "maximize_throughput", "minimize_hops", "fault_tolerant"]>;
export type TopologyObjective = z.infer<typeof TopologyObjectiveSchema>;
export declare const PreferredTopologySchema: z.ZodEnum<["mesh", "tree", "ring", "star", "hybrid"]>;
export type PreferredTopology = z.infer<typeof PreferredTopologySchema>;
export declare const TopologyConstraintsSchema: z.ZodObject<{
    maxConnections: z.ZodOptional<z.ZodNumber>;
    minRedundancy: z.ZodOptional<z.ZodNumber>;
    preferredTopology: z.ZodOptional<z.ZodEnum<["mesh", "tree", "ring", "star", "hybrid"]>>;
}, "strip", z.ZodTypeAny, {
    maxConnections?: number | undefined;
    minRedundancy?: number | undefined;
    preferredTopology?: "mesh" | "tree" | "ring" | "star" | "hybrid" | undefined;
}, {
    maxConnections?: number | undefined;
    minRedundancy?: number | undefined;
    preferredTopology?: "mesh" | "tree" | "ring" | "star" | "hybrid" | undefined;
}>;
export type TopologyConstraints = z.infer<typeof TopologyConstraintsSchema>;
export declare const TopologyOptimizeInputSchema: z.ZodObject<{
    agents: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        preferences: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
        capabilities: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        location: z.ZodOptional<z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
            z: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
            z?: number | undefined;
        }, {
            x: number;
            y: number;
            z?: number | undefined;
        }>>;
        embedding: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }, {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }>, "many">;
    objective: z.ZodDefault<z.ZodEnum<["minimize_latency", "maximize_throughput", "minimize_hops", "fault_tolerant"]>>;
    constraints: z.ZodOptional<z.ZodObject<{
        maxConnections: z.ZodOptional<z.ZodNumber>;
        minRedundancy: z.ZodOptional<z.ZodNumber>;
        preferredTopology: z.ZodOptional<z.ZodEnum<["mesh", "tree", "ring", "star", "hybrid"]>>;
    }, "strip", z.ZodTypeAny, {
        maxConnections?: number | undefined;
        minRedundancy?: number | undefined;
        preferredTopology?: "mesh" | "tree" | "ring" | "star" | "hybrid" | undefined;
    }, {
        maxConnections?: number | undefined;
        minRedundancy?: number | undefined;
        preferredTopology?: "mesh" | "tree" | "ring" | "star" | "hybrid" | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    agents: {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }[];
    objective: "minimize_latency" | "maximize_throughput" | "minimize_hops" | "fault_tolerant";
    constraints?: {
        maxConnections?: number | undefined;
        minRedundancy?: number | undefined;
        preferredTopology?: "mesh" | "tree" | "ring" | "star" | "hybrid" | undefined;
    } | undefined;
}, {
    agents: {
        id: string;
        preferences?: Record<string, number> | undefined;
        constraints?: Record<string, unknown> | undefined;
        capabilities?: string[] | undefined;
        location?: {
            x: number;
            y: number;
            z?: number | undefined;
        } | undefined;
        embedding?: number[] | undefined;
    }[];
    constraints?: {
        maxConnections?: number | undefined;
        minRedundancy?: number | undefined;
        preferredTopology?: "mesh" | "tree" | "ring" | "star" | "hybrid" | undefined;
    } | undefined;
    objective?: "minimize_latency" | "maximize_throughput" | "minimize_hops" | "fault_tolerant" | undefined;
}>;
export type TopologyOptimizeInput = z.infer<typeof TopologyOptimizeInputSchema>;
export interface TopologyEdge {
    source: string;
    target: string;
    weight: number;
    latency?: number;
}
export interface TopologyResult {
    edges: TopologyEdge[];
    topology: PreferredTopology;
    metrics: {
        avgLatency: number;
        redundancy: number;
        diameter: number;
        avgDegree: number;
    };
}
export interface TopologyOptimizeOutput {
    topology: PreferredTopology;
    edges: TopologyEdge[];
    metrics: {
        avgLatency: number;
        redundancy: number;
        diameter: number;
        avgDegree: number;
    };
    details: {
        objective: TopologyObjective;
        agentCount: number;
        edgeCount: number;
        interpretation: string;
    };
}
export declare const MemoryActionSchema: z.ZodEnum<["store", "retrieve", "consolidate", "forget", "synchronize"]>;
export type MemoryAction = z.infer<typeof MemoryActionSchema>;
export declare const MemoryScopeSchema: z.ZodEnum<["global", "team", "pair"]>;
export type MemoryScope = z.infer<typeof MemoryScopeSchema>;
export declare const ConsolidationStrategySchema: z.ZodEnum<["ewc", "replay", "distillation"]>;
export type ConsolidationStrategy = z.infer<typeof ConsolidationStrategySchema>;
export declare const CollectiveMemoryInputSchema: z.ZodObject<{
    action: z.ZodEnum<["store", "retrieve", "consolidate", "forget", "synchronize"]>;
    memory: z.ZodOptional<z.ZodObject<{
        key: z.ZodOptional<z.ZodString>;
        value: z.ZodOptional<z.ZodUnknown>;
        importance: z.ZodDefault<z.ZodNumber>;
        expiry: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        importance: number;
        value?: unknown;
        key?: string | undefined;
        expiry?: string | undefined;
    }, {
        value?: unknown;
        key?: string | undefined;
        importance?: number | undefined;
        expiry?: string | undefined;
    }>>;
    scope: z.ZodDefault<z.ZodEnum<["global", "team", "pair"]>>;
    consolidationStrategy: z.ZodDefault<z.ZodEnum<["ewc", "replay", "distillation"]>>;
}, "strip", z.ZodTypeAny, {
    action: "store" | "retrieve" | "consolidate" | "forget" | "synchronize";
    scope: "global" | "team" | "pair";
    consolidationStrategy: "ewc" | "replay" | "distillation";
    memory?: {
        importance: number;
        value?: unknown;
        key?: string | undefined;
        expiry?: string | undefined;
    } | undefined;
}, {
    action: "store" | "retrieve" | "consolidate" | "forget" | "synchronize";
    memory?: {
        value?: unknown;
        key?: string | undefined;
        importance?: number | undefined;
        expiry?: string | undefined;
    } | undefined;
    scope?: "global" | "team" | "pair" | undefined;
    consolidationStrategy?: "ewc" | "replay" | "distillation" | undefined;
}>;
export type CollectiveMemoryInput = z.infer<typeof CollectiveMemoryInputSchema>;
export interface MemoryEntry {
    key: string;
    value: unknown;
    importance: number;
    createdAt: number;
    updatedAt: number;
    accessCount: number;
    scope: MemoryScope;
}
export interface CollectiveMemoryOutput {
    action: MemoryAction;
    success: boolean;
    data?: unknown;
    details: {
        scope: MemoryScope;
        entryCount?: number;
        consolidatedCount?: number;
        interpretation: string;
    };
}
export declare const TaskTypeSchema: z.ZodObject<{
    type: z.ZodString;
    objectives: z.ZodArray<z.ZodString, "many">;
    constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    type: string;
    objectives: string[];
    constraints?: Record<string, unknown> | undefined;
}, {
    type: string;
    objectives: string[];
    constraints?: Record<string, unknown> | undefined;
}>;
export type TaskType = z.infer<typeof TaskTypeSchema>;
export declare const CommunicationBudgetSchema: z.ZodObject<{
    symbolsPerMessage: z.ZodDefault<z.ZodNumber>;
    messagesPerRound: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    symbolsPerMessage: number;
    messagesPerRound: number;
}, {
    symbolsPerMessage?: number | undefined;
    messagesPerRound?: number | undefined;
}>;
export type CommunicationBudget = z.infer<typeof CommunicationBudgetSchema>;
export declare const EmergentProtocolInputSchema: z.ZodObject<{
    task: z.ZodObject<{
        type: z.ZodString;
        objectives: z.ZodArray<z.ZodString, "many">;
        constraints: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        type: string;
        objectives: string[];
        constraints?: Record<string, unknown> | undefined;
    }, {
        type: string;
        objectives: string[];
        constraints?: Record<string, unknown> | undefined;
    }>;
    communicationBudget: z.ZodOptional<z.ZodObject<{
        symbolsPerMessage: z.ZodDefault<z.ZodNumber>;
        messagesPerRound: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        symbolsPerMessage: number;
        messagesPerRound: number;
    }, {
        symbolsPerMessage?: number | undefined;
        messagesPerRound?: number | undefined;
    }>>;
    trainingEpisodes: z.ZodDefault<z.ZodNumber>;
    interpretability: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    task: {
        type: string;
        objectives: string[];
        constraints?: Record<string, unknown> | undefined;
    };
    trainingEpisodes: number;
    interpretability: boolean;
    communicationBudget?: {
        symbolsPerMessage: number;
        messagesPerRound: number;
    } | undefined;
}, {
    task: {
        type: string;
        objectives: string[];
        constraints?: Record<string, unknown> | undefined;
    };
    communicationBudget?: {
        symbolsPerMessage?: number | undefined;
        messagesPerRound?: number | undefined;
    } | undefined;
    trainingEpisodes?: number | undefined;
    interpretability?: boolean | undefined;
}>;
export type EmergentProtocolInput = z.infer<typeof EmergentProtocolInputSchema>;
export interface ProtocolSymbol {
    id: number;
    meaning: string;
    frequency: number;
    contextualMeaning: Map<string, string>;
}
export interface EmergentProtocolResult {
    symbols: ProtocolSymbol[];
    vocabulary: Map<number, string>;
    compositionRules: string[];
    successRate: number;
}
export interface EmergentProtocolOutput {
    protocolLearned: boolean;
    vocabularySize: number;
    successRate: number;
    details: {
        trainingEpisodes: number;
        symbols: Array<{
            id: number;
            meaning: string;
            frequency: number;
        }>;
        compositionRules: string[];
        interpretation: string;
    };
}
export declare const SwarmBehaviorTypeSchema: z.ZodEnum<["flocking", "foraging", "formation", "task_allocation", "exploration", "aggregation", "dispersion"]>;
export type SwarmBehaviorType = z.infer<typeof SwarmBehaviorTypeSchema>;
export declare const ObservabilitySchema: z.ZodObject<{
    recordTrajectories: z.ZodOptional<z.ZodBoolean>;
    measureEmergence: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    recordTrajectories?: boolean | undefined;
    measureEmergence?: boolean | undefined;
}, {
    recordTrajectories?: boolean | undefined;
    measureEmergence?: boolean | undefined;
}>;
export type Observability = z.infer<typeof ObservabilitySchema>;
export declare const SwarmBehaviorInputSchema: z.ZodObject<{
    behavior: z.ZodEnum<["flocking", "foraging", "formation", "task_allocation", "exploration", "aggregation", "dispersion"]>;
    parameters: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    adaptiveRules: z.ZodDefault<z.ZodBoolean>;
    observability: z.ZodOptional<z.ZodObject<{
        recordTrajectories: z.ZodOptional<z.ZodBoolean>;
        measureEmergence: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        recordTrajectories?: boolean | undefined;
        measureEmergence?: boolean | undefined;
    }, {
        recordTrajectories?: boolean | undefined;
        measureEmergence?: boolean | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    behavior: "flocking" | "foraging" | "formation" | "task_allocation" | "exploration" | "aggregation" | "dispersion";
    adaptiveRules: boolean;
    parameters?: Record<string, unknown> | undefined;
    observability?: {
        recordTrajectories?: boolean | undefined;
        measureEmergence?: boolean | undefined;
    } | undefined;
}, {
    behavior: "flocking" | "foraging" | "formation" | "task_allocation" | "exploration" | "aggregation" | "dispersion";
    parameters?: Record<string, unknown> | undefined;
    adaptiveRules?: boolean | undefined;
    observability?: {
        recordTrajectories?: boolean | undefined;
        measureEmergence?: boolean | undefined;
    } | undefined;
}>;
export type SwarmBehaviorInput = z.infer<typeof SwarmBehaviorInputSchema>;
export interface SwarmMetrics {
    cohesion: number;
    alignment: number;
    separation: number;
    emergenceScore: number;
}
export interface SwarmBehaviorResult {
    behaviorActive: boolean;
    metrics: SwarmMetrics;
    agentPositions: Array<{
        id: string;
        x: number;
        y: number;
        z?: number;
    }>;
    trajectories?: Array<Array<{
        t: number;
        x: number;
        y: number;
    }>>;
}
export interface SwarmBehaviorOutput {
    behaviorActive: boolean;
    metrics: {
        cohesion: number;
        alignment: number;
        separation: number;
        emergenceScore: number;
    };
    details: {
        behavior: SwarmBehaviorType;
        agentCount: number;
        adaptiveRules: boolean;
        interpretation: string;
    };
}
export interface NeuralCoordinationConfig {
    consensus: {
        defaultProtocol: ConsensusProtocol;
        maxRounds: number;
        convergenceThreshold: number;
    };
    topology: {
        defaultObjective: TopologyObjective;
        maxConnections: number;
    };
    memory: {
        defaultScope: MemoryScope;
        consolidationInterval: number;
        maxEntries: number;
    };
    swarm: {
        defaultBehavior: SwarmBehaviorType;
        adaptationRate: number;
    };
}
export declare const DEFAULT_CONFIG: NeuralCoordinationConfig;
export interface NervousSystemBridgeInterface {
    initialized: boolean;
    propagate(signals: Float32Array[]): Promise<Float32Array[]>;
    synchronize(states: Float32Array[]): Promise<Float32Array>;
    coordinate(agents: Agent[]): Promise<{
        assignments: Map<string, string>;
    }>;
}
export interface AttentionBridgeInterface {
    initialized: boolean;
    flashAttention(query: Float32Array, key: Float32Array, value: Float32Array): Float32Array;
    multiHeadAttention(query: Float32Array, key: Float32Array, value: Float32Array): Float32Array;
    computeWeights(query: Float32Array, keys: Float32Array[]): number[];
}
/**
 * Create a successful MCP tool result
 */
export declare function successResult(data: unknown): MCPToolResult;
/**
 * Create an error MCP tool result
 */
export declare function errorResult(error: Error | string): MCPToolResult;
/**
 * Calculate cosine similarity between two vectors
 */
export declare function cosineSimilarity(a: number[] | Float32Array, b: number[] | Float32Array): number;
//# sourceMappingURL=types.d.ts.map