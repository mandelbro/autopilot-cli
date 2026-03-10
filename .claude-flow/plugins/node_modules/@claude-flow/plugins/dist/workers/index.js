/**
 * Worker Integration Module
 *
 * Provides comprehensive worker capabilities for plugin development.
 * Integrates with agentic-flow worker pools and task execution.
 */
import { EventEmitter } from 'events';
// ============================================================================
// Worker Events
// ============================================================================
export const WORKER_EVENTS = {
    SPAWNED: 'worker:spawned',
    STARTED: 'worker:started',
    COMPLETED: 'worker:completed',
    FAILED: 'worker:failed',
    TERMINATED: 'worker:terminated',
    HEALTH_CHECK: 'worker:health-check',
    METRICS_UPDATE: 'worker:metrics-update',
};
const DEFAULT_POOL_CONFIG = {
    minWorkers: 1,
    maxWorkers: 10,
    taskQueueSize: 100,
    workerIdleTimeout: 60000,
    healthCheckInterval: 30000,
    scalingThreshold: 0.8,
};
/**
 * Worker instance implementation.
 */
export class WorkerInstance extends EventEmitter {
    id;
    definition;
    _status = 'idle';
    _currentTask;
    _metrics;
    startTime;
    // Track last activity for idle detection
    lastActivity;
    constructor(id, definition) {
        super();
        this.id = id;
        this.definition = definition;
        this.startTime = Date.now();
        this.lastActivity = Date.now();
        this._metrics = this.initMetrics();
    }
    get status() {
        return this._status;
    }
    get currentTask() {
        return this._currentTask;
    }
    get metrics() {
        return { ...this._metrics };
    }
    initMetrics() {
        return {
            tasksExecuted: 0,
            tasksSucceeded: 0,
            tasksFailed: 0,
            avgDuration: 0,
            totalTokensUsed: 0,
            currentLoad: 0,
            uptime: 0,
            lastActivity: Date.now(),
            healthScore: 1.0,
        };
    }
    async execute(task) {
        if (this._status === 'terminated') {
            throw new Error(`Worker ${this.id} is terminated`);
        }
        this._status = 'busy';
        this._currentTask = task;
        this.lastActivity = Date.now();
        const startTime = Date.now();
        try {
            // Execute the task (placeholder - actual execution would happen via agentic-flow)
            const result = await this.executeTask(task);
            const duration = Date.now() - startTime;
            this.updateMetrics(true, duration, result.tokensUsed);
            this._status = 'idle';
            this._currentTask = undefined;
            return {
                workerId: this.id,
                taskId: task.id,
                taskType: task.type,
                success: true,
                output: result.output,
                duration,
                tokensUsed: result.tokensUsed,
                metadata: result.metadata,
            };
        }
        catch (error) {
            const duration = Date.now() - startTime;
            this.updateMetrics(false, duration);
            this._status = 'error';
            this._currentTask = undefined;
            return {
                workerId: this.id,
                taskId: task.id,
                taskType: task.type,
                success: false,
                error: error instanceof Error ? error.message : String(error),
                duration,
            };
        }
    }
    async executeTask(task) {
        // Placeholder for actual task execution
        // In production, this would integrate with agentic-flow task execution
        const timeout = task.timeout ?? this.definition.timeout ?? 30000;
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                reject(new Error(`Task ${task.id} timed out after ${timeout}ms`));
            }, timeout);
            // Simulate task completion (replace with actual execution)
            setImmediate(() => {
                clearTimeout(timer);
                resolve({
                    output: { status: 'completed', taskId: task.id },
                    tokensUsed: 0,
                    metadata: { executedBy: this.id },
                });
            });
        });
    }
    updateMetrics(success, duration, tokensUsed) {
        this._metrics.tasksExecuted++;
        if (success) {
            this._metrics.tasksSucceeded++;
        }
        else {
            this._metrics.tasksFailed++;
        }
        // Running average for duration
        const totalDuration = this._metrics.avgDuration * (this._metrics.tasksExecuted - 1) + duration;
        this._metrics.avgDuration = totalDuration / this._metrics.tasksExecuted;
        if (tokensUsed) {
            this._metrics.totalTokensUsed += tokensUsed;
        }
        this._metrics.uptime = Date.now() - this.startTime;
        this._metrics.lastActivity = Date.now();
        // Calculate health score
        const successRate = this._metrics.tasksSucceeded / Math.max(1, this._metrics.tasksExecuted);
        this._metrics.healthScore = successRate;
    }
    async terminate() {
        this._status = 'terminated';
        this._currentTask = undefined;
        this.emit(WORKER_EVENTS.TERMINATED, { workerId: this.id });
    }
    async healthCheck() {
        const issues = [];
        if (this._status === 'error') {
            issues.push('Worker in error state');
        }
        if (this._status === 'terminated') {
            issues.push('Worker terminated');
        }
        const successRate = this._metrics.tasksSucceeded / Math.max(1, this._metrics.tasksExecuted);
        if (successRate < 0.5) {
            issues.push('Low success rate');
        }
        let status = 'healthy';
        if (issues.length > 0 && successRate >= 0.5) {
            status = 'degraded';
        }
        else if (issues.length > 0 || this._status === 'terminated') {
            status = 'unhealthy';
        }
        return {
            status,
            score: this._metrics.healthScore,
            issues,
            resources: {
                memoryMb: process.memoryUsage().heapUsed / 1024 / 1024,
                cpuPercent: 0, // Would need actual CPU monitoring
            },
        };
    }
    getMetrics() {
        this._metrics.uptime = Date.now() - this.startTime;
        this._metrics.currentLoad = this._status === 'busy' ? 1.0 : 0.0;
        return { ...this._metrics };
    }
}
/**
 * Worker pool implementation.
 */
