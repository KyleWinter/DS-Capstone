"use client";

import { useEffect, useState } from "react";
import { FileText, ArrowRight, Sparkles } from "lucide-react";
import { getRelatedNotes, RelatedNote } from "@/lib/api";

interface RelatedNotesProps {
  chunkId: number;
  onNoteClick?: (filePath: string) => void;
}

export function RelatedNotes({ chunkId, onNoteClick }: RelatedNotesProps) {
  const [relatedNotes, setRelatedNotes] = useState<RelatedNote[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [mode, setMode] = useState<'cluster' | 'embed'>('embed');

  useEffect(() => {
    async function loadRelatedNotes() {
      // Don't load if chunkId is invalid
      if (!chunkId || chunkId === 0) {
        setIsLoading(false);
        setRelatedNotes([]);
        return;
      }

      try {
        setIsLoading(true);
        const response = await getRelatedNotes(chunkId, mode, 5);
        setRelatedNotes(response.items);
      } catch (error) {
        console.error("Failed to load related notes:", error);
        setRelatedNotes([]);
      } finally {
        setIsLoading(false);
      }
    }
    loadRelatedNotes();
  }, [chunkId, mode]);

  const getReasonLabel = (reason: string) => {
    if (reason === 'same_topic') return 'Same Topic';
    if (reason === 'semantic_similarity') return 'Similar Content';
    return 'Related';
  };

  const getReasonColor = (reason: string) => {
    if (reason === 'same_topic') return 'text-blue-400 bg-blue-950/50 border-blue-800';
    if (reason === 'semantic_similarity') return 'text-purple-400 bg-purple-950/50 border-purple-800';
    return 'text-zinc-400 bg-zinc-900 border-zinc-800';
  };

  const extractFileName = (filePath: string) => {
    return filePath.split('/').pop() || filePath;
  };

  if (isLoading) {
    return (
      <div className="mt-16 mb-8 border-t border-zinc-800 pt-8">
        <div className="flex items-center gap-2 mb-6">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h2 className="text-xl font-semibold text-zinc-100">Related Notes</h2>
        </div>
        <div className="text-center py-8 text-zinc-500">Loading related notes...</div>
      </div>
    );
  }

  if (relatedNotes.length === 0) {
    return null;
  }

  return (
    <div className="mt-16 mb-8 border-t border-zinc-800 pt-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h2 className="text-xl font-semibold text-zinc-100">Related Notes</h2>
          <span className="text-sm text-zinc-500">({relatedNotes.length})</span>
        </div>

        {/* Mode toggle */}
        <button
          onClick={() => setMode(mode === 'cluster' ? 'embed' : 'cluster')}
          className="px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-300 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg transition-colors"
        >
          {mode === 'cluster' ? 'Topic-based' : 'Similarity-based'}
        </button>
      </div>

      {/* Notes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {relatedNotes.map((note, index) => (
          <div
            key={`${note.file_path}-${index}`}
            onClick={() => {
              console.log('Related note clicked, filePath:', note.file_path);
              onNoteClick?.(note.file_path);
            }}
            className="group bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 hover:bg-zinc-900/80 transition-all cursor-pointer"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-start gap-2 flex-1 min-w-0">
                <FileText className="w-4 h-4 text-zinc-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-zinc-200 group-hover:text-blue-400 transition-colors line-clamp-2">
                    {extractFileName(note.file_path)}
                  </h3>
                  <p className="text-xs text-zinc-600 mt-0.5 truncate">
                    {note.file_path}
                  </p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-600 group-hover:text-blue-400 transition-colors flex-shrink-0 mt-0.5" />
            </div>

            {/* Stats */}
            <div className="flex items-center gap-3 text-xs">
              <div className={`px-2 py-1 rounded border ${getReasonColor(note.reason)}`}>
                {getReasonLabel(note.reason)}
              </div>

              {mode === 'embed' && (
                <div className="text-zinc-500">
                  {Math.round(note.score * 100)}% match
                </div>
              )}

              <div className="text-zinc-600">
                {note.matched_chunks} {note.matched_chunks === 1 ? 'section' : 'sections'}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer hint */}
      <p className="text-xs text-zinc-600 mt-4 text-center">
        Click on a note to view its full content
      </p>
    </div>
  );
}
