# Frontend Development Guide

**最后更新时间**: 2026-01-07

本文档提供前端开发的详细技术指南，包括组件设计、状态管理、API 集成和最佳实践。

---

## 📋 目录

1. [架构概述](#架构概述)
2. [核心组件详解](#核心组件详解)
3. [状态管理](#状态管理)
4. [API 集成](#api-集成)
5. [样式系统](#样式系统)
6. [性能优化](#性能优化)
7. [开发工作流](#开发工作流)
8. [常见模式](#常见模式)
9. [调试技巧](#调试技巧)
10. [贡献指南](#贡献指南)

---

## 架构概述

### 技术选型理由

| 技术 | 选择原因 |
|------|---------|
| **Next.js 14** | 服务端渲染、App Router、自动代码分割、优秀的开发体验 |
| **TypeScript** | 类型安全、更好的 IDE 支持、减少运行时错误 |
| **Tailwind CSS** | 实用优先、快速原型开发、一致的设计系统 |
| **ReactFlow** | 成熟的图谱可视化库、高性能、丰富的交互功能 |
| **react-markdown** | 安全的 Markdown 渲染、支持 GFM、可扩展 |

### 项目结构设计原则

```
src/
├── app/           # Next.js App Router - 路由和页面
├── components/    # 可复用组件 - UI 构建块
└── lib/          # 工具和业务逻辑 - 纯函数
```

**设计原则**:
1. **单一职责**: 每个组件只负责一个功能
2. **组合优于继承**: 通过组合小组件构建复杂 UI
3. **Props 向下，Events 向上**: 单向数据流
4. **展示与容器分离**: 区分 UI 组件和业务逻辑

---

## 核心组件详解

### 1. page.tsx - 主页面容器

**位置**: `src/app/page.tsx`
**行数**: 980+ 行
**职责**: 应用主入口，状态管理中枢，布局协调

#### 主要状态

```typescript
// 视图控制
const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
const [rightPanelMode, setRightPanelMode] = useState<'suggestions' | 'graph'>('suggestions');
const [viewMode, setViewMode] = useState<'clusters' | 'files'>('clusters');
const [displayMode, setDisplayMode] = useState<'single' | 'file'>('single');

// 内容状态
const [activeNote, setActiveNote] = useState<TreeNode | null>(null);
const [activeChunk, setActiveChunk] = useState<ChunkDetail | null>(null);
const [activeChunks, setActiveChunks] = useState<ChunkDetail[]>([]);
const [activeFileContent, setActiveFileContent] = useState<string>("");
const [activeFilePath, setActiveFilePath] = useState<string>("");

// 数据状态
const [clusterTree, setClusterTree] = useState<TreeNode | null>(null);
const [fileTree, setFileTree] = useState<FileTreeNode | null>(null);
const [breadcrumbs, setBreadcrumbs] = useState<string[]>([]);

// 布局状态 ⭐ NEW
const [leftSidebarWidth, setLeftSidebarWidth] = useState(288);
const [rightSidebarWidth, setRightSidebarWidth] = useState(320);
```

#### 核心函数

**handleChunkSelect** - Chunk 选择处理
```typescript
const handleChunkSelect = async (chunkId: number) => {
  const chunk = await getChunk(chunkId);
  setActiveChunk(chunk);
  setDisplayMode('single');
  setBreadcrumbs(pathToBreadcrumbs(chunk.file_path));
};
```

**handleFileSelect** - 文件选择处理
```typescript
const handleFileSelect = async (filePath: string) => {
  const [fileContent, chunks] = await Promise.all([
    getFileContent(filePath),
    getFileChunks(filePath)
  ]);

  setActiveFilePath(filePath);
  setActiveFileContent(fileContent);
  setActiveChunks(chunks);
  setDisplayMode('file');
  setBreadcrumbs(pathToBreadcrumbs(filePath));
};
```

**handleRelatedNoteClick** - 相关笔记点击 ⭐
```typescript
const handleRelatedNoteClick = async (filePath: string) => {
  const [fileContent, chunks] = await Promise.all([
    getFileContent(filePath),
    getFileChunks(filePath)
  ]);

  setActiveFilePath(filePath);
  setActiveFileContent(fileContent);
  setActiveChunks(chunks);
  setActiveChunk(null);
  setDisplayMode('file');
  setBreadcrumbs(pathToBreadcrumbs(filePath));

  window.scrollTo({ top: 0, behavior: 'smooth' });
};
```

**scrollToChunk** - 滚动到 Chunk ⭐
```typescript
const scrollToChunk = (chunkId: number) => {
  const anchor = document.getElementById(`chunk-${chunkId}`);
  if (anchor) {
    anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });

    const nextElement = anchor.nextElementSibling;
    if (nextElement) {
      // 清除旧高亮
      document.querySelectorAll('.highlight-chunk').forEach(el => {
        el.classList.remove('highlight-chunk');
      });

      // 添加新高亮
      nextElement.classList.add('highlight-chunk');
      setTimeout(() => {
        nextElement?.classList.remove('highlight-chunk');
      }, 2000);
    }
  }
};
```

#### 锚点生成算法 ⭐

**markdownWithAnchors** - 智能锚点插入
```typescript
const markdownWithAnchors = useMemo(() => {
  if (!activeFileContent || activeChunks.length === 0) return activeFileContent;

  const sortedChunks = [...activeChunks].sort((a, b) => a.ordinal - b.ordinal);
  const insertions: Array<{ position: number; anchor: string }> = [];

  for (const chunk of sortedChunks) {
    const chunkContent = chunk.content.trim();
    let position = -1;

    // 策略 1: 标题匹配
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

    // 策略 2: 内容前缀匹配
    if (position === -1 && chunkContent.length > 20) {
      const contentPreview = chunkContent.substring(0, Math.min(150, chunkContent.length));
      position = activeFileContent.indexOf(contentPreview);
    }

    // 策略 3: 首行匹配
    if (position === -1) {
      const firstLine = chunkContent.split('\n')[0].trim();
      if (firstLine.length > 10) {
        position = activeFileContent.indexOf(firstLine);
      }
    }

    if (position !== -1) {
      insertions.push({
        position,
        anchor: `<div id="chunk-${chunk.id}" class="chunk-anchor"></div>\n`
      });
    }
  }

  // 从后往前插入，避免位置偏移
  insertions.sort((a, b) => b.position - a.position);

  let result = activeFileContent;
  for (const insertion of insertions) {
    result = result.slice(0, insertion.position)
      + insertion.anchor
      + result.slice(insertion.position);
  }

  return result;
}, [activeFileContent, activeChunks]);
```

### 2. KnowledgeGraph.tsx - 知识图谱 ⭐

**位置**: `src/components/KnowledgeGraph.tsx`
**行数**: 290+ 行
**依赖**: ReactFlow

#### Props 接口

```typescript
interface KnowledgeGraphProps {
  filePath: string;         // 当前文件路径
  chunkId: number;          // 当前 chunk ID
  onNodeClick?: (filePath: string) => void;  // 节点点击回调
  onClose?: () => void;     // 关闭回调
}
```

#### 核心逻辑

**节点布局算法**:
```typescript
// 中心节点
const centralNode: GraphNode = {
  id: 'central',
  position: { x: 400, y: 300 },
  data: {
    label: extractFileName(filePath),
    filePath: filePath,
    isCentral: true,
  },
  style: {
    background: '#3b82f6', // 蓝色
    // ...
  },
};

// 周围节点（圆形分布）
const relatedNodes: GraphNode[] = relatedNotes.map((note, index) => {
  const angle = (2 * Math.PI * index) / relatedNotes.length;
  const radius = 250;
  const x = 400 + radius * Math.cos(angle);
  const y = 300 + radius * Math.sin(angle);

  const isSameTopic = note.reason === 'same_topic';
  const color = isSameTopic ? '#8b5cf6' : '#ec4899'; // 紫色/粉色

  return {
    id: `note-${index}`,
    position: { x, y },
    data: {
      label: extractFileName(note.file_path),
      filePath: note.file_path,
      isCentral: false,
      reason: note.reason,
      score: note.score,
    },
    style: { background: color, /* ... */ },
  };
});
```

**边配置**:
```typescript
const newEdges: Edge[] = relatedNotes.map((note, index) => {
  const isSameTopic = note.reason === 'same_topic';
  const edgeColor = isSameTopic ? '#8b5cf6' : '#ec4899';

  return {
    id: `edge-${index}`,
    source: 'central',
    target: `note-${index}`,
    type: 'smoothstep',
    animated: true,
    style: {
      stroke: edgeColor,
      strokeWidth: 2,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: edgeColor,
    },
    label: mode === 'embed' ? `${Math.round(note.score * 100)}%` : '',
    // ...
  };
});
```

### 3. ResizeHandle.tsx - 拖拽调整 ⭐

**位置**: `src/components/ResizeHandle.tsx`
**行数**: 60 行
**职责**: 提供面板间的拖拽调整功能

#### Props 接口

```typescript
interface ResizeHandleProps {
  onResize: (deltaX: number) => void;  // 增量变化回调
  className?: string;
}
```

#### 核心实现

**拖拽逻辑**:
```typescript
const handleMouseDown = (e: React.MouseEvent) => {
  e.preventDefault();
  setIsDragging(true);

  let lastX = e.clientX;

  const handleMouseMove = (moveEvent: MouseEvent) => {
    const deltaX = moveEvent.clientX - lastX;
    lastX = moveEvent.clientX;
    onResize(deltaX); // 增量更新
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  };

  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
};
```

**视觉反馈**:
```typescript
<div
  className={`group relative w-1 hover:w-1.5 transition-all cursor-col-resize ${
    isDragging ? "bg-blue-400" : "bg-zinc-800 hover:bg-zinc-700"
  }`}
  onMouseDown={handleMouseDown}
>
  <div className={`... ${
    isDragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"
  }`}>
    <GripVertical className={`w-4 h-4 ${
      isDragging ? "text-blue-400" : "text-zinc-600"
    }`} />
  </div>
</div>
```

### 4. RelatedNotes.tsx - 相关笔记 ⭐

**位置**: `src/components/RelatedNotes.tsx`
**行数**: 135 行
**职责**: 显示文件级别的相关推荐

#### Props 接口

```typescript
interface RelatedNotesProps {
  chunkId: number;                        // 当前 chunk ID
  onNoteClick?: (filePath: string) => void;  // 点击回调
}
```

#### 核心功能

**模式切换**:
```typescript
const [mode, setMode] = useState<'cluster' | 'embed'>('embed');

useEffect(() => {
  async function loadRelatedNotes() {
    const response = await getRelatedNotes(chunkId, mode, 5);
    setRelatedNotes(response.items);
  }
  loadRelatedNotes();
}, [chunkId, mode]);
```

**推荐原因标签**:
```typescript
const getReasonLabel = (reason: string) => {
  if (reason === 'same_topic') return 'Same Topic';
  if (reason === 'semantic_similarity') return 'Similar Content';
  return 'Related';
};

const getReasonColor = (reason: string) => {
  if (reason === 'same_topic')
    return 'text-blue-400 bg-blue-950/50 border-blue-800';
  if (reason === 'semantic_similarity')
    return 'text-purple-400 bg-purple-950/50 border-purple-800';
  return 'text-zinc-400 bg-zinc-900 border-zinc-800';
};
```

### 5. CommandPalette.tsx - 搜索面板

**位置**: `src/components/CommandPalette.tsx`
**行数**: 300+ 行
**职责**: 全局搜索和快捷导航

#### 核心特性

**双模式搜索**:
```typescript
const [searchMode, setSearchMode] = useState<'semantic' | 'keyword'>('semantic');

const handleSearch = useMemo(
  () => debounce(async (query: string) => {
    if (searchMode === 'semantic') {
      const suggestions = await suggestClusters(query, 10);
      // 处理语义搜索结果
    } else {
      const results = await searchChunks(query, 20);
      // 处理关键词搜索结果
    }
  }, 300),
  [searchMode]
);
```

**键盘导航**:
```typescript
const handleKeyDown = (e: React.KeyboardEvent) => {
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      setSelectedIndex((prev) =>
        Math.min(prev + 1, results.length - 1)
      );
      break;
    case 'ArrowUp':
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
      break;
    case 'Enter':
      e.preventDefault();
      handleSelectResult(results[selectedIndex]);
      break;
    case 'Escape':
      onClose();
      break;
  }
};
```

---

## 状态管理

### 状态提升原则

**规则**:
1. **本地状态优先**: 仅影响单个组件的状态放在组件内
2. **提升共享状态**: 多个组件需要的状态提升到最近的共同父组件
3. **避免 prop drilling**: 超过 3 层传递考虑使用 Context

**示例**:
```typescript
// ❌ 不好 - prop drilling
<Parent>
  <Child1 value={value} onChange={onChange} />
  <Child2>
    <GrandChild value={value} onChange={onChange} />
  </Child2>
</Parent>

// ✅ 好 - Context
const ValueContext = createContext();

<ValueContext.Provider value={{ value, onChange }}>
  <Parent>
    <Child1 />
    <Child2>
      <GrandChild />
    </Child2>
  </Parent>
</ValueContext.Provider>
```

### 异步状态模式

**加载状态管理**:
```typescript
const [data, setData] = useState<T | null>(null);
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState<Error | null>(null);

const fetchData = async () => {
  try {
    setIsLoading(true);
    setError(null);
    const result = await apiCall();
    setData(result);
  } catch (err) {
    setError(err);
  } finally {
    setIsLoading(false);
  }
};
```

### useMemo 和 useCallback 使用

**useMemo** - 缓存计算结果:
```typescript
const markdownWithAnchors = useMemo(() => {
  // 昂贵的计算
  return processMarkdown(activeFileContent, activeChunks);
}, [activeFileContent, activeChunks]); // 依赖变化时重新计算
```

**useCallback** - 缓存函数引用:
```typescript
const handleClick = useCallback((id: number) => {
  // 函数逻辑
}, []); // 空依赖 - 函数永不改变
```

---

## API 集成

### API 客户端设计

**位置**: `src/lib/api.ts`

**设计原则**:
1. **单一职责**: 每个函数只负责一个 API 调用
2. **类型安全**: 完整的 TypeScript 类型定义
3. **错误处理**: 统一的错误处理逻辑
4. **可测试**: 纯函数，易于 mock

**示例函数**:
```typescript
export async function getRelatedNotes(
  chunkId: number,
  mode: 'cluster' | 'embed' = 'embed',
  k: number = 5
): Promise<RelatedNotesResponse> {
  const response = await fetch(
    `${API_BASE}/chunks/${chunkId}/related-notes?mode=${mode}&k=${k}`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch related notes: ${response.statusText}`);
  }

  return response.json();
}
```

### 并行请求优化

**使用 Promise.all**:
```typescript
// ❌ 串行 - 慢
const fileContent = await getFileContent(filePath);
const chunks = await getFileChunks(filePath);

// ✅ 并行 - 快
const [fileContent, chunks] = await Promise.all([
  getFileContent(filePath),
  getFileChunks(filePath)
]);
```

### 错误处理模式

**组件级错误处理**:
```typescript
try {
  const data = await fetchData();
  setData(data);
} catch (error) {
  console.error("Failed to fetch:", error);
  // 可选：显示错误消息给用户
  setErrorMessage("加载失败，请重试");
}
```

---

## 样式系统

### Tailwind CSS 最佳实践

**类名组织**:
```typescript
// ❌ 不好 - 难以阅读
<div className="w-80 flex flex-col border-l border-zinc-800 bg-zinc-950 overflow-hidden">

// ✅ 好 - 分组和换行
<div className={`
  w-80 flex flex-col overflow-hidden
  border-l border-zinc-800
  bg-zinc-950
`}>

// ⭐ 最好 - 条件类名
<div className={`
  flex items-center gap-2 px-3 py-1.5 rounded-md
  text-xs font-medium transition-colors
  ${isActive
    ? 'bg-zinc-800 text-zinc-100'
    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
  }
`}>
```

### 动画和过渡

**CSS 动画** (`globals.css`):
```css
.highlight-chunk {
  animation: highlight-pulse 2s ease-out;
}

@keyframes highlight-pulse {
  0% { background-color: rgba(59, 130, 246, 0.2); }
  50% { background-color: rgba(59, 130, 246, 0.1); }
  100% { background-color: transparent; }
}
```

**Tailwind 过渡**:
```typescript
<div className="transition-all duration-200 hover:bg-zinc-800">
  // hover 时平滑过渡
</div>
```

### 响应式设计

**断点使用**:
```typescript
<div className={`
  grid grid-cols-1       /* 手机 */
  md:grid-cols-2         /* 平板 */
  lg:grid-cols-3         /* 桌面 */
  gap-4
`}>
```

---

## 性能优化

### React 性能优化

**1. 避免不必要的重渲染**:
```typescript
// 使用 React.memo
export const ExpensiveComponent = React.memo(({ data }) => {
  // 组件逻辑
}, (prevProps, nextProps) => {
  // 返回 true 表示 props 相同，跳过渲染
  return prevProps.data === nextProps.data;
});
```

**2. 虚拟化长列表**:
```typescript
// TODO: 实现虚拟滚动
// 使用 react-window 或 react-virtual
```

**3. 代码分割**:
```typescript
// 动态导入大组件
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <div>Loading...</div>,
  ssr: false
});
```

### 图片和资源优化

**Next.js Image 组件**:
```typescript
import Image from 'next/image';

<Image
  src="/logo.png"
  width={200}
  height={50}
  alt="Logo"
  priority // 首屏图片优先加载
/>
```

### Bundle 大小优化

**分析 bundle**:
```bash
npm run build
# 查看 .next/build-manifest.json
```

**动态导入**:
```typescript
// 仅在需要时加载
const ReactFlow = dynamic(() => import('reactflow'), {
  ssr: false
});
```

---

## 开发工作流

### 开发流程

```bash
# 1. 创建新分支
git checkout -b feature/your-feature

# 2. 开发
npm run dev

# 3. 测试
npm run lint
npm run build

# 4. 提交
git add .
git commit -m "feat: add new feature"

# 5. 推送和 PR
git push origin feature/your-feature
```

### 代码风格

**组件模板**:
```typescript
"use client"; // 客户端组件

import { useState, useEffect } from "react";
import { SomeIcon } from "lucide-react";

interface ComponentProps {
  // Props 类型定义
}

export function Component({ prop1, prop2 }: ComponentProps) {
  // Hooks
  const [state, setState] = useState();

  // Effects
  useEffect(() => {
    // 副作用逻辑
  }, [dependencies]);

  // Event handlers
  const handleClick = () => {
    // 处理逻辑
  };

  // Early returns
  if (loading) return <div>Loading...</div>;

  // Main render
  return (
    <div>
      {/* JSX */}
    </div>
  );
}
```

### Git Commit 规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
perf: 性能优化
test: 测试相关
chore: 构建/工具相关
```

---

## 常见模式

### 1. 模态框模式

```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Content */}
      <div className="relative z-10 bg-white rounded-lg p-6">
        {children}
      </div>
    </div>
  );
}
```

### 2. 加载状态模式

```typescript
{isLoading ? (
  <div className="flex items-center justify-center p-8">
    <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
  </div>
) : data ? (
  <DataView data={data} />
) : (
  <EmptyState />
)}
```

### 3. 错误边界模式

```typescript
class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <h1>Something went wrong.</h1>;
    }

    return this.props.children;
  }
}
```

---

## 调试技巧

### React DevTools

1. **组件树检查**: 查看组件层级和 props
2. **性能分析**: Profiler 标签分析渲染性能
3. **Hooks 检查**: 查看所有 hooks 的值

### Chrome DevTools

**网络请求调试**:
1. Network 标签查看所有 API 请求
2. 筛选 XHR/Fetch 查看数据请求
3. 检查请求/响应头和 body

**性能分析**:
1. Performance 标签录制交互
2. 查看 JavaScript 执行时间
3. 识别性能瓶颈

### 常用调试代码

```typescript
// 1. 条件断点
if (chunkId === 123) {
  debugger;
}

// 2. 日志分组
console.group('API Call');
console.log('Request:', params);
console.log('Response:', data);
console.groupEnd();

// 3. 性能测量
console.time('expensive-operation');
performExpensiveOperation();
console.timeEnd('expensive-operation');

// 4. 追踪渲染
useEffect(() => {
  console.log('Component rendered', { props });
});
```

---

## 贡献指南

### 添加新组件

1. **创建组件文件**: `src/components/NewComponent.tsx`
2. **定义 Props 接口**: 使用 TypeScript
3. **实现组件逻辑**: 遵循函数组件模式
4. **添加样式**: 使用 Tailwind CSS
5. **导出组件**: 使用命名导出
6. **更新文档**: 在此文件中记录

### 添加新 API 端点

1. **更新类型定义**: `src/lib/api.ts`
2. **实现 API 函数**: 遵循现有模式
3. **错误处理**: try-catch 和错误消息
4. **测试**: 手动测试或单元测试
5. **更新文档**: README 和此文件

### Code Review 清单

- [ ] TypeScript 类型完整
- [ ] 无 ESLint 错误
- [ ] 无 console.error/warn
- [ ] 代码格式化（Prettier）
- [ ] 组件可复用
- [ ] 性能考虑（memo/callback）
- [ ] 可访问性（a11y）
- [ ] 响应式设计
- [ ] 错误处理
- [ ] 文档更新

---

## 附录

### 有用的链接

- [Next.js 文档](https://nextjs.org/docs)
- [React 文档](https://react.dev)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [ReactFlow 文档](https://reactflow.dev)
- [TypeScript 手册](https://www.typescriptlang.org/docs)

### 常用命令

```bash
# 开发
npm run dev

# 构建
npm run build

# 生产运行
npm start

# Lint
npm run lint

# 类型检查
npx tsc --noEmit

# 清理缓存
rm -rf .next node_modules
npm install
```

---

**文档维护**: 请在添加新功能或修改架构时更新此文档。

**最后更新**: 2026-01-07
