# 开发进度文档

**最后更新时间**: 2026-01-07

本文档记录了智能知识库系统的详细开发进度、技术实现和待办任务，供下次开发时参考。

---

## 📋 目录

1. [项目概述](#项目概述)
2. [已完成功能](#已完成功能)
3. [技术实现细节](#技术实现细节)
4. [文件结构和关键代码](#文件结构和关键代码)
5. [待开发功能](#待开发功能)
6. [已知问题](#已知问题)
7. [开发环境](#开发环境)
8. [快速启动指南](#快速启动指南)

---

## 项目概述

**项目名称**: Intelligent Knowledge Base System

**项目类型**: NTU SC6117 Capstone Project - Track 3 (Knowledge Base)

**技术架构**:
- 前端: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- 后端: Python 3.10+ + FastAPI + SQLite
- 向量检索: Sentence Transformers / OpenAI Embeddings

**主要功能**:
基于 AI 的智能知识库管理系统，支持 Markdown 笔记的智能检索、分类、关联推荐和可视化展示。

---

## 已完成功能

### ✅ 后端功能 (已完成)

#### 1. 文档处理与索引
- [x] Markdown 文件扫描和加载 (`src/kb/ingest/loader.py`)
- [x] Markdown 解析（标题、段落识别）(`src/kb/ingest/parser.py`)
- [x] 智能分块（Chunking）策略 (`src/kb/ingest/chunker.py`)
- [x] SQLite 数据库存储 (`src/kb/store/db.py`, `schema.sql`)
- [x] 全文搜索索引（FTS5）

#### 2. 智能检索
- [x] 词法检索（FTS）(`src/kb/search/lexical.py`)
- [x] 语义检索（Embedding-based）(`src/kb/search/semantic.py`)
- [x] 向量嵌入生成（本地 + OpenAI）(`src/kb/embed/`)

#### 3. 主题聚类
- [x] 聚类算法实现 (`src/kb/cluster/clusterer.py`)
- [x] 主题标签生成 (`src/kb/cluster/labeler.py`)

#### 4. 智能推荐
- [x] Chunk 级别推荐 (`src/kb/suggest/recommender.py`)
  - 基于主题聚类（cluster-based）
  - 基于语义相似度（embedding-based）
- [x] Note 级别推荐（文件级别聚合）
  - 支持两种模式切换

#### 5. RESTful API (`src/kb/api/routes.py`)
- [x] 搜索端点
  - `GET /api/search` - 全文搜索
  - `GET /api/clusters/suggest` - 语义搜索
- [x] 内容获取端点
  - `GET /api/chunks/{chunk_id}` - 获取单个 chunk
  - `GET /api/files/chunks?file_path=xxx` - 获取文件所有 chunks
  - `GET /api/files/content?file_path=xxx` - 获取原始文件内容
  - `GET /api/files/tree` - 获取文件树结构
- [x] 推荐端点
  - `GET /api/chunks/{chunk_id}/related` - 相关 chunks
  - `GET /api/chunks/{chunk_id}/related-notes` - 相关笔记
- [x] 聚类端点
  - `GET /api/clusters` - 列出所有聚类
  - `GET /api/clusters/{cluster_id}` - 聚类详情

### ✅ 前端功能 (已完成)

#### 1. 基础架构
- [x] Next.js 14 项目初始化
- [x] TypeScript 配置
- [x] Tailwind CSS 配置和主题定制
- [x] 深色主题 UI 设计

#### 2. 页面布局 (`frontend/src/app/page.tsx`)
- [x] 三栏响应式布局
  - 左侧边栏（集群/文件树）
  - 中间内容区（Markdown 渲染）
  - 右侧边栏（AI 建议/知识图谱）
- [x] 顶部导航栏
  - 搜索按钮
  - 右侧边栏切换按钮
- [x] 面包屑导航
- [x] **可调整大小的面板** ⭐ NEW (2026-01-07)
  - 左侧边栏宽度可调（200px - 500px）
  - 右侧边栏宽度可调（250px - 600px）
  - 拖拽式调整，实时预览

#### 3. 文件浏览组件
- [x] **FileTree** (`frontend/src/components/FileTree.tsx`)
  - 集群树状视图
  - 懒加载集群成员
  - 展开/收起动画
- [x] **FileDirectoryTree** (`frontend/src/components/FileDirectoryTree.tsx`)
  - 文件系统树状视图
  - 目录/文件图标区分
  - 递归渲染子目录

#### 4. Markdown 渲染
- [x] **react-markdown** 集成
- [x] **remark-gfm** 支持（GitHub Flavored Markdown）
- [x] **rehype-raw** 支持（HTML 渲染）
- [x] 自定义样式组件
  - 标题（h1-h6）
  - 代码块（inline/block）
  - 列表（ul/ol）
  - 引用块（blockquote）
  - 链接（a）
- [x] 两种展示模式
  - **Single Mode**: 单个 chunk 展示
  - **File Mode**: 完整文件展示

#### 5. 搜索功能
- [x] **CommandPalette** (`frontend/src/components/CommandPalette.tsx`)
  - 快捷键支持（Cmd/Ctrl + K）
  - 两种搜索模式切换
    - Semantic Search（语义搜索，主题建议）
    - Keyword Search（关键词搜索，全文检索）
  - 实时搜索（防抖优化）
  - 键盘导航（↑↓ Enter Escape）

#### 6. 关联推荐功能
- [x] **SuggestionPanel** (`frontend/src/components/SuggestionPanel.tsx`)
  - Chunk 级别推荐
  - 显示匹配分数和预览
  - 支持模式切换（cluster/embed）
  - 点击跳转到对应 chunk
- [x] **RelatedNotes** (`frontend/src/components/RelatedNotes.tsx`)
  - Note 级别推荐（文件级别）
  - 显示在文件展示页面底部
  - 显示推荐原因（Same Topic / Similar Content）
  - 显示匹配分数和章节数
  - **点击跳转到对应笔记** ⭐ (2026-01-07)
    - 自动加载目标文件内容
    - 平滑滚动到页面顶部
    - 更新面包屑导航

#### 7. 知识图谱可视化 ⭐ NEW (2026-01-07)
- [x] **KnowledgeGraph** (`frontend/src/components/KnowledgeGraph.tsx`)
  - 使用 **ReactFlow** 库实现
  - 功能特性：
    - 以当前笔记为中心的放射状布局
    - 节点颜色区分（当前/同主题/相似内容）
    - 动画连接线显示关联关系
    - 显示相似度分数
    - 交互功能：
      - 点击节点跳转到对应笔记
      - 拖拽平移视图
      - 滚轮缩放
      - 小地图导航
      - 控制面板（放大/缩小/适应视图）
    - 支持全屏模式
    - 支持模式切换（Topic-based / Similarity-based）
  - UI 组件：
    - 图例面板（说明节点含义）
    - 模式切换按钮
    - 全屏切换按钮

#### 8. 交互导航功能 ⭐ (2026-01-07)
- [x] **Chunk 内跳转**
  - 点击 SuggestionPanel 的推荐 chunk
  - 在文件模式下平滑滚动到对应位置
  - 高亮动画提示（2秒蓝色脉冲）
  - **智能锚点插入**：
    - 策略1: 通过标题匹配定位
    - 策略2: 通过内容前缀匹配
    - 策略3: 通过首行匹配
- [x] **文件间跳转**
  - 点击 RelatedNotes 的推荐文件
  - 自动加载完整文件内容
  - 更新面包屑和状态
  - 平滑滚动到顶部

#### 9. UI 组件库
- [x] **ResizeHandle** (`frontend/src/components/ResizeHandle.tsx`) ⭐ NEW
  - 可拖拽分隔条
  - 视觉反馈（悬停/拖拽状态）
  - 边界限制保护
  - 平滑的拖拽体验

#### 10. API 客户端
- [x] **api.ts** (`frontend/src/lib/api.ts`)
  - 完整的类型定义（TypeScript）
  - 所有后端 API 的封装函数
  - 错误处理

#### 11. 工具函数
- [x] **utils.ts** (`frontend/src/lib/utils.ts`)
  - 集群树构建（buildClusterTree）
  - Chunk 转树节点（chunksToTreeNodes）
  - 路径转面包屑（pathToBreadcrumbs）

---

## 技术实现细节

### 前端关键技术点

#### 1. 可调整大小的面板实现

**文件**: `frontend/src/components/ResizeHandle.tsx`

**核心逻辑**:
```typescript
// 使用原生拖拽实现，无需第三方库
const handleMouseDown = (e: React.MouseEvent) => {
  let lastX = e.clientX;

  const handleMouseMove = (moveEvent: MouseEvent) => {
    const deltaX = moveEvent.clientX - lastX;
    lastX = moveEvent.clientX;
    onResize(deltaX); // 增量更新
  };

  // 添加全局事件监听
  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);
};
```

**集成方式** (`page.tsx`):
```typescript
// 状态管理
const [leftSidebarWidth, setLeftSidebarWidth] = useState(288);
const [rightSidebarWidth, setRightSidebarWidth] = useState(320);

// 调整处理
const handleLeftSidebarResize = (deltaX: number) => {
  setLeftSidebarWidth((prev) => Math.min(Math.max(prev + deltaX, 200), 500));
};

// 应用到布局
<aside style={{ width: `${leftSidebarWidth}px` }}>
```

#### 2. 知识图谱布局算法

**文件**: `frontend/src/components/KnowledgeGraph.tsx`

**放射状布局**:
```typescript
// 中心节点
const centralNode = {
  id: 'central',
  position: { x: 400, y: 300 }
};

// 周围节点呈圆形分布
relatedNodes.map((note, index) => {
  const angle = (2 * Math.PI * index) / relatedNotes.length;
  const radius = 250;
  return {
    id: `note-${index}`,
    position: {
      x: 400 + radius * Math.cos(angle),
      y: 300 + radius * Math.sin(angle)
    }
  };
});
```

#### 3. Chunk 锚点定位算法

**文件**: `frontend/src/app/page.tsx:232-277`

**三策略匹配**:
1. **标题匹配**: 尝试匹配 `# heading` 到 `###### heading`
2. **内容前缀匹配**: 匹配 chunk 内容的前 150 字符
3. **首行匹配**: 匹配 chunk 的第一行（长度>10）

**插入顺序**: 从后往前插入，避免位置偏移

```typescript
// 从后往前排序
insertions.sort((a, b) => b.position - a.position);

// 依次插入锚点
for (const insertion of insertions) {
  result = result.slice(0, insertion.position)
    + insertion.anchor
    + result.slice(insertion.position);
}
```

#### 4. 右侧边栏标签切换

**文件**: `frontend/src/app/page.tsx:532-586`

**状态管理**:
```typescript
const [rightPanelMode, setRightPanelMode] = useState<'suggestions' | 'graph'>('suggestions');

// 条件渲染
{rightPanelMode === 'suggestions' ? (
  <SuggestionPanel ... />
) : (
  <KnowledgeGraph ... />
)}
```

### 后端关键技术点

#### 1. Note 级别推荐聚合

**文件**: `src/kb/api/routes.py:350-413`

**聚合逻辑**:
1. 获取 chunk 级别推荐（k=50）
2. 按 `file_path` 分组
3. 计算每个文件的最高分数
4. 记录匹配的 chunk 数量
5. 排序并截取 top-k

```python
# 按文件分组
by_file: dict[str, list] = {}
for item in chunk_items:
    by_file.setdefault(item.file_path, []).append(item)

# 聚合分数
for file_path, items in by_file.items():
    score = max(float(it.score) for it in items if it.score)
    notes.append(RelatedNoteOut(
        file_path=file_path,
        score=score,
        matched_chunks=len(items),
        top_chunk_ids=[it.chunk_id for it in items[:5]]
    ))
```

#### 2. 文件树构建

**文件**: `src/kb/api/routes.py:416-502`

**递归构建**:
```python
# 分割路径并递归构建
for file_path in all_files:
    parts = file_path.split("/")
    current = root
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        if is_last:
            # 叶子节点（文件）
            current["children"][part] = {"type": "file", ...}
        else:
            # 中间节点（目录）
            if part not in current["children"]:
                current["children"][part] = {"type": "directory", ...}
            current = current["children"][part]
```

---

## 文件结构和关键代码

### 前端关键文件

```
frontend/src/
├── app/
│   ├── page.tsx                   # 🔥 主页面（980+ 行）
│   │   ├── 状态管理（面板宽度、显示模式等）
│   │   ├── 数据加载（集群、文件树）
│   │   ├── 事件处理（跳转、滚动、调整大小）
│   │   ├── Markdown 锚点生成
│   │   └── 三栏布局渲染
│   ├── layout.tsx                 # 根布局
│   └── globals.css                # 全局样式（高亮动画等）
│
├── components/
│   ├── FileTree.tsx               # 集群树组件（200+ 行）
│   ├── FileDirectoryTree.tsx      # 文件树组件（150+ 行）
│   ├── CommandPalette.tsx         # 搜索面板（300+ 行）
│   ├── SuggestionPanel.tsx        # AI 建议面板（115 行）
│   ├── RelatedNotes.tsx           # 相关笔记推荐（135 行）⭐
│   ├── KnowledgeGraph.tsx         # 🔥 知识图谱（290+ 行）⭐ NEW
│   └── ResizeHandle.tsx           # 🔥 拖拽调整组件（60 行）⭐ NEW
│
└── lib/
    ├── api.ts                      # 🔥 API 客户端（225 行）
    │   ├── 所有接口函数
    │   ├── TypeScript 类型定义
    │   └── 错误处理
    ├── utils.ts                    # 工具函数（60 行）
    └── mockData.ts                 # 模拟数据（测试用）
```

### 后端关键文件

```
src/kb/
├── api/
│   ├── app.py                      # FastAPI 应用入口
│   ├── routes.py                   # 🔥 API 路由（555 行）
│   │   ├── 搜索端点
│   │   ├── Chunk/File 获取端点
│   │   ├── 推荐端点（chunk & note 级别）⭐
│   │   ├── 聚类端点
│   │   └── 文件树端点
│   └── schemas.py                  # Pydantic 模型
│
├── ingest/
│   ├── loader.py                   # 文件加载
│   ├── parser.py                   # Markdown 解析
│   └── chunker.py                  # 分块策略
│
├── store/
│   ├── db.py                       # 数据库连接
│   ├── schema.sql                  # 表结构定义
│   └── repo.py                     # 数据访问层
│
├── search/
│   ├── lexical.py                  # FTS 搜索
│   ├── semantic.py                 # 语义搜索
│   └── hybrid.py                   # 混合搜索
│
├── cluster/
│   ├── clusterer.py                # 聚类算法
│   ├── labeler.py                  # 主题标签生成
│   └── graph.py                    # 关系图
│
└── suggest/
    └── recommender.py              # 🔥 推荐引擎
        ├── related_by_cluster()     # 基于聚类推荐
        └── related_by_embedding()   # 基于向量推荐
```

### 关键配置文件

```
frontend/
├── package.json                    # 依赖管理
│   └── 新增: reactflow (图谱库)
├── tailwind.config.ts              # Tailwind 配置
├── tsconfig.json                   # TypeScript 配置
└── next.config.mjs                 # Next.js 配置
```

---

## 待开发功能

### 🔜 高优先级

1. **用户偏好持久化**
   - [ ] 保存面板宽度设置到 localStorage
   - [ ] 保存推荐模式偏好
   - [ ] 保存视图模式偏好（cluster/files）

2. **性能优化**
   - [ ] 实现虚拟滚动（长文档）
   - [ ] 图谱节点懒加载（大规模网络）
   - [ ] Chunk 内容缓存

3. **搜索增强**
   - [ ] 搜索历史记录
   - [ ] 搜索结果高亮
   - [ ] 高级过滤选项（日期、标签等）

4. **导出功能**
   - [ ] 导出笔记为 PDF
   - [ ] 导出知识图谱为图片
   - [ ] 导出搜索结果

### 🔮 中优先级

5. **多文档比较**
   - [ ] 并排查看两个笔记
   - [ ] 差异对比视图

6. **标签系统**
   - [ ] 自定义标签
   - [ ] 标签自动建议
   - [ ] 按标签过滤

7. **笔记编辑**
   - [ ] 在线编辑 Markdown
   - [ ] 实时预览
   - [ ] 自动保存

8. **协作功能**
   - [ ] 多用户支持
   - [ ] 笔记分享
   - [ ] 评论系统

### 💡 低优先级

9. **高级可视化**
   - [ ] 时间线视图
   - [ ] 热力图（笔记活跃度）
   - [ ] 3D 知识图谱

10. **AI 增强**
    - [ ] 自动摘要生成
    - [ ] 智能问答（基于笔记内容）
    - [ ] 写作建议

11. **移动端适配**
    - [ ] 响应式优化（小屏幕）
    - [ ] 触摸手势支持
    - [ ] PWA 支持

---

## 已知问题

### 🐛 Bug

1. **ESLint 警告**
   - 位置: `frontend/src/components/CommandPalette.tsx:64`
   - 内容: `useEffect` 缺少依赖 `handleSelectResult`
   - 影响: 无（仅警告）
   - 修复计划: 重构 useEffect 或添加 useCallback

2. **锚点定位准确性**
   - 场景: 某些格式特殊的 markdown 文件
   - 问题: 锚点可能定位不准确
   - 影响: 跳转位置偏差
   - 修复计划: 改进匹配算法

### ⚠️ 限制

1. **大文件性能**
   - 超大文件（>10MB）渲染可能卡顿
   - 建议: 实现虚拟滚动

2. **图谱节点数量**
   - 节点过多（>50）时性能下降
   - 建议: 添加节点数量限制或分页

3. **浏览器兼容性**
   - 仅测试 Chrome/Edge（现代浏览器）
   - Safari/Firefox 未充分测试

---

## 开发环境

### 系统要求

- **操作系统**: macOS / Linux / Windows (WSL2)
- **Node.js**: 18.x 或更高
- **Python**: 3.10 或更高
- **浏览器**: Chrome 90+ / Edge 90+ / Firefox 88+

### 开发工具

- **IDE**: VS Code (推荐)
- **VS Code 扩展**:
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense
  - Python
  - Pylance

### 环境变量

#### 前端 (`frontend/.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

#### 后端 (`.env`)
```bash
# 可选：OpenAI API Key
OPENAI_API_KEY=sk-...

# 数据库路径
DB_PATH=data/kb.sqlite

# 笔记目录
NOTES_DIR=data/notes
```

---

## 快速启动指南

### 完整启动流程

#### 1. 后端启动

```bash
# 1. 安装依赖
pip install uvicorn fastapi
pip install sentence-transformers torch
pip install openai  # 可选

# 2. 构建索引（首次运行或笔记更新后）
python scripts/build_index.py           # 必需
python scripts/build_embeddings.py      # 可选
python scripts/build_clusters.py        # 可选

# 3. 验证数据库
python scripts/verify_db.py

# 4. 启动后端服务
uvicorn src.kb.api.app:app --reload --port 8000

# 访问 API 文档: http://localhost:8000/docs
```

#### 2. 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖（首次运行）
npm install

# 3. 启动开发服务器
npm run dev

# 访问应用: http://localhost:3000
```

### 开发调试技巧

#### 前端调试

1. **开启 React DevTools**
   - Chrome 扩展: React Developer Tools

2. **查看网络请求**
   - Chrome DevTools > Network
   - 筛选 XHR/Fetch 查看 API 调用

3. **控制台调试**
   - 关键日志已添加 `console.log`/`console.warn`
   - 搜索 "Failed to" 可快速定位错误

#### 后端调试

1. **查看 API 文档**
   - http://localhost:8000/docs
   - 可直接测试 API

2. **数据库查询**
   ```bash
   sqlite3 data/kb.sqlite
   # .tables - 查看所有表
   # .schema chunks - 查看表结构
   # SELECT * FROM chunks LIMIT 5;
   ```

3. **日志输出**
   - FastAPI 自动记录请求日志
   - 添加 `print()` 调试

---

## 最近更新日志

### 2026-01-07 - 重大更新

#### 新增功能
1. ✅ **知识关联图谱可视化**
   - 使用 ReactFlow 实现
   - 支持交互式导航
   - 全屏模式
   - 两种推荐模式

2. ✅ **可调整大小的面板**
   - 左右侧边栏宽度可调
   - 拖拽式交互
   - 边界限制保护

3. ✅ **点击跳转功能完善**
   - 相关笔记点击跳转
   - Chunk 精确定位
   - 平滑滚动和高亮

#### 技术改进
1. 📦 安装 `reactflow` 库
2. 🔧 创建 `ResizeHandle` 组件
3. 🔧 创建 `KnowledgeGraph` 组件
4. 🎨 优化锚点插入算法（三策略匹配）
5. 📝 更新 README 和开发文档

#### 文件变更
- 新增: `frontend/src/components/KnowledgeGraph.tsx`
- 新增: `frontend/src/components/ResizeHandle.tsx`
- 修改: `frontend/src/app/page.tsx` (添加图谱集成和调整大小)
- 更新: `frontend/package.json` (添加 reactflow)
- 更新: `README.md`
- 新增: `DEVELOPMENT.md`

---

## 下一步开发建议

1. **立即改进**（下次开发时优先）
   - 修复 CommandPalette 的 ESLint 警告
   - 添加面板宽度持久化（localStorage）
   - 实现搜索结果高亮

2. **短期目标**（1-2 周）
   - 实现虚拟滚动优化大文件
   - 添加导出功能（PDF/图片）
   - 完善移动端适配

3. **长期规划**（1 个月+）
   - 在线编辑功能
   - 多用户协作
   - AI 增强功能

---

## 技术债务追踪

1. **代码重构**
   - [ ] page.tsx 过长（980+ 行），考虑拆分
   - [ ] 提取公共 hooks（useResizable, useMarkdown 等）
   - [ ] 统一错误处理机制

2. **类型安全**
   - [ ] 完善所有组件的 TypeScript 类型
   - [ ] 添加 API 响应的运行时验证（zod）

3. **测试覆盖**
   - [ ] 添加前端单元测试（Jest + React Testing Library）
   - [ ] 添加 E2E 测试（Playwright）
   - [ ] 提高后端测试覆盖率

---

## 联系和协作

**项目仓库**: (添加你的 GitHub 仓库链接)

**问题反馈**: (添加 Issue 链接)

**贡献指南**: 欢迎提交 Pull Request！

---

**文档维护**: 请在每次重大更新后同步更新此文档。
