"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, FolderClosed, FolderOpen, FileText } from "lucide-react";
import { FileTreeNode } from "@/lib/api";

interface FileDirectoryTreeProps {
  node: FileTreeNode;
  level?: number;
  activePath?: string;
  onFileSelect?: (node: FileTreeNode) => void;
}

export function FileDirectoryTree({
  node,
  level = 0,
  activePath,
  onFileSelect
}: FileDirectoryTreeProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2); // Auto-expand first 2 levels

  const hasChildren = node.children && node.children.length > 0;
  const isActive = activePath === node.path;
  const isDirectory = node.type === "directory";
  const isFile = node.type === "file";

  const handleToggle = () => {
    if (isDirectory && hasChildren) {
      setIsExpanded(!isExpanded);
    }

    if (isFile && onFileSelect) {
      onFileSelect(node);
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
        {isDirectory && hasChildren && (
          <button className="p-0.5 hover:bg-zinc-700 rounded transition-colors">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-zinc-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-zinc-400" />
            )}
          </button>
        )}

        {/* Icon based on type */}
        {isDirectory ? (
          isExpanded ? (
            <FolderOpen className="w-4 h-4 text-amber-400 flex-shrink-0" />
          ) : (
            <FolderClosed className="w-4 h-4 text-amber-400 flex-shrink-0" />
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

        {/* Badge for file count in directories */}
        {isDirectory && hasChildren && (
          <span className="text-xs text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">
            {node.children?.length}
          </span>
        )}
      </div>

      {/* Recursive children */}
      {hasChildren && isExpanded && (
        <div className="mt-0.5">
          {node.children?.map((child, index) => (
            <FileDirectoryTree
              key={`${child.path}-${index}`}
              node={child}
              level={level + 1}
              activePath={activePath}
              onFileSelect={onFileSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
