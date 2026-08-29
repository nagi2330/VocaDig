# VocaDig

**VocaDig** is a personal Vocaloid music discovery system.

It continuously collects new Vocaloid posts from Niconico, compares them with the user's personal music library and taste profile, and digs out songs that the user is likely to enjoy.

> **Dig out your next favorite.**

The system focuses on:

- personalized discovery
- long-tail/new-producer discovery
- configurable recommendation parameters
- explainable recommendations
- user-owned Vocaloid library

The mobile application is a future client. The initial development focuses on the backend and recommendation engine.

## Initial stack

- Python
- SQLite
- SQLAlchemy
- FastAPI
- NumPy / SciPy
- PyTorch
- music/text embedding models
- pytest

## Core pipeline

```text
Niconico new posts
        ↓
candidate filtering
        ↓
audio + text + metadata features
        ↓
personal taste profile
        ↓
candidate scoring
        ↓
exploration + diversity reranking
        ↓
Daily Dig
        ↓
user feedback
```

The recommendation algorithm should remain interpretable and user-configurable.

---

## Main modules

```text
backend/
├── crawler/
├── database/
├── features/
├── recommendation/
├── scheduler/
└── api/
```

Keep data acquisition, feature extraction, recommendation, and API layers independent.

---

## MVP

The MVP should be able to:

1. crawl recent Niconico Vocaloid posts
2. maintain a local Vocaloid library
3. extract basic song features
4. build a personal taste profile
5. rank new songs
6. generate a daily recommendation list
7. record user feedback

The first objective is to verify whether VocaDig can consistently discover previously unknown songs that the user genuinely likes.