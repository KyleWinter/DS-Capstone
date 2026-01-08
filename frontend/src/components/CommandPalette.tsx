"use client";

import { useEffect, useState, useRef } from "react";
import { Search, Clock, File, Zap, Hash } from "lucide-react";
import { searchChunks } from "@/lib/api";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onChunkSelect?: (chunkId: number) => void;
  onFileChunkSelect?: (filePath: string, chunkId: number) => void;
  onClusterSelect?: (clusterId: number) => void;
}

interface SearchResult {
  id: string;
  title: string;
  path: string;
  preview: string;
  type: "note";
  score?: number;
  lexical_score?: number;
  semantic_score?: number;
  chunkId: number;
  matchSources: ('lexical' | 'semantic')[]; // Track which searches found this result
}

const recentSearches = ["transformer", "链表", "attention mechanism"];

export function CommandPalette({ isOpen, onClose, onChunkSelect, onFileChunkSelect, onClusterSelect }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && results[selectedIndex]) {
        handleSelectResult(results[selectedIndex]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, results, selectedIndex, onClose]);

  useEffect(() => {
    if (query.trim()) {
      const timer = setTimeout(async () => {
        setIsLoading(true);
        try {
          // Call both lexical and semantic searches in parallel
          const [lexicalResponse, semanticResponse] = await Promise.all([
            searchChunks(query, { mode: 'lexical', limit: 10, fts_k: 200 }),
            searchChunks(query, { mode: 'semantic', limit: 10, fts_k: 200 }).catch(() => ({ mode: 'semantic' as const, total: null, items: [] }))
          ]);

          // Merge results by chunk_id
          const resultMap = new Map<number, SearchResult>();

          // Process lexical results
          lexicalResponse.items.forEach((chunk) => {
            const fileName = chunk.file_path.split('/').pop() || 'Untitled';
            const chunkTitle = chunk.heading || 'Untitled Section';
            resultMap.set(chunk.chunk_id, {
              id: `chunk-${chunk.chunk_id}`,
              title: `${fileName} > ${chunkTitle}`,
              path: chunk.file_path,
              preview: chunk.preview,
              type: "note" as const,
              score: chunk.score,
              lexical_score: chunk.lexical_score,
              semantic_score: chunk.semantic_score,
              chunkId: chunk.chunk_id,
              matchSources: ['lexical'],
            });
          });

          // Process semantic results and merge
          semanticResponse.items.forEach((chunk) => {
            const existing = resultMap.get(chunk.chunk_id);
            if (existing) {
              // This chunk appears in both results - mark as hybrid
              existing.matchSources.push('semantic');
              // Update semantic score if available
              if (chunk.semantic_score !== undefined) {
                existing.semantic_score = chunk.semantic_score;
              }
              // Use the higher overall score
              if (chunk.score !== undefined && (existing.score === undefined || chunk.score > existing.score)) {
                existing.score = chunk.score;
              }
            } else {
              // Only in semantic results
              const fileName = chunk.file_path.split('/').pop() || 'Untitled';
              const chunkTitle = chunk.heading || 'Untitled Section';
              resultMap.set(chunk.chunk_id, {
                id: `chunk-${chunk.chunk_id}`,
                title: `${fileName} > ${chunkTitle}`,
                path: chunk.file_path,
                preview: chunk.preview,
                type: "note" as const,
                score: chunk.score,
                lexical_score: chunk.lexical_score,
                semantic_score: chunk.semantic_score,
                chunkId: chunk.chunk_id,
                matchSources: ['semantic'],
              });
            }
          });

          // Convert map to array and sort by score
          const mergedResults = Array.from(resultMap.values()).sort((a, b) => {
            const scoreA = a.score ?? 0;
            const scoreB = b.score ?? 0;
            return scoreB - scoreA;
          });

          setResults(mergedResults);
        } catch (error) {
          console.error("Search failed:", error);
          setResults([]);
        } finally {
          setIsLoading(false);
        }
      }, 300);
      return () => clearTimeout(timer);
    } else {
      setResults([]);
    }
  }, [query]);

  const handleSelectResult = (result: SearchResult) => {
    if (result.chunkId && result.path) {
      // Load the full file and scroll to the chunk
      if (onFileChunkSelect) {
        onFileChunkSelect(result.path, result.chunkId);
      } else if (onChunkSelect) {
        // Fallback to single chunk view
        onChunkSelect(result.chunkId);
      }
    } else {
      console.log("Selected:", result);
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
          <div className="flex items-center gap-1.5">
            <Hash className="w-4 h-4 text-amber-400" />
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <span className="text-sm font-medium text-zinc-300">Dual Search</span>
          <span className="text-xs text-zinc-600">·</span>
          <span className="text-xs text-zinc-500">Keyword + Semantic</span>
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800">
          <Search className="w-5 h-5 text-zinc-500" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search your knowledge base..."
            className="flex-1 bg-transparent text-zinc-100 placeholder:text-zinc-600 outline-none text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="px-2 py-1 text-xs font-medium text-zinc-500 bg-zinc-800 rounded border border-zinc-700">
            ESC
          </kbd>
        </div>

        {/* Results or Recent Searches */}
        <div className="max-h-[400px] overflow-y-auto">
          {query.trim() ? (
            isLoading ? (
              <div className="p-8 text-center text-zinc-500 text-sm">Searching...</div>
            ) : results.length > 0 ? (
              <div className="p-2">
                {results.map((result, index) => {
                  // Determine match type based on which searches found this result
                  const hasLexical = result.matchSources.includes('lexical');
                  const hasSemantic = result.matchSources.includes('semantic');
                  const isHybrid = hasLexical && hasSemantic;

                  return (
                    <div
                      key={result.id}
                      className={`
                        flex items-start gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                        ${index === selectedIndex ? "bg-zinc-800" : "hover:bg-zinc-800/50"}
                      `}
                      onClick={() => handleSelectResult(result)}
                    >
                      <File className="w-4 h-4 text-blue-400 mt-1 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <h3 className="text-sm font-medium text-zinc-200 truncate">{result.title}</h3>
                          <div className="flex items-center gap-2">
                            {result.score !== undefined && (
                              <span className="text-xs text-blue-400 font-medium">
                                {(result.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-xs text-zinc-500 truncate">{result.path}</span>
                          <span className="text-xs text-zinc-700">•</span>
                          <div className="flex items-center gap-1.5">
                            {isHybrid ? (
                              // Show both tags for hybrid matches
                              <>
                                <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs text-amber-400 bg-amber-400/10 rounded">
                                  <Hash className="w-3 h-3" />
                                  Keyword
                                </span>
                                <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs text-purple-400 bg-purple-400/10 rounded">
                                  <Zap className="w-3 h-3" />
                                  Semantic
                                </span>
                              </>
                            ) : hasLexical ? (
                              // Only keyword match
                              <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs text-amber-400 bg-amber-400/10 rounded">
                                <Hash className="w-3 h-3" />
                                Keyword
                              </span>
                            ) : (
                              // Only semantic match
                              <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs text-purple-400 bg-purple-400/10 rounded">
                                <Zap className="w-3 h-3" />
                                Semantic
                              </span>
                            )}
                          </div>
                        </div>
                        <p className="text-xs text-zinc-600 line-clamp-2">{result.preview}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-zinc-500 text-sm">No results found</div>
            )
          ) : (
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-zinc-500" />
                <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Recent Searches</span>
              </div>
              <div className="space-y-1">
                {recentSearches.map((search, index) => (
                  <button
                    key={index}
                    className="w-full text-left px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-800 rounded-lg transition-colors"
                    onClick={() => setQuery(search)}
                  >
                    {search}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-zinc-800 bg-zinc-950">
          <div className="flex items-center justify-between text-xs text-zinc-600">
            <div className="flex items-center gap-4">
              <span>
                <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-zinc-700">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-zinc-700 ml-1">↓</kbd>
                <span className="ml-2">Navigate</span>
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-zinc-700">↵</kbd>
                <span className="ml-2">Select</span>
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-amber-400 font-medium">FTS5</span>
              <span>+</span>
              <span className="text-purple-400 font-medium">AI</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
