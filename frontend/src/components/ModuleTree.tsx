"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, FolderClosed, FolderOpen, FileText, Layers } from "lucide-react";
import { ModuleListItem, NoteItem, getModuleNotes } from "@/lib/api";

interface ModuleTreeProps {
  modules: ModuleListItem[];
  activePath?: string;
  onFileSelect?: (filePath: string) => void;
}

export function ModuleTree({ modules, activePath, onFileSelect }: ModuleTreeProps) {
  const [expandedModules, setExpandedModules] = useState<Set<number>>(new Set());
  const [moduleNotes, setModuleNotes] = useState<Map<number, NoteItem[]>>(new Map());
  const [loadingModules, setLoadingModules] = useState<Set<number>>(new Set());

  const handleModuleToggle = async (module: ModuleListItem) => {
    const isExpanded = expandedModules.has(module.id);

    if (!isExpanded) {
      // Expand and load notes if not already loaded
      if (!moduleNotes.has(module.id)) {
        setLoadingModules((prev) => new Set(prev).add(module.id));
        try {
          const notes = await getModuleNotes(module.id);
          setModuleNotes((prev) => new Map(prev).set(module.id, notes));
        } catch (error) {
          console.error(`Failed to load notes for module ${module.id}:`, error);
        } finally {
          setLoadingModules((prev) => {
            const newSet = new Set(prev);
            newSet.delete(module.id);
            return newSet;
          });
        }
      }
      setExpandedModules((prev) => new Set(prev).add(module.id));
    } else {
      // Collapse
      setExpandedModules((prev) => {
        const newSet = new Set(prev);
        newSet.delete(module.id);
        return newSet;
      });
    }
  };

  const handleFileClick = (filePath: string) => {
    if (onFileSelect) {
      onFileSelect(filePath);
    }
  };

  return (
    <div className="select-none">
      {modules.map((module) => {
        const isExpanded = expandedModules.has(module.id);
        const isLoading = loadingModules.has(module.id);
        const notes = moduleNotes.get(module.id) || [];

        return (
          <div key={module.id} className="mb-0.5">
            {/* Module Header */}
            <div
              className="flex items-center gap-2 px-3 py-2 cursor-pointer rounded-md hover:bg-zinc-800/50 transition-colors group"
              onClick={() => handleModuleToggle(module)}
            >
              {/* Chevron */}
              <button className="p-0.5 hover:bg-zinc-700 rounded transition-colors">
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-zinc-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-zinc-400" />
                )}
              </button>

              {/* Module Icon */}
              {isExpanded ? (
                <FolderOpen className="w-4 h-4 text-purple-400 flex-shrink-0" />
              ) : (
                <FolderClosed className="w-4 h-4 text-purple-400 flex-shrink-0" />
              )}

              {/* Module Name */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-zinc-100 truncate">
                    {module.name}
                  </span>
                  <span className="text-xs text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded flex-shrink-0">
                    {module.file_count}
                  </span>
                </div>
                {module.description && (
                  <p className="text-xs text-zinc-500 truncate mt-0.5">
                    {module.description}
                  </p>
                )}
              </div>
            </div>

            {/* Module Notes */}
            {isExpanded && (
              <div className="ml-6 mt-1">
                {isLoading ? (
                  <div className="px-3 py-2 text-xs text-zinc-500">Loading notes...</div>
                ) : notes.length > 0 ? (
                  notes.map((note, index) => {
                    const isActive = activePath === note.file_path;
                    return (
                      <div
                        key={`${note.file_path}-${index}`}
                        className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer rounded-md hover:bg-zinc-800/50 transition-colors ${
                          isActive ? "bg-blue-600/20 text-blue-400" : "text-zinc-300"
                        }`}
                        onClick={() => handleFileClick(note.file_path)}
                      >
                        <FileText className="w-4 h-4 text-zinc-400 flex-shrink-0 ml-6" />
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm truncate ${isActive ? "font-medium" : ""}`}>
                            {note.title}
                          </div>
                          {note.preview && (
                            <div className="text-xs text-zinc-500 truncate mt-0.5">
                              {note.preview}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="px-3 py-2 text-xs text-zinc-500">No notes in this module</div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
