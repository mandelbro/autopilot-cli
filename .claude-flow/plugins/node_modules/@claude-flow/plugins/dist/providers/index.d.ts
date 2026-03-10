/**
 * LLM Provider Integration Module
 *
 * Provides unified interface for LLM providers in the plugin system.
 * Enables multi-provider support, fallback chains, and cost optimization.
 */
import { EventEmitter } from 'events';
import type { LLMProviderDefinition, LLMCapability, LLMRequest, LLMResponse, LLMMessage, LLMTool, LLMToolCall, RateLimitConfig, CostConfig, ILogger, IEventBus } from '../types/index.js';
export declare const PROVIDER_EVENTS: {
    readonly REGISTERED: "provider:registered";
    readonly UNREGISTERED: "provider:unregistered";
    readonly REQUEST_START: "provider:request-start";
    readonly REQUEST_COMPLETE: "provider:request-complete";
    readonly REQUEST_ERROR: "provider:request-error";
    readonly RATE_LIMITED: "provider:rate-limited";
    readonly FALLBACK: "provider:fallback";
};
export type ProviderEvent = typeof PROVIDER_EVENTS[keyof typeof PROVIDER_EVENTS];
export interface ILLMProvider {
    readonly definition: LLMProviderDefinition;
    complete(request: LLMRequest): Promise<LLMResponse>;
    stream?(request: LLMRequest): AsyncIterable<Partial<LLMResponse>>;
    embed?(texts: string[]): Promise<number[][]>;
    healthCheck(): Promise<{
        healthy: boolean;
        latencyMs: number;
    }>;
    getRateLimitStatus(): RateLimitStatus;
    getCostEstimate(request: LLMRequest): number;
}
export interface RateLimitStatus {
    requestsRemaining: number;
    tokensRemaining: number;
    resetAt: Date;
    isLimited: boolean;
}
export interface ProviderRegistryConfig {
    logger?: ILogger;
    eventBus?: IEventBus;
    defaultProvider?: string;
    fallbackChain?: string[];
    costOptimization?: boolean;
    retryConfig?: RetryConfig;
}
export interface RetryConfig {
    maxRetries: number;
    initialDelayMs: number;
    maxDelayMs: number;
    backoffMultiplier: number;
}
export interface ProviderEntry {
    readonly provider: ILLMProvider;
    readonly registeredAt: Date;
    requestCount: number;
    errorCount: number;
    totalTokensUsed: number;
    totalCost: number;
    lastUsed?: Date;
}
export interface ProviderRegistryStats {
    totalProviders: number;
    totalRequests: number;
    totalErrors: number;
    totalTokensUsed: number;
    totalCost: number;
    providerStats: Record<string, {
        requests: number;
        errors: number;
        tokensUsed: number;
        cost: number;
        avgLatency: number;
    }>;
}
/**
 * Central registry for LLM provider management.
 */
export declare class ProviderRegistry extends EventEmitter {
    private readonly providers;
    private readonly config;
    private readonly latencyTracking;
    constructor(config?: ProviderRegistryConfig);
    /**
     * Register a provider.
     */
    register(provider: ILLMProvider): void;
    /**
     * Unregister a provider.
     */
    unregister(name: string): boolean;
    /**
     * Get a provider by name.
     */
    get(name: string): ILLMProvider | undefined;
    /**
     * Get the best available provider based on criteria.
     */
    getBest(options?: {
        capabilities?: LLMCapability[];
        model?: string;
        preferCheaper?: boolean;
    }): ILLMProvider | undefined;
    /**
     * Execute a request with automatic provider selection and fallback.
     */
    execute(request: LLMRequest): Promise<LLMResponse>;
    /**
     * Execute a request on a specific provider with retry.
     */
    executeWithProvider(providerName: string, request: LLMRequest): Promise<LLMResponse>;
    private tryFallback;
    private delay;
    /**
     * List all registered providers.
     */
    list(): LLMProviderDefinition[];
    /**
     * Get provider statistics.
     */
    getStats(): ProviderRegistryStats;
    /**
     * Health check all providers.
     */
    healthCheck(): Promise<Map<string, {
        healthy: boolean;
        latencyMs: number;
    }>>;
}
/**
 * Abstract base class for LLM providers.
 */
export declare abstract class BaseLLMProvider implements ILLMProvider {
    readonly definition: LLMProviderDefinition;
    protected rateLimitState: {
        requestsInWindow: number;
        tokensInWindow: number;
        windowStart: Date;
    };
    constructor(definition: LLMProviderDefinition);
    abstract complete(request: LLMRequest): Promise<LLMResponse>;
    stream?(request: LLMRequest): AsyncIterable<Partial<LLMResponse>>;
    embed?(texts: string[]): Promise<number[][]>;
    healthCheck(): Promise<{
        healthy: boolean;
        latencyMs: number;
    }>;
    getRateLimitStatus(): RateLimitStatus;
    getCostEstimate(request: LLMRequest): number;
    protected updateRateLimits(tokensUsed: number): void;
}
/**
 * Factory for creating provider definitions.
 */
export declare class ProviderFactory {
    /**
     * Create an Anthropic Claude provider definition.
     */
    static createClaude(options?: {
        displayName?: string;
        models?: string[];
        rateLimit?: RateLimitConfig;
        costPerToken?: CostConfig;
    }): LLMProviderDefinition;
    /**
     * Create an OpenAI provider definition.
     */
    static createOpenAI(options?: {
        displayName?: string;
        models?: string[];
        rateLimit?: RateLimitConfig;
        costPerToken?: CostConfig;
    }): LLMProviderDefinition;
    /**
     * Create a local/self-hosted provider definition.
     */
    static createLocal(options: {
        name: string;
        displayName: string;
        models: string[];
        capabilities: LLMCapability[];
        endpoint?: string;
    }): LLMProviderDefinition;
    /**
     * Create a custom provider definition.
     */
    static createCustom(definition: LLMProviderDefinition): LLMProviderDefinition;
}
export type { LLMProviderDefinition, LLMCapability, LLMRequest, LLMResponse, LLMMessage, LLMTool, LLMToolCall, RateLimitConfig, CostConfig, };
//# sourceMappingURL=index.d.ts.map