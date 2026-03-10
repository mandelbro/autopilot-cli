/**
 * GNN Bridge for Code Graph Analysis
 *
 * Provides graph neural network operations for code structure analysis
 * using ruvector-gnn-wasm for high-performance graph algorithms.
 *
 * Features:
 * - Code graph construction
 * - Node embedding computation
 * - Impact prediction using graph propagation
 * - Community detection for module discovery
 * - Pattern matching in code graphs
 *
 * Based on ADR-035: Advanced Code Intelligence Plugin
 *
 * @module v3/plugins/code-intelligence/bridges/gnn-bridge
 */
/**
 * GNN Bridge Implementation
 */
export class GNNBridge {
    // WASM module for future performance optimization (currently uses JS fallback)
    wasmModule = null;
    initialized = false;
    embeddingDim;
    constructor(embeddingDim = 128) {
        this.embeddingDim = embeddingDim;
    }
    /**
     * Initialize the WASM module
     */
    async initialize() {
        if (this.initialized)
            return;
        try {
            // Dynamic import of WASM module
            this.wasmModule = await this.loadWasmModule();
            this.initialized = true;
        }
        catch {
            // Fallback to pure JS implementation
            console.warn('WASM GNN module not available, using JS fallback');
            this.wasmModule = null;
            this.initialized = true;
        }
    }
    /**
     * Check if initialized
     */
    isInitialized() {
        return this.initialized;
    }
    /**
     * Build code graph from files
     */
    async buildCodeGraph(files, _includeCallGraph) {
        if (!this.initialized) {
            await this.initialize();
        }
        const nodes = [];
        const edges = [];
        const nodeMap = new Map();
        // Create nodes for each file
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (!file)
                continue;
            nodeMap.set(file, i);
            nodes.push({
                id: file,
                label: file.split('/').pop() ?? file,
                type: 'file',
                language: this.detectLanguage(file),
            });
        }
        // Build edges from imports (simplified - in production would parse AST)
        for (const file of files) {
            const imports = await this.extractImports(file, files);
            for (const imp of imports) {
                if (nodeMap.has(imp)) {
                    edges.push({
                        from: file,
                        to: imp,
                        type: 'import',
                        weight: 1,
                    });
                }
            }
        }
        // Calculate metadata
        const avgDegree = edges.length > 0 ? (edges.length * 2) / nodes.length : 0;
        const maxDepth = this.calculateMaxDepth(nodes, edges);
        return {
            nodes,
            edges,
            metadata: {
                totalNodes: nodes.length,
                totalEdges: edges.length,
                avgDegree,
                maxDepth,
            },
        };
    }
    /**
     * Compute node embeddings using GNN
     */
    async computeNodeEmbeddings(graph, embeddingDim) {
        if (!this.initialized) {
            await this.initialize();
        }
        const embeddings = new Map();
        const nodeCount = graph.nodes.length;
        if (nodeCount === 0) {
            return embeddings;
        }
        // Create node lookup
        const nodeMap = new Map();
        graph.nodes.forEach((node, index) => {
            nodeMap.set(node.id, index);
        });
        // Build adjacency list for WASM
        const edgeArray = new Uint32Array(graph.edges.length * 2);
        for (let i = 0; i < graph.edges.length; i++) {
            const edge = graph.edges[i];
            if (!edge)
                continue;
            const fromIdx = nodeMap.get(edge.from) ?? 0;
            const toIdx = nodeMap.get(edge.to) ?? 0;
            edgeArray[i * 2] = fromIdx;
            edgeArray[i * 2 + 1] = toIdx;
        }
        // Initialize features (simple degree-based features)
        const featureDim = 16;
        const features = new Float32Array(nodeCount * featureDim);
        for (let i = 0; i < nodeCount; i++) {
            const node = graph.nodes[i];
            if (!node)
                continue;
            // In-degree
            features[i * featureDim] = graph.edges.filter(e => e.to === node.id).length;
            // Out-degree
            features[i * featureDim + 1] = graph.edges.filter(e => e.from === node.id).length;
            // Node type encoding
            features[i * featureDim + 2] = this.encodeNodeType(node.type);
            // Language encoding
            features[i * featureDim + 3] = node.language ? this.encodeLanguage(node.language) : 0;
        }
        // Compute embeddings (using JS fallback)
        const embeddingMatrix = this.computeEmbeddingsJS(graph, features, featureDim, embeddingDim);
        // Extract embeddings per node
        for (let i = 0; i < nodeCount; i++) {
            const node = graph.nodes[i];
            if (!node)
                continue;
            const nodeEmbedding = embeddingMatrix.slice(i * embeddingDim, (i + 1) * embeddingDim);
            embeddings.set(node.id, nodeEmbedding);
        }
        return embeddings;
    }
    /**
     * Predict impact of changes using GNN
     */
    async predictImpact(graph, changedNodes, depth) {
        if (!this.initialized) {
            await this.initialize();
        }
        const impact = new Map();
        const nodeCount = graph.nodes.length;
        if (nodeCount === 0) {
            return impact;
        }
        // Create node lookup
        const nodeMap = new Map();
        graph.nodes.forEach((node, index) => {
            nodeMap.set(node.id, index);
        });
        // Build adjacency list (reverse direction for impact propagation)
        const adj = Array.from({ length: nodeCount }, () => []);
        for (const edge of graph.edges) {
            const fromIdx = nodeMap.get(edge.from);
            const toIdx = nodeMap.get(edge.to);
            if (fromIdx !== undefined && toIdx !== undefined) {
                // Reverse: impact flows from dependency to dependent
                adj[toIdx]?.push(fromIdx);
            }
        }
        // Initialize impact scores
        const scores = new Float32Array(nodeCount);
        for (const nodeId of changedNodes) {
            const idx = nodeMap.get(nodeId);
            if (idx !== undefined) {
                scores[idx] = 1.0;
            }
        }
        // Propagate impact using BFS with decay
        const visited = new Set();
        const queue = [];
        // Initialize queue with changed nodes
        for (const nodeId of changedNodes) {
            const idx = nodeMap.get(nodeId);
            if (idx !== undefined) {
                queue.push({ node: idx, depth: 0, score: 1.0 });
                visited.add(idx);
            }
        }
        // BFS propagation
        while (queue.length > 0) {
            const current = queue.shift();
            if (!current || current.depth >= depth)
                continue;
            for (const neighbor of adj[current.node] ?? []) {
                const newScore = current.score * 0.7; // Decay factor
                const neighborScore = scores[neighbor];
                if (neighborScore !== undefined && newScore > neighborScore) {
                    scores[neighbor] = newScore;
                }
                if (!visited.has(neighbor)) {
                    visited.add(neighbor);
                    queue.push({
                        node: neighbor,
                        depth: current.depth + 1,
                        score: newScore,
                    });
                }
            }
        }
        // Convert to map
        for (let i = 0; i < nodeCount; i++) {
            const node = graph.nodes[i];
            const score = scores[i];
            if (node && score !== undefined && score > 0) {
                impact.set(node.id, score);
            }
        }
        return impact;
    }
    /**
     * Detect communities in code graph
     */
    async detectCommunities(graph) {
        if (!this.initialized) {
            await this.initialize();
        }
        const communities = new Map();
        const nodeCount = graph.nodes.length;
        if (nodeCount === 0) {
            return communities;
        }
        // Create node lookup
        const nodeMap = new Map();
        graph.nodes.forEach((node, index) => {
            nodeMap.set(node.id, index);
        });
        // Build adjacency list (undirected)
        const adj = Array.from({ length: nodeCount }, () => new Set());
        for (const edge of graph.edges) {
            const fromIdx = nodeMap.get(edge.from);
            const toIdx = nodeMap.get(edge.to);
            if (fromIdx !== undefined && toIdx !== undefined) {
                adj[fromIdx]?.add(toIdx);
                adj[toIdx]?.add(fromIdx);
            }
        }
        // Simple community detection using connected components
        // In production, would use Louvain or similar
        const community = new Array(nodeCount).fill(-1);
        let communityId = 0;
        for (let i = 0; i < nodeCount; i++) {
            if (community[i] !== -1)
                continue;
            // BFS to find connected component
            const queue = [i];
            community[i] = communityId;
            while (queue.length > 0) {
                const current = queue.shift();
                for (const neighbor of adj[current] ?? []) {
                    if (community[neighbor] === -1) {
                        community[neighbor] = communityId;
                        queue.push(neighbor);
                    }
                }
            }
            communityId++;
        }
        // Convert to map
        for (let i = 0; i < nodeCount; i++) {
            const node = graph.nodes[i];
            const comm = community[i];
            if (node && comm !== undefined) {
                communities.set(node.id, comm);
            }
        }
        return communities;
    }
    /**
     * Find similar code patterns
     */
    async findSimilarPatterns(graph, patternGraph, threshold) {
        if (!this.initialized) {
            await this.initialize();
        }
        const matches = [];
        // Compute embeddings for both graphs
        const graphEmbeddings = await this.computeNodeEmbeddings(graph, this.embeddingDim);
        const patternEmbeddings = await this.computeNodeEmbeddings(patternGraph, this.embeddingDim);
        // Average pattern embedding
        const patternAvg = new Float32Array(this.embeddingDim);
        let patternCount = 0;
        for (const [, embedding] of patternEmbeddings) {
            for (let i = 0; i < this.embeddingDim; i++) {
                patternAvg[i] = (patternAvg[i] ?? 0) + (embedding[i] ?? 0);
            }
            patternCount++;
        }
        if (patternCount > 0) {
            for (let i = 0; i < this.embeddingDim; i++) {
                patternAvg[i] = (patternAvg[i] ?? 0) / patternCount;
            }
        }
        // Find similar nodes in main graph
        for (const [nodeId, embedding] of graphEmbeddings) {
            const similarity = this.cosineSimilarity(embedding, patternAvg);
            if (similarity >= threshold) {
                matches.push({ matchId: nodeId, score: similarity });
            }
        }
        // Sort by score descending
        matches.sort((a, b) => b.score - a.score);
        return matches;
    }
    // ============================================================================
    // Private Helper Methods
    // ============================================================================
    /**
     * Load WASM module dynamically
     */
    async loadWasmModule() {
        throw new Error('WASM module loading not implemented');
    }
    /**
     * Detect language from file extension
     */
    detectLanguage(filePath) {
        const ext = filePath.split('.').pop()?.toLowerCase();
        const langMap = {
            ts: 'typescript',
            tsx: 'typescript',
            js: 'javascript',
            jsx: 'javascript',
            py: 'python',
            java: 'java',
            go: 'go',
            rs: 'rust',
            cpp: 'cpp',
            c: 'cpp',
            cs: 'csharp',
            rb: 'ruby',
            php: 'php',
            swift: 'swift',
            kt: 'kotlin',
            scala: 'scala',
        };
        return ext ? langMap[ext] : undefined;
    }
    /**
     * Extract imports from file (simplified)
     */
    async extractImports(_file, _allFiles) {
        // In production, would parse AST
        // For now, return empty array
        return [];
    }
    /**
     * Calculate max depth of dependency graph
     */
    calculateMaxDepth(nodes, edges) {
        if (nodes.length === 0)
            return 0;
        // Build adjacency list
        const adj = new Map();
        for (const node of nodes) {
            adj.set(node.id, []);
        }
        for (const edge of edges) {
            adj.get(edge.from)?.push(edge.to);
        }
        // Find nodes with no incoming edges (roots)
        const hasIncoming = new Set();
        for (const edge of edges) {
            hasIncoming.add(edge.to);
        }
        const roots = nodes.filter(n => !hasIncoming.has(n.id)).map(n => n.id);
        if (roots.length === 0) {
            // Cycle - use first node
            roots.push(nodes[0].id);
        }
        // BFS to find max depth
        let maxDepth = 0;
        const visited = new Set();
        const queue = [];
        for (const root of roots) {
            queue.push({ node: root, depth: 0 });
            visited.add(root);
        }
        while (queue.length > 0) {
            const current = queue.shift();
            maxDepth = Math.max(maxDepth, current.depth);
            for (const neighbor of adj.get(current.node) ?? []) {
                if (!visited.has(neighbor)) {
                    visited.add(neighbor);
                    queue.push({ node: neighbor, depth: current.depth + 1 });
                }
            }
        }
        return maxDepth;
    }
    /**
     * Encode node type as number
     */
    encodeNodeType(type) {
        const types = {
            file: 0.1,
            module: 0.2,
            package: 0.3,
            class: 0.4,
            function: 0.5,
        };
        return types[type];
    }
    /**
     * Encode language as number
     */
    encodeLanguage(language) {
        const languages = {
            typescript: 0.1,
            javascript: 0.15,
            python: 0.2,
            java: 0.25,
            go: 0.3,
            rust: 0.35,
            cpp: 0.4,
            csharp: 0.45,
            ruby: 0.5,
            php: 0.55,
        };
        return languages[language] ?? 0;
    }
    /**
     * Compute embeddings using JS (fallback)
     */
    computeEmbeddingsJS(graph, features, featureDim, outputDim) {
        const nodeCount = graph.nodes.length;
        const embeddings = new Float32Array(nodeCount * outputDim);
        // Create adjacency matrix
        const nodeMap = new Map();
        graph.nodes.forEach((node, index) => {
            nodeMap.set(node.id, index);
        });
        // Simple message passing (1 layer)
        for (let i = 0; i < nodeCount; i++) {
            const node = graph.nodes[i];
            if (!node)
                continue;
            // Aggregate neighbor features
            const neighbors = graph.edges
                .filter(e => e.to === node.id)
                .map(e => nodeMap.get(e.from))
                .filter((idx) => idx !== undefined);
            // Initialize with own features (projected to output dim)
            for (let j = 0; j < outputDim; j++) {
                const featureIdx = j % featureDim;
                embeddings[i * outputDim + j] = features[i * featureDim + featureIdx] ?? 0;
            }
            // Add neighbor contributions
            if (neighbors.length > 0) {
                for (const neighborIdx of neighbors) {
                    for (let j = 0; j < outputDim; j++) {
                        const featureIdx = j % featureDim;
                        const contribution = (features[neighborIdx * featureDim + featureIdx] ?? 0) / neighbors.length;
                        const embIdx = i * outputDim + j;
                        embeddings[embIdx] = (embeddings[embIdx] ?? 0) + contribution * 0.5;
                    }
                }
            }
        }
        // Normalize embeddings
        for (let i = 0; i < nodeCount; i++) {
            let norm = 0;
            for (let j = 0; j < outputDim; j++) {
                const val = embeddings[i * outputDim + j] ?? 0;
                norm += val * val;
            }
            norm = Math.sqrt(norm);
            if (norm > 0) {
                for (let j = 0; j < outputDim; j++) {
                    embeddings[i * outputDim + j] = (embeddings[i * outputDim + j] ?? 0) / norm;
                }
            }
        }
        return embeddings;
    }
    /**
     * Compute cosine similarity
     */
    cosineSimilarity(a, b) {
        let dot = 0;
        let normA = 0;
        let normB = 0;
        for (let i = 0; i < a.length; i++) {
            const aVal = a[i] ?? 0;
            const bVal = b[i] ?? 0;
            dot += aVal * bVal;
            normA += aVal * aVal;
            normB += bVal * bVal;
        }
        const denominator = Math.sqrt(normA) * Math.sqrt(normB);
        return denominator > 0 ? dot / denominator : 0;
    }
}
/**
 * Create and export default bridge instance
 */
export function createGNNBridge(embeddingDim = 128) {
    return new GNNBridge(embeddingDim);
}
export default GNNBridge;
//# sourceMappingURL=gnn-bridge.js.map