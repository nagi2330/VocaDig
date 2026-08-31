# VocaDig — 开发计划

## 开发策略

先构建发现引擎，后开发客户端。

```text
数据
→
个人曲库
→
基础 Dig
→
音频/文本 Embedding
→
可配置画像
→
反馈
→
探索 + 多样性
→
每日 Dig
→
API
→
移动端
→
Learning-to-Rank
```

不要从移动端 UI 或复杂的神经网络推荐器开始。

---

## 阶段 0 — 项目骨架

建立：

- [x] Python 环境
- [x] 依赖管理
- [x] SQLAlchemy
- [x] pytest
- [x] 日志
- [x] 配置

创建：

```text
[x] backend/
[x] tests/
[x] data/
[x] config/
[x] scripts/
```

验收标准：

```text
[x] 应用可启动
[x] 测试可执行
```

---

## 阶段 1 — 个人 Vocaloid 曲库

实现：

- [x] Song 模型
- [x] UserFavorite
- [x] UserFeedback
- [x] UserProfile
- [x] 仓储层
- [x] CRUD 操作

支持：

```text
[x] add
[x] remove
[x] favorite
[x] rate
[x] search
```

验收标准：

[x] 本地数据库能够维护规模可观的个人 Vocaloid 曲库。

---

## 阶段 2 — Niconico 采集器

实现：

```text
[x] crawler/niconico.py
[x] crawler/parser.py
```

要求：

- [x] 增量采集
- [x] 重复检测
- [x] 重试
- [x] 速率限制
- [x] 日志

验收标准：

[x] 可自动将新的 Niconico 候选项写入本地数据库。

---

## 阶段 3 — 基础 Dig 引擎

在使用 embedding 前，先构建一个简单的基于元数据的推荐器。

使用：

```text
tags
producer
vocalist
metadata
novelty
```

实现：

```text
[x] recommendation/profile.py
[x] recommendation/similarity.py
[x] recommendation/scorer.py
[x] recommendation/ranking.py
```

验收标准：

[x] 给定个人曲库和新候选项，VocaDig 能生成有意义的排序列表。

---

## 阶段 4 — 音频 Embedding

增加音乐层面的相似度。

实现：

```text
features/audio.py
features/embedding.py
```

编码器接口必须保持独立于具体模型。

可选的首个模型：

```text
MERT
```

不要让推荐代码直接依赖模型实现。

验收标准：

新歌曲可以转换为 embedding 并与个人曲库进行比较。

---

## 阶段 5 — 文本 Embedding

增加来自以下内容的语义信息：

```text
title
description
tags
```

使用支持日语的文本 embedding 模型。

组合：

```text
audio similarity
+
text similarity
+
metadata similarity
```

并使用可配置的权重。

验收标准：

改变权重会以可预测的方式改变排序。

---

## 阶段 6 — 可配置的品味画像

实现由用户控制的参数：

```text
音频权重
文本权重
元数据权重

新颖度权重
流行度权重
探索权重

流派偏好
作者偏好
歌姬偏好

内容过滤器
```

评分器必须将画像作为参数接收。

不推荐：

```python
score = 0.6 * audio + 0.3 * text
```

推荐：

```python
score = scorer.score(song, user_profile)
```

验收标准：

不得硬编码任何用户专属的推荐参数。

---

## 阶段 7 — 探索与多样性

实现：

```text
novelty
exploration
diversity reranking
```

目标是避免：

```text
10 条推荐
→
10 首几乎相同的歌曲
```

验收标准：

每日列表应同时保持相关性和多样性。

---

## 阶段 8 — 用户反馈

记录：

```text
play
skip
like
dislike
favorite
```

初始反馈权重可以基于规则。

示例：

```text
favorite → 强正向
like → 正向
play → 弱正向
skip → 弱负向
dislike → 强负向
```

使用这些信号更新个人品味画像。

不要立即训练神经网络推荐器。

---

## 阶段 9 — 每日 Dig

实现：

```python
generate_daily_recommendations(user_id)
```

流水线：

```text
采集
↓
过滤
↓
提取特征
↓
构建画像
↓
评分
↓
探索
↓
重排序
↓
Top-K
↓
解释
↓
保存
```

保存：

```text
date
rank
score
评分组成部分
原因
算法版本
```

验收标准：

VocaDig 能自动生成可复现的每日推荐列表。

---

## 阶段 10 — FastAPI

通过 REST 暴露发现引擎。

初始端点：

```text
GET  /recommendations/today
GET  /recommendations/history

GET  /library
POST /library/{song_id}
DELETE /library/{song_id}

POST /feedback

GET  /profile
PUT  /profile
```

验收标准：

无需导入后端内部模块即可访问完整的发现流程。

---

## 阶段 11 — 最小化 Web 客户端

构建可用界面：

```text
今日 / 每日 Dig
曲库
歌曲详情
推荐设置
历史记录
```

不优先追求视觉精致度。

目标是验证推荐质量。

---

## 阶段 12 — 移动端客户端

仅在推荐引擎已经展现出实用效果后再开始。

可选技术：

```text
Flutter
```

移动端职责：

```text
每日 Dig
歌曲导航
曲库
反馈
设置
通知
```

后端继续负责：

```text
采集
特征提取
推荐
数据库
定时任务
```

---

## 阶段 13 — Learning-to-Rank

仅在积累足够的交互数据后再开始。

可选模型：

```text
LightGBM
XGBoost
小型神经网络排序模型
```

训练输入：

```text
歌曲特征
+
用户画像
+
推荐上下文
```

目标：

```text
like 概率
favorite 概率
skip 概率
```

初期应将学习排序作为可解释评分系统的一个组成部分，而不是完全替代它。

---

# 测试

重要测试：

## 采集器

```text
[x] 重复投稿
[x] 畸形元数据
- [ ] 网络失败（已实现重试行为，但缺少自动化测试）
- [ ] 分页（已实现偏移量分页，但缺少自动化测试）
```

## 数据库

```text
[x] CRUD
[x] 唯一歌曲 ID
[x] 重复防止
```

## Dig 引擎

```text
已知收藏 → 高分
排除的类别 → 被过滤
新颖度权重 → 可预测的效果
音频权重 → 可预测的效果
```

## 排序

```text
高相关性
+
合理的多样性
```

## 每日流水线

```text
相同输入
+
相同算法版本
→
可复现结果
```

依赖网络的测试应与离线测试分离。

---

# MVP 定义

满足以下条件时，MVP 即告完成：

```text
用户拥有个人 Vocaloid 曲库
            ↓
VocaDig 采集近期 Niconico 投稿
            ↓
候选项被过滤
            ↓
特征被提取
            ↓
个人品味被估计
            ↓
新歌曲被评分
            ↓
候选项经过多样化处理
            ↓
每日 Dig 已生成
            ↓
用户提供反馈
            ↓
反馈被保存
```

移动应用不是 MVP 的必要条件。

首要成功标准是：

> **VocaDig 能否持续挖掘出用户此前未知且真正喜欢的歌曲？**