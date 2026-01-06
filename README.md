项目架构：
track3-kb/
├── README.md
├── pyproject.toml              # 或 requirements.txt
├── .env.example                # OPENAI_API_KEY=...（可选）
├── .gitignore

├── data/
│   ├── notes/                  # 你的一堆 md 文件放这里（或配置外部路径）
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

│   │   ├── ingest/
│   │   │   ├── loader.py        # 扫描文件、读取 md
│   │   │   ├── parser.py        # 解析 markdown（标题/段落）
│   │   │   └── chunker.py       # chunk 切分策略

│   │   ├── store/
│   │   │   ├── db.py            # SQLite 连接与迁移
│   │   │   ├── schema.sql       # 表结构（chunks、fts、embeddings、clusters）
│   │   │   └── repo.py          # 数据访问层（CRUD）

│   │   ├── search/
│   │   │   ├── lexical.py       # FTS 查询
│   │   │   ├── semantic.py      # embedding 相似度（rerank）
│   │   │   └── hybrid.py        # orchestrator：lexical → semantic

│   │   ├── embed/
│   │   │   ├── openai_embed.py  # 用 OpenAI key 的 embedding（可选）
│   │   │   └── local_embed.py   # 本地 embedding（备选）

│   │   ├── cluster/
│   │   │   ├── clusterer.py     # 聚类算法（离线）
│   │   │   ├── labeler.py       # cluster 命名/摘要（LLM 或关键词）
│   │   │   └── graph.py         # kNN / 相似度图（可选）

│   │   ├── suggest/
│   │   │   └── recommender.py   # 同簇/近邻推荐、相关簇建议

│   │   └── api/
│   │       ├── app.py           # FastAPI（可选）
│   │       └── routes.py

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

python ./scripts/demo_cli.py search "解题"
python ./scripts/verify_db.py


pip install -U pytest
pytest -q

pip install -U openai
python scripts/build_embeddings.py --batch 64

To start：
pip install uvicorn fastapi
uvicorn src.kb.api.app:app --reload --port 8000
