# 抖音自动化工作流

## 目标

减少手动发布操作，把 7BYTE 视频形成稳定闭环：

```text
视频素材 + 标题 + 文案 + 话题 + 发布时间
  ↓
写入排期表
  ↓
到点发布
  ↓
回收播放、点赞、评论、分享等数据
  ↓
反推下一期选题
```

## 实现路径

只保留一条主路径：官方开放平台授权 + 本地排期器。

不做：

- 绕过扫码登录。
- 绕过验证码。
- 爬创作者中心后台页面。
- 模拟人工点击批量发布。

## 当前阶段

已完成：

- 账号定位归档。
- `data/douyin_posts.csv` 排期表。
- `scripts/queue.py` 台账校验与待发布查询。
- `templates/douyin-video.md` 视频脚本模板。

未接入：

- 上传视频。
- 创建视频。
- 数据回收。
- GitHub Actions 定时发布。

这些必须等开放平台应用、权限和授权流程确认后再接。

## 排期字段

见 `creator-workflow/data/douyin_posts.csv`。

关键字段：

- `id`：唯一内容 ID。
- `status`：`idea`、`draft`、`ready`、`scheduled`、`published`、`archived`、`failed`。
- `video_path`：仓库内或发布机上的视频文件路径。
- `cover_path`：封面路径。
- `scheduled_at`：计划发布时间，建议使用 ISO 格式。
- `published_at`：真实发布时间。
- `douyin_item_id`：发布成功后回填。
- `play_count`、`like_count`、`comment_count`、`share_count`：数据回收字段。

## 本地检查

```bash
python creator-workflow/scripts/queue.py validate
python creator-workflow/scripts/queue.py due --platform douyin
```

## 接入发布前必须补齐

1. 抖音开放平台应用。
2. 发布视频权限。
3. 授权账号。
4. 安全保存 access token 的位置。
5. 本地或服务器发布机。
6. 失败时的单次重试策略。
7. 发布后回填 `douyin_item_id` 的写入方式。

当前不写真实发布代码，避免产生不能运行的假自动化。
