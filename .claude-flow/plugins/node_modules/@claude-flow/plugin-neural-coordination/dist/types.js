/**
 * Neural Coordination Plugin - Type Definitions
 *
 * Types for multi-agent neural coordination including consensus mechanisms,
 * topology optimization, collective memory, emergent protocols, and swarm behavior.
 */
import { z } from 'zod';
// ============================================================================
// Agent Types
// ============================================================================
export const AgentSchema = z.object({
    id: z.string().max(100).describe('Unique agent identifier'),
    preferences: z.record(z.string(), z.number().min(-1).max(1)).optional()
        .describe('Agent preferences as key-value pairs with normalized values'),
    constraints: z.record(z.string(), z.unknown()).optional()
        .describe('Agent-specific constraints'),
    capabilities: z.array(z.string()).optional()
        .describe('Agent capabilities'),
    location: z.object({
        x: z.number(),
        y: z.number(),
        z: z.number().optional(),
    }).optional().describe('Agent location in 2D/3D space'),
    embedding: z.array(z.number()).optional()
        .describe('Agent state embedding vector'),
});
export const AgentStateSchema = z.object({
    agentId: z.string().max(100),
    embedding: z.array(z.number()).describe('Agent state embedding'),
    vote: z.union([z.string(), z.boolean()]).optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
});
// ============================================================================
// Consensus Types
// ============================================================================
export const ConsensusProtocolSchema = z.enum([
    'neural_voting',
    'iterative_refinement',
    'auction',
    'contract_net',
]);
export const ProposalSchema = z.object({
    topic: z.string().max(1000).describe('Topic of the proposal'),
    options: z.array(z.object({
        id: z.string().max(100),
        value: z.unknown(),
    })).min(2).max(100).describe('Options to choose from'),
    constraints: z.record(z.string(), z.unknown()).optional(),
});
export const NeuralConsensusInputSchema = z.object({
    proposal: ProposalSchema.describe('Proposal to reach consensus on'),
    agents: z.array(AgentSchema).min(2).max(1000)
        .describe('Agents participating in consensus'),
    protocol: ConsensusProtocolSchema.default('iterative_refinement')
        .describe('Consensus protocol to use'),
    maxRounds: z.number().int().min(1).max(1000).default(10)
        .describe('Maximum negotiation rounds'),
});
// ============================================================================
// Topology Types
// ============================================================================
export const TopologyObjectiveSchema = z.enum([
    'minimize_latency',
    'maximize_throughput',
    'minimize_hops',
    'fault_tolerant',
]);
export const PreferredTopologySchema = z.enum([
    'mesh',
    'tree',
    'ring',
    'star',
    'hybrid',
]);
export const TopologyConstraintsSchema = z.object({
    maxConnections: z.number().int().min(1).max(100).optional(),
    minRedundancy: z.number().min(0).max(1).optional(),
    preferredTopology: PreferredTopologySchema.optional(),
});
export const TopologyOptimizeInputSchema = z.object({
    agents: z.array(AgentSchema).min(2).max(1000)
        .describe('Agents to optimize topology for'),
    objective: TopologyObjectiveSchema.default('minimize_latency')
        .describe('Optimization objective'),
    constraints: TopologyConstraintsSchema.optional()
        .describe('Topology constraints'),
});
// ============================================================================
// Collective Memory Types
// ============================================================================
export const MemoryActionSchema = z.enum([
    'store',
    'retrieve',
    'consolidate',
    'forget',
    'synchronize',
]);
export const MemoryScopeSchema = z.enum(['global', 'team', 'pair']);
export const ConsolidationStrategySchema = z.enum(['ewc', 'replay', 'distillation']);
export const CollectiveMemoryInputSchema = z.object({
    action: MemoryActionSchema.describe('Memory action to perform'),
    memory: z.object({
        key: z.string().max(500).optional(),
        value: z.unknown().optional(),
        importance: z.number().min(0).max(1).default(0.5),
        expiry: z.string().datetime().optional(),
    }).optional().describe('Memory entry data'),
    scope: MemoryScopeSchema.default('team').describe('Memory scope'),
    consolidationStrategy: ConsolidationStrategySchema.default('ewc')
        .describe('Consolidation strategy for memory management'),
});
// ============================================================================
// Emergent Protocol Types
// ============================================================================
export const TaskTypeSchema = z.object({
    type: z.string().max(100),
    objectives: z.array(z.string()).max(20),
    constraints: z.record(z.string(), z.unknown()).optional(),
});
export const CommunicationBudgetSchema = z.object({
    symbolsPerMessage: z.number().int().min(1).max(100).default(10),
    messagesPerRound: z.number().int().min(1).max(10).default(3),
});
export const EmergentProtocolInputSchema = z.object({
    task: TaskTypeSchema.describe('Cooperative task requiring communication'),
    communicationBudget: CommunicationBudgetSchema.optional()
        .describe('Budget for communication'),
    trainingEpisodes: z.number().int().min(10).max(10000).default(1000)
        .describe('Number of training episodes'),
    interpretability: z.boolean().default(true)
        .describe('Enable interpretability analysis'),
});
// ============================================================================
// Swarm Behavior Types
// ============================================================================
export const SwarmBehaviorTypeSchema = z.enum([
    'flocking',
    'foraging',
    'formation',
    'task_allocation',
    'exploration',
    'aggregation',
    'dispersion',
]);
export const ObservabilitySchema = z.object({
    recordTrajectories: z.boolean().optional(),
    measureEmergence: z.boolean().optional(),
});
export const SwarmBehaviorInputSchema = z.object({
    behavior: SwarmBehaviorTypeSchema.describe('Type of swarm behavior'),
    parameters: z.record(z.string(), z.unknown()).optional()
        .describe('Behavior-specific parameters'),
    adaptiveRules: z.boolean().default(true)
        .describe('Allow neural adaptation of behavior rules'),
    observability: ObservabilitySchema.optional()
        .describe('Observability options'),
});
export const DEFAULT_CONFIG = {
    consensus: {
        defaultProtocol: 'iterative_refinement',
        maxRounds: 10,
        convergenceThreshold: 0.8,
    },
    topology: {
        defaultObjective: 'minimize_latency',
        maxConnections: 10,
    },
    memory: {
        defaultScope: 'team',
        consolidationInterval: 60000,
        maxEntries: 10000,
    },
    swarm: {
        defaultBehavior: 'flocking',
        adaptationRate: 0.1,
    },
};
// ============================================================================
// Helper Functions
// ============================================================================
/**
 * Create a successful MCP tool result
 */
export function successResult(data) {
    return {
        content: [{
                type: 'text',
                text: JSON.stringify(data, null, 2),
            }],
    };
}
/**
 * Create an error MCP tool result
 */
export function errorResult(error) {
    const message = error instanceof Error ? error.message : error;
    return {
        content: [{
                type: 'text',
                text: JSON.stringify({
                    error: true,
                    message,
                    timestamp: new Date().toISOString(),
                }, null, 2),
            }],
        isError: true,
    };
}
/**
 * Calculate cosine similarity between two vectors
 */
export function cosineSimilarity(a, b) {
    if (a.length !== b.length) {
        throw new Error(`Vector length mismatch: ${a.length} vs ${b.length}`);
    }
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < a.length; i++) {
        dotProduct += (a[i] ?? 0) * (b[i] ?? 0);
        normA += (a[i] ?? 0) * (a[i] ?? 0);
        normB += (b[i] ?? 0) * (b[i] ?? 0);
    }
    const denominator = Math.sqrt(normA) * Math.sqrt(normB);
    if (denominator === 0)
        return 0;
    return dotProduct / denominator;
}
//# sourceMappingURL=types.js.map