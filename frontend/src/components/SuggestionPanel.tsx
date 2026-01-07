"use client";

import { useEffect, useState } from "react";
import { Sparkles, TrendingUp } from "lucide-react";
import { getRelatedChunks, RelatedItem } from "@/lib/api";

interface SuggestionPanelProps {
  chunkId: number;
  onNoteClick?: (chunkId: number) => void;
}

export function SuggestionPanel({ chunkId, onNoteClick }: SuggestionPanelProps) {
  const [relatedNotes, setRelatedNotes] = useState<RelatedItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [mode, setMode] = useState<'cluster' | 'embed'>('embed');

  useEffect(() => {
    async function loadRelatedItems() {
      try {
        setIsLoading(true);
        const items = await getRelatedChunks(chunkId, mode, 10);
        setRelatedNotes(items);
      } catch (error) {
        console.error("Failed to load related items:", error);
        setRelatedNotes([]);
      } finally {
        setIsLoading(false);
      }
    }
    loadRelatedItems();
  }, [chunkId, mode]);

  const getMatchColor = (score: number | null) => {
    if (!score) return "text-purple-400 bg-purple-950/50 border-purple-800";
    if (score >= 0.9) return "text-green-400 bg-green-950/50 border-green-800";
    if (score >= 0.8) return "text-blue-400 bg-blue-950/50 border-blue-800";
    return "text-purple-400 bg-purple-950/50 border-purple-800";
  };

  const getMatchLabel = (score: number | null) => {
    if (!score) return "Related";
    if (score >= 0.9) return "Excellent";
    if (score >= 0.8) return "Good";
    return "Related";
  };

  return (
    <div className="h-full bg-zinc-950 border-l border-zinc-800 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-semibold text-zinc-100">AI Suggestions</h2>
        </div>
        <p className="text-xs text-zinc-500 mt-1">Based on current context</p>
      </div>

      {/* Related Notes List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <div className="text-center py-8 text-zinc-500 text-sm">Loading suggestions...</div>
        ) : relatedNotes.length > 0 ? (
          relatedNotes.map((note) => (
            <div
              key={note.chunk_id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 hover:border-zinc-700 hover:bg-zinc-900/80 transition-all cursor-pointer group"
              onClick={() => onNoteClick?.(note.chunk_id)}
            >
              {/* Title and Match Badge */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="text-sm font-medium text-zinc-200 line-clamp-2 group-hover:text-blue-400 transition-colors flex-1">
                  {note.heading || note.file_path.split('/').pop() || 'Untitled'}
                </h3>
                {note.score !== null && (
                  <div
                    className={`
                      flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium whitespace-nowrap
                      ${getMatchColor(note.score)}
                    `}
                  >
                    <TrendingUp className="w-3 h-3" />
                    {Math.round(note.score * 100)}%
                  </div>
                )}
              </div>

              {/* Preview */}
              <p className="text-xs text-zinc-500 line-clamp-2 mb-2">{note.preview}</p>

              {/* Match Label */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-600">{note.file_path}</span>
                <span className={`text-xs font-medium ${getMatchColor(note.score).split(" ")[0]}`}>
                  {getMatchLabel(note.score)} Match
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-zinc-500 text-sm">No suggestions available</div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-zinc-800">
        <button
          className="w-full px-3 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg text-xs font-medium text-zinc-300 transition-colors"
          onClick={() => setMode(mode === 'cluster' ? 'embed' : 'cluster')}
        >
          Switch to {mode === 'cluster' ? 'Embedding' : 'Cluster'} Mode
        </button>
      </div>
    </div>
  );
}
