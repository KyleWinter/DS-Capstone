"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
  MiniMap,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Network, X, Maximize2, Minimize2 } from "lucide-react";
import { getRelatedNotes, RelatedNote } from "@/lib/api";

interface KnowledgeGraphProps {
  filePath: string;
  chunkId: number;
  onNodeClick?: (filePath: string) => void;
  onClose?: () => void;
}

interface GraphNodeData {
  label: string;
  filePath: string;
  isCentral: boolean;
  reason?: string;
  score?: number;
}

type GraphNode = Node<GraphNodeData>;

export function KnowledgeGraph({ filePath, chunkId, onNodeClick, onClose }: KnowledgeGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [mode, setMode] = useState<'cluster' | 'embed'>('embed');
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Extract file name from path
  const extractFileName = (path: string) => {
    return path.split('/').pop() || path;
  };

  // Load graph data
  useEffect(() => {
    async function loadGraphData() {
      // Don't load if filePath or chunkId is invalid
      if (!filePath || !chunkId || chunkId === 0) {
        setIsLoading(false);
        setNodes([]);
        setEdges([]);
        return;
      }

      try {
        setIsLoading(true);

        // Get related notes
        const response = await getRelatedNotes(chunkId, mode, 10);
        const relatedNotes = response.items;

        // Create central node
        const centralNode: GraphNode = {
          id: 'central',
          type: 'default',
          position: { x: 400, y: 300 },
          data: {
            label: extractFileName(filePath),
            filePath: filePath,
            isCentral: true,
          },
          style: {
            background: '#3b82f6',
            color: '#fff',
            border: '2px solid #2563eb',
            borderRadius: '8px',
            padding: '12px 20px',
            fontSize: '14px',
            fontWeight: '600',
            width: 'auto',
            minWidth: '150px',
          },
        };

        // Create nodes for related notes
        const relatedNodes: GraphNode[] = relatedNotes.map((note, index) => {
          const angle = (2 * Math.PI * index) / relatedNotes.length;
          const radius = 250;
          const x = 400 + radius * Math.cos(angle);
          const y = 300 + radius * Math.sin(angle);

          const isSameTopic = note.reason === 'same_topic';
          const color = isSameTopic ? '#8b5cf6' : '#ec4899';
          const borderColor = isSameTopic ? '#7c3aed' : '#db2777';

          return {
            id: `note-${index}`,
            type: 'default',
            position: { x, y },
            data: {
              label: extractFileName(note.file_path),
              filePath: note.file_path,
              isCentral: false,
              reason: note.reason,
              score: note.score,
            },
            style: {
              background: color,
              color: '#fff',
              border: `2px solid ${borderColor}`,
              borderRadius: '8px',
              padding: '10px 16px',
              fontSize: '12px',
              fontWeight: '500',
              width: 'auto',
              minWidth: '120px',
              cursor: 'pointer',
            },
          };
        });

        // Create edges
        const newEdges: Edge[] = relatedNotes.map((note, index) => {
          const isSameTopic = note.reason === 'same_topic';
          const edgeColor = isSameTopic ? '#8b5cf6' : '#ec4899';

          return {
            id: `edge-${index}`,
            source: 'central',
            target: `note-${index}`,
            type: 'smoothstep',
            animated: true,
            style: {
              stroke: edgeColor,
              strokeWidth: 2,
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: edgeColor,
            },
            label: mode === 'embed' ? `${Math.round(note.score * 100)}%` : '',
            labelStyle: {
              fill: '#a1a1aa',
              fontSize: 10,
              fontWeight: 500,
            },
            labelBgStyle: {
              fill: '#18181b',
              fillOpacity: 0.8,
            },
          };
        });

        setNodes([centralNode, ...relatedNodes]);
        setEdges(newEdges);
      } catch (error) {
        console.error("Failed to load graph data:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadGraphData();
  }, [filePath, chunkId, mode, setNodes, setEdges]);

  // Handle node click
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const graphNode = node as GraphNode;
      if (!graphNode.data.isCentral && onNodeClick) {
        onNodeClick(graphNode.data.filePath);
      }
    },
    [onNodeClick]
  );

  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50' : 'relative w-full h-full'} bg-zinc-950 flex flex-col`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-semibold text-zinc-100">Knowledge Graph</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 hover:bg-zinc-800 rounded transition-colors"
            title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4 text-zinc-400" />
            ) : (
              <Maximize2 className="w-4 h-4 text-zinc-400" />
            )}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-zinc-800 rounded transition-colors"
            >
              <X className="w-4 h-4 text-zinc-400" />
            </button>
          )}
        </div>
      </div>

      {/* Graph Container */}
      <div className="flex-1 relative">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-sm text-zinc-500">Loading knowledge graph...</p>
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            fitView
            attributionPosition="bottom-right"
            className="bg-zinc-950"
            minZoom={0.1}
            maxZoom={2}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={16}
              size={1}
              color="#27272a"
            />
            <Controls
              className="bg-zinc-900 border-zinc-800"
            />
            <MiniMap
              className="bg-zinc-900 border border-zinc-800"
              nodeColor={(node) => {
                const graphNode = node as GraphNode;
                return graphNode.data.isCentral ? '#3b82f6' : '#8b5cf6';
              }}
              maskColor="rgba(0, 0, 0, 0.5)"
            />

            {/* Legend Panel */}
            <Panel position="top-left" className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 space-y-2">
              <div className="text-xs font-semibold text-zinc-100 mb-2">Legend</div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-400"></div>
                <span className="text-xs text-zinc-400">Current Note</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-purple-400"></div>
                <span className="text-xs text-zinc-400">Same Topic</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-pink-400"></div>
                <span className="text-xs text-zinc-400">Similar Content</span>
              </div>
            </Panel>

            {/* Mode Toggle Panel */}
            <Panel position="top-right" className="bg-zinc-900 border border-zinc-800 rounded-lg p-2">
              <button
                onClick={() => setMode(mode === 'cluster' ? 'embed' : 'cluster')}
                className="px-3 py-1.5 text-xs font-medium text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 rounded transition-colors"
              >
                {mode === 'cluster' ? 'Topic-based' : 'Similarity-based'}
              </button>
            </Panel>
          </ReactFlow>
        )}
      </div>

      {/* Footer */}
      {!isLoading && (
        <div className="px-4 py-2 border-t border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
          <p className="text-xs text-zinc-500 text-center">
            Click on a node to navigate • Drag to pan • Scroll to zoom
          </p>
        </div>
      )}
    </div>
  );
}