export class WorkerPool extends EventEmitter {
    config;
    _workers = new Map();
    taskQueue = [];
    nextWorkerId = 1;
    poolMetrics;
    healthCheckTimer;
    constructor(config) {
        super();
        this.config = { ...DEFAULT_POOL_CONFIG, ...config };
        this.poolMetrics = this.initPoolMetrics();
        this.startHealthChecks();
    }
    get workers() {
        return this._workers;
    }
    initPoolMetrics() {
        return {
            totalWorkers: 0,
            activeWorkers: 0,
            idleWorkers: 0,
            queuedTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            avgTaskDuration: 0,
        };
    }
    startHealthChecks() {
        this.healthCheckTimer = setInterval(() => this.performHealthChecks(), this.config.healthCheckInterval);
    }
    async performHealthChecks() {
        const results = await this.healthCheck();
        this.emit(WORKER_EVENTS.HEALTH_CHECK, { results: Object.fromEntries(results) });
    }
    async spawn(definition) {
        if (this._workers.size >= this.config.maxWorkers) {
            throw new Error(`Maximum worker limit (${this.config.maxWorkers}) reached`);
        }
        const workerId = `worker-${this.nextWorkerId++}`;
        const worker = new WorkerInstance(workerId, definition);
        this._workers.set(workerId, worker);
        this.poolMetrics.totalWorkers++;
        this.poolMetrics.idleWorkers++;
        this.emit(WORKER_EVENTS.SPAWNED, { workerId, definition });
        return worker;
    }
    async terminate(workerId) {
        const worker = this._workers.get(workerId);
        if (!worker) {
            throw new Error(`Worker ${workerId} not found`);
        }
        await worker.terminate();
        this._workers.delete(workerId);
        this.poolMetrics.totalWorkers--;
        if (worker.status === 'idle') {
            this.poolMetrics.idleWorkers--;
        }
        else if (worker.status === 'busy') {
            this.poolMetrics.activeWorkers--;
        }
    }
    async submit(task) {
        // Find available worker
        const worker = this.getAvailableWorker();
        if (!worker) {
            // Queue the task if no worker available
            if (this.taskQueue.length >= this.config.taskQueueSize) {
                throw new Error('Task queue is full');
            }
            return new Promise((resolve, reject) => {
                this.taskQueue.push(task);
                this.poolMetrics.queuedTasks++;
                // Wait for worker to become available
                const checkWorker = setInterval(() => {
                    const available = this.getAvailableWorker();
                    if (available) {
                        clearInterval(checkWorker);
                        const idx = this.taskQueue.indexOf(task);
                        if (idx !== -1) {
                            this.taskQueue.splice(idx, 1);
                            this.poolMetrics.queuedTasks--;
                        }
                        this.executeOnWorker(available, task).then(resolve).catch(reject);
                    }
                }, 100);
                // Timeout for queued tasks
                setTimeout(() => {
                    clearInterval(checkWorker);
                    const idx = this.taskQueue.indexOf(task);
                    if (idx !== -1) {
                        this.taskQueue.splice(idx, 1);
                        this.poolMetrics.queuedTasks--;
                        reject(new Error(`Task ${task.id} timed out in queue`));
                    }
                }, task.timeout ?? 30000);
            });
        }
        return this.executeOnWorker(worker, task);
    }
    async executeOnWorker(worker, task) {
        this.poolMetrics.idleWorkers--;
        this.poolMetrics.activeWorkers++;
        this.emit(WORKER_EVENTS.STARTED, { workerId: worker.id, taskId: task.id });
        try {
            const result = await worker.execute(task);
            if (result.success) {
                this.poolMetrics.completedTasks++;
                this.emit(WORKER_EVENTS.COMPLETED, { workerId: worker.id, taskId: task.id, result });
            }
            else {
                this.poolMetrics.failedTasks++;
                this.emit(WORKER_EVENTS.FAILED, { workerId: worker.id, taskId: task.id, error: result.error });
            }
            // Update average duration
            const totalDuration = this.poolMetrics.avgTaskDuration * (this.poolMetrics.completedTasks + this.poolMetrics.failedTasks - 1) +
                result.duration;
            this.poolMetrics.avgTaskDuration =
                totalDuration / (this.poolMetrics.completedTasks + this.poolMetrics.failedTasks);
            this.poolMetrics.activeWorkers--;
            this.poolMetrics.idleWorkers++;
            return result;
        }
        catch (error) {
            this.poolMetrics.activeWorkers--;
            this.poolMetrics.idleWorkers++;
            this.poolMetrics.failedTasks++;
            throw error;
        }
    }
    getWorker(workerId) {
        return this._workers.get(workerId);
    }
    getAvailableWorker(type) {
        for (const worker of this._workers.values()) {
            if (worker.status === 'idle') {
                if (!type || worker.definition.type === type) {
                    return worker;
                }
            }
        }
        return undefined;
    }
    async healthCheck() {
        const results = new Map();
        for (const [id, worker] of this._workers) {
            results.set(id, await worker.healthCheck());
        }
        return results;
    }
    getPoolMetrics() {
        return {
            ...this.poolMetrics,
            queuedTasks: this.taskQueue.length,
        };
    }
    async shutdown() {
        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
        }
        const terminatePromises = Array.from(this._workers.keys()).map(id => this.terminate(id));
        await Promise.all(terminatePromises);
        this.taskQueue.length = 0;
        this.poolMetrics = this.initPoolMetrics();
    }
}
// ============================================================================
// Worker Factory
// ============================================================================
/**
 * Factory for creating worker definitions.
 */
