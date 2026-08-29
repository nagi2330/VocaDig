# VocaDig — System Architecture

## 1. System overview

VocaDig consists of six major layers:

```text
┌──────────────────────┐
│      Niconico        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│       Crawler        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│     Song Database    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Feature Extraction  │
│ audio / text / meta  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Personal Dig Engine │
│ scoring / exploration│
│ / diversity          │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│     Daily Dig        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│      FastAPI         │
└──────────┬───────────┘
           ↓
      Web / Mobile
```

The recommendation engine is the core of the system. Client applications should not contain recommendation logic.

---

# 2. Repository structure

```text
voca-dig/
│
├── backend/
│   ├── crawler/
│   │   ├── niconico.py
│   │   └── parser.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── repository.py
│   │
│   ├── features/
│   │   ├── audio.py
│   │   ├── text.py
│   │   ├── metadata.py
│   │   └── embedding.py
│   │
│   ├── recommendation/
│   │   ├── profile.py
│   │   ├── similarity.py
│   │   ├── scorer.py
│   │   └── ranking.py
│   │
│   ├── scheduler/
│   │   └── daily.py
│   │
│   ├── api/
│   │   ├── songs.py
│   │   ├── library.py
│   │   ├── recommendations.py
│   │   └── users.py
│   │
│   └── main.py
│
├── tests/
├── data/
├── config/
├── scripts/
├── requirements.txt
└── README.md
```

---

# 3. Database

Use SQLite initially through SQLAlchemy.

The database should be designed so that PostgreSQL can be introduced later.

## Song

```text
song_id
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
created_at
updated_at
```

`song_id` is the unique external identifier.

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

The feature schema must not depend on one specific embedding model.

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

Possible sources:

```text
manual
import
recommendation
```

---

## UserFeedback

Store interactions independently from favorites.

```text
user_id
song_id
action
timestamp
```

Possible actions:

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

Store user-controlled preferences and algorithm parameters.

Example:

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

User-specific recommendation parameters must never be hard-coded.

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

Store the algorithm version to make recommendation experiments reproducible.

---

# 4. Crawler

The crawler is responsible only for data acquisition.

```text
discover new posts
        ↓
parse metadata
        ↓
identify song ID
        ↓
store/update Song
```

It must not contain recommendation logic.

Requirements:

- incremental crawling
- duplicate detection
- retry handling
- rate limiting
- logging
- failure recovery

The implementation must respect Niconico's access policies and technical restrictions.

---

# 5. Candidate filtering

Filtering happens before recommendation scoring.

```text
Niconico posts
      ↓
Vocaloid relevance filter
      ↓
content-type filter
      ↓
candidate songs
```

Possible content types:

```text
original
cover
remix
instrumental
MMD
talkloid
other
```

Explicit exclusions should be implemented as filters rather than negative recommendation scores.

---

# 6. Feature extraction

Feature extraction consists of three independent groups.

## Audio

Potential models:

- MERT
- Music2Vec
- other music embedding models

Output:

```text
audio_embedding
```

Optional features:

```text
BPM
energy
rhythm
spectral features
```

The audio encoder should expose a model-independent interface.

---

## Text

Inputs:

```text
title
description
tags
```

Output:

```text
text_embedding
```

The text model should be suitable for Japanese.

---

## Metadata

Examples:

```text
producer
vocalist
tags
upload time
view count
```

Metadata remains available as explicit recommendation features.

---

# 7. Personal taste profile

The initial implementation should construct the user's taste representation from the personal library.

For example:

```text
user_audio_embedding
=
weighted average of favorite audio embeddings
```

and:

```text
user_text_embedding
=
weighted average of favorite text embeddings
```

Weights may later incorporate:

- rating
- interaction history
- recency
- explicit preference

Do not train a neural user model in the first version.

---

# 8. Dig scoring

The initial scoring model should be explicit and interpretable.

Conceptually:

```text
score =
    w_audio       * audio_similarity
  + w_text        * text_similarity
  + w_metadata    * metadata_score
  + w_novelty     * novelty_score
  + w_popularity  * popularity_score
  + w_exploration * exploration_score
```

The scorer should return both the final score and individual components.

Example:

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

# 9. Long-tail discovery

VocaDig should actively search beyond popular songs.

Potential novelty signals:

```text
low view count
new producer
new vocalist
unfamiliar genre
unfamiliar producer
recent upload
```

Novelty should be configurable.

The system should not optimize only for similarity to existing favorites.

---

# 10. Exploration vs exploitation

The system should support both:

```text
exploitation
→ songs close to known preferences

exploration
→ unfamiliar songs and regions of the music space
```

The balance should be user-configurable.

---

# 11. Diversity reranking

Do not simply select the highest-scoring K candidates.

Use diversity-aware reranking.

One possible approach is MMR:

```text
final_score =
    relevance_score
    -
    diversity_penalty
```

The exact reranking algorithm should remain replaceable.

---

# 12. Recommendation explanation

The recommendation engine should first produce structured evidence:

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

Natural-language explanations may later be generated from this data.

An LLM must not invent recommendation reasons that are unsupported by the scoring results.

---

# 13. API

Initial REST API:

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

Use FastAPI + Pydantic.

The frontend must not directly access database models.

---

# 14. Daily Dig

The daily recommendation pipeline:

```text
crawl
 ↓
candidate filtering
 ↓
feature extraction
 ↓
taste profile
 ↓
scoring
 ↓
exploration
 ↓
diversity reranking
 ↓
Top-K
 ↓
explanation
 ↓
database
```

Expose the pipeline through a single callable function:

```python
generate_daily_recommendations(user_id)
```

It should be possible to run this manually during development and automatically through the scheduler.

The pipeline should be idempotent whenever practical.

---

# 15. Client architecture

The mobile application is a future client.

Possible architecture:

```text
Flutter
   ↓
REST API
   ↓
FastAPI
   ↓
VocaDig Engine
   ↓
Database
```

The client handles:

- display
- navigation
- playback
- user feedback
- library management
- settings
- notifications

The backend handles crawling, feature extraction, recommendation and persistence.

---

# 16. Architectural principles

1. Recommendation is the core domain.
2. Crawler must not contain recommendation logic.
3. User preferences must be data, not hard-coded logic.
4. Scores must remain decomposable and inspectable.
5. Models must be replaceable.
6. Store model and algorithm versions.
7. Cache expensive feature extraction.
8. Keep the pipeline testable offline.
9. Avoid premature machine-learning complexity.
10. Keep the mobile client independent from the recommendation implementation.