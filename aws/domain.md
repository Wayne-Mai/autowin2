# marketingblogs.org

**注册商:** Cloudflare Registrar
**注册日期:** 2026-05-23
**到期日:** 2027-05-23
**Domain Status:** `ok` · `addperiod`(60 天内退款窗口)
**DNSSEC:** unsigned(建议日后在 CF 后台启用)

---

## DNS

托管在 Cloudflare,nameservers:

| Nameserver |
|---|
| `BILL.NS.CLOUDFLARE.COM` |
| `JESSICA.NS.CLOUDFLARE.COM` |

### 当前 DNS 记录

| Type | Name | Target | 谁创建 |
|---|---|---|---|
| CNAME(flattened) | `marketingblogs.org`(apex) | `e7b1e381-f44f-4165-a856-37d8d4bb56e3.cfargotunnel.com` | CF Tunnel 自动创建 |

> CF 用 **CNAME flattening** 在 apex 上实现 CNAME(标准 DNS 不允许 apex CNAME,CF 在边缘自动展平)。

---

## 注册人信息(被 CF WHOIS Privacy 隐藏)

| 字段 | 值 |
|---|---|
| 姓名 | LUCIA BLOG |
| 邮箱 | waynemaibutterfly@gmail.com |
| 电话 | +966.0546212341 |
| 国家 / 城市 | SA / Thuwal / Makkah |
| 地址 / 邮编 | Harbour / 23955 |

> 公共 WHOIS 查询返回 `REDACTED FOR PRIVACY`,实际数据仅 CF + 注册局可见。Admin / Tech 联系人与 Registrant 相同。

---

## 域名架构(最终,简化版)

**只用 apex,不用任何子域名。** 这是几次迭代后的最终选择。

| 角色 | 域名 | 内容 |
|---|---|---|
| 主入口(且唯一入口) | `marketingblogs.org` | Hugo 营销博客 + 秘密 WS 路径 → Xray |

### 为什么不用子域名(踩坑历史)

之前试过 `analytics.marketingblogs.org` 当节点入口,主域留给博客。后来想清楚反而不如直接用 apex:

| 维度 | 子域名方案(已弃) | apex 方案(当前) |
|---|---|---|
| 攻击者看到长连接 | "为什么连分析端点这么久?" — 异常 | "在读博客" — 自然 |
| 子域名上挂博客 vs 假端点 | 挂博客 = 逻辑不通,挂假端点 = 欲盖弥彰 | 一个 URL,所有路径默认走博客 |
| 现代博客是否有 WebSocket | 几乎不会用 analytics 子域跑 WS | 营销博客挂 Intercom / Crisp / live comments 普遍用 WS |
| GFW 流量分析 ML | "analytics 子域 + 长连接" 异常组合 | "博客 + 长连接" 训练集里出现过无数次 |
| 总结 | 多此一举,反而更可疑 | 越简单越像 |

### 子域命名禁用词(以备日后参考)

千万别在子域名出现:`vpn / proxy / xray / clash / v2ray / tunnel / ss / trojan` — GFW 扫描器和人眼都对这些敏感。如果以后要用子域,应该贴合主域主题(如 `cdn.`, `static.`, `m.`, `docs.`)。

---

## Cloudflare Tunnel 配置

### Tunnel 元信息

| 项 | 值 |
|---|---|
| Tunnel name | `aws-sydney-tunnel` |
| **Tunnel ID** | `e7b1e381-f44f-4165-a856-37d8d4bb56e3` |
| Connector ID(VPS 上的 cloudflared 实例)| `cb6da332-0e8b-4769-becc-31902fe6c3c1` |
| Replica origin IP | `2406:da1c:69:2200:f22e:50a7:91fd:ce75`(VPS 的 IPv6) |
| Edge locations(冗余 4 路) | `mel01`, `syd05`, `mel02`, `syd06` |
| Protocol | QUIC |
| cloudflared version | 2026.5.0 |
| Architecture | linux_amd64 |

### Public hostname route(只有 1 条)

| Field | Value |
|---|---|
| Type | Published application |
| Hostname | `marketingblogs.org`(apex,subdomain 字段留空)|
| Path | (空 = match all) |
| **Service URL** | **`http://localhost:8080`** ← 必须 `http://`,见下文 |

