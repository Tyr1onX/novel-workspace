# Fanqie Data Probe

`shared/tools/fanqie_data_probe.py` is the repository's read-only collector for the authenticated Fanqie author dashboard.

## Safety boundary

The probe may persist only sanitized analytics needed to evaluate a work:

- book-level reader / shelf / follow / reminder / comment summary metrics;
- verified income totals already shown in the author dashboard;
- chapter metadata needed for quality analysis: chapter number, title, word count, publish time;
- chapter completion rate and chapter follow-read rate;
- traffic-source counts for the dashboard's 7 / 14 / 30 day views.

The probe must not persist or print authentication material or private account data. In particular, snapshots must never contain cookies, `msToken`, `a_bogus`, signed query strings, `book_id`, `item_id`, phone / identity / bank fields, comments or messages, or chapter bodies.

## Snapshot schema v2

Snapshots remain under:

`novels/<project>/platform-sync/analytics/snapshots/<timestamp>.json`

Existing `stats` and `income` fields are preserved for backward compatibility. Schema v2 adds:

- `quality.stats_update_time`
- `quality.chapters[]`
  - `chapter_number`
  - `title`
  - `word_number`
  - `publish_time`
  - `read_completion_rate`
  - `follow_read_rate`
- `quality.word_completion`
- `traffic.7d / 14d / 30d`
  - `start_date`
  - `end_date`
  - `dates[]`
  - `sources.bookstore`
  - `sources.category`
  - `sources.shelf`
  - `sources.continue_reading`
  - `sources.search`
  - `sources.other`

The source mapping is taken from the dashboard's own traffic-composition request:

- `24` → bookstore / 书城
- `27` → category / 分类
- `26` → shelf / 书架
- `25` → continue_reading / 继续阅读
- `28` → search / 搜索
- `29` → other / 其他

Chapter quality uses the dashboard's chapter list request:

- `stats_type=3` → chapter completion rate / 章节完读率
- `stats_type=4` → chapter follow-read rate / 章节跟读率

The separate dashboard tab named `字数读完率` is intentionally marked unavailable until its numeric payload is mapped to a stable, unambiguous read-only API field. Do not infer or relabel another metric merely to fill that field.

## Collection strategy

For deep metrics the probe observes the dashboard's own authenticated GET responses after navigating and switching analytics tabs. Signed request parameters exist only in memory and are discarded. The probe does not construct or persist private request URLs.

A missing deep metric is fail-soft: summary analytics and income can still be captured. Missing values must remain missing rather than being guessed.
