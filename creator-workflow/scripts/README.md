# Scripts

当前只保留一个脚本：`queue.py`。

## 校验台账

```bash
python creator-workflow/scripts/queue.py validate
```

校验内容：

- `data/posts.csv`
- `data/douyin_posts.csv`
- 必要字段是否存在
- `id` 是否重复
- `status` 是否合法
- `scheduled_at` 是否是 ISO 时间
- 已登记的 `archive_path` 是否真实存在

## 查看待发布内容

```bash
python creator-workflow/scripts/queue.py due --platform douyin
```

只输出 `ready` 或 `scheduled` 且已到时间的内容。它不会上传、发布或修改台账。
