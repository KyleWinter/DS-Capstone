# Search Interface Update

## 更新内容

### 简化搜索模式
- **移除**: 移除了搜索模式选择标签（Hybrid、Lexical、Semantic）
- **统一**: 所有搜索统一使用 **Hybrid 模式**（FTS5 + AI 语义重排序）
- **优势**: 提供最佳的速度和准确性平衡

### 智能搜索结果分类
系统会根据评分阈值自动判断匹配类型，在搜索结果中显示：

- **⚡ Hybrid** (蓝色): 同时满足词法和语义强匹配
  - Lexical Score > -8.0 **AND** Semantic Score > 0.25
  - 关键词精确匹配 + AI 语义理解
  - 最高质量的匹配结果

- **# Keyword** (琥珀色): 主要为词法匹配
  - Lexical Score > -8.0 BUT Semantic Score ≤ 0.25
  - 纯关键词/FTS5 匹配
  - 精确的文本匹配

- **⚡ Semantic** (紫色): 主要为语义匹配
  - Lexical Score ≤ -8.0 BUT Semantic Score > 0.25
  - 基于 AI 语义相似度
  - 理解查询意图，即使关键词不同

## 评分系统

每个搜索结果包含以下评分：

- **score**: 综合评分 (0-1) - 显示给用户的主要分数
- **lexical_score**: 词法评分（负对数）- 内部判断用
  - 数值越大越好（越接近 0 越好）
  - 阈值: > -8.0 表示强匹配
- **semantic_score**: 语义评分 (0-1) - 内部判断用
  - 数值越高越好
  - 阈值: > 0.25 表示强匹配

### 分类阈值
```typescript
const LEXICAL_THRESHOLD = -8.0;   // 词法强匹配阈值
const SEMANTIC_THRESHOLD = 0.25;  // 语义强匹配阈值
```

### 分类逻辑
```typescript
if (lexical_score > -8.0 && semantic_score > 0.25) {
  type = "Hybrid"      // 🔵 两者都强
} else if (semantic_score > 0.25) {
  type = "Semantic"    // 🟣 语义理解强
} else {
  type = "Keyword"     // 🟡 关键词匹配
}
```

## 技术实现

### 后端 (Python)
- **API**: `/api/search?q={query}&mode=hybrid&limit={n}`
- **默认参数**:
  - `mode`: `hybrid`
  - `fts_k`: `200` (FTS 候选数量)
  - `limit`: `10` (返回结果数)

### 前端 (TypeScript/React)
- **组件**: `CommandPalette.tsx`
- **快捷键**: `⌘K` / `Ctrl+K`
- **功能**:
  - 实时搜索（300ms 防抖）
  - 键盘导航
  - 匹配类型可视化

## 使用示例

### 搜索 "链表"
```
Mode: hybrid
Results: 2

1. 🔵 Hybrid
   CSMA/CD 协议
   Overall: 0.40 | Lexical: -7.83 | Semantic: 0.25
   Strong Lexical: True | Strong Semantic: True
   File: 计算机网络 - 链路层.md

2. 🟡 Keyword
   文件属性
   Overall: 0.17 | Lexical: -6.54 | Semantic: 0.22
   Strong Lexical: True | Strong Semantic: False
   File: Linux.md
```

### 搜索 "transformer"
```
Mode: hybrid
Results: 2

1. 🟣 Semantic
   JDK
   Overall: 0.47 | Lexical: -9.16 | Semantic: 0.34
   Strong Lexical: False | Strong Semantic: True
   File: 设计模式.md

2. 🟣 Semantic
   JDK
   Overall: 0.27 | Lexical: -9.12 | Semantic: 0.34
   Strong Lexical: False | Strong Semantic: True
   File: 设计模式 - 抽象工厂.md
```

## 优势

1. **用户体验简化**: 不需要选择搜索模式，系统自动优化
2. **智能分类**: 基于评分阈值自动判断匹配类型
   - Hybrid: 两者都强 → 最佳结果
   - Keyword: 关键词匹配强 → 精确匹配
   - Semantic: 语义理解强 → 概念匹配
3. **结果透明**: 清晰显示匹配类型和综合评分
4. **精准区分**: 只有同时满足两个阈值才标记为 Hybrid
5. **性能优化**: FTS5 快速过滤 + AI 精准重排序

## 文件修改

### 后端
- `src/kb/api/schemas.py`: 添加 hybrid 模式支持，添加评分字段

### 前端
- `frontend/src/lib/api.ts`: 更新 API 接口
- `frontend/src/components/CommandPalette.tsx`: 简化 UI，添加结果区分
