"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Search,
  Menu,
  PanelRightClose,
  PanelRightOpen,
  Library,
  ChevronRight,
  FolderTree,
  Network,
} from "lucide-react";
import { FileTree } from "@/components/FileTree";
import { FileDirectoryTree } from "@/components/FileDirectoryTree";
import { SuggestionPanel } from "@/components/SuggestionPanel";
import { CommandPalette } from "@/components/CommandPalette";
import { RelatedNotes } from "@/components/RelatedNotes";
import { TreeNode } from "@/lib/mockData";
import { listClusters, getChunk, getClusterDetail, ChunkDetail, getFileTree, FileTreeNode, getFileChunks, getFileContent } from "@/lib/api";
import { buildClusterTree, pathToBreadcrumbs, chunksToTreeNodes } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

export default function DashboardPage() {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [activeNote, setActiveNote] = useState<TreeNode | null>(null);
  const [activeChunk, setActiveChunk] = useState<ChunkDetail | null>(null);
  const [activeChunks, setActiveChunks] = useState<ChunkDetail[]>([]);
  const [activeFileContent, setActiveFileContent] = useState<string>("");
  const [displayMode, setDisplayMode] = useState<'single' | 'file'>('single');
  const [clusterTree, setClusterTree] = useState<TreeNode | null>(null);
  const [fileTree, setFileTree] = useState<FileTreeNode | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'clusters' | 'files'>('clusters');
  const [activeFilePath, setActiveFilePath] = useState<string>("");

  // Load clusters and file tree on mount
  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);

        // Load both clusters and file tree in parallel
        const [clusters, fileTreeData] = await Promise.all([
          listClusters(100),
          getFileTree()
        ]);

        const tree = buildClusterTree(clusters);
        setClusterTree(tree);
        setFileTree(fileTreeData);
      } catch (error) {
        console.error("Failed to load data:", error);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  // Handle Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleClusterExpand = async (node: TreeNode) => {
    // Extract cluster ID from node ID (format: "cluster-123")
    if (!node.id.startsWith("cluster-")) return;

    const clusterId = parseInt(node.id.replace("cluster-", ""));
    try {
      const clusterDetail = await getClusterDetail(clusterId, 50);
      const memberNodes = chunksToTreeNodes(clusterDetail.members);

      // Update the tree by finding and updating this cluster node
      setClusterTree((prevTree) => {
        if (!prevTree) return prevTree;

        const updateNode = (n: TreeNode): TreeNode => {
          if (n.id === node.id) {
            return { ...n, children: memberNodes };
          }
          if (n.children) {
            return { ...n, children: n.children.map(updateNode) };
          }
          return n;
        };

        return updateNode(prevTree);
      });
    } catch (error) {
      console.error("Failed to load cluster members:", error);
    }
  };

  const handleChunkSelect = async (chunkId: number) => {
    try {
      const chunk = await getChunk(chunkId);
      setActiveChunk(chunk);
      setActiveChunks([]);
      setActiveFileContent("");
      setDisplayMode('single');
      setBreadcrumbs(pathToBreadcrumbs(chunk.file_path));
    } catch (error) {
      console.error("Failed to load chunk:", error);
    }
  };

  const handleNoteSelect = (node: TreeNode) => {
    setActiveNote(node);
    // Extract chunk ID if this is a chunk node
    if (node.id.startsWith("chunk-")) {
      const chunkId = parseInt(node.id.replace("chunk-", ""));
      handleChunkSelect(chunkId);
    } else if (node.path) {
      setBreadcrumbs(pathToBreadcrumbs(node.path));
    }
  };

  const handleFileSelect = async (node: FileTreeNode) => {
    if (node.type === 'file' && node.path) {
      try {
        setActiveFilePath(node.path);

        // Load both raw file content and chunks in parallel
        // - Raw content for display
        // - Chunks for getting chunk IDs (needed for suggestions panel)
        const [fileContent, chunks] = await Promise.all([
          getFileContent(node.path),
          getFileChunks(node.path)
        ]);

        setActiveFileContent(fileContent);
        setActiveChunks(chunks);
        setActiveChunk(null);
        setDisplayMode('file');
        setBreadcrumbs(pathToBreadcrumbs(node.path));
      } catch (error) {
        console.error("Failed to load file:", error);
      }
    }
  };

  const handleRelatedNoteClick = async (filePath: string) => {
    try {
      // Load both file content and chunks in parallel
      const [fileContent, chunks] = await Promise.all([
        getFileContent(filePath),
        getFileChunks(filePath)
      ]);

      if (chunks.length > 0) {
        // Update all state
        setActiveFilePath(filePath);
        setActiveFileContent(fileContent);
        setActiveChunks(chunks);
        setActiveChunk(null);
        setDisplayMode('file');
        setBreadcrumbs(pathToBreadcrumbs(filePath));

        // Scroll to top of the page smoothly
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } catch (error) {
      console.error("Failed to load related note:", error);
    }
  };

  const scrollToChunk = (chunkId: number) => {
    const anchor = document.getElementById(`chunk-${chunkId}`);
    if (anchor) {
      anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });

      // Find the next sibling element to highlight (the actual content after anchor)
      const nextElement = anchor.nextElementSibling;

      if (nextElement) {
        // Highlight the content briefly
        nextElement.classList.add('highlight-chunk');
        setTimeout(() => {
          nextElement?.classList.remove('highlight-chunk');
        }, 2000);
      }
    }
  };

  // Prepare markdown content with anchors for navigation
  const markdownWithAnchors = useMemo(() => {
    if (!activeFileContent || activeChunks.length === 0) return activeFileContent;

    // Insert anchors before each chunk's content position
    // This is a simple approach - we add anchors at the beginning
    // A more sophisticated approach would try to match chunk content to file content
    return activeChunks
      .map(chunk => `<div id="chunk-${chunk.id}" class="chunk-anchor"></div>`)
      .join('\n') + '\n\n' + activeFileContent;
  }, [activeFileContent, activeChunks]);

  return (
    <div className="h-screen flex flex-col bg-zinc-950">
      {/* Top Navigation Bar */}
      <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-4 bg-zinc-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
            <Menu className="w-5 h-5 text-zinc-400" />
          </button>
          <div className="flex items-center gap-2">
            <Library className="w-5 h-5 text-blue-400" />
            <h1 className="text-sm font-semibold text-zinc-100">Intelligent Knowledge Base</h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors group"
            onClick={() => setIsCommandPaletteOpen(true)}
          >
            <Search className="w-4 h-4 text-zinc-400" />
            <span className="text-sm text-zinc-500">Search</span>
            <kbd className="px-1.5 py-0.5 text-xs font-medium text-zinc-500 bg-zinc-900 rounded border border-zinc-700">
              ⌘K
            </kbd>
          </button>

          <button
            className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            onClick={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
          >
            {isRightSidebarOpen ? (
              <PanelRightClose className="w-5 h-5 text-zinc-400" />
            ) : (
              <PanelRightOpen className="w-5 h-5 text-zinc-400" />
            )}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-72 border-r border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden">
          {/* Header with view toggle */}
          <div className="px-4 py-3 border-b border-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-zinc-100">
                {viewMode === 'clusters' ? 'Knowledge Graph' : 'File Explorer'}
              </h2>
              <div className="flex gap-1 bg-zinc-900 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('clusters')}
                  className={`p-1.5 rounded transition-colors ${
                    viewMode === 'clusters'
                      ? 'bg-zinc-800 text-blue-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                  title="Cluster View"
                >
                  <Network className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('files')}
                  className={`p-1.5 rounded transition-colors ${
                    viewMode === 'files'
                      ? 'bg-zinc-800 text-amber-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                  title="File Tree View"
                >
                  <FolderTree className="w-4 h-4" />
                </button>
              </div>
            </div>
            <p className="text-xs text-zinc-500">
              {viewMode === 'clusters' ? 'AI-Clustered Notes' : 'Directory Structure'}
            </p>
          </div>

          {/* Tree content */}
          <div className="flex-1 overflow-y-auto py-2">
            {isLoading ? (
              <div className="p-4 text-center text-zinc-500 text-sm">Loading...</div>
            ) : viewMode === 'clusters' ? (
              clusterTree ? (
                <FileTree
                  node={clusterTree}
                  activeNoteId={activeNote?.id}
                  onNoteSelect={handleNoteSelect}
                  onClusterExpand={handleClusterExpand}
                />
              ) : (
                <div className="p-4 text-center text-zinc-500 text-sm">No clusters available</div>
              )
            ) : (
              fileTree ? (
                <FileDirectoryTree
                  node={fileTree}
                  activePath={activeFilePath}
                  onFileSelect={handleFileSelect}
                />
              ) : (
                <div className="p-4 text-center text-zinc-500 text-sm">No files available</div>
              )
            )}
          </div>
        </aside>

        {/* Center Panel - Editor/Viewer */}
        <main className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
          {/* Breadcrumbs */}
          <div className="h-12 border-b border-zinc-800 flex items-center px-6 gap-2">
            {breadcrumbs.map((crumb, index) => (
              <div key={index} className="flex items-center gap-2">
                {index > 0 && <ChevronRight className="w-4 h-4 text-zinc-600" />}
                <span
                  className={`text-sm ${
                    index === breadcrumbs.length - 1
                      ? "text-zinc-100 font-medium"
                      : "text-zinc-500 hover:text-zinc-400 cursor-pointer"
                  }`}
                >
                  {crumb}
                </span>
              </div>
            ))}
          </div>

          {/* Markdown Content */}
          <div className="flex-1 overflow-y-auto">
            {displayMode === 'single' && activeChunk ? (
              <article className="max-w-4xl mx-auto px-8 py-12">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose prose-invert prose-zinc max-w-none"
                  components={{
                    h1: ({ node, ...props }) => <h1 className="text-3xl font-bold mb-6 text-zinc-100" {...props} />,
                    h2: ({ node, ...props }) => <h2 className="text-2xl font-semibold mb-4 mt-8 text-zinc-100" {...props} />,
                    h3: ({ node, ...props }) => <h3 className="text-xl font-semibold mb-3 mt-6 text-zinc-200" {...props} />,
                    p: ({ node, ...props }) => <p className="mb-4 text-zinc-300 leading-relaxed" {...props} />,
                    code: ({ node, inline, ...props }: any) =>
                      inline ? (
                        <code className="bg-zinc-900 text-blue-400 px-1.5 py-0.5 rounded text-sm" {...props} />
                      ) : (
                        <code className="block bg-zinc-900 text-zinc-300 p-4 rounded-lg overflow-x-auto" {...props} />
                      ),
                    pre: ({ node, ...props }) => (
                      <pre className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto my-4" {...props} />
                    ),
                    ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-4 text-zinc-300 space-y-2" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-4 text-zinc-300 space-y-2" {...props} />,
                    a: ({ node, ...props }) => (
                      <a className="text-blue-400 hover:text-blue-300 underline transition-colors" {...props} />
                    ),
                    blockquote: ({ node, ...props }) => (
                      <blockquote
                        className="border-l-4 border-zinc-700 pl-4 py-2 my-4 italic text-zinc-400"
                        {...props}
                      />
                    ),
                  }}
                >
                  {activeChunk.content}
                </ReactMarkdown>
              </article>
            ) : displayMode === 'file' && activeFileContent ? (
              <article className="max-w-4xl mx-auto px-8 py-12">
                {/* Render raw markdown file content with anchors for chunk navigation */}
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                  className="prose prose-invert prose-zinc max-w-none"
                  components={{
                    h1: ({ node, ...props }) => <h1 className="text-3xl font-bold mb-6 text-zinc-100" {...props} />,
                    h2: ({ node, ...props }) => <h2 className="text-2xl font-semibold mb-4 mt-8 text-zinc-100" {...props} />,
                    h3: ({ node, ...props }) => <h3 className="text-xl font-semibold mb-3 mt-6 text-zinc-200" {...props} />,
                    p: ({ node, ...props }) => <p className="mb-4 text-zinc-300 leading-relaxed" {...props} />,
                    code: ({ node, inline, ...props }: any) =>
                      inline ? (
                        <code className="bg-zinc-900 text-blue-400 px-1.5 py-0.5 rounded text-sm" {...props} />
                      ) : (
                        <code className="block bg-zinc-900 text-zinc-300 p-4 rounded-lg overflow-x-auto" {...props} />
                      ),
                    pre: ({ node, ...props }) => (
                      <pre className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto my-4" {...props} />
                    ),
                    ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-4 text-zinc-300 space-y-2" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-4 text-zinc-300 space-y-2" {...props} />,
                    a: ({ node, ...props }) => (
                      <a className="text-blue-400 hover:text-blue-300 underline transition-colors" {...props} />
                    ),
                    blockquote: ({ node, ...props }) => (
                      <blockquote
                        className="border-l-4 border-zinc-700 pl-4 py-2 my-4 italic text-zinc-400"
                        {...props}
                      />
                    ),
                  }}
                >
                  {markdownWithAnchors}
                </ReactMarkdown>

                {/* Related Notes Section */}
                {activeChunks.length > 0 && (
                  <RelatedNotes
                    chunkId={activeChunks[0].id}
                    onNoteClick={handleRelatedNoteClick}
                  />
                )}
              </article>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <h2 className="text-xl font-semibold text-zinc-400 mb-2">No content selected</h2>
                  <p className="text-sm text-zinc-600">
                    Select a note from the sidebar or use <kbd className="px-2 py-1 bg-zinc-800 rounded text-xs">⌘K</kbd> to search
                  </p>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Right Sidebar - AI Suggestions */}
        {isRightSidebarOpen && (activeChunk || activeChunks.length > 0) && (
          <aside className="w-80">
            <SuggestionPanel
              chunkId={activeChunk?.id || (activeChunks.length > 0 ? activeChunks[0].id : 0)}
              onNoteClick={displayMode === 'file' ? scrollToChunk : handleChunkSelect}
            />
          </aside>
        )}
      </div>

      {/* Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onChunkSelect={handleChunkSelect}
      />
    </div>
  );
}
