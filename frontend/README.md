# Intelligent Knowledge Base - Frontend

A modern, AI-powered knowledge management interface built with Next.js 14, featuring intelligent clustering, semantic search, knowledge graph visualization, and flexible layouts.

## ✨ Features

### 🎨 **Beautiful Dark-Mode UI**
- Professional IDE-like interface with deep customization
- Responsive 3-column layout (Holy Grail pattern)
- **Resizable panels** - Drag to adjust sidebar widths ⭐ NEW
- Optimized typography for extended reading sessions
- Smooth animations and transitions throughout

### 📂 **Smart Knowledge Organization**
- **Left Sidebar**:
  - Dual view modes: AI-clustered view / File tree view
  - Recursive nesting with lazy loading
  - Expandable/collapsible clusters
  - Quick view mode switching
- **Center Panel**:
  - Markdown viewer with GitHub Flavored Markdown support
  - Syntax highlighting for code blocks
  - Two display modes: Single chunk / Full file
  - Breadcrumb navigation
  - **Smart chunk anchoring** for precise navigation ⭐ NEW
- **Right Sidebar**:
  - **Tab-based interface**: AI Suggestions / Knowledge Graph ⭐ NEW
  - Context-aware recommendations
  - Similarity scoring with visual indicators
  - Interactive graph visualization ⭐ NEW

### 🔍 **Powerful Search**
- **Command Palette** (⌘K / Ctrl+K)
- Dual search modes:
  - **Semantic Search**: AI-powered topic-based search
  - **Keyword Search**: Traditional full-text search (FTS5)
- Real-time search with debouncing (300ms)
- Keyboard navigation (↑↓ arrows, Enter, Escape)
- Search result preview snippets

### 🤖 **AI-Powered Recommendations**

#### Suggestion Panel (Chunk-level)
- Automatically suggests related chunks
- Two recommendation modes:
  - **Cluster-based**: Topic similarity
  - **Embedding-based**: Semantic similarity
- Similarity scoring displayed as percentage
- Quick preview and navigation
- **Click to scroll to chunk** ⭐ NEW

#### Related Notes (File-level)
- File-level recommendations at page bottom
- Shows matched sections count
- Displays recommendation reason (Same Topic / Similar Content)
- **Click to navigate to related file** ⭐ NEW
- Automatic content loading and smooth scrolling

### 📊 **Knowledge Graph Visualization** ⭐ NEW
- Interactive force-directed graph using ReactFlow
- Visual features:
  - Color-coded nodes (Current / Same Topic / Similar)
  - Animated connections with arrows
  - Similarity scores on edges
  - Legend panel for easy understanding
- Interaction capabilities:
  - Click nodes to navigate to notes
  - Drag to pan the view
  - Scroll to zoom in/out
  - Mini-map for overview
  - Control panel (zoom in/out/fit view)
  - Full-screen mode
- Switch between Topic-based and Similarity-based modes

