# VocaDig — 系统架构

## 1. 系统概览

VocaDig 当前是一个本地优先的音乐曲库后端。已经实现的核心包括数据采集、持久化、跨平台匹配和收藏夹同步；推荐、HTTP API 与移动端客户端仍处于规划阶段，尚不是当前的运行组件。

```text
当前实现

Niconico / Bilibili / Niconico mylist
          ↓
             平台适配器
          ↓
    规范曲目 + 平台投稿
          ↓
匹配 / 收藏 / 收藏夹同步
          ↓
    SQLite 仓储层

后续演进

SQLite 仓储层 → 特征提取 → 推荐引擎
      ↓                      ↓
  授权与同步              每日推荐
      ↓                      ↓
      FastAPI 服务 → Web / 移动端客户端
```

推荐引擎仍是未来的核心领域。客户端必须消费后端结果，而不能实现推荐逻辑。平台特定的数据采集和授权必须与规范曲目、曲库和推荐领域保持分离。

---

# 2. 仓库结构

```text
voca-dig/
│
├── backend/
│   ├── crawler/
│   │   ├── niconico.py
│   │   ├── niconico_favorites.py
│   │   ├── bilibili.py
│   │   ├── cookies.py
│   │   └── parser.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── repository.py
│   │
│   ├── sync/
│   │   └── favorite_collections.py
│   ├── matching.py
│   └── main.py
│
├── tests/
├── data/
├── config/
├── scripts/
├── requirements.txt
└── README.md
```

以下目录仍处于规划阶段，只有在具备可运行的垂直功能切片时才应添加：`features/`、`recommendation/`、`api/` 和 `scheduler/`。`scripts/` 包含当前的运维入口；`main.py` 仅初始化数据库，并非 API 服务器。

---

# 3. 数据库

初期通过 SQLAlchemy 使用 SQLite。

数据库设计应允许后续引入 PostgreSQL。

## CanonicalSong

```text
id
title
producer
created_at
updated_at
```

`CanonicalSong` 表示系统能够识别出的音乐作品。它不能以外部平台 ID 作为主标识：一首作品可能拥有 Niconico、Bilibili 以及未来其他平台的多个投稿。仅属于某次投稿的字段应归入 `PlatformVideo`。

## PlatformVideo

```text
id
platform                 # niconico, bilibili, ...
platform_video_id        # stable ID within platform
canonical_song_id        # nullable until reviewed or auto-confirmed
title
producer
upload_time
description
tags
url
thumbnail_url
duration
vocalist
view_count
like_count
comment_count
raw_metadata
created_at
updated_at
```

`(platform, platform_video_id)` 为唯一键。匹配建议只有在满足配置的自动确认规则或通过人工审核后，才会将平台投稿关联到规范曲目。原始来源元数据应与规范化字段分开保留，以便适配器演进时不会破坏规范数据。

## MatchSuggestion

```text
id
source_platform_video_id
candidate_canonical_song_id
confidence
evidence_json
status                   # pending, confirmed, rejected
reviewed_at
created_at
```

该模型保证跨平台匹配可审计、可回退。确认建议时只更新 `PlatformVideo.canonical_song_id`，不会合并或删除来源记录。

---

## AudioFeature

```text
song_id
model_name
model_version
embedding
bpm
key
energy
other_features
```

特征 schema 不得依赖某一种特定的 embedding 模型。

---

## TextFeature

```text
song_id
model_name
model_version
title_embedding
description_embedding
tag_embedding
combined_embedding
```

---

## UserFavorite

```text
user_id
song_id
rating
created_at
source
```

可能的来源：

```text
manual
import
recommendation
```

---

## UserFeedback

交互记录应独立于收藏记录保存。

```text
user_id
song_id
action
timestamp
```

可能的行为：

```text
play
skip
like
dislike
favorite
open
```

---

## UserProfile

保存由用户控制的偏好和算法参数。

示例：

```json
{
    "weights": {
        "audio": 0.6,
        "text": 0.3,
        "metadata": 0.1,
        "novelty": 0.3,
        "popularity": 0.0,
        "exploration": 0.2
    },

    "filters": {
        "cover": false,
        "remix": true,
        "talkloid": false
    },

    "preferences": {
        "genres": {},
        "vocalists": {},
        "producers": {}
    }
}
```

用户专属的推荐参数绝不能硬编码。

---

## DailyRecommendation

```text
user_id
date
song_id
score
rank
reason
algorithm_version
created_at
```

保存算法版本，以使推荐实验可复现。

---

# 4. 平台采集与授权

平台适配器只负责数据采集和来源数据规范化。

```text
发现新投稿
        ↓
解析来源元数据
    ↓
写入或更新 PlatformVideo
    ↓
建议或确认 CanonicalSong 关联
```

其中不得包含推荐逻辑。

要求：

- 增量采集
- 重复检测
- 重试处理
- 速率限制
- 日志记录
- 失败恢复

收藏夹同步属于应用服务，而非采集器逻辑。它将获取的远程快照与 `DefaultFavoriteCollection` 成员记录对比，记录新增与移除，但不删除曲目、平台投稿或反馈历史。

授权必须封装在平台提供方专属的接口之后。当前本地桌面端流程可使用用户通过环境变量或本地密钥存储提供的 Bilibili Cookie。未来移动端在平台提供所需权限范围时，应优先采用官方 OAuth 授权码与刷新令牌流程。浏览器 Cookie 绝不能写入应用数据库、API 响应或日志。

所有适配器都必须遵守各平台的访问策略、认证限制和速率限制。

---

# 5. 候选过滤

