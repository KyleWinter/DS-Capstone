# Intelligent Knowledge Base System

一个基于 AI 的智能知识库管理系统，支持 Markdown 笔记的智能检索、分类和关联推荐。

## 系统架构

### 后端架构 (Python + FastAPI)

```
track3-kb/
├── README.md
├── pyproject.toml              # 或 requirements.txt
├── .env.example                # OPENAI_API_KEY=...（可选）
├── .gitignore

├── data/
│   ├── notes/                  # Markdown 文件存放目录
│   ├── cache/
│   │   ├── chunks.jsonl        # 可选：中间产物（便于调试）
│   │   └── embeddings.npy      # 可选：向量缓存
│   └── kb.sqlite               # SQLite 数据库（FTS 索引、元数据、聚类结果）

├── src/
│   ├── kb/
│   │   ├── __init__.py
│   │   ├── config.py           # 路径、参数、开关（是否启用语义/LLM）
│   │   ├── logging.py
│   │   ├── types.py            # Note/Chunk/Cluster 数据结构
│   │
│   │   ├── ingest/
│   │   │   ├── loader.py        # 扫描文件、读取 md
│   │   │   ├── parser.py        # 解析 markdown（标题/段落）
│   │   │   └── chunker.py       # chunk 切分策略
│   │
│   │   ├── store/
│   │   │   ├── db.py            # SQLite 连接与迁移
│   │   │   ├── schema.sql       # 表结构（chunks、fts、embeddings、clusters）
│   │   │   └── repo.py          # 数据访问层（CRUD）
│   │
│   │   ├── search/
│   │   │   ├── lexical.py       # FTS 查询
│   │   │   ├── semantic.py      # embedding 相似度（rerank）
│   │   │   └── hybrid.py        # orchestrator：lexical → semantic
│   │
│   │   ├── embed/
│   │   │   ├── openai_embed.py  # 用 OpenAI key 的 embedding（可选）
│   │   │   └── local_embed.py   # 本地 embedding（备选）
│   │
│   │   ├── cluster/
│   │   │   ├── clusterer.py     # 聚类算法（离线）
│   │   │   ├── labeler.py       # cluster 命名/摘要（LLM 或关键词）
│   │   │   └── graph.py         # kNN / 相似度图（可选）
│   │
│   │   ├── suggest/
│   │   │   └── recommender.py   # 同簇/近邻推荐、相关簇建议
│   │
│   │   └── api/
│   │       ├── app.py           # FastAPI 应用入口
│   │       ├── routes.py        # API 路由
│   │       └── schemas.py       # Pydantic 数据模型

├── scripts/
│   ├── build_index.py           # 1) ingest + 2) 写入 DB + 3) 建 FTS
│   ├── build_embeddings.py      # 批量 embedding（可选）
│   ├── build_clusters.py        # 离线聚类 + label（可选）
│   └── demo_cli.py              # 命令行 demo：search/open/recommend

├── tests/
│   ├── test_chunker.py
│   ├── test_fts.py
│   └── test_hybrid.py

└── docs/
    ├── architecture.md          # 报告用：架构说明
    ├── demo.md                  # 演示脚本：输入什么、看到什么
    └── dataset.md               # 数据描述：notes 来源、规模、统计
```

### 前端架构 (Next.js + React)

```
frontend/
├── package.json
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json

├── src/
│   ├── app/
│   │   ├── layout.tsx           # 根布局
│   │   ├── page.tsx             # 主仪表板页面
│   │   └── globals.css          # 全局样式和动画
│   │
│   ├── components/
│   │   ├── FileTree.tsx         # 集群树组件
│   │   ├── FileDirectoryTree.tsx # 文件目录树组件
│   │   ├── CommandPalette.tsx   # 搜索命令面板
│   │   ├── SuggestionPanel.tsx  # AI 建议面板（chunk级别）
│   │   ├── RelatedNotes.tsx     # 相关文件推荐（文件级别）
│   │   ├── KnowledgeGraph.tsx   # 知识关联图谱
│   │   └── ResizeHandle.tsx     # 可调整大小的拖拽条
│   │
│   └── lib/
│       ├── api.ts               # 后端 API 客户端
│       ├── utils.ts             # 工具函数
│       └── mockData.ts          # 模拟数据

└── public/                      # 静态资源
```

## 核心功能

### 后端功能

1. **文档处理与索引**
   - Markdown 文件自动解析和分块（chunking）
   - 全文搜索索引（FTS）
   - 向量化嵌入（Embeddings）

2. **智能检索**
   - 词法检索（FTS）
   - 语义检索（Embedding-based）
   - 混合检索（Hybrid）

3. **主题聚类**
   - 基于聚类的主题分组
   - LLM 自动生成主题标签和摘要

