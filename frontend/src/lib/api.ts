// API client for the backend Knowledge Base API

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface ChunkHit {
  chunk_id: number;
  file_path: string;
  heading: string;
  preview: string;
}

export interface ChunkDetail {
  id: number;
  file_path: string;
  heading: string;
  ordinal: number;
  content: string;
}

export interface RelatedItem {
  chunk_id: number;
  file_path: string;
  heading: string;
  preview: string;
  score: number | null;
}

export interface ClusterSuggestion {
  cluster_id: number;
  name: string;
  score: number;
}

export interface ClusterListItem {
  id: number;
  name: string;
  size: number;
  method: string;
  k: number;
}

export interface ClusterMeta {
  id: number;
  name: string;
  summary: string;
  size: number;
}

export interface ClusterDetail {
  meta: ClusterMeta;
  members: ChunkHit[];
}

/**
 * Search for chunks using FTS (Full-Text Search)
 */
export async function searchChunks(query: string, limit: number = 10): Promise<ChunkHit[]> {
  const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get a chunk by ID
 */
export async function getChunk(chunkId: number): Promise<ChunkDetail> {
  const response = await fetch(`${API_BASE}/chunks/${chunkId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch chunk: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get related items for a chunk
 * @param chunkId - The chunk ID
 * @param mode - "cluster" for cluster-based, "embed" for embedding-based
 * @param k - Number of related items to return
 */
export async function getRelatedChunks(
  chunkId: number,
  mode: 'cluster' | 'embed' = 'cluster',
  k: number = 10
): Promise<RelatedItem[]> {
  const response = await fetch(
    `${API_BASE}/chunks/${chunkId}/related?mode=${mode}&k=${k}`
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch related chunks: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get cluster suggestions based on search query
 */
export async function suggestClusters(
  query: string,
  limit: number = 5,
  ftsK: number = 50
): Promise<ClusterSuggestion[]> {
  const response = await fetch(
    `${API_BASE}/clusters/suggest?q=${encodeURIComponent(query)}&limit=${limit}&fts_k=${ftsK}`
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch cluster suggestions: ${response.statusText}`);
  }
  return response.json();
}

/**
 * List all clusters
 */
export async function listClusters(limit: number = 100): Promise<ClusterListItem[]> {
  const response = await fetch(`${API_BASE}/clusters?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch clusters: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get cluster details including members
 */
export async function getClusterDetail(clusterId: number, limit: number = 50): Promise<ClusterDetail> {
  const response = await fetch(`${API_BASE}/clusters/${clusterId}?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch cluster detail: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<{ ok: boolean }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}
