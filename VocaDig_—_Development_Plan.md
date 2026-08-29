# VocaDig — Development Plan

## Development strategy

Build the discovery engine first and the client later.

```text
Data
→
Personal Library
→
Baseline Dig
→
Audio/Text Embeddings
→
Configurable Profile
→
Feedback
→
Exploration + Diversity
→
Daily Dig
→
API
→
Mobile
→
Learning-to-Rank
```

Do not begin with mobile UI or a complex neural recommender.

---

## Phase 0 — Project skeleton

Set up:

- Python environment
- dependency management
- SQLAlchemy
- pytest
- logging
- configuration

Create:

```text
backend/
tests/
data/
config/
scripts/
```

Acceptance:

```text
application starts
tests execute
```

---

## Phase 1 — Personal Vocaloid Library

Implement:

- Song model
- UserFavorite
- UserFeedback
- UserProfile
- repository layer
- CRUD operations

Support:

```text
add
remove
favorite
rate
search
```

Acceptance:

A local database can maintain a substantial personal Vocaloid library.

---

## Phase 2 — Niconico Crawler

Implement:

```text
crawler/niconico.py
crawler/parser.py
```

Requirements:

- incremental crawling
- duplicate detection
- retries
- rate limiting
- logging

Acceptance:

New Niconico candidates can be inserted into the local database automatically.

---

## Phase 3 — Baseline Dig Engine

Before using embeddings, build a simple metadata-based recommender.

Use:

```text
tags
producer
vocalist
metadata
novelty
```

Implement:

```text
recommendation/profile.py
recommendation/similarity.py
recommendation/scorer.py
recommendation/ranking.py
```

Acceptance:

Given a personal library and new candidates, VocaDig produces a meaningful ranked list.

---

## Phase 4 — Audio Embeddings

Add music-level similarity.

Implement:

```text
features/audio.py
features/embedding.py
```

The encoder interface must remain model-independent.

Potential first model:

```text
MERT
```

Do not allow recommendation code to depend directly on the model implementation.

Acceptance:

New songs can be converted into embeddings and compared with the personal library.

---

## Phase 5 — Text Embeddings

Add semantic information from:

```text
title
description
tags
```

Use a Japanese-capable text embedding model.

Combine:

```text
audio similarity
+
text similarity
+
metadata similarity
```

with configurable weights.

Acceptance:

Changing the weights predictably changes the ranking.

---

## Phase 6 — Configurable Taste Profile

Implement user-controlled parameters:

```text
audio weight
text weight
metadata weight

novelty weight
popularity weight
exploration weight

genre preferences
producer preferences
vocalist preferences

content filters
```

The scorer must receive the profile as an argument.

Bad:

```python
score = 0.6 * audio + 0.3 * text
```

Good:

```python
score = scorer.score(song, user_profile)
```

Acceptance:

No user-specific recommendation parameter is hard-coded.

---

## Phase 7 — Exploration and Diversity

Implement:

```text
novelty
exploration
diversity reranking
```

The goal is to avoid:

```text
10 recommendations
→
10 nearly identical songs
```

Acceptance:

The daily list remains both relevant and diverse.

---

## Phase 8 — User Feedback

Record:

```text
play
skip
like
dislike
favorite
```

Initial feedback weights can be rule-based.

Example:

```text
favorite → strong positive
like → positive
play → weak positive
skip → weak negative
dislike → strong negative
```

Use these signals to update the personal taste profile.

Do not immediately train a neural recommender.

---

## Phase 9 — Daily Dig

Implement:

```python
generate_daily_recommendations(user_id)
```

Pipeline:

```text
crawl
↓
filter
↓
extract features
↓
build profile
↓
score
↓
explore
↓
rerank
↓
Top-K
↓
explain
↓
save
```

Save:

```text
date
rank
score
score components
reason
algorithm version
```

Acceptance:

VocaDig can automatically generate a reproducible daily recommendation list.

---

## Phase 10 — FastAPI

Expose the discovery engine through REST.

Initial endpoints:

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

Acceptance:

The complete discovery workflow can be accessed without importing backend internals.

---

## Phase 11 — Minimal Web Client

Build a functional interface:

```text
Today / Daily Dig
Library
Song Detail
Recommendation Settings
History
```

Do not prioritize visual polish.

The purpose is to validate recommendation quality.

---

## Phase 12 — Mobile Client

Only after the recommendation engine demonstrates useful results.

Possible technology:

```text
Flutter
```

Mobile responsibilities:

```text
Daily Dig
song navigation
library
feedback
settings
notifications
```

Backend remains responsible for:

```text
crawling
feature extraction
recommendation
database
scheduled jobs
```

---

## Phase 13 — Learning-to-Rank

Only after sufficient interaction data exists.

Potential models:

```text
LightGBM
XGBoost
small neural ranking model
```

Training input:

```text
song features
+
user profile
+
recommendation context
```

Target:

```text
like probability
favorite probability
skip probability
```

Initially use learned ranking as a component of the interpretable scoring system rather than replacing it completely.

---

# Testing

Important tests:

## Crawler

```text
duplicate posts
malformed metadata
network failures
pagination
```

## Database

```text
CRUD
unique song IDs
duplicate prevention
```

## Dig Engine

```text
known favorite → high score
excluded category → filtered
novelty weight → predictable effect
audio weight → predictable effect
```

## Ranking

```text
high relevance
+
reasonable diversity
```

## Daily Pipeline

```text
same input
+
same algorithm version
→
reproducible result
```

Network-dependent tests should be separated from offline tests.

---

# MVP Definition

The MVP is complete when:

```text
User has a personal Vocaloid library
            ↓
VocaDig crawls recent Niconico posts
            ↓
Candidates are filtered
            ↓
Features are extracted
            ↓
Personal taste is estimated
            ↓
New songs are scored
            ↓
Candidates are diversified
            ↓
Daily Dig is generated
            ↓
User provides feedback
            ↓
Feedback is stored
```

The mobile application is not required for MVP.

The primary success criterion is:

> **Can VocaDig repeatedly dig out previously unknown songs that the user genuinely likes?**