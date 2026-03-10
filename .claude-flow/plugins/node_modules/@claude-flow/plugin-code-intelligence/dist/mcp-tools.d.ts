/**
 * Code Intelligence Plugin - MCP Tools
 *
 * Implements 5 MCP tools for advanced code analysis:
 * 1. code/semantic-search - Find semantically similar code patterns
 * 2. code/architecture-analyze - Analyze codebase architecture
 * 3. code/refactor-impact - Predict refactoring impact using GNN
 * 4. code/split-suggest - Suggest module splits using MinCut
 * 5. code/learn-patterns - Learn patterns from code history
 *
 * Based on ADR-035: Advanced Code Intelligence Plugin
 *
 * @module v3/plugins/code-intelligence/mcp-tools
 */
import { z } from 'zod';
import type { SemanticSearchResult, ArchitectureAnalysisResult, RefactoringImpactResult, ModuleSplitResult, PatternLearningResult, IGNNBridge, IMinCutBridge } from './types.js';
import { SemanticSearchInputSchema, ArchitectureAnalyzeInputSchema, RefactorImpactInputSchema, SplitSuggestInputSchema, LearnPatternsInputSchema } from './types.js';
/**
 * MCP Tool definition
 */
export interface MCPTool<TInput = unknown, TOutput = unknown> {
    name: string;
    description: string;
    category: string;
    version: string;
    inputSchema: z.ZodType<TInput, z.ZodTypeDef, any>;
    handler: (input: TInput, context: ToolContext) => Promise<MCPToolResult<TOutput>>;
}
/**
 * Tool execution context
 */
export interface ToolContext {
    get<T>(key: string): T | undefined;
    set<T>(key: string, value: T): void;
    bridges: {
        gnn: IGNNBridge;
        mincut: IMinCutBridge;
    };
    config: {
        allowedRoots: string[];
        blockedPatterns: RegExp[];
        maskSecrets: boolean;
    };
}
/**
 * MCP Tool result format
 */
export interface MCPToolResult<T = unknown> {
    content: Array<{
        type: 'text';
        text: string;
    }>;
    data?: T;
}
/**
 * MCP Tool: code/semantic-search
 *
 * Search for semantically similar code patterns
 */
export declare const semanticSearchTool: MCPTool<z.infer<typeof SemanticSearchInputSchema>, SemanticSearchResult>;
/**
 * MCP Tool: code/architecture-analyze
 *
 * Analyze codebase architecture and detect drift
 */
export declare const architectureAnalyzeTool: MCPTool<z.infer<typeof ArchitectureAnalyzeInputSchema>, ArchitectureAnalysisResult>;
/**
 * MCP Tool: code/refactor-impact
 *
 * Analyze impact of proposed code changes using GNN
 */
export declare const refactorImpactTool: MCPTool<z.infer<typeof RefactorImpactInputSchema>, RefactoringImpactResult>;
/**
 * MCP Tool: code/split-suggest
 *
 * Suggest optimal code splitting using MinCut algorithm
 */
export declare const splitSuggestTool: MCPTool<z.infer<typeof SplitSuggestInputSchema>, ModuleSplitResult>;
/**
 * MCP Tool: code/learn-patterns
 *
 * Learn recurring patterns from code changes using SONA
 */
export declare const learnPatternsTool: MCPTool<z.infer<typeof LearnPatternsInputSchema>, PatternLearningResult>;
/**
 * All Code Intelligence MCP Tools
 */
export declare const codeIntelligenceTools: MCPTool[];
/**
 * Tool name to handler map
 */
export declare const toolHandlers: Map<string, (input: unknown, context: ToolContext) => Promise<MCPToolResult<unknown>>>;
/**
 * Create tool context with bridges
 */
export declare function createToolContext(config?: Partial<ToolContext['config']>): ToolContext;
export default codeIntelligenceTools;
//# sourceMappingURL=mcp-tools.d.ts.map