export class WorkerFactory {
    /**
     * Create a coder worker.
     */
    static createCoder(name, capabilities) {
        return {
            type: 'coder',
            name,
            description: 'Code implementation and development worker',
            capabilities: capabilities ?? ['code-generation', 'refactoring', 'debugging'],
            maxConcurrentTasks: 3,
            timeout: 60000,
            priority: 50,
        };
    }
    /**
     * Create a reviewer worker.
     */
    static createReviewer(name, capabilities) {
        return {
            type: 'reviewer',
            name,
            description: 'Code review and quality analysis worker',
            capabilities: capabilities ?? ['code-review', 'security-audit', 'style-check'],
            maxConcurrentTasks: 5,
            timeout: 30000,
            priority: 60,
        };
    }
    /**
     * Create a tester worker.
     */
    static createTester(name, capabilities) {
        return {
            type: 'tester',
            name,
            description: 'Test generation and execution worker',
            capabilities: capabilities ?? ['test-generation', 'test-execution', 'coverage-analysis'],
            maxConcurrentTasks: 4,
            timeout: 120000,
            priority: 55,
        };
    }
    /**
     * Create a researcher worker.
     */
    static createResearcher(name, capabilities) {
        return {
            type: 'researcher',
            name,
            description: 'Information gathering and analysis worker',
            capabilities: capabilities ?? ['web-search', 'documentation-analysis', 'pattern-recognition'],
            maxConcurrentTasks: 6,
            timeout: 60000,
            priority: 40,
        };
    }
    /**
     * Create a planner worker.
     */
    static createPlanner(name, capabilities) {
        return {
            type: 'planner',
            name,
            description: 'Task planning and decomposition worker',
            capabilities: capabilities ?? ['task-decomposition', 'dependency-analysis', 'scheduling'],
            maxConcurrentTasks: 2,
            timeout: 30000,
            priority: 70,
        };
    }
    /**
     * Create a coordinator worker.
     */
    static createCoordinator(name, capabilities) {
        return {
            type: 'coordinator',
            name,
            description: 'Multi-agent coordination worker',
            capabilities: capabilities ?? ['agent-coordination', 'task-routing', 'consensus-building'],
            maxConcurrentTasks: 1,
            timeout: 45000,
            priority: 90,
        };
    }
    /**
     * Create a security worker.
     */
    static createSecurity(name, capabilities) {
        return {
            type: 'security',
            name,
            description: 'Security analysis and vulnerability detection worker',
            capabilities: capabilities ?? ['vulnerability-scan', 'threat-modeling', 'security-review'],
            maxConcurrentTasks: 3,
            timeout: 90000,
            priority: 80,
        };
    }
    /**
     * Create a performance worker.
     */
    static createPerformance(name, capabilities) {
        return {
            type: 'performance',
            name,
            description: 'Performance analysis and optimization worker',
            capabilities: capabilities ?? ['profiling', 'bottleneck-detection', 'optimization'],
            maxConcurrentTasks: 2,
            timeout: 120000,
            priority: 65,
        };
    }
    /**
     * Create a specialized worker.
     */
    static createSpecialized(name, capabilities, options) {
        return {
            type: 'specialized',
            name,
            capabilities,
            maxConcurrentTasks: options?.maxConcurrentTasks ?? 3,
            timeout: options?.timeout ?? 60000,
            priority: options?.priority ?? 50,
            description: options?.description,
            specialization: options?.specialization,
            metadata: options?.metadata,
        };
    }
    /**
     * Create a long-running worker.
     */
    static createLongRunning(name, capabilities, options) {
        return {
            type: 'long-running',
            name,
            capabilities,
            maxConcurrentTasks: 1,
            timeout: options?.timeout ?? 3600000, // 1 hour default
            priority: options?.priority ?? 30,
            description: options?.description ?? 'Long-running background worker',
            specialization: options?.specialization,
            metadata: options?.metadata,
        };
    }
}
//# sourceMappingURL=index.js.map