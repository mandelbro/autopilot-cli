/**
 * Integrations Module
 *
 * Provides integration bridges for external systems:
 * - agentic-flow@alpha for swarm coordination
 * - AgentDB for vector storage and similarity search
 */
export { 
// Agentic Flow
AgenticFlowBridge, getAgenticFlowBridge, AGENTIC_FLOW_EVENTS, 
// AgentDB
AgentDBBridge, getAgentDBBridge, resetBridges, } from './agentic-flow.js';
//# sourceMappingURL=index.js.map