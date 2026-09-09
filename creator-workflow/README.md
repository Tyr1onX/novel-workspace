# Creator Workflow

这个目录用于管理公众号、抖音和后续内容平台的选题、排期、发布状态与数据回收。

当前原则：

1. 小说内容继续留在 `novels/`，不和短内容混在一起。
2. 公众号与抖音统一放在 `creator-workflow/`。
3. 已生成内容先归档为 Markdown，方便检索、复用和二次改写。
4. 发布版末尾不再展示“资料来源”；内部归档可以保留参考信息，方便回查。
5. 抖音自动化优先走官方开放平台授权，不做绕登录、绕扫码、爬后台的实现。

## 目录

```text
creator-workflow/
  accounts/                 # 账号定位与规则
  archive/                  # 已做内容归档
  data/                     # 排期与数据台账
  docs/platforms/           # 平台工作流说明
  scripts/                  # 台账校验与待发布队列
  templates/                # 新内容模板
```

## 当前账号

- `闻舟会用`：50+ 数字生活、手机微信、AI 工具、防骗安全。
- `7BYTE`：不露脸计算机知识短视频。

## 当前最小工作流

```text
选题
  ↓
生成正文 / 视频脚本
  ↓
归档到 archive
  ↓
写入 data/posts.csv / data/douyin_posts.csv
  ↓
校验台账
  ↓
手动或自动发布
  ↓
回填发布时间、链接、播放/阅读数据
```

## 本地命令

在仓库根目录执行：

```bash
python creator-workflow/scripts/queue.py validate
python creator-workflow/scripts/queue.py due --platform douyin
```

`validate` 用来发现台账字段错位、状态拼写错误、归档路径丢失等问题。`due` 只列出到期内容，不会自动发布。

## 状态流转

```text
idea → draft → ready → scheduled → published → archived
                         ↓
                       failed
```

抖音真实发布接口必须等开放平台权限、授权账号和访问令牌确认后再接入。当前脚本只处理排期与校验，不做假发布。
