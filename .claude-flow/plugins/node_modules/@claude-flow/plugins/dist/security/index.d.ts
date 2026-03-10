/**
 * Security Module
 *
 * Provides security utilities for plugin development.
 * Implements best practices for input validation, sanitization, and safe operations.
 */
/**
 * Validate and sanitize a string input.
 */
export declare function validateString(input: unknown, options?: {
    minLength?: number;
    maxLength?: number;
    pattern?: RegExp;
    trim?: boolean;
    lowercase?: boolean;
    uppercase?: boolean;
}): string | null;
/**
 * Validate a number input.
 */
export declare function validateNumber(input: unknown, options?: {
    min?: number;
    max?: number;
    integer?: boolean;
}): number | null;
/**
 * Validate a boolean input.
 */
export declare function validateBoolean(input: unknown): boolean | null;
/**
 * Validate an array input.
 */
export declare function validateArray<T>(input: unknown, itemValidator: (item: unknown) => T | null, options?: {
    minLength?: number;
    maxLength?: number;
    unique?: boolean;
}): T[] | null;
/**
 * Validate an enum value.
 */
export declare function validateEnum<T extends string>(input: unknown, allowedValues: readonly T[]): T | null;
/**
 * Validate a file path for safety.
 */
export declare function validatePath(inputPath: unknown, options?: {
    allowedExtensions?: string[];
    blockedPatterns?: RegExp[];
    mustExist?: boolean;
    allowAbsolute?: boolean;
}): string | null;
/**
 * Create a safe path relative to a base directory.
 * Prevents path traversal attacks.
 */
export declare function safePath(baseDir: string, ...segments: string[]): string;
/**
 * Async version of safePath that uses realpath.
 * More secure as it resolves symlinks.
 */
export declare function safePathAsync(baseDir: string, ...segments: string[]): Promise<string>;
/**
 * Parse JSON safely, stripping dangerous keys.
 */
export declare function safeJsonParse<T = unknown>(content: string): T;
/**
 * Stringify JSON with circular reference detection.
 */
export declare function safeJsonStringify(value: unknown, options?: {
    space?: number;
    maxDepth?: number;
    replacer?: (key: string, value: unknown) => unknown;
}): string;
/**
 * Validate a command for safe execution.
 */
export declare function validateCommand(command: unknown, options?: {
    allowedCommands?: Set<string>;
    blockedCommands?: Set<string>;
    allowShellMetachars?: boolean;
}): {
    command: string;
    args: string[];
} | null;
/**
 * Escape a string for safe shell argument use.
 */
export declare function escapeShellArg(arg: string): string;
/**
 * Sanitize error messages to remove sensitive data.
 */
export declare function sanitizeErrorMessage(error: unknown): string;
/**
 * Create a safe error object for logging/transmission.
 */
export declare function sanitizeError(error: unknown): {
    name: string;
    message: string;
    code?: string;
};
export interface RateLimiter {
    tryAcquire(): boolean;
    getRemaining(): number;
    reset(): void;
}
/**
 * Create a token bucket rate limiter.
 */
export declare function createRateLimiter(options: {
    maxTokens: number;
    refillRate: number;
    refillInterval: number;
}): RateLimiter;
/**
 * Generate a secure random ID.
 */
export declare function generateSecureId(length?: number): string;
/**
 * Generate a secure random token (URL-safe).
 */
export declare function generateSecureToken(length?: number): string;
/**
 * Hash a string securely.
 */
export declare function hashString(input: string, algorithm?: string): string;
/**
 * Compare two strings in constant time.
 */
export declare function constantTimeCompare(a: string, b: string): boolean;
export interface ResourceLimits {
    maxMemoryMB: number;
    maxCPUPercent: number;
    maxFileSize: number;
    maxOpenFiles: number;
    maxExecutionTime: number;
}
/**
 * Create a resource limiter.
 */
export declare function createResourceLimiter(limits?: Partial<ResourceLimits>): {
    check(): {
        ok: boolean;
        violations: string[];
    };
    enforce<T>(fn: () => Promise<T>): Promise<T>;
};
export declare const Security: {
    validateString: typeof validateString;
    validateNumber: typeof validateNumber;
    validateBoolean: typeof validateBoolean;
    validateArray: typeof validateArray;
    validateEnum: typeof validateEnum;
    validatePath: typeof validatePath;
    validateCommand: typeof validateCommand;
    safePath: typeof safePath;
    safePathAsync: typeof safePathAsync;
    safeJsonParse: typeof safeJsonParse;
    safeJsonStringify: typeof safeJsonStringify;
    escapeShellArg: typeof escapeShellArg;
    sanitizeError: typeof sanitizeError;
    sanitizeErrorMessage: typeof sanitizeErrorMessage;
    createRateLimiter: typeof createRateLimiter;
    generateSecureId: typeof generateSecureId;
    generateSecureToken: typeof generateSecureToken;
    hashString: typeof hashString;
    constantTimeCompare: typeof constantTimeCompare;
    createResourceLimiter: typeof createResourceLimiter;
};
//# sourceMappingURL=index.d.ts.map