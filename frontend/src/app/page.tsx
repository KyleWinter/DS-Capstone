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
  Layers,
  ArrowLeft,
} from "lucide-react";
import { FileTree } from "@/components/FileTree";
import { FileDirectoryTree } from "@/components/FileDirectoryTree";
import { ModuleTree } from "@/components/ModuleTree";
import { SuggestionPanel } from "@/components/SuggestionPanel";
import { CommandPalette } from "@/components/CommandPalette";
import { RelatedNotes } from "@/components/RelatedNotes";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { ResizeHandle } from "@/components/ResizeHandle";
import { TreeNode } from "@/lib/mockData";
import { listClusters, getChunk, getClusterDetail, ChunkDetail, getFileTree, FileTreeNode, getFileChunks, getFileContent, listModules, ModuleListItem } from "@/lib/api";
import { buildClusterTree, pathToBreadcrumbs, chunksToTreeNodes } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

export default function DashboardPage() {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [rightPanelMode, setRightPanelMode] = useState<'suggestions' | 'graph'>('suggestions');
  const [activeNote, setActiveNote] = useState<TreeNode | null>(null);
  const [activeChunk, setActiveChunk] = useState<ChunkDetail | null>(null);
  const [activeChunks, setActiveChunks] = useState<ChunkDetail[]>([]);
  const [activeFileContent, setActiveFileContent] = useState<string>("");
  const [displayMode, setDisplayMode] = useState<'single' | 'file'>('single');
  const [clusterTree, setClusterTree] = useState<TreeNode | null>(null);
  const [fileTree, setFileTree] = useState<FileTreeNode | null>(null);
  const [modules, setModules] = useState<ModuleListItem[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'clusters' | 'files' | 'modules'>('clusters');
  const [activeFilePath, setActiveFilePath] = useState<string>("");

  // Navigation history for back button
  interface HistoryEntry {
    type: 'chunk' | 'file' | 'file-scroll';
    chunkId?: number;
    filePath?: string;
    displayMode: 'single' | 'file';
    scrollToChunkId?: number; // For file-scroll type: which chunk to scroll to
  }
  const [navigationHistory, setNavigationHistory] = useState<HistoryEntry[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Resizable panel widths
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(288); // 72 * 4 = 288px (w-72)
  const [rightSidebarWidth, setRightSidebarWidth] = useState(320); // 80 * 4 = 320px (w-80)

  // Load clusters, file tree, and modules on mount
  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);

        // Load clusters, file tree, and modules in parallel
        const [clusters, fileTreeData, modulesData] = await Promise.all([
          listClusters(100),
          getFileTree(),
          listModules(100)
        ]);

        const tree = buildClusterTree(clusters);
        setClusterTree(tree);
        setFileTree(fileTreeData);
        setModules(modulesData);
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

  const addToHistory = (entry: HistoryEntry) => {
    setNavigationHistory((prev) => {
      // Remove any forward history when navigating to a new location
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(entry);
      // Keep max 50 entries
      if (newHistory.length > 50) {
        newHistory.shift();
      }
      return newHistory;
    });
    setHistoryIndex((prev) => Math.min(prev + 1, 49));
  };

  const handleChunkSelect = async (chunkId: number, addHistory: boolean = true) => {
    try {
      const chunk = await getChunk(chunkId);
      setActiveChunk(chunk);
      setActiveChunks([]);
      setActiveFileContent("");
      setDisplayMode('single');
      setActiveFilePath(chunk.file_path);
      setBreadcrumbs(pathToBreadcrumbs(chunk.file_path));

      if (addHistory) {
        addToHistory({
          type: 'chunk',
          chunkId,
          displayMode: 'single',
        });
      }
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

  const handleFileSelect = async (node: FileTreeNode, addHistory: boolean = true) => {
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

        if (addHistory) {
          addToHistory({
            type: 'file',
            filePath: node.path,
            displayMode: 'file',
          });
        }
      } catch (error) {
        console.error("Failed to load file:", error);
      }
    }
  };

  const handleModuleFileSelect = async (filePath: string, addHistory: boolean = true) => {
    try {
      setActiveFilePath(filePath);

      // Load both raw file content and chunks in parallel
      const [fileContent, chunks] = await Promise.all([
        getFileContent(filePath),
        getFileChunks(filePath)
      ]);

      setActiveFileContent(fileContent);
      setActiveChunks(chunks);
      setActiveChunk(null);
      setDisplayMode('file');
      setBreadcrumbs(pathToBreadcrumbs(filePath));

      if (addHistory) {
        addToHistory({
          type: 'file',
          filePath,
          displayMode: 'file',
        });
      }
    } catch (error) {
      console.error("Failed to load file from module:", error);
    }
  };

  const handleRelatedNoteClick = async (filePath: string, addHistory: boolean = true) => {
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

        if (addHistory) {
          addToHistory({
            type: 'file',
            filePath,
            displayMode: 'file',
          });
        }

        // Scroll to top of the page smoothly
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } catch (error) {
      console.error("Failed to load related note:", error);
    }
  };

  // Handle AI Suggestion clicks - unified handler for all views
  const handleSuggestionClick = async (chunkId: number) => {
    if (displayMode === 'file' && activeFilePath) {
      // In file mode, scroll to the chunk in the current file
      // But first check if the chunk belongs to the current file
      try {
        const chunk = await getChunk(chunkId);

        if (chunk.file_path === activeFilePath) {
          // Same file: just scroll to the chunk and record scroll history
          scrollToChunk(chunkId);
          addToHistory({
            type: 'file-scroll',
            filePath: activeFilePath,
            displayMode: 'file',
            scrollToChunkId: chunkId,
          });
        } else {
          // Different file: load the new file
          await handleRelatedNoteClick(chunk.file_path, true);
          // Then scroll to the specific chunk
          setTimeout(() => scrollToChunk(chunkId), 300);
        }
      } catch (error) {
        console.error("Failed to handle suggestion click:", error);
        // Fallback: load chunk in single mode
        await handleChunkSelect(chunkId, true);
      }
    } else {
      // In single chunk mode, load the new chunk
      await handleChunkSelect(chunkId, true);
    }
  };

  // Go back in navigation history
  const handleGoBack = async () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      const entry = navigationHistory[newIndex];

      setHistoryIndex(newIndex);

      if (entry.type === 'chunk' && entry.chunkId) {
        await handleChunkSelect(entry.chunkId, false);
      } else if (entry.type === 'file' && entry.filePath) {
        await handleRelatedNoteClick(entry.filePath, false);
      } else if (entry.type === 'file-scroll' && entry.filePath && entry.scrollToChunkId) {
        // For file-scroll type: load the file (if not already loaded) and scroll to position
        if (activeFilePath !== entry.filePath || displayMode !== 'file') {
          await handleRelatedNoteClick(entry.filePath, false);
          // Wait for render then scroll
          setTimeout(() => scrollToChunk(entry.scrollToChunkId!), 300);
        } else {
          // Already on the same file, just scroll
          scrollToChunk(entry.scrollToChunkId);
        }
      }
    }
  };

  const scrollToChunk = (chunkId: number) => {
    const anchor = document.getElementById(`chunk-${chunkId}`);
    if (anchor) {
      // Scroll to the anchor with smooth behavior
      anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });

      // Find the next sibling element to highlight (the actual content after anchor)
      const nextElement = anchor.nextElementSibling;

      if (nextElement) {
        // Remove any existing highlights first
        document.querySelectorAll('.highlight-chunk').forEach(el => {
          el.classList.remove('highlight-chunk');
        });

        // Highlight the content briefly
        nextElement.classList.add('highlight-chunk');
        setTimeout(() => {
          nextElement?.classList.remove('highlight-chunk');
        }, 2000);
      }
    } else {
      console.warn(`Chunk anchor not found for chunk_id: ${chunkId}`);
    }
  };

  // Handle left sidebar resize
  const handleLeftSidebarResize = (deltaX: number) => {
    setLeftSidebarWidth((prevWidth) => {
      const newWidth = prevWidth + deltaX;
      // Constrain between 200px and 500px
      return Math.min(Math.max(newWidth, 200), 500);
    });
  };

  // Handle right sidebar resize
  const handleRightSidebarResize = (deltaX: number) => {
    setRightSidebarWidth((prevWidth) => {
      const newWidth = prevWidth - deltaX; // Subtract because dragging right should shrink
      // Constrain between 250px and 600px
      return Math.min(Math.max(newWidth, 250), 600);
    });
  };

  // Prepare markdown content with anchors for navigation
  const markdownWithAnchors = useMemo(() => {
    if (!activeFileContent || activeChunks.length === 0) return activeFileContent;

    // Sort chunks by ordinal to maintain order
    const sortedChunks = [...activeChunks].sort((a, b) => a.ordinal - b.ordinal);

    // Build a list of insertions (position, anchor html)
    const insertions: Array<{ position: number; anchor: string }> = [];

    for (const chunk of sortedChunks) {
      // Try to find chunk content in the file
      const chunkContent = chunk.content.trim();

      let position = -1;

      // Strategy 1: Try to find the heading in markdown format
      if (chunk.heading) {
        const headingPatterns = [
          `# ${chunk.heading}`,
          `## ${chunk.heading}`,
          `### ${chunk.heading}`,
          `#### ${chunk.heading}`,
          `##### ${chunk.heading}`,
          `###### ${chunk.heading}`,
        ];

        for (const pattern of headingPatterns) {
          position = activeFileContent.indexOf(pattern);
          if (position !== -1) break;
        }
      }

      // Strategy 2: If heading not found, try to match a significant portion of content
      if (position === -1 && chunkContent.length > 20) {
        // Try to match the first 150 characters of content (or less if content is shorter)
        const contentPreview = chunkContent.substring(0, Math.min(150, chunkContent.length));
        position = activeFileContent.indexOf(contentPreview);
      }

      // Strategy 3: Try matching first line of content
      if (position === -1) {
        const firstLine = chunkContent.split('\n')[0].trim();
        if (firstLine.length > 10) {
          position = activeFileContent.indexOf(firstLine);
        }
      }

      // If we found a position, add an insertion point
      if (position !== -1) {
        insertions.push({
          position,
          anchor: `<div id="chunk-${chunk.id}" class="chunk-anchor"></div>\n`
        });
      }
    }

    // Sort insertions by position (descending) to insert from back to front
    // This prevents position shifts as we insert
    insertions.sort((a, b) => b.position - a.position);

    // Apply insertions
    let result = activeFileContent;
    for (const insertion of insertions) {
      result = result.slice(0, insertion.position) + insertion.anchor + result.slice(insertion.position);
    }

    return result;
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
        <aside
          className="border-r border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden"
          style={{ width: `${leftSidebarWidth}px` }}
        >
          {/* Header with view toggle */}
          <div className="px-4 py-3 border-b border-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-zinc-100">
                {viewMode === 'clusters' ? 'Knowledge Graph' : viewMode === 'files' ? 'File Explorer' : 'Modules'}
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
                <button
                  onClick={() => setViewMode('modules')}
                  className={`p-1.5 rounded transition-colors ${
                    viewMode === 'modules'
                      ? 'bg-zinc-800 text-purple-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                  title="Module View"
                >
                  <Layers className="w-4 h-4" />
                </button>
              </div>
            </div>
            <p className="text-xs text-zinc-500">
              {viewMode === 'clusters' ? 'AI-Clustered Notes' : viewMode === 'files' ? 'Directory Structure' : 'Module Classification'}
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
            ) : viewMode === 'files' ? (
              fileTree ? (
                <FileDirectoryTree
                  node={fileTree}
                  activePath={activeFilePath}
                  onFileSelect={handleFileSelect}
                />
              ) : (
                <div className="p-4 text-center text-zinc-500 text-sm">No files available</div>
              )
            ) : (
              modules.length > 0 ? (
                <ModuleTree
                  modules={modules}
                  activePath={activeFilePath}
                  onFileSelect={handleModuleFileSelect}
                />
              ) : (
                <div className="p-4 text-center text-zinc-500 text-sm">No modules available</div>
              )
            )}
          </div>
        </aside>

        {/* Left Resize Handle */}
        <ResizeHandle onResize={handleLeftSidebarResize} />

        {/* Center Panel - Editor/Viewer */}
        <main className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
          {/* Breadcrumbs with Back Button */}
          <div className="h-12 border-b border-zinc-800 flex items-center px-6 gap-2">
            {/* Back Button */}
            {historyIndex > 0 && (
              <button
                onClick={handleGoBack}
                className="flex items-center gap-1.5 px-2 py-1 mr-2 rounded-md bg-zinc-800 hover:bg-zinc-700 transition-colors group"
                title="Go back to previous note"
              >
                <ArrowLeft className="w-4 h-4 text-zinc-400 group-hover:text-zinc-200" />
                <span className="text-xs text-zinc-400 group-hover:text-zinc-200">Back</span>
              </button>
            )}

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
                {activeChunks.length > 0 && activeChunks[0].id && activeChunks[0].id > 0 && (
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

        {/* Right Sidebar - AI Suggestions / Knowledge Graph */}
        {isRightSidebarOpen && (activeChunk || activeChunks.length > 0) && (() => {
          const chunkId = activeChunk?.id || (activeChunks.length > 0 ? activeChunks[0].id : 0);
          const filePath = activeFilePath || activeChunk?.file_path || (activeChunks.length > 0 ? activeChunks[0].file_path : '');

          // Only render if we have valid data
          if (!chunkId || chunkId === 0) {
            return null;
          }

          return (
            <>
              {/* Right Resize Handle */}
              <ResizeHandle onResize={handleRightSidebarResize} />

              <aside
                className="flex flex-col"
                style={{ width: `${rightSidebarWidth}px` }}
              >
              {/* Tab Switcher */}
              <div className="h-12 border-b border-l border-zinc-800 bg-zinc-900/50 backdrop-blur-sm flex items-center px-2 gap-1">
                <button
                  onClick={() => setRightPanelMode('suggestions')}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    rightPanelMode === 'suggestions'
                      ? 'bg-zinc-800 text-zinc-100'
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                  }`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                  Suggestions
                </button>
                <button
                  onClick={() => setRightPanelMode('graph')}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    rightPanelMode === 'graph'
                      ? 'bg-zinc-800 text-zinc-100'
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                  }`}
                >
                  <Network className="w-3.5 h-3.5" />
                  Graph
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-hidden border-l border-zinc-800">
                {rightPanelMode === 'suggestions' ? (
                  <SuggestionPanel
                    chunkId={chunkId}
                    onNoteClick={handleSuggestionClick}
                  />
                ) : (
                  <KnowledgeGraph
                    filePath={filePath}
                    chunkId={chunkId}
                    onNodeClick={handleRelatedNoteClick}
                  />
                )}
              </div>
            </aside>
            </>
          );
        })()}
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
