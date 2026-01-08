# 搜索结果分类快速指南

## 分类规则

### 🔵 Hybrid (蓝色)
**条件**: Lexical Score > -8.0 **AND** Semantic Score > 0.25

```
示例:
CSMA/CD 协议
Overall: 0.40 | Lexical: -7.83 | Semantic: 0.25
✓ -7.83 > -8.0  (关键词匹配强)
✓ 0.25 ≥ 0.25  (语义理解强)
→ Hybrid Match 🔵
```

**特点**:
- 关键词精确匹配
- 语义理解到位
- 最高质量结果
- 推荐优先查看

---

### 🟡 Keyword (琥珀色)
**条件**: Lexical Score > -8.0 **BUT** Semantic Score ≤ 0.25

```
示例:
文件属性
Overall: 0.17 | Lexical: -6.54 | Semantic: 0.22
✓ -6.54 > -8.0  (关键词匹配强)
✗ 0.22 < 0.25   (语义理解弱)
→ Keyword Match 🟡
```

**特点**:
- 精确的文本匹配
- 关键词直接命中
- 适合查找特定术语
- FTS5 全文搜索

---

### 🟣 Semantic (紫色)
**条件**: Lexical Score ≤ -8.0 **BUT** Semantic Score > 0.25

```
示例:
JDK
Overall: 0.47 | Lexical: -9.16 | Semantic: 0.34
✗ -9.16 < -8.0  (关键词匹配弱)
✓ 0.34 > 0.25   (语义理解强)
→ Semantic Match 🟣
```

**特点**:
- AI 理解查询意图
- 概念相关匹配
- 关键词可能不同
- 发现相关内容

---

## 调整阈值

如果需要调整分类的敏感度，修改 `CommandPalette.tsx`:

```typescript
// 位置: frontend/src/components/CommandPalette.tsx

const LEXICAL_THRESHOLD = -8.0;   // 更大 = 更严格
const SEMANTIC_THRESHOLD = 0.25;  // 更大 = 更严格
```

### 阈值调整建议

| 场景 | Lexical | Semantic | 效果 |
|------|---------|----------|------|
| 默认 | -8.0 | 0.25 | 平衡 |
| 更多 Hybrid | -9.0 | 0.20 | 放宽条件 |
| 更严格 | -7.0 | 0.30 | 提高质量 |
| 偏向关键词 | -8.5 | 0.30 | 更重视精确匹配 |
| 偏向语义 | -7.0 | 0.20 | 更重视理解意图 |

---

## 评分含义

### Lexical Score (词法评分)
- **类型**: 负对数分数
- **范围**: 负无穷 到 0
- **解释**:
  - 0: 完美匹配
  - -5: 非常好的匹配
  - -8: 良好的匹配
  - -10: 较弱的匹配
  - < -15: 很弱的匹配

### Semantic Score (语义评分)
- **类型**: 余弦相似度
- **范围**: 0 到 1
- **解释**:
  - 0.8-1.0: 极高相似度
  - 0.5-0.8: 高相似度
  - 0.25-0.5: 中等相似度
  - 0.1-0.25: 低相似度
  - < 0.1: 几乎无关

### Overall Score (综合评分)
- **类型**: 归一化分数
- **范围**: 0 到 1
- **用途**: 显示给用户的主要指标
- **计算**: 结合 lexical 和 semantic 的加权平均

---

## 使用建议

### 查找特定术语
- 期望看到: 🟡 Keyword
- 示例: "TCP/IP", "链表", "快速排序"

### 探索相关概念
- 期望看到: 🟣 Semantic
- 示例: "机器学习算法", "设计模式应用"

### 综合查询
- 期望看到: 🔵 Hybrid
- 示例: 文档中确实包含该术语且内容相关

---

## 故障排查

### 所有结果都是 Keyword
**原因**: Semantic 分数普遍较低
**解决**:
- 降低 `SEMANTIC_THRESHOLD` (如 0.20)
- 检查是否生成了 embeddings

### 所有结果都是 Semantic
**原因**: Lexical 分数普遍较低
**解决**:
- 降低 `LEXICAL_THRESHOLD` (如 -9.0)
- 检查搜索词是否太短或太泛

### 没有 Hybrid 结果
**原因**: 阈值设置过严格
**解决**:
- 同时降低两个阈值
- 查看实际分数分布调整

---

## 技术细节

### 实现位置
```
frontend/src/components/CommandPalette.tsx
- 第 163-196 行: 匹配类型判断逻辑
```

### 数据流
```
用户输入查询
    ↓
调用 /api/search (hybrid mode)
    ↓
返回带评分的结果
    ↓
前端根据阈值判断
    ↓
显示匹配类型标签
```

### 测试命令
```bash
# 测试搜索分类
curl -s "http://localhost:8000/api/search?q=链表&mode=hybrid&limit=5" \
  | python3 /tmp/test_search.py
```
