/**
 * Code Intelligence Plugin - Type Definitions
 *
 * Core types for advanced code analysis including semantic search,
 * architecture analysis, refactoring impact prediction, module splitting,
 * and pattern learning.
 *
 * Based on ADR-035: Advanced Code Intelligence Plugin
 *
 * @module v3/plugins/code-intelligence/types
 */
import { z } from 'zod';
// ============================================================================
// Language & Search Types
// ============================================================================
/**
 * Supported programming languages
 */
export const Language = z.enum([
    'typescript',
    'javascript',
    'python',
    'java',
    'go',
    'rust',
    'cpp',
    'csharp',
    'ruby',
    'php',
    'swift',
    'kotlin',
    'scala',
]);
/**
 * Language tiers for support level
 */
export const LanguageTier = {
    typescript: 'tier1',
    javascript: 'tier1',
    python: 'tier2',
    java: 'tier2',
    go: 'tier3',
    rust: 'tier3',
    cpp: 'tier3',
    csharp: 'tier2',
    ruby: 'tier2',
    php: 'tier2',
    swift: 'tier3',
    kotlin: 'tier3',
    scala: 'tier2',
};
/**
 * Search type for semantic code search
 */
export const SearchType = z.enum([
    'semantic', // Meaning-based search
    'structural', // AST pattern matching
    'clone', // Code clone detection
    'api_usage', // API usage pattern search
]);
// ============================================================================
// Architecture Analysis Types
// ============================================================================
/**
 * Analysis types for architecture
 */
export const AnalysisType = z.enum([
    'dependency_graph',
    'layer_violations',
    'circular_deps',
    'component_coupling',
    'module_cohesion',
    'dead_code',
    'api_surface',
    'architectural_drift',
]);
/**
 * Output format for architecture analysis
 */
export const OutputFormat = z.enum([
    'json',
    'graphviz',
    'mermaid',
]);
// ============================================================================
// Refactoring Impact Types
// ============================================================================
/**
 * Change type for refactoring
 */
export const ChangeType = z.enum([
    'rename',
    'move',
    'delete',
    'extract',
    'inline',
]);
// ============================================================================
// Module Splitting Types
// ============================================================================
/**
 * Splitting strategy
 */
export const SplitStrategy = z.enum([
    'minimize_coupling',
    'balance_size',
    'feature_isolation',
]);
// ============================================================================
// Pattern Learning Types
// ============================================================================
/**
 * Pattern types to learn
 */
export const PatternType = z.enum([
    'bug_patterns',
    'refactor_patterns',
    'api_patterns',
    'test_patterns',
]);
// ============================================================================
// MCP Tool Input Schemas
// ============================================================================
/**
 * Input schema for code/semantic-search
 */
export const SemanticSearchInputSchema = z.object({
    query: z.string().min(1).max(5000),
    scope: z.object({
        paths: z.array(z.string().max(500)).max(100).optional(),
        languages: z.array(Language).max(20).optional(),
        excludeTests: z.boolean().default(false),
    }).optional(),
    searchType: SearchType.default('semantic'),
    topK: z.number().int().min(1).max(1000).default(10),
});
/**
 * Input schema for code/architecture-analyze
 */
export const ArchitectureAnalyzeInputSchema = z.object({
    rootPath: z.string().max(500).default('.'),
    analysis: z.array(AnalysisType).optional(),
    baseline: z.string().max(100).optional(),
    outputFormat: OutputFormat.optional(),
    layers: z.record(z.string(), z.array(z.string())).optional(),
});
/**
 * Input schema for code/refactor-impact
 */
export const RefactorImpactInputSchema = z.object({
    changes: z.array(z.object({
        file: z.string().max(500),
        type: ChangeType,
        details: z.record(z.string(), z.unknown()).optional(),
    })).min(1).max(100),
    depth: z.number().int().min(1).max(10).default(3),
    includeTests: z.boolean().default(true),
});
/**
 * Input schema for code/split-suggest
 */
export const SplitSuggestInputSchema = z.object({
    targetPath: z.string().max(500),
    strategy: SplitStrategy.default('minimize_coupling'),
    constraints: z.object({
        maxModuleSize: z.number().optional(),
        minModuleSize: z.number().optional(),
        preserveBoundaries: z.array(z.string()).optional(),
    }).optional(),
    targetModules: z.number().int().min(2).max(50).optional(),
});
/**
 * Input schema for code/learn-patterns
 */
export const LearnPatternsInputSchema = z.object({
    scope: z.object({
        gitRange: z.string().default('HEAD~100..HEAD'),
        authors: z.array(z.string()).optional(),
        paths: z.array(z.string()).optional(),
    }).optional(),
    patternTypes: z.array(PatternType).optional(),
    minOccurrences: z.number().int().min(1).max(100).default(3),
});
/**
 * Default configuration
 */
export const DEFAULT_CONFIG = {
    search: {
        embeddingDimension: 384,
        defaultTopK: 10,
        similarityThreshold: 0.7,
    },
    architecture: {
        maxGraphDepth: 10,
        includeVendor: false,
    },
    refactoring: {
        defaultDepth: 3,
        includeTests: true,
    },
    security: {
        allowedRoots: ['.'],
        blockedPatterns: [
            '\\.env$',
            '\\.git/config$',
            'credentials',
            'secrets?\\.',
            '\\.pem$',
            '\\.key$',
            'id_rsa',
        ],
        maskSecrets: true,
    },
};
// ============================================================================
// Error Types
// ============================================================================
/**
 * Code intelligence plugin error codes
 */
export const CodeIntelligenceErrorCodes = {
    PATH_TRAVERSAL: 'CODE_PATH_TRAVERSAL',
    SENSITIVE_FILE: 'CODE_SENSITIVE_FILE',
    GRAPH_TOO_LARGE: 'CODE_GRAPH_TOO_LARGE',
    ANALYSIS_FAILED: 'CODE_ANALYSIS_FAILED',
    PARSER_ERROR: 'CODE_PARSER_ERROR',
    WASM_NOT_INITIALIZED: 'CODE_WASM_NOT_INITIALIZED',
    LANGUAGE_NOT_SUPPORTED: 'CODE_LANGUAGE_NOT_SUPPORTED',
    GIT_ERROR: 'CODE_GIT_ERROR',
};
/**
 * Code intelligence plugin error
 */
export class CodeIntelligenceError extends Error {
    code;
    details;
    constructor(code, message, details) {
        super(message);
        this.name = 'CodeIntelligenceError';
        this.code = code;
        this.details = details;
    }
}
// ============================================================================
// Security Utilities
// ============================================================================
/**
 * Secret patterns for masking
 */
export const SECRET_PATTERNS = [
    /(['"])(?:api[_-]?key|apikey|secret|password|token|auth)['"]\s*[:=]\s*['"][^'"]+['"]/gi,
    /(?:sk|pk)[-_](?:live|test)[-_][a-zA-Z0-9]{24,}/g,
    /ghp_[a-zA-Z0-9]{36}/g,
    /-----BEGIN (?:RSA |EC )?PRIVATE KEY-----/g,
    /xox[baprs]-[a-zA-Z0-9-]+/g,
    /AKIA[0-9A-Z]{16}/g,
];
/**
 * Mask secrets in code snippet
 */
export function maskSecrets(code) {
    let masked = code;
    for (const pattern of SECRET_PATTERNS) {
        masked = masked.replace(pattern, '[REDACTED]');
    }
    return masked;
}
//# sourceMappingURL=types.js.map