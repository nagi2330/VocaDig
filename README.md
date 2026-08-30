# VocaDig

VocaDig 是一个本地优先的 Vocaloid 曲库与新曲发现后端。目前已经具备：

- 从 Niconico 搜索接口导入新曲视频；
- 从 Bilibili 收藏夹同步个人曲库；
- 保留 Niconico 视频号与 Bilibili BV 号；
- 根据曲名、P 主、歌姬和时长匹配同一首曲目的不同投稿；
- 自动确认明确匹配，并将不确定的近似项交给用户确认；
- 保存本地收藏、评分、反馈与偏好。

推荐、音频/文本特征、Web API 和客户端仍处于后续开发阶段，详见 [开发计划](VocaDig_—_Development_Plan.md)。

## 环境准备

需要 Python 3.11 或更高版本。建议在虚拟环境中安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

数据库默认保存在 `data/vocadig.db`，首次执行任意脚本时会自动创建表。

初始化空数据库：

```powershell
python -m backend.main
```

可复制 `config/settings.example.toml` 作为本地配置参考。当前命令行脚本的参数优先于该示例配置。

## 模块与职责

| 模块 | 功能 | 主要入口 |
| --- | --- | --- |
| `backend/database` | SQLAlchemy 数据模型、数据库初始化和曲库读写 | `LibraryRepository` |
| `backend/crawler/niconico.py` | 分页获取 Niconico 搜索结果，重试、限速并导入 | `scripts/crawl_niconico.py` |
| `backend/crawler/bilibili.py` | 获取一个 Bilibili 收藏夹并同步其中的视频 | `scripts/sync_bilibili_favorites.py` |
| `backend/matching.py` | 标准化元数据并计算跨平台匹配置信度 | 由 Repository 调用 |
| `backend/database/repository.py` | 收藏、反馈、跨平台链接和人工审核的业务接口 | Python 后端调用 |
| `scripts/review_cross_platform_matches.py` | 列出、确认或拒绝待审核匹配 | 命令行 |

## 数据模型

`songs` 保存**一条投稿视频**的元数据，因此同一首曲在不同站点可以各有一条记录。

- `platform_videos` 保存稳定的平台标识：Niconico 的 `sm...` 等视频号与 Bilibili 的 `BV...`；
- `canonical_songs` 表示被确认后的“同一首曲目”；
- `video_match_suggestions` 保存匹配分数、各字段证据及 `pending` / `confirmed` / `rejected` 审核状态；
- `user_favorites`、`user_feedback`、`user_profiles` 保存个人数据。

已有的旧版 Niconico `songs` 数据会在第一次 Bilibili 同步时自动登记为 Niconico 平台视频，不需要重建数据库。

## 导入 Niconico 新曲

默认使用 Niconico Snapshot Search API，导入 `VOCALOID` 查询结果：

```powershell
python scripts/crawl_niconico.py --query VOCALOID --max-pages 10
```

常用参数：

```text
--database-url sqlite:///data/vocadig.db  指定本地数据库
--query <关键词>                           搜索词
--max-pages <数量>                         最多抓取页数
--proxy <代理地址>                         HTTP(S) 代理
--user-agent <名称>                        请求 User-Agent
```

重复执行会更新已有视频的元数据，只把此前不存在的视频计入新增数。

## 同步 Bilibili 收藏夹

### 1. 获取收藏夹 ID

打开目标收藏夹页面，从其 URL 中取得 `fid` 对应的数值；该数值作为 `--media-id`。请确认该账户有权读取目标收藏夹。

### 2. 仅在当前终端设置登录 Cookie

脚本从环境变量读取完整的 Cookie 请求头，不会把 Cookie 写入数据库或配置文件。请不要提交 Cookie、截图或分享给他人。

```powershell
$env:BILIBILI_COOKIE = "浏览器请求中的完整 Cookie 内容"
python scripts/sync_bilibili_favorites.py --media-id 123456 --user-id nagi
```

可选参数：

```text
--database-url <URL>       指定数据库
--cookie-env <变量名>      默认 BILIBILI_COOKIE
--max-pages <数量>         最多读取的收藏夹页数
```

同步会为每个 Bilibili 视频建立 `bilibili:BV...` 曲库记录，并以 `bilibili_favorite` 来源加入指定本地用户的收藏。重复同步不会重复创建收藏。

## 跨平台匹配与人工确认