### 🚨 关键:Service URL 为什么是 `http://` 不是 `https://`

**这是个隐蔽坑 — CF Dashboard 默认会给 `localhost:8080` 自动补 `https://`,但那会导致 502。**

**架构里的 TLS 边界:**

```
[客户端] ─HTTPS(CF Universal SSL)─> [CF 边缘] ─加密 Tunnel(QUIC,内置 mTLS)─> [cloudflared] ─HTTP─> [nginx]
                                                                                                ↑
                                                                                  同一台 VPS 的 loopback,
                                                                                  不是真网络
```

**三段加密情况:**

| 段 | 是否加密 | 由谁 |
|---|---|---|
| 客户端 → CF 边缘 | ✅ TLS 1.3 | CF Universal SSL |
| CF 边缘 → cloudflared | ✅ QUIC + mTLS-equivalent | Tunnel 协议内置 |
| **cloudflared → nginx** | ❌ HTTP(loopback)| 不需要 |

**为什么 loopback 不需要 TLS:**

- `127.0.0.1` 数据走的是**内核 buffer**,不是网卡
- 没有任何中间节点,**没有可被监听的物理路径**
- 唯一能看到这段流量的是 VPS 上的 root 用户
- 如果攻击者已经拿到 VPS root,他能改 Xray 配置 / 看 cloudflared 内存 / 读所有文件 — **TLS 救不了已经攻破的机器**

**强行加 HTTPS 的代价(零收益):**

- 要给 `localhost` 生成自签证书(LE 不给 localhost 签)
- cloudflared 默认不信任自签 → 要加 `noTLSVerify: true` 或导入 CA
- 多一份 CPU 加解密开销
- 多一个故障点(自签证书有效期、cloudflared 配置漂移)
- **业界准则:加密的边界应该和"信任边界"重合,信任边界内的加密是仪式不是安全**

**对比 — 什么时候 Service URL 该用 https:**

| 场景 | Service URL |
|---|---|
| 本架构(cloudflared + nginx 同机)| `http://localhost:8080` ✅ |
| nginx 和 cloudflared 跨容器(Docker bridge)| `http://nginx:80` 或 `https://nginx:443`(如果容器内有真证书)|
| nginx 在另一台 VPS,跨网络回源 | `https://` + 真域名 + 真证书 ✅ |

---

## nginx 路由(VPS 上)

唯一一个 server 块,catch-all server_name `_`,按 path 分流:

| Path | 行为 |
|---|---|
| `/2f9a853f07e82681`(秘密 WS path)+ `Upgrade: websocket` | 反代到 Xray `127.0.0.1:8090` → 翻墙 |
| 同 path 但无 upgrade 头 | 返回 `404`(像真 404,162 字节) |
| 其他任意路径 | `try_files $uri $uri/ /index.html` → SPA 风格 fallthrough 到 Hugo 博客 |

> SPA fallthrough 的好处:扫描器 / 主动探测访问任何**乱编路径**(`/admin`, `/api/v1`, etc.)都会看到博客首页,看起来就像一个普通的 SPA 博客在做客户端路由。

---

## 默认页:Hugo 静态市场营销博客(伪装)

| 项 | 值 |
|---|---|
| 站名 | Marketing Blogs |
| 技术栈 | Hugo v0.145.0(brew) + 自写极简 layouts(无第三方主题) |
| 本地源码 | `/Users/wayne/Documents/Trade/aws/hugo/` |
| 构建命令 | `cd hugo && /usr/local/Homebrew/Cellar/hugo/0.145.0/bin/hugo --minify` |
| 构建输出 | `hugo/public/` |
| VPS 部署目录 | `/var/www/html/`(由 nginx serve) |
| 部署 | `rsync -avz --delete -e "ssh -i KEY" public/ ubuntu@VPS:/tmp/site/ && ssh ... 'sudo rsync -a --delete /tmp/site/ /var/www/html/'` |
| 内容 | 6 篇市场营销主题博文(SEO / 内容策略 / 邮件 / 归因 / 品牌 / MQL)+ About 页 |

> 之前试过 PaperMod / ananke 主题都要求 Hugo ≥ 0.146,而 brew 装的是 0.145。改成自写 layouts(`layouts/_default/baseof.html` + `list.html` + `single.html` + `partials/head.html`)→ 完全没有外部主题依赖,**Hugo 任何版本都能 build**。

详见 `hugo/README.md`。

---

## 与 VPN 节点的关系

| 视角 | 看到什么 |
|---|---|
| 普通访客打开 `https://marketingblogs.org` | Marketing Blogs Hugo 首页(伪装) |
| 客户端发 vless+ws 到 `https://marketingblogs.org/2f9a853f07e82681` 带 `Upgrade: websocket` | nginx 识别 → 反代到 Xray(`127.0.0.1:8090`) → 翻墙 |
| 主动探测者 / GFW 探任意路径 | 返回博客首页(SPA fallthrough)或 404,没有任何"代理服务"特征 |
| GFW SNI 观察 | SNI 是 `marketingblogs.org`(ECH on 后加密),看到的就是"这人在访问一个营销博客",完全合理 |

---

## 历史决策记录

| 时间 | 决策 | 理由 |
|---|---|---|
| 2026-05-23 上午 | 注册 `marketingblogs.org` | 域名本身就像"营销博客",和 Hugo 内容主题完美契合 |
| 2026-05-23 中午 | 用 `analytics.` 当节点子域 | 想着 analytics 子域加 stub 当伪装 |
| 2026-05-23 下午 | **改为只用 apex,弃用 analytics** | 子域伪装反而欲盖弥彰;apex 直接挂博客 + 秘密 path,看起来就是普通博客 |

---

## 浏览器访问 vs VPN 客户端访问 — 对比

**核心 trick:同一个域名 `https://marketingblogs.org/`,同一台 nginx,**根据 HTTP 请求的路径 + Upgrade 头**分流给两种完全不同的后端**。**这是这套架构的灵魂。

### 网络路径 — 两种用户完全一样

```
[Mac/iPhone] ─HTTPS─> [CF 边缘] ─Tunnel─> [cloudflared] ─http─> [nginx :8080]
                                                                       │
                                                            分流就发生在这里
                                                                       │
                          ┌────────────────────────────────────────────┴────────────────────────────────────────────┐
                          ▼                                                                                          ▼
              GET / HTTP/1.1                                                       GET /2f9a853f07e82681 HTTP/1.1
              Host: marketingblogs.org                                             Host: marketingblogs.org
              (无 Upgrade 头)                                                       Upgrade: websocket
                                                                                   Connection: Upgrade
                                                                                   Sec-WebSocket-Key: ...
                          │                                                                                          │
                          ▼                                                                                          ▼
              location / { try_files ... }                                         location = /2f9a853f07e82681 {
              返回 /var/www/html/index.html                                          proxy_pass http://127.0.0.1:8090;
              (Hugo 博客 HTML)                                                       ... 转发给 Xray ...
                                                                                   }
                          │                                                                                          │
                          ▼                                                                                          ▼
              HTTP/1.1 200 OK                                                      HTTP/1.1 101 Switching Protocols
              Content-Type: text/html                                              Upgrade: websocket
              <html>...Marketing Blogs...</html>                                   <进入持久 WebSocket,后续是二进制流>
                                                                                                       │
                                                                                                       ▼
                                                                                   Xray 解 VLESS 头(UUID 校验),
                                                                                   把 WS payload 当成普通 TCP 流转发到
                                                                                   freedom outbound → 互联网
```

### 关键差异表

| 维度 | 浏览器(普通访问) | VPN 客户端 |
|---|---|---|
| URL | `https://marketingblogs.org/` | `https://marketingblogs.org/2f9a853f07e82681` |
| HTTP 方法 | GET | GET + WebSocket upgrade |
| 关键请求头 | 无 `Upgrade` | `Upgrade: websocket`, `Connection: Upgrade`, `Sec-WebSocket-Key: ...` |
| nginx 匹配的 location 块 | `location /`(catch-all) | `location = /2f9a853f07e82681`(exact match) |
| nginx 后端 | 直接读 `/var/www/html/` 文件 | `proxy_pass http://127.0.0.1:8090`(Xray) |
| 响应 | `200 OK` + HTML 内容 | `101 Switching Protocols` → 进入持久双向流 |
| 数据格式 | 一次请求-一次响应 | 持久 WebSocket,内部跑 VLESS 协议 |
| 用了多久 | 几百 ms,加载完关闭 | 持久,直到客户端断开 |
| 服务程序 | nginx 直接服务 | Xray 解 VLESS → freedom 出站 → 真实目标网站 |

### 一句话总结这套设计

> nginx 是一个"会变身的接待员"。同一个门牌号(`marketingblogs.org`),它根据访客敲门的暗号(URL path + Upgrade 头)决定带你去博客阅览室还是 VPN 通道,**而站在门外的人(GFW / 攻击者)只能看到有人在敲这家店的门,看不到接待员怎么分流**。

### 为什么 GFW 看不出差别

整个流程套了 TLS,GFW 只能看到这些**外层信号**:

| 外层可见信号 | 浏览器情况 | VPN 客户端情况 | GFW 怎么判断 |
|---|---|---|---|
| 目的 IP | CF anycast IP | CF anycast IP | 一样,无信息 |
| 目的端口 | 443 | 443 | 一样,无信息 |
| TLS SNI | `marketingblogs.org` | `marketingblogs.org` | 一样;开 ECH 后干脆加密 |
| TLS Client Hello 指纹(JA3) | Chrome / Safari | Chrome(uTLS 伪装) | 一样 |
| 是否 WebSocket | 看不到(在 TLS 里) | 看不到 | — |
| 连接时长 | 5-30 秒(浏览完关闭) | 几分钟到几小时 | **唯一的概率性信号**:长连接 |
| 流量模式 | 突发下载页面 + 偶尔 ws(chat 等) | 持续双向流 | **概率性信号**:持续双向 |

GFW 能拿到的最多是**长连接 + 持续双向流量**这种统计特征,而这恰好是现代博客挂 Intercom/Crisp/在线客服的典型行为 — 训练数据里这种 pattern 出现过无数次,机器学习模型不太会单凭这个就判定为代理。

### 同一个 TLS 证书覆盖两种用途

CF 为 `marketingblogs.org` 自动签发的 Universal SSL 证书是给整个 zone 用的 — 浏览器看到的合法证书 = VPN 客户端看到的合法证书 = **同一张**。从 PKI 角度,这两类用户在 CF 眼里没有任何区别。

### 这个设计的"防御深度"

| 攻击者动作 | 我们的反应 |
|---|---|
| 主动探测 `https://marketingblogs.org/`(标准 GET) | 返回 200 + 真博客内容,看着就是个营销博客 |
| 主动探测 `https://marketingblogs.org/admin` / 任意乱编路径 | 返回 200 + 博客首页(SPA fallthrough),看着像现代 SPA 路由 |
| 主动探测 `https://marketingblogs.org/2f9a853f07e82681`(凑巧猜中 path,但没带 upgrade 头) | nginx `if` 检测 `$http_upgrade != "websocket"` → 返回 404,看着就是普通缺失页面 |
| 暴力扫所有路径 | 全部返回 200(博客)或 404(假死),没有任何"代理"特征 |
| 截 TCP 包做模式识别 | 看到的全是加密 TLS,看不出来里面是 HTML 还是 WS |
| 拿到 VPS IP 直连扫端口 | **拿不到** — VPS IP 不在 DNS 里,无入站端口可扫 |

---

## 待办

- [x] apex DNS CNAME(CF Tunnel 已自动创建)
- [x] CF SSL/TLS → Encryption mode = **Full**(用户已配)
- [ ] CF SSL/TLS → Edge Certificates → **ECH = ON**(强烈建议,加密 SNI)
- [ ] CF SSL/TLS → Always Use HTTPS = ON
- [ ] CF SSL/TLS → Minimum TLS = 1.2 / TLS 1.3 = ON
- [ ] (可选)CF DNSSEC 启用
- [ ] (可选)加 `www.marketingblogs.org` Tunnel route 让 www 也通(目前 www 子域没 DNS)
- [ ] (DEFERRED)Xray ws → XHTTP H2/H3 迁移
