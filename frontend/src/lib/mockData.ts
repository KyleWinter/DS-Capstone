export interface TreeNode {
  id: string;
  name: string;
  type: "cluster" | "note";
  children?: TreeNode[];
  path?: string;
  similarity?: number;
}

export interface RelatedNote {
  id: string;
  title: string;
  path: string;
  similarity: number;
  preview: string;
}

export const mockClusterTree: TreeNode = {
  id: "root",
  name: "Knowledge Base",
  type: "cluster",
  children: [
    {
      id: "ml",
      name: "Machine Learning",
      type: "cluster",
      children: [
        {
          id: "ml-transformers",
          name: "Transformers",
          type: "cluster",
          children: [
            {
              id: "note-1",
              name: "Attention Mechanism",
              type: "note",
              path: "/ml/transformers/attention",
            },
            {
              id: "note-2",
              name: "Multi-Head Attention",
              type: "note",
              path: "/ml/transformers/multi-head",
            },
            {
              id: "note-3",
              name: "Self-Attention",
              type: "note",
              path: "/ml/transformers/self-attention",
            },
          ],
        },
        {
          id: "ml-optimization",
          name: "Optimization",
          type: "cluster",
          children: [
            {
              id: "note-4",
              name: "Adam Optimizer",
              type: "note",
              path: "/ml/optimization/adam",
            },
            {
              id: "note-5",
              name: "Learning Rate Schedules",
              type: "note",
              path: "/ml/optimization/lr-schedules",
            },
          ],
        },
        {
          id: "note-6",
          name: "Neural Networks Basics",
          type: "note",
          path: "/ml/nn-basics",
        },
      ],
    },
    {
      id: "algorithms",
      name: "Algorithms",
      type: "cluster",
      children: [
        {
          id: "algo-sorting",
          name: "Sorting",
          type: "cluster",
          children: [
            {
              id: "note-7",
              name: "Quick Sort",
              type: "note",
              path: "/algorithms/sorting/quicksort",
            },
            {
              id: "note-8",
              name: "Merge Sort",
              type: "note",
              path: "/algorithms/sorting/mergesort",
            },
          ],
        },
        {
          id: "algo-graphs",
          name: "Graph Algorithms",
          type: "cluster",
          children: [
            {
              id: "note-9",
              name: "Dijkstra's Algorithm",
              type: "note",
              path: "/algorithms/graphs/dijkstra",
            },
            {
              id: "note-10",
              name: "BFS and DFS",
              type: "note",
              path: "/algorithms/graphs/bfs-dfs",
            },
          ],
        },
      ],
    },
    {
      id: "systems",
      name: "Distributed Systems",
      type: "cluster",
      children: [
        {
          id: "note-11",
          name: "CAP Theorem",
          type: "note",
          path: "/systems/cap-theorem",
        },
        {
          id: "note-12",
          name: "Consensus Algorithms",
          type: "note",
          path: "/systems/consensus",
        },
        {
          id: "note-13",
          name: "Raft Protocol",
          type: "note",
          path: "/systems/raft",
        },
      ],
    },
    {
      id: "leetcode",
      name: "Leetcode 题解",
      type: "cluster",
      children: [
        {
          id: "note-14",
          name: "链表",
          type: "note",
          path: "/leetcode/linked-list",
        },
        {
          id: "note-15",
          name: "二叉树",
          type: "note",
          path: "/leetcode/binary-tree",
        },
        {
          id: "note-16",
          name: "动态规划",
          type: "note",
          path: "/leetcode/dynamic-programming",
        },
      ],
    },
  ],
};

export const mockRelatedNotes: RelatedNote[] = [
  {
    id: "note-2",
    title: "Multi-Head Attention",
    path: "/ml/transformers/multi-head",
    similarity: 0.98,
    preview: "Multi-head attention allows the model to jointly attend to information from different representation subspaces...",
  },
  {
    id: "note-3",
    title: "Self-Attention",
    path: "/ml/transformers/self-attention",
    similarity: 0.95,
    preview: "Self-attention is a mechanism that allows the model to weigh the importance of different parts of the input...",
  },
  {
    id: "note-6",
    title: "Neural Networks Basics",
    path: "/ml/nn-basics",
    similarity: 0.87,
    preview: "Neural networks are computing systems inspired by biological neural networks that constitute animal brains...",
  },
  {
    id: "note-5",
    title: "Learning Rate Schedules",
    path: "/ml/optimization/lr-schedules",
    similarity: 0.82,
    preview: "Learning rate schedules adjust the learning rate during training to improve convergence and final performance...",
  },
  {
    id: "note-4",
    title: "Adam Optimizer",
    path: "/ml/optimization/adam",
    similarity: 0.78,
    preview: "Adam is an adaptive learning rate optimization algorithm that's been designed specifically for training deep neural networks...",
  },
];

export const mockMarkdownContent = `# Attention Mechanism

The **attention mechanism** is a crucial component of modern deep learning architectures, particularly in natural language processing and computer vision tasks.

## What is Attention?

Attention allows a model to focus on specific parts of the input when producing an output. Instead of compressing all information into a fixed-length vector, attention provides a way to dynamically select which parts of the input are most relevant.

## Key Concepts

### 1. Query, Key, and Value

The attention mechanism operates on three main components:

- **Query (Q)**: What we're looking for
- **Key (K)**: What we're looking at
- **Value (V)**: What we actually retrieve

### 2. Attention Score

The attention score is calculated as:

\`\`\`
score = softmax(Q · K^T / √d_k)
\`\`\`

Where \`d_k\` is the dimension of the key vectors.

### 3. Weighted Sum

The final output is computed as a weighted sum of values:

\`\`\`
output = score · V
\`\`\`

## Types of Attention

### Self-Attention
Self-attention allows the model to look at other positions in the input sequence when encoding a particular position.

### Cross-Attention
Cross-attention attends to a different sequence, commonly used in encoder-decoder architectures.

### Multi-Head Attention
Multi-head attention runs multiple attention operations in parallel, allowing the model to jointly attend to information from different representation subspaces.

## Applications

- **Machine Translation**: Aligning source and target language words
- **Text Summarization**: Focusing on important sentences
- **Image Captioning**: Connecting image regions to generated words
- **Question Answering**: Locating relevant information in context

## Code Example

\`\`\`python
import torch
import torch.nn.functional as F

def attention(query, key, value, mask=None):
    d_k = query.size(-1)
    scores = torch.matmul(query, key.transpose(-2, -1)) / torch.sqrt(torch.tensor(d_k))

    if mask is not None:
        scores = scores.masked_fill(mask == 0, -1e9)

    attention_weights = F.softmax(scores, dim=-1)
    output = torch.matmul(attention_weights, value)

    return output, attention_weights
\`\`\`

## Related Concepts

- **Transformers**: Architecture built entirely on attention mechanisms
- **BERT**: Uses bidirectional self-attention
- **GPT**: Uses unidirectional (causal) self-attention

## References

1. Vaswani et al. (2017) - "Attention Is All You Need"
2. Bahdanau et al. (2014) - "Neural Machine Translation by Jointly Learning to Align and Translate"

---

*Last updated: 2024*
`;