每个同步的 Bilibili 视频会与本地已知的 Niconico 视频比较：

| 字段 | 权重 |
| --- | ---: |
| 曲名 | 60% |
| P 主 | 20% |
| 歌姬 | 10% |
| 时长 | 10% |

曲名会进行 Unicode 标准化、忽略大小写，并去掉常见括号附注。时长在 3 秒内视为完全一致；超过 45 秒则不相似。

- 置信度低于 `0.65`：不建立建议；
- `0.65` 及以上：建立待审核建议；
- `0.90` 及以上，且第一名比第二名至少高 `0.08`：自动确认；
- 其他高相似度结果：必须由用户确认或拒绝。

查看待审核项：

```powershell
python scripts/review_cross_platform_matches.py
```

确认或拒绝：

```powershell
python scripts/review_cross_platform_matches.py --suggestion-id 12 --confirm
python scripts/review_cross_platform_matches.py --suggestion-id 13 --reject
```

确认后，两条视频记录会链接到同一个规范曲目；后端可通过 `LibraryRepository.get_platform_counterparts(song_id, "niconico")` 查询 Bilibili 视频对应的 Niconico 投稿。

## 默认收藏夹与定期同步

可以为一个本地用户保存多个需要长期监控的收藏夹：Niconico 使用 mylist ID，Bilibili 使用收藏夹 `media_id`。收藏夹配置只保存 Cookie 的**环境变量名称**，不会保存 Cookie 本身。

添加或更新一个默认收藏夹：

```powershell
python scripts/manage_default_collections.py add --user-id nagi --platform bilibili --remote-id 123456 --name "常听 Vocaloid" --credential-env BILIBILI_COOKIE --interval-minutes 360
python scripts/manage_default_collections.py add --user-id nagi --platform niconico --remote-id 987654 --name "Nico 收藏" --credential-env NICONICO_COOKIE --interval-minutes 360
```

`--name` 是可选项；省略时，首次成功同步会自动采用平台上的收藏夹名称。显式指定名称后，后续同步不会覆盖它。

查看已启用的收藏夹：

```powershell
python scripts/manage_default_collections.py list --user-id nagi
```

停止监控并删除一个收藏夹配置（先用 `list` 查看编号）：

```powershell
python scripts/manage_default_collections.py remove --user-id nagi --collection-id 1
```

该操作会删除收藏夹配置和它的成员快照，并删除只属于该收藏夹的歌曲及其收藏、反馈和平台关联；仍在其他已监控收藏夹中的歌曲会保留。

执行一次到期检查；只有距离上次成功同步超过该收藏夹的 `--interval-minutes` 时才会访问平台：

```powershell
$env:BILIBILI_COOKIE = "浏览器请求中的完整 Cookie 内容"
$env:NICONICO_COOKIE = "浏览器请求中的完整 Cookie 内容"
python scripts/sync_default_collections.py --user-id nagi
```

也可以把浏览器扩展导出的 Cookie JSON 文件路径直接设为环境变量。同步程序会只选择目标站点域名下的全部 Cookie，并将它们作为请求头发送：

```powershell
$env:BILIBILI_COOKIE = "C:\path\to\bilibili-cookies.json"
python scripts/sync_default_collections.py --user-id nagi --force
```

`--force` 可忽略间隔立即同步。该脚本适合作为 Windows 任务计划程序、cron 或其他调度器的定时任务入口。

每次完整同步都会记录收藏夹成员快照，并输出 `+新增 -移除 =未变`。移除项仅从该收藏夹的成员记录中标记为不再存在，**不会删除**本地曲目、手动收藏或历史反馈，避免误丢个人数据。

## 作为 Python 模块使用

`LibraryRepository` 是数据库操作边界。示例：

```python
from backend.database.database import create_database, create_session_factory
from backend.database.repository import LibraryRepository

sessions = create_session_factory("sqlite:///data/vocadig.db")
create_database(sessions.kw["bind"])

with sessions() as session:
    library = LibraryRepository(session)
    niconico_uploads = library.get_platform_counterparts(
        "bilibili:BV1xxxxxxx", "niconico"
    )
```

## 测试

运行离线测试：

```powershell
python -m pytest -q
```

现有测试覆盖曲库 CRUD、Niconico 导入、默认收藏夹差异检测，以及 Bilibili 收藏同步、自动匹配和人工确认流程。网络请求均通过可替换 HTTP 客户端隔离，测试不依赖真实账户或网络。
