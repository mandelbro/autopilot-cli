/**
 * Hooks Integration Module
 *
 * Provides comprehensive hook capabilities for plugin development.
 * Enables lifecycle event interception, transformation, and monitoring.
 */
import { EventEmitter } from 'events';
import type { HookDefinition, HookEvent, HookPriority, HookHandler, HookContext, HookResult, ILogger, IEventBus } from '../types/index.js';
import { HookEvent as HookEventEnum, HookPriority as HookPriorityEnum } from '../types/index.js';
export interface HookRegistryConfig {
    logger?: ILogger;
    eventBus?: IEventBus;
    maxHooksPerEvent?: number;
    defaultTimeout?: number;
    parallelExecution?: boolean;
}
export interface HookEntry {
    readonly hook: HookDefinition;
    readonly pluginName?: string;
    readonly registeredAt: Date;
    executionCount: number;
    lastExecuted?: Date;
    lastError?: string;
    avgExecutionTime: number;
}
export interface HookRegistryStats {
    totalHooks: number;
    hooksByEvent: Record<string, number>;
    executionCount: number;
    errorCount: number;
    avgExecutionTime: number;
}
/**
 * Central registry for hook management.
 */
export declare class HookRegistry extends EventEmitter {
    private readonly hooks;
    private readonly config;
    private stats;
    constructor(config?: HookRegistryConfig);
    /**
     * Register a hook.
     */
    register(hook: HookDefinition, pluginName?: string): () => void;
    /**
     * Unregister a hook.
     */
    unregister(event: HookEvent, handler: HookHandler): boolean;
    /**
     * Execute hooks for an event.
     */
    execute(event: HookEvent, data: unknown, source?: string): Promise<HookResult[]>;
    private groupByPriority;
    private executeHook;
    /**
     * Get hooks for a specific event.
     */
    getHooks(event: HookEvent): HookEntry[];
    /**
     * Get all registered hooks.
     */
    getAllHooks(): Map<HookEvent, HookEntry[]>;
    /**
     * Get registry statistics.
     */
    getStats(): HookRegistryStats;
    /**
     * Clear all hooks.
     */
    clear(): void;
}
/**
 * Fluent builder for creating hooks.
 */
export declare class HookBuilder {
    private event;
    private name?;
    private description?;
    private priority;
    private isAsync;
    private handler?;
    private conditions;
    private transformers;
    constructor(event: HookEvent);
    withName(name: string): this;
    withDescription(description: string): this;
    withPriority(priority: HookPriority): this;
    synchronous(): this;
    /**
     * Add a condition that must be met for the hook to execute.
     */
    when(condition: (context: HookContext) => boolean): this;
    /**
     * Add a data transformer that runs before the handler.
     */
    transform(transformer: (data: unknown) => unknown): this;
    /**
     * Set the handler function.
     */
    handle(handler: HookHandler): this;
    /**
     * Build the hook definition.
     */
    build(): HookDefinition;
}
/**
 * Factory for creating common hooks.
 */
export declare class HookFactory {
    /**
     * Create a logging hook for any event.
     */
    static createLogger(event: HookEvent, logger: ILogger, options?: {
        name?: string;
        logLevel?: 'debug' | 'info' | 'warn';
    }): HookDefinition;
    /**
     * Create a timing hook that measures execution time.
     */
    static createTimer(event: HookEvent, _onComplete: (duration: number, context: HookContext) => void): HookDefinition;
    /**
     * Create a validation hook.
     */
    static createValidator<T>(event: HookEvent, validator: (data: T) => boolean | string, options?: {
        name?: string;
        abortOnFail?: boolean;
    }): HookDefinition;
    /**
     * Create a rate limiting hook.
     */
    static createRateLimiter(event: HookEvent, options: {
        maxPerMinute: number;
        name?: string;
    }): HookDefinition;
    /**
     * Create a caching hook.
     */
    static createCache<T>(event: HookEvent, options: {
        keyExtractor: (data: T) => string;
        ttlMs?: number;
        maxSize?: number;
        name?: string;
    }): HookDefinition;
    /**
     * Create a retry hook.
     */
    static createRetry(event: HookEvent, options: {
        maxRetries: number;
        delayMs?: number;
        backoffMultiplier?: number;
        name?: string;
    }): HookDefinition;
}
/**
 * Utility for executing hooks in different patterns.
 */
export declare class HookExecutor {
    private readonly registry;
    constructor(registry: HookRegistry);
    /**
     * Execute hooks and collect all results.
     */
    executeAll(event: HookEvent, data: unknown, source?: string): Promise<HookResult[]>;
    /**
     * Execute hooks and return the first successful result.
     */
    executeFirst(event: HookEvent, data: unknown, source?: string): Promise<HookResult | null>;
    /**
     * Execute hooks and return true if all succeeded.
     */
    executeValidate(event: HookEvent, data: unknown, source?: string): Promise<boolean>;
    /**
     * Execute hooks and return the final transformed data.
     */
    executeTransform<T>(event: HookEvent, data: T, source?: string): Promise<T>;
    /**
     * Execute hooks until one aborts.
     */
    executeUntilAbort(event: HookEvent, data: unknown, source?: string): Promise<{
        results: HookResult[];
        aborted: boolean;
    }>;
}
export { HookEventEnum as HookEvent, HookPriorityEnum as HookPriority, type HookDefinition, type HookHandler, type HookContext, type HookResult, };
//# sourceMappingURL=index.d.ts.map