过滤发生在推荐评分之前。

```text
Niconico 投稿
      ↓
Vocaloid 相关性过滤
      ↓
内容类型过滤
      ↓
候选曲目
```

可能的内容类型：

```text
original
cover
remix
instrumental
MMD
talkloid
other
```

明确排除的内容应通过过滤器实现，而不是给予负向推荐分数。

---

# 6. 特征提取

特征提取由三组相互独立的特征构成。

## Audio

候选模型：

- MERT
- Music2Vec
- 其他音乐 embedding 模型

输出：

```text
audio_embedding
```

可选特征：

```text
BPM
energy
rhythm
频谱特征
```

音频编码器应提供独立于具体模型的接口。

---

## Text

输入：

```text
title
description
tags
```

输出：

```text
text_embedding
```

文本模型应适用于日语。

---

## Metadata

示例：

```text
producer
vocalist
tags
上传时间
播放量
```

元数据仍可作为显式推荐特征使用。

---

# 7. 个人品味画像

初始实现应从个人曲库构建用户的品味表示。

例如：

```text
user_audio_embedding
=
收藏曲目音频 embedding 的加权平均
```

以及：

```text
user_text_embedding
=
收藏曲目文本 embedding 的加权平均
```

权重后续可以纳入：

- rating
- 交互历史
- 时效性
- 显式偏好

第一版不训练神经网络用户模型。

---

# 8. Dig 评分

初始评分模型应保持显式且可解释。

概念上：

```text
score =
    w_audio       * audio_similarity
  + w_text        * text_similarity
  + w_metadata    * metadata_score
  + w_novelty     * novelty_score
  + w_popularity  * popularity_score
  + w_exploration * exploration_score
```

评分器应同时返回最终分数和各个组成部分。

示例：

```python
{
    "total": 0.87,
    "audio": 0.91,
    "text": 0.74,
    "metadata": 0.65,
    "novelty": 0.88,
    "popularity": 0.20
}
```

---

# 9. 长尾发现

VocaDig 应主动发现热门歌曲之外的内容。

潜在的新颖度信号：

```text
低播放量
新作者
新歌姬
不熟悉的流派
不熟悉的作者
近期上传
```

新颖度应可配置。

系统不应只针对与已有收藏的相似度进行优化。

---

# 10. 探索与利用

系统应同时支持：

```text
利用
→ 与已知偏好接近的曲目

探索
→ 不熟悉的曲目和音乐空间区域
```

两者间的平衡应由用户配置。

---

# 11. 多样性重排序

不应直接选择得分最高的 K 个候选项。

应使用具备多样性意识的重排序。

一种可选方法是 MMR：

```text
final_score =
    relevance_score
    -
    diversity_penalty
```

具体的重排序算法应保持可替换。

---

# 12. 推荐解释

推荐引擎应先产出结构化证据：

```python
{
    "audio_similarity": 0.91,
    "text_similarity": 0.72,
    "producer_similarity": 0.15,
    "novelty": 0.88,
    "main_reasons": [
        "similar_audio",
        "new_producer",
        "low_popularity"
    ]
}
```

后续可以基于这些数据生成自然语言解释。

LLM 不得编造评分结果未支持的推荐理由。

---

# 13. API（规划）

初始 REST API：

```text
GET  /songs/{song_id}
GET  /songs/search

GET  /library
POST /library/{song_id}
DELETE /library/{song_id}

POST /feedback

GET  /recommendations/today
GET  /recommendations/history

GET  /profile
PUT  /profile
```

引入服务边界时使用 FastAPI + Pydantic。初始 API 应暴露曲库、反馈、画像、推荐和授权状态资源；绝不能返回平台提供方凭据。前端必须使用 API DTO，而不能直接使用数据库模型。

VocaDig 账户认证与可选的平台绑定账户相互独立。绑定的平台账户必须支持解除绑定和凭据撤销。

---

# 14. 每日推荐（规划）

每日推荐流水线：

```text
采集
 ↓
候选过滤
 ↓
特征提取
 ↓
品味画像
 ↓
评分
 ↓
探索
 ↓
多样性重排序
 ↓
Top-K
 ↓
解释
 ↓
数据库
```

应通过一个可调用函数暴露该流水线：

```python
generate_daily_recommendations(user_id)
```

开发期间应能手动运行，并可通过调度器自动运行。

在可行情况下，流水线应保持幂等。

---

# 15. 客户端架构（规划）

移动应用是未来的客户端。

可选架构：

```text
Flutter / Web
      ↓
REST API
      ↓
FastAPI application
      ↓
VocaDig domain services
      ↓
Database / job workers
```

客户端负责：

- 展示
- 导航
- 播放
- 用户反馈
- 曲库管理
- 设置
- 通知

后端负责采集、平台授权、特征提取、推荐和持久化。移动客户端在平台支持时处理 OAuth 重定向或应用间授权交接，但不得提取、上传或持久化浏览器会话 Cookie。

---

# 16. 架构原则

1. 规范曲目和平台投稿是两种独立的身份标识。
2. 平台适配器不得包含匹配、推荐或曲库策略。
3. 推荐是未来的核心领域；用户偏好必须是数据，而不是硬编码逻辑。
4. 分数和匹配证据必须保持可分解、可检查。
5. 模型、平台适配器和授权提供方必须可替换。
6. 保存模型和算法版本。
7. 只保存所需的最少平台授权材料，且绝不向客户端暴露。
8. 缓存高成本特征提取结果。
9. 让采集、匹配、同步和推荐能够离线测试。
10. 保持移动客户端独立于推荐实现和浏览器 Cookie 处理。