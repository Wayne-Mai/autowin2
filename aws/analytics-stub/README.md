# analytics-stub

伪装内容,放在 `analytics.marketingblogs.org` 上。**不是真的分析服务** — 它的存在只是为了让"GFW 主动探测 / 好奇路人"打开这个子域名时看到一个**像真的 analytics tracker 落地页**,而不是空白或可疑页面。

## 文件

- `index.html` — 单页静态 HTML,视觉风格与主站(Hugo 博客)完全一致(同一组 CSS 变量),看起来像同一家公司的子产品
- `pixel.gif` — 1×1 透明 GIF(42 字节),用于"假"的追踪像素端点

## 部署目标

VPS 上的 `/var/www/analytics/`,由 nginx 在 `analytics.marketingblogs.org` server_name 下 serve。

## 同步命令

```bash
KEY=/Users/wayne/Documents/Trade/aws/LightsailDefaultKey-ap-southeast-2.pem
VPS=ubuntu@52.64.70.157
SRC=/Users/wayne/Documents/Trade/aws/analytics-stub/

rsync -avz --delete -e "ssh -i $KEY" "$SRC" "$VPS:/tmp/analytics/"
ssh -i $KEY $VPS 'sudo rsync -a --delete /tmp/analytics/ /var/www/analytics/ && sudo chown -R www-data:www-data /var/www/analytics/'
```

## 假端点(nginx 配的,非静态文件)

| Path | 行为 |
|---|---|
| `/` | 返回 `index.html` |
| `/pixel.gif` | 返回那张 42 字节透明 GIF |
| `/collect` | nginx `return 204`(像真 tracker 一样) |
| `/event` | nginx `return 204` |
| `/healthz` | nginx `return 200 "ok\n"` |
| `/<ws-secret-path>` 带 `Upgrade: websocket` | 反代到 Xray,这才是 VPN 真入口 |
| 其他 | 落到 `index.html`(soft 404,看着像 SPA)|

## 为什么这设计有效

1. 配合域名主题 — "营销博客"配"分析子域"逻辑自洽
2. 视觉延续 — 头部 `Marketing Blogs / analytics` brand 和主站一致
3. 给出**可验证的端点列表** — `/healthz` 真返回 200,`/collect` 真返回 204,任何探测器跑过都对得上"this is a real analytics service"
4. 顶部一句 "no reader-facing content here" 自然解释了为什么没博文 — 不至于让访客觉得"这子域怎么是空的"

## 下次新 VPS 复用

整个目录拷贝走即可,只需要在新 VPS 的 nginx 里挂到对应 server_name。文件本身**无任何域名硬编码到不能换的程度**(主站链接 `marketingblogs.org` 字符串改成新域名即可)。
