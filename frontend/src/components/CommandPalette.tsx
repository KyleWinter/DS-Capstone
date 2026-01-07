"use client";

import { useEffect, useState, useRef } from "react";
import { Search, Sparkles, Hash, FileText, Clock } from "lucide-react";
import { searchChunks, suggestClusters, ChunkHit, ClusterSuggestion } from "@/lib/api";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onChunkSelect?: (chunkId: number) => void;
}

type SearchMode = "semantic" | "keyword";

interface SearchResult {
  id: string;
  title: string;
  path: string;
  preview: string;
  type: "note" | "cluster";
  relevance?: number;
  chunkId?: number;
  clusterId?: number;
}

const recentSearches = ["transformer", "链表", "attention mechanism"];

export function CommandPalette({ isOpen, onClose, onChunkSelect }: CommandPaletteProps) {
  const [searchMode, setSearchMode] = useState<SearchMode>("keyword");
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
          if (searchMode === "keyword") {
            // Use FTS search for keyword mode
            const response = await searchChunks(query, 10);
            const mappedResults: SearchResult[] = response.items.map((chunk) => ({
              id: `chunk-${chunk.chunk_id}`,
              title: chunk.heading || chunk.file_path.split('/').pop() || 'Untitled',
              path: chunk.file_path,
              preview: chunk.preview,
              type: "note" as const,
              chunkId: chunk.chunk_id,
            }));
            setResults(mappedResults);
          } else {
            // Use cluster suggestions for semantic mode
            const clusters = await suggestClusters(query, 10);
            const mappedResults: SearchResult[] = clusters.map((cluster) => ({
              id: `cluster-${cluster.cluster_id}`,
              title: cluster.name || `Cluster ${cluster.cluster_id}`,
              path: `Cluster #${cluster.cluster_id}`,
              preview: `Relevance score: ${(cluster.score * 100).toFixed(1)}%`,
              type: "cluster" as const,
              relevance: cluster.score,
              clusterId: cluster.cluster_id,
            }));
            setResults(mappedResults);
          }
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
  }, [query, searchMode]);

  const handleSelectResult = (result: SearchResult) => {
    if (result.chunkId && onChunkSelect) {
      onChunkSelect(result.chunkId);
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
        {/* Search Mode Tabs */}
        <div className="flex border-b border-zinc-800 bg-zinc-950">
          <button
            className={`
              flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors relative
              ${searchMode === "semantic" ? "text-blue-400 bg-zinc-900" : "text-zinc-500 hover:text-zinc-300"}
            `}
            onClick={() => setSearchMode("semantic")}
          >
            <Sparkles className="w-4 h-4" />
            Semantic Search
            {searchMode === "semantic" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />}
          </button>
          <button
            className={`
              flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors relative
              ${searchMode === "keyword" ? "text-blue-400 bg-zinc-900" : "text-zinc-500 hover:text-zinc-300"}
            `}
            onClick={() => setSearchMode("keyword")}
          >
            <Hash className="w-4 h-4" />
            Keyword Search
            {searchMode === "keyword" && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />}
          </button>
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800">
          <Search className="w-5 h-5 text-zinc-500" />
          <input
            ref={inputRef}
            type="text"
            placeholder={
              searchMode === "semantic"
                ? "Search by meaning... (e.g., 'how does attention work?')"
                : "Search by keywords... (e.g., 'transformer attention')"
            }
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
                {results.map((result, index) => (
                  <div
                    key={result.id}
                    className={`
                      flex items-start gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                      ${index === selectedIndex ? "bg-zinc-800" : "hover:bg-zinc-800/50"}
                    `}
                    onClick={() => handleSelectResult(result)}
                  >
                    <FileText className="w-4 h-4 text-zinc-500 mt-1 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <h3 className="text-sm font-medium text-zinc-200 truncate">{result.title}</h3>
                        {result.relevance && (
                          <span className="text-xs text-blue-400 font-medium">
                            {Math.round(result.relevance * 100)}%
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 mb-1">{result.path}</p>
                      <p className="text-xs text-zinc-600 line-clamp-1">{result.preview}</p>
                    </div>
                  </div>
                ))}
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
            <span>
              Powered by{" "}
              <span className="text-blue-400 font-medium">{searchMode === "semantic" ? "AI" : "FTS5"}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