### 🎯 **Smart Navigation**
- **Smooth scrolling** to target content
- **Highlight animation** (2-second pulse effect)
- **Intelligent chunk positioning** with 3-strategy matching:
  1. Heading-based matching (# to ######)
  2. Content prefix matching (first 150 chars)
  3. First-line matching
- Automatic breadcrumb updates
- Visual feedback for all interactions

### 🖱️ **Flexible Layout** ⭐ NEW
- **Resizable sidebars**:
  - Left sidebar: 200px - 500px (default: 288px)
  - Right sidebar: 250px - 600px (default: 320px)
- **Drag handles** between panels with visual feedback
- Smooth resize animations
- Boundary constraints to prevent panels from being too small/large
- Settings persist in session (can be saved to localStorage)

## 🛠 Tech Stack

### Core
- **Framework**: Next.js 14.2 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 3.4

### UI & Visualization
- **Icons**: Lucide React 0.447
- **Markdown**:
  - react-markdown 9.0.1
  - remark-gfm 4.0.0 (GitHub Flavored Markdown)
  - rehype-raw 7.0.0 (HTML rendering)
- **Graph**: ReactFlow (for knowledge graph) ⭐ NEW

### Development
- **Linting**: ESLint with Next.js config
- **Package Manager**: npm / yarn / pnpm

## 🚀 Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm / yarn / pnpm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install
# or
yarn install
# or
pnpm install
```

### Environment Configuration

Create a `.env.local` file in the frontend directory:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Development

```bash
# Run the development server
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

The page auto-updates as you edit files.

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

### Linting

```bash
# Run ESLint
npm run lint
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css          # Global styles + animations
│   │   ├── layout.tsx           # Root layout with metadata
│   │   └── page.tsx             # Main dashboard (980+ lines)
│   │
│   ├── components/
│   │   ├── FileTree.tsx         # Cluster tree view component
│   │   ├── FileDirectoryTree.tsx # File system tree component
│   │   ├── SuggestionPanel.tsx  # AI suggestions (chunk-level)
│   │   ├── RelatedNotes.tsx     # Related files (file-level) ⭐
│   │   ├── CommandPalette.tsx   # Global search modal
│   │   ├── KnowledgeGraph.tsx   # Graph visualization ⭐ NEW
│   │   └── ResizeHandle.tsx     # Draggable resize handle ⭐ NEW
│   │
│   └── lib/
│       ├── api.ts               # Backend API client (225 lines)
│       ├── utils.ts             # Utility functions
│       └── mockData.ts          # Mock data for development
│
├── public/                      # Static assets
├── package.json                 # Dependencies & scripts
├── tailwind.config.ts           # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
├── next.config.mjs             # Next.js configuration
└── README.md                   # This file
```

## 🎨 Key Components

### FileTree
Cluster-based tree view with:
- Lazy loading of cluster members
- Expandable/collapsible nodes
- Active state highlighting
- Smooth expand/collapse animations
- File count badges

**Location**: `src/components/FileTree.tsx`

### FileDirectoryTree
File system tree view with:
- Recursive directory rendering
- File/folder icon differentiation
- Alphabetically sorted entries
- Click to open files

**Location**: `src/components/FileDirectoryTree.tsx`

### SuggestionPanel
AI-powered chunk recommendations featuring:
- Related chunks with similarity scores
- Color-coded match quality (Excellent/Good/Related)
- Quick preview snippets
- Mode switching (Cluster/Embedding)
- **Click to scroll to chunk in file view** ⭐

**Location**: `src/components/SuggestionPanel.tsx`

### RelatedNotes ⭐
File-level recommendations featuring:
- Related files displayed at page bottom
- Recommendation reason badges
- Similarity scores (percentage)
- Matched sections count
- **Click to navigate to related file** ⭐
- Mode switching (Topic-based/Similarity-based)

**Location**: `src/components/RelatedNotes.tsx`

### KnowledgeGraph ⭐ NEW
Interactive knowledge graph featuring:
- Force-directed graph layout
- Color-coded nodes by relationship type
- Animated edges with similarity scores
- Draggable, zoomable interface
- Mini-map for navigation
- Full-screen mode toggle
- Legend panel
- **Click nodes to navigate** ⭐

**Location**: `src/components/KnowledgeGraph.tsx`

### ResizeHandle ⭐ NEW
Draggable panel resizer featuring:
- Smooth drag interactions
- Visual feedback (color change on hover/drag)
- Grip icon indicator
- Boundary constraints
- Cursor change on hover

**Location**: `src/components/ResizeHandle.tsx`

### CommandPalette
Global search interface with:
- Keyboard shortcuts (⌘K / Ctrl+K)
- Tab-based search modes (Semantic/Keyword)
- Keyboard navigation (↑↓, Enter, ESC)
- Real-time search with debouncing
- Result preview and relevance scores

**Location**: `src/components/CommandPalette.tsx`

## 🔌 Backend Integration

### API Client

The API client (`src/lib/api.ts`) provides TypeScript-typed functions for:

**Search**:
- `searchChunks(query, limit)` - Full-text search
- `suggestClusters(query, limit, ftsK)` - Semantic search

**Content Retrieval**:
- `getChunk(chunkId)` - Get single chunk
- `getFileChunks(filePath)` - Get all chunks in file
- `getFileContent(filePath)` - Get raw markdown content
- `getFileTree()` - Get file tree structure

**Recommendations**:
- `getRelatedChunks(chunkId, mode, k)` - Get related chunks
- `getRelatedNotes(chunkId, mode, k)` - Get related files ⭐

**Clustering**:
- `listClusters(limit)` - List all clusters
- `getClusterDetail(clusterId, limit)` - Get cluster with members

### API Response Types

All responses are fully typed with TypeScript interfaces:
- `ChunkHit`, `ChunkDetail` - Chunk data
- `RelatedItem` - Related chunk recommendation
- `RelatedNote` - Related file recommendation ⭐
- `SearchResponse` - Search results
- `ClusterListItem`, `ClusterDetail` - Cluster data
- `FileTreeNode` - File tree structure

### Starting the Backend

```bash
# From the project root directory
uvicorn src.kb.api.app:app --reload --port 8000

# API documentation will be available at:
# http://localhost:8000/docs
```

## ⌨️ Keyboard Shortcuts

- `⌘K` / `Ctrl+K`: Open command palette
- `ESC`: Close command palette / dialogs
- `↑` `↓`: Navigate search results
- `Enter`: Select result
- `Tab`: Switch search mode (Semantic ↔ Keyword)

## 🎨 Customization

### Theme Colors

Edit `tailwind.config.ts` to customize colors:

```typescript
theme: {
  extend: {
    colors: {
      // Primary colors
      border: "hsl(var(--border))",
      background: "hsl(var(--background))",
      foreground: "hsl(var(--foreground))",
    }
  }
}
```

### Global Styles

Edit `src/app/globals.css` for:
- Custom animations (e.g., `highlight-pulse`)
- Chunk anchor styles
- Custom CSS utilities

### Panel Widths

Default panel widths can be changed in `src/app/page.tsx`:

```typescript
const [leftSidebarWidth, setLeftSidebarWidth] = useState(288);  // Change default
const [rightSidebarWidth, setRightSidebarWidth] = useState(320); // Change default
```

## 🧪 Development Tips

### Hot Reload
Next.js provides fast refresh - changes appear instantly without losing state.

### Type Checking
Run TypeScript compiler to check for type errors:
```bash
npx tsc --noEmit
```

### Debugging
- Use React DevTools browser extension
- Check browser console for `console.log` outputs
- Network tab shows all API calls
- Search for "Failed to" in console to find errors

### Mock Data (for testing without backend)
Edit `src/lib/mockData.ts` to customize:
- `mockClusterTree` - File tree structure
- Sample content and clusters

## 📦 Dependencies

### Production Dependencies
```json
{
  "next": "14.2.35",
  "react": "18.3.0",
  "react-dom": "18.3.0",
  "react-markdown": "9.0.1",
  "remark-gfm": "4.0.0",
  "rehype-raw": "7.0.0",
  "reactflow": "^11.11.0",
  "lucide-react": "^0.447.0"
}
```

### Dev Dependencies
```json
{
  "typescript": "^5",
  "tailwindcss": "^3.4.1",
  "eslint": "^8",
  "eslint-config-next": "14.2.35"
}
```

## 🐛 Known Issues

1. **ESLint Warning** in `CommandPalette.tsx:64`
   - Warning about missing `useEffect` dependency
   - Does not affect functionality
   - Will be fixed in next refactor

2. **Large File Performance**
   - Files over 10MB may have render lag
   - Consider implementing virtual scrolling

3. **Graph Node Limit**
   - Performance degrades with >50 nodes
   - Consider pagination or node filtering

## 🚀 Future Enhancements

### High Priority
- [ ] Persist panel widths to localStorage
- [ ] Virtual scrolling for large files
- [ ] Search result highlighting
- [ ] Export notes to PDF

### Medium Priority
- [ ] Real-time collaboration
- [ ] Note editing capabilities
- [ ] Multi-document comparison view
- [ ] Tag system
- [ ] Search history

### Low Priority
- [ ] Custom themes (light mode)
- [ ] Mobile responsive design
- [ ] PWA offline support
- [ ] 3D knowledge graph
- [ ] Timeline view

## 📚 Additional Documentation

- **Main Project README**: `../README.md`
- **Development Guide**: `../DEVELOPMENT.md` - Detailed development progress and technical details
- **API Documentation**: http://localhost:8000/docs (when backend is running)

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
npx kill-port 3000

# Or use different port
npm run dev -- -p 3001
```

### API Connection Issues
1. Check backend is running on port 8000
2. Verify `.env.local` has correct API URL
3. Check CORS settings in backend
4. Look for errors in browser console

### Build Errors
```bash
# Clear Next.js cache
rm -rf .next

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 📄 License

MIT

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a Pull Request

## 🙏 Acknowledgments

- Built with [Next.js](https://nextjs.org/)
- UI components inspired by modern IDE designs
- Graph visualization powered by [ReactFlow](https://reactflow.dev/)
- Icons from [Lucide](https://lucide.dev/)

---

**Last Updated**: 2026-01-07

For detailed development progress and technical implementation details, see `DEVELOPMENT.md` in the project root.
