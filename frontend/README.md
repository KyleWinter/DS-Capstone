# Intelligent Knowledge Base - Frontend

A modern, AI-powered knowledge management interface built with Next.js 14, featuring auto-clustering and semantic search capabilities.

## Features

### 🎨 **Beautiful Dark-Mode UI**
- Professional IDE-like interface
- Responsive 3-column layout (Holy Grail)
- Optimized typography for reading
- Smooth animations and transitions

### 📂 **Smart Knowledge Organization**
- **Left Sidebar**: AI-clustered file tree with recursive nesting
- **Center Panel**: Markdown viewer with syntax highlighting
- **Right Sidebar**: Context-aware AI suggestions with similarity scores

### 🔍 **Powerful Search**
- **Command Palette** (⌘K / Ctrl+K)
- Dual search modes:
  - **Semantic Search**: AI-powered meaning-based search
  - **Keyword Search**: Traditional full-text search
- Real-time search results with relevance scoring

### 🤖 **AI Suggestions**
- Automatically suggests related notes
- Similarity scoring (displayed as percentage)
- Context-aware recommendations
- Quick navigation to related content

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Markdown**: react-markdown with remark-gfm

## Getting Started

### Installation

\`\`\`bash
# Install dependencies
npm install

# or
yarn install

# or
pnpm install
\`\`\`

### Development

\`\`\`bash
# Run the development server
npm run dev

# or
yarn dev

# or
pnpm dev
\`\`\`

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

\`\`\`bash
# Build for production
npm run build

# Start production server
npm start
\`\`\`

## Project Structure

\`\`\`
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css       # Global styles
│   │   ├── layout.tsx        # Root layout
│   │   └── page.tsx          # Main dashboard page
│   ├── components/
│   │   ├── FileTree.tsx      # Recursive file tree component
│   │   ├── SuggestionPanel.tsx  # AI suggestions sidebar
│   │   └── CommandPalette.tsx   # Search modal
│   └── lib/
│       └── mockData.ts       # Mock data for development
├── public/                   # Static assets
├── tailwind.config.ts        # Tailwind configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies
\`\`\`

## Key Components

### FileTree
Recursive component displaying the knowledge graph with:
- Expandable/collapsible clusters
- File and folder icons
- Active state highlighting
- Hover effects

### SuggestionPanel
AI-powered recommendations featuring:
- Related notes with similarity scores
- Color-coded match quality
- Quick preview snippets
- One-click navigation

### CommandPalette
Global search interface with:
- Keyboard shortcuts (⌘K)
- Tab-based search modes
- Keyboard navigation (↑↓ arrows)
- Recent search history

## Customization

### Colors
Edit \`tailwind.config.ts\` to customize the color scheme:
\`\`\`typescript
colors: {
  border: "hsl(var(--border))",
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
}
\`\`\`

### Mock Data
Edit \`src/lib/mockData.ts\` to customize the sample content:
- \`mockClusterTree\`: File tree structure
- \`mockRelatedNotes\`: AI suggestions
- \`mockMarkdownContent\`: Note content

## Backend Integration

The frontend is now fully integrated with the Python backend API!

### API Client

The API client is located in \`src/lib/api.ts\` and provides functions for:
- **Search**: FTS-based keyword search
- **Chunks**: Fetch individual chunks and their content
- **Related Items**: Get related chunks by cluster or embedding similarity
- **Clusters**: List clusters, get cluster details with members
- **Suggestions**: Get cluster suggestions based on search queries

### Environment Configuration

Configure the backend API URL in \`.env.local\`:
\`\`\`bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
\`\`\`

### Starting the Backend

Make sure the Python backend is running before starting the frontend:
\`\`\`bash
# From the project root directory
uvicorn src.kb.api.app:app --reload --host 0.0.0.0 --port 8000
\`\`\`

## Keyboard Shortcuts

- \`⌘K\` / \`Ctrl+K\`: Open command palette
- \`ESC\`: Close command palette
- \`↑\` \`↓\`: Navigate search results
- \`Enter\`: Select result

## Future Enhancements

- [ ] Real-time collaboration
- [ ] Note editing capabilities
- [ ] Graph visualization view
- [ ] Export/import functionality
- [ ] Custom themes
- [ ] Mobile responsive design
- [ ] Offline support with PWA

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
