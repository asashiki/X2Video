# 热帖速览短视频的画面与流程

调研对象：抖音 / TikTok、B 站竖屏、YouTube Shorts、X 上「外网热帖 / tweet recap / 推文解说」类营销号。用来改 X2Video 的分镜，不是学术综述。

## 结论先说

1. **语速略快是类型惯例，不是 bug。** 抖音竖屏常见把配音提约 10–15%，因为完播率优先、观众划走很快。[来源：平台适配教程写明抖音版「语速提升 15%」](https://blog.csdn.net/weixin_29607511/article/details/157485209)
2. **开场必须是独立画面。** 前 1–2 秒是标题卡 / bumper（一句钩子），第一条推文还没出现。X 时间线也要求 hook 落在约 1.5 秒内。[Kompozy: trim so the hook lands in the first 1.5 seconds](https://kompozy.io/repurpose-from/youtube-to-x-twitter)
3. **禁止「小卡片贴在大黑底上」。** 同类成片几乎都会填满 9:16：推文截图铺满或居中放大，背后是模糊实景 / GIF / 媒体图，而不是纯黑。[TikTok aesthetic tweet tutorials: tweet + full-screen moving background](https://www.youtube.com/watch?v=0Acx4PzmKxc)；[Blotato: tweet card over photo/video + backdrop blur](https://help.blotato.com/api/visuals/9714ae5c-7e6b-4878-be4a-4b1ba5d0cd66)；[BrandGhost: 9:16 把 tweet 放中间或上三分之一，周围用 B-roll 填](https://blog.brandghost.ai/posts/how-to-turn-a-tweet-into-a-screenshot/)
4. **短推文时把中文当「花字」铺在下半屏**，原帖当收据放在上中，不要把小卡片顶到最上面留半屏黑。
5. **字幕避开平台 UI。** 抖音/Shorts 底栏和顶栏会吃掉画布；内容要落在中间安全区，底留口播花字。[NemoVideo: 抖音安全区远小于 1080×1920](https://www.nemovideo.com/zh-CN/blog/seedance-2-vertical-video-tiktok-reels)

## 标准流程（一条 N 条合集）

```
0:00–0:02  开场卡：一句钩子 + 栏目名（今日外网）
0:02–     条目循环：
           大号序号
           模糊背景（推文图 / 头像拉满）
           放大的推文卡（居中）
           中文爆点花字（下半屏）
           轻微推镜
           下一条硬切或短淡
结尾 1 句   可叠在最后一条尾或单独黑卡
```

每条 12–20 秒；5–7 条合计约两分钟。

## 各平台怎么填空

| 做法 | 谁在用 | 短推文时 |
| --- | --- | --- |
| 推文卡 + 全屏动态/模糊背景 | TikTok aesthetic tweet、Blotato | 背景负责填满，卡片可以偏大 |
| 推文截图几乎铺满 9:16 | YouTube Shorts tweet recap、TweetsGen | 字号加大，暗色卡 |
| 绿幕/分屏把推文当背景 | X Commentary、TikTok green screen | 推文就是底，人声在上 |
| 纯黑底小卡片 | — | **对标账号几乎不用，X2Video 上一版踩了这个坑** |

## 封面（和视频不是同一张图）

抖音信息流封面是 **3:4（1080×1440）**，不是 9:16。个人主页会把 9:16 封面裁成 3:4，底 25% 被标题/作者挡住。[色彩韵 2026 封面尺寸](https://www.secaiyun.com/docs/short-video-cover-size-guide-2026-05-23.html)

资讯号封面要素：

- 最上：日期（8月27日）+ 栏目名
- 中间安全区：≤15 字大标题（今天最炸的那一句）
- 底 25%：**留空**，不放字
- 标题字号要大到缩略图也能读（约 60–80px 起）

B 站竖屏封面可用 9:16，但自动化应默认先出 3:4，人工上传时按平台选。

## 时效

营销号新闻的生命是「哪一天」。对标账号每条都会报日期；过了这一周就不是热帖速览。自动化必须：

- 搜索窗口默认 24h，硬上限 7 天
- 画面上写「8月27日」，口播第一句也带这个日期
- 封面日期与成片日期一致
- 不靠模型「记得写日期」：渲染层补上

## X2Video 对照

- 要抄：独立开场卡、模糊铺满背景、卡片居中放大、中文花字占下半、语速 +10% 左右、3:4 封面、每条带日期。
- 别抄：出镜绿幕（无真人素材）、花哨综艺花字彩虹描边（科技速览会显得廉价）。

## 已落地（自动化）

- 花字：14 字以内爆点，描边，不是整段译文
- 每条带「今日外网」栏目 + 几月几号
- 轻微推镜（Ken Burns）
- 可选 BGM：`assets/bgm.mp3` 或 `bgm_path`
- 无人值守 QC：0 条选题失败、少于 3 条警告、成片过短失败
- Publish Kit 含审片清单和原帖链接
