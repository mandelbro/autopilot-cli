/**
 * Worker Integration Module
 *
 * Provides comprehensive worker capabilities for plugin development.
 * Integrates with agentic-flow worker pools and task execution.
 */
import { EventEmitter } from 'events';
import type { WorkerDefinition, WorkerType, WorkerResult, WorkerMetrics, WorkerHealth, ILogger, IEventBus } from '../types/index.js';
export declare const WORKER_EVENTS: {
    readonly SPAWNED: "worker:spawned";
    readonly STARTED: "worker:started";
    readonly COMPLETED: "worker:completed";
    readonly FAILED: "worker:failed";
    readonly TERMINATED: "worker:terminated";
    readonly HEALTH_CHECK: "worker:health-check";
    readonly METRICS_UPDATE: "worker:metrics-update";
};
export type WorkerEvent = typeof WORKER_EVENTS[keyof typeof WORKER_EVENTS];
export interface WorkerTask {
    readonly id: string;
    readonly type: string;
    readonly input: unknown;
    readonly priority?: number;
    readonly timeout?: number;
    readonly retries?: number;
    readonly metadata?: Record<string, unknown>;
}
export interface WorkerTaskResult extends WorkerResult {
    readonly taskId: string;
    readonly taskType: string;
    readonly retryCount?: number;
}
export interface WorkerPoolConfig {
    readonly minWorkers: number;
    readonly maxWorkers: number;
    readonly taskQueueSize: number;
    readonly workerIdleTimeout: number;
    readonly healthCheckInterval: number;
    readonly scalingThreshold: number;
    readonly logger?: ILogger;
    readonly eventBus?: IEventBus;
}
export interface IWorkerInstance {
    readonly id: string;
    readonly definition: WorkerDefinition;
    readonly status: 'idle' | 'busy' | 'error' | 'terminated';
    readonly currentTask?: WorkerTask;
    readonly metrics: WorkerMetrics;
    execute(task: WorkerTask): Promise<WorkerTaskResult>;
    terminate(): Promise<void>;
    healthCheck(): Promise<WorkerHealth>;
    getMetrics(): WorkerMetrics;
}
/**
 * Worker instance implementation.
 */
export declare class WorkerInstance extends EventEmitter implements IWorkerInstance {
    readonly id: string;
    readonly definition: WorkerDefinition;
    private _status;
    private _currentTask?;
    private _metrics;
    private readonly startTime;
    lastActivity: number;
    constructor(id: string, definition: WorkerDefinition);
    get status(): 'idle' | 'busy' | 'error' | 'terminated';
    get currentTask(): WorkerTask | undefined;
    get metrics(): WorkerMetrics;
    private initMetrics;
    execute(task: WorkerTask): Promise<WorkerTaskResult>;
    private executeTask;
    private updateMetrics;
    terminate(): Promise<void>;
    healthCheck(): Promise<WorkerHealth>;
    getMetrics(): WorkerMetrics;
}
export interface IWorkerPool {
    readonly config: WorkerPoolConfig;
    readonly workers: ReadonlyMap<string, IWorkerInstance>;
    spawn(definition: WorkerDefinition): Promise<IWorkerInstance>;
    terminate(workerId: string): Promise<void>;
    submit(task: WorkerTask): Promise<WorkerTaskResult>;
    getWorker(workerId: string): IWorkerInstance | undefined;
    getAvailableWorker(type?: WorkerType): IWorkerInstance | undefined;
    healthCheck(): Promise<Map<string, WorkerHealth>>;
    getPoolMetrics(): PoolMetrics;
    shutdown(): Promise<void>;
}
export interface PoolMetrics {
    totalWorkers: number;
    activeWorkers: number;
    idleWorkers: number;
    queuedTasks: number;
    completedTasks: number;
    failedTasks: number;
    avgTaskDuration: number;
}
/**
 * Worker pool implementation.
 */
export declare class WorkerPool extends EventEmitter implements IWorkerPool {
    readonly config: WorkerPoolConfig;
    private readonly _workers;
    private readonly taskQueue;
    private nextWorkerId;
    private poolMetrics;
    private healthCheckTimer?;
    constructor(config?: Partial<WorkerPoolConfig>);
    get workers(): ReadonlyMap<string, IWorkerInstance>;
    private initPoolMetrics;
    private startHealthChecks;
    private performHealthChecks;
    spawn(definition: WorkerDefinition): Promise<IWorkerInstance>;
    terminate(workerId: string): Promise<void>;
    submit(task: WorkerTask): Promise<WorkerTaskResult>;
    private executeOnWorker;
    getWorker(workerId: string): IWorkerInstance | undefined;
    getAvailableWorker(type?: WorkerType): IWorkerInstance | undefined;
    healthCheck(): Promise<Map<string, WorkerHealth>>;
    getPoolMetrics(): PoolMetrics;
    shutdown(): Promise<void>;
}
/**
 * Factory for creating worker definitions.
 */
export declare class WorkerFactory {
    /**
     * Create a coder worker.
     */
    static createCoder(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a reviewer worker.
     */
    static createReviewer(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a tester worker.
     */
    static createTester(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a researcher worker.
     */
    static createResearcher(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a planner worker.
     */
    static createPlanner(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a coordinator worker.
     */
    static createCoordinator(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a security worker.
     */
    static createSecurity(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a performance worker.
     */
    static createPerformance(name: string, capabilities?: string[]): WorkerDefinition;
    /**
     * Create a specialized worker.
     */
    static createSpecialized(name: string, capabilities: string[], options?: Partial<Omit<WorkerDefinition, 'type' | 'name' | 'capabilities'>>): WorkerDefinition;
    /**
     * Create a long-running worker.
     */
    static createLongRunning(name: string, capabilities: string[], options?: Partial<Omit<WorkerDefinition, 'type' | 'name' | 'capabilities'>>): WorkerDefinition;
}
export type { WorkerDefinition, WorkerType, WorkerResult, WorkerMetrics, WorkerHealth };
//# sourceMappingURL=index.d.ts.map