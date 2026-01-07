// Utility functions for the frontend

import { ClusterListItem, ChunkHit } from "./api";
import { TreeNode } from "./mockData";

/**
 * Build a hierarchical tree structure from flat cluster list
 * Groups clusters by their name prefix and creates a nested structure
 */
export function buildClusterTree(clusters: ClusterListItem[]): TreeNode {
  const root: TreeNode = {
    id: "root",
    name: "Knowledge Base",
    type: "cluster",
    children: [],
  };

  // Sort clusters by size (largest first)
  const sortedClusters = [...clusters].sort((a, b) => b.size - a.size);

  // Add each cluster as a top-level folder
  root.children = sortedClusters.map((cluster) => ({
    id: `cluster-${cluster.id}`,
    name: cluster.name || `Cluster ${cluster.id}`,
    type: "cluster" as const,
    path: `/clusters/${cluster.id}`,
    children: [], // Will be populated when cluster is expanded
  }));

  return root;
}

/**
 * Convert chunk hits to tree nodes
 */
export function chunksToTreeNodes(chunks: ChunkHit[]): TreeNode[] {
  return chunks.map((chunk) => ({
    id: `chunk-${chunk.chunk_id}`,
    name: chunk.heading || chunk.file_path.split('/').pop() || 'Untitled',
    type: "note" as const,
    path: chunk.file_path,
    children: undefined,
  }));
}

/**
 * Format file path into breadcrumbs
 */
export function pathToBreadcrumbs(filePath: string): string[] {
  return filePath
    .split('/')
    .filter(Boolean)
    .map((part) =>
      part
        .split(/[-_]/)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    );
}