4. **智能推荐**
   - Chunk 级别相关推荐
   - Note 级别相关推荐
   - 支持两种模式：主题相关 / 语义相似

### 前端功能

1. **多视图展示**
   - 集群视图：按主题聚类浏览
   - 文件树视图：按文件结构浏览
   - 单块模式：查看单个 chunk
   - 文件模式：查看完整文件

2. **Markdown 渲染**
   - 支持 GitHub Flavored Markdown (GFM)
   - 代码高亮
   - 响应式布局
   - 深色主题优化

3. **智能搜索**
   - 命令面板（Cmd/Ctrl + K）
   - 语义搜索（主题建议）
   - 关键词搜索（全文检索）

4. **关联推荐**
   - **AI Suggestions Panel**：显示相关 chunk
   - **Related Notes**：页面底部显示相关文件
   - 支持两种推荐模式切换：
     - Topic-based（主题相关）
     - Similarity-based（语义相似）

5. **知识关联图谱** ⭐ NEW
   - 可视化展示笔记间的关联关系
   - 交互式节点导航
   - 支持拖拽、缩放、平移
   - 小地图导航
   - 全屏模式

6. **可调整布局** ⭐ NEW
   - 左侧边栏可调整宽度（200px - 500px）
   - 右侧边栏可调整宽度（250px - 600px）
   - 拖拽式调整，实时预览
   - 优雅的视觉反馈

7. **交互导航**
   - 点击相关笔记自动跳转
   - 平滑滚动到目标 chunk
   - 高亮动画提示
   - 面包屑导航

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite (FTS5)
- **向量化**: OpenAI Embeddings / Sentence Transformers
- **聚类**: scikit-learn
- **其他**: Python 3.10+

### 前端
- **框架**: Next.js 14 (React 18)
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **Markdown**: react-markdown, remark-gfm, rehype-raw
- **图谱**: ReactFlow
- **图标**: lucide-react

## 快速开始

### 后端设置

1. **安装依赖**
```bash
pip install uvicorn fastapi
pip install sentence-transformers torch
# 可选：OpenAI Embeddings
pip install openai
```

2. **构建索引**
```bash
# 建立基础索引
python scripts/build_index.py

# 生成向量嵌入（可选）
python scripts/build_embeddings.py

# 生成主题聚类（可选）
python scripts/build_clusters.py

# 验证数据库
python scripts/verify_db.py
```

3. **启动后端服务**
```bash
uvicorn src.kb.api.app:app --reload --port 8000
```

API 文档: http://localhost:8000/docs

### 前端设置

1. **安装依赖**
```bash
cd frontend
npm install
```

2. **配置环境变量**
```bash
# 创建 .env.local 文件
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

3. **启动开发服务器**
```bash
npm run dev
```

应用访问: http://localhost:3000

4. **生产构建**
```bash
npm run build
npm start
```

## API 端点

### 搜索相关
- `GET /api/search` - 全文搜索
- `GET /api/clusters/suggest` - 语义搜索（主题建议）

### 内容获取
- `GET /api/chunks/{chunk_id}` - 获取单个 chunk
- `GET /api/files/chunks?file_path=xxx` - 获取文件所有 chunks
- `GET /api/files/content?file_path=xxx` - 获取原始文件内容
- `GET /api/files/tree` - 获取文件树结构

### 推荐相关
- `GET /api/chunks/{chunk_id}/related` - 获取相关 chunks
- `GET /api/chunks/{chunk_id}/related-notes` - 获取相关笔记（文件级别）

### 聚类相关
- `GET /api/clusters` - 列出所有主题聚类
- `GET /api/clusters/{cluster_id}` - 获取聚类详情

## 使用示例

### 命令行搜索
```bash
python ./scripts/demo_cli.py search "解题"
```

### API 调用示例
```bash
# 搜索
curl "http://localhost:8000/api/search?q=算法&limit=10"

# 获取相关笔记
curl "http://localhost:8000/api/chunks/123/related-notes?mode=embed&k=5"

# 获取文件内容
curl "http://localhost:8000/api/files/content?file_path=notes/example.md"
```

## 测试

```bash
# 安装测试依赖
pip install -U pytest

# 运行测试
pytest -q
```

## 开发指南

详细的开发进度和任务追踪请查看 `DEVELOPMENT.md` 文件。

## 主要特性亮点

1. **零配置开箱即用** - 自动扫描和索引 Markdown 文件
2. **多模态检索** - 支持关键词、语义、主题多种检索方式
3. **智能推荐** - 基于内容相似度和主题关联的推荐
4. **可视化图谱** - 直观展示知识关联关系
5. **灵活布局** - 可自定义的三栏布局
6. **现代化 UI** - 深色主题、流畅动画、响应式设计

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
