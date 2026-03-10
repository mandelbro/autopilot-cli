/**
 * Neural Coordination MCP Tools
 *
 * 5 MCP tools for multi-agent neural coordination:
 * - coordination/neural-consensus: Neural negotiation consensus
 * - coordination/topology-optimize: GNN-based topology optimization
 * - coordination/collective-memory: Shared memory management
 * - coordination/emergent-protocol: MARL communication protocols
 * - coordination/swarm-behavior: Emergent swarm behaviors
 */
import type { MCPTool, MCPToolResult, ToolContext } from './types.js';
export declare const neuralConsensusTool: MCPTool;
export declare const topologyOptimizeTool: MCPTool;
export declare const collectiveMemoryTool: MCPTool;
export declare const emergentProtocolTool: MCPTool;
export declare const swarmBehaviorTool: MCPTool;
export declare const neuralCoordinationTools: MCPTool[];
export declare const toolHandlers: Map<string, (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>>;
export declare function getTool(name: string): MCPTool | undefined;
export declare function getToolNames(): string[];
export default neuralCoordinationTools;
//# sourceMappingURL=mcp-tools.d.ts.map