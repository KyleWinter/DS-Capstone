"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, FolderClosed, FolderOpen, FileText } from "lucide-react";
import { TreeNode } from "@/lib/mockData";

interface FileTreeProps {
  node: TreeNode;
  level?: number;
  activeNoteId?: string;
  onNoteSelect?: (node: TreeNode) => void;
  onClusterExpand?: (node: TreeNode) => Promise<void>;
}

export function FileTree({ node, level = 0, activeNoteId, onNoteSelect, onClusterExpand }: FileTreeProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2); // Auto-expand first 2 levels
  const [isLoading, setIsLoading] = useState(false);

  const hasChildren = node.children && node.children.length > 0;
  const isActive = activeNoteId === node.id;
  const isCluster = node.type === "cluster";

  const handleToggle = async () => {
    if (isCluster && !isExpanded && !hasChildren && onClusterExpand) {
      // Lazy load cluster members
      setIsLoading(true);
      try {
        await onClusterExpand(node);
      } catch (error) {
        console.error("Failed to load cluster members:", error);
      } finally {
        setIsLoading(false);
      }
    }

    if (hasChildren || isCluster) {
      setIsExpanded(!isExpanded);
    }

    if (node.type === "note" && onNoteSelect) {
      onNoteSelect(node);
    }
  };

  return (
    <div className="select-none">
      <div
        className={`
          flex items-center gap-2 px-3 py-1.5 cursor-pointer rounded-md
          hover:bg-zinc-800/50 transition-colors group
          ${isActive ? "bg-blue-600/20 text-blue-400" : "text-zinc-300"}
        `}
        style={{ paddingLeft: `${level * 12 + 12}px` }}
        onClick={handleToggle}
      >
        {/* Chevron icon for expandable items */}
        {hasChildren && (
          <button className="p-0.5 hover:bg-zinc-700 rounded transition-colors">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-zinc-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-zinc-400" />
            )}
          </button>
        )}

        {/* Icon based on type */}
        {isCluster ? (
          isExpanded ? (
            <FolderOpen className="w-4 h-4 text-blue-400 flex-shrink-0" />
          ) : (
            <FolderClosed className="w-4 h-4 text-blue-400 flex-shrink-0" />
          )
        ) : (
          <FileText className="w-4 h-4 text-zinc-400 flex-shrink-0 ml-6" />
        )}

        {/* Node name */}
        <span
          className={`
            text-sm truncate flex-1
            ${isActive ? "font-medium" : ""}
          `}
        >
          {node.name}
        </span>

        {/* Badge for cluster size */}
        {isCluster && hasChildren && (
          <span className="text-xs text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">
            {node.children?.length}
          </span>
        )}
      </div>

      {/* Recursive children */}
      {hasChildren && isExpanded && (
        <div className="mt-0.5">
          {node.children?.map((child) => (
            <FileTree
              key={child.id}
              node={child}
              level={level + 1}
              activeNoteId={activeNoteId}
              onNoteSelect={onNoteSelect}
              onClusterExpand={onClusterExpand}
            />
          ))}
        </div>
      )}
      {isLoading && isExpanded && (
        <div className="px-3 py-1.5 text-xs text-zinc-500" style={{ paddingLeft: `${(level + 1) * 12 + 12}px` }}>
          Loading...
        </div>
      )}
    </div>
  );
}
