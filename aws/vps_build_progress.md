# VPN VPS 构建进度

**构建日期:** 2026-05-23
**对应教程:** [vpn_build_plan.md](../vpn_build_plan.md)

---

## 基本信息

| 项 | 值 |
|---|---|
| Provider | AWS Lightsail |
| Region | `ap-southeast-2` (Sydney) |
| Plan | $12 USD/月(头 90 天免费)— 实际选了 2 GB 档(原计划 $7/1GB) |
| 资源 | 2 GB RAM · 2 vCPU · 60 GB SSD · 1.5 TB transfer |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | `6.17.0-1010-aws` |
| Network | Dual-stack(IPv4 + IPv6) |
| 实例名 | `auto-win-ubuntu-sydney` |
| **Static IP (IPv4)** | **`52.64.70.157`** (名:`sydney-static`) |
| IPv6 | `2406:da1c:69:2200:f22e:50a7:91fd:ce75` |
| Private IPv4 | `172.26.12.191` |
| Username | `ubuntu`(passwordless sudo) |
| 防火墙 | TCP 22 (Any IPv4/v6) · 80/443 全关 |
| Default SSH key | `/Users/wayne/Documents/Trade/aws/LightsailDefaultKey-ap-southeast-2.pem` |
| 域名 | `marketingblogs.org`(节点子域:`analytics.marketingblogs.org`) |

**SSH 命令:**
```bash
ssh -i /Users/wayne/Documents/Trade/aws/LightsailDefaultKey-ap-southeast-2.pem ubuntu@52.64.70.157
```

---

## 阶段 3: 系统初始化 — ✅ 完成

- [x] `apt update && apt upgrade -y` — 已是最新内核,无需 reboot
- [x] 安装 `curl socat ufw fail2ban`(以及自带 nginx-light 依赖)
- [x] ufw 规则:`deny incoming` · `allow outgoing` · 仅放 22/tcp(v4+v6)
- [x] fail2ban v1.0.2 enable + active
- [ ] (跳过)ed25519 SSH 密钥升级 — 后续需要时再做

**版本:**
- ufw 0.36.2
- Fail2Ban v1.0.2

---

## 阶段 4: Xray 安装 — ✅ 完成

| 项 | 值 |
|---|---|
| **Xray 版本** | **v26.3.27** (`d2758a0`, go1.26.1, linux/amd64) |
| 二进制 | `/usr/local/bin/xray` (35 MB) |
| 配置目录 | `/usr/local/etc/xray/` |
| 日志目录 | `/var/log/xray/` |
| systemd unit | `xray.service`(enabled, active) |
| 内存占用 | ~5 MB |
| 安装脚本 | `github.com/XTLS/Xray-install` 官方一键 |

**⚠️ 已记录的废弃警告:**
> `WebSocket transport (with ALPN http/1.1, etc.) is deprecated, not recommended for using and might be removed. Please migrate to XHTTP H2 & H3 as soon as possible.`

当前 ws 仍可用,长期可考虑迁 XHTTP H2/H3。

---

## 阶段 5: nginx 伪装站 — ✅ 完成

| 项 | 值 |
|---|---|
| **nginx 版本** | **nginx/1.24.0 (Ubuntu)** |
| 包 | `nginx-light` |
| 监听 | `127.0.0.1:8080` · `[::1]:8080`(仅本地) |
| 默认页 | `/var/www/html/index.nginx-debian.html`(615 字节) |
| 角色 | **Tunnel 入口 + WS 反代到 Xray + 默认伪装站**(架构修正后) |

---

## 阶段 6: Xray 配置 — ✅ 完成(架构已修正)

### 重要架构变更

**教程原方案**(Xray 在前 + fallback 到 nginx)**在 ws 网络下不工作** — Xray 的 `fallbacks` 字段只在 `network: tcp` 时生效,`network: ws` 不支持。结果非 WS 请求会拿到 Xray 自己的空 404。

**实际部署的架构(nginx 在前,反代 WS 到 Xray):**

```
Tunnel → 127.0.0.1:8080 (nginx)
            ├── /<ws-path> + Upgrade:websocket  →  127.0.0.1:8090 (Xray VLESS+ws)
            ├── /<ws-path> 无 upgrade header     →  404(像真 404,162 字节)
            └── 其他所有路径                      →  /var/www/html 静态页(200 字节)
```

### Xray 配置

| 项 | 值 |
|---|---|
| 监听 | **`127.0.0.1:8090`** |
| 协议 | VLESS over WebSocket(无 TLS,TLS 在 CF 边缘) |
| **UUID** | **`dc4a1417-7ba3-4079-b40b-fd528ffebd9e`** |
| **WS path** | **`/2f9a853f07e82681`** |
| `decryption` | none |
| `fallbacks` | (已移除,nginx 接管路由) |

UUID 和 path 备份在 `/usr/local/etc/xray/.uuid` 和 `.wspath`(VPS 上)。

### 验证结果

| 测试 | 结果 |
|---|---|
| `curl 127.0.0.1:8080/` | 200, 615 bytes, nginx welcome ✓ |
| `curl 127.0.0.1:8080<ws_path>` 无 upgrade 头 | 404, 162 bytes(伪装) ✓ |
| `curl <ws_path>` 带 upgrade 头 | 转发到 Xray ✓ |
| `ss -ltn` | 仅 8080/8090 监听,均 localhost only ✓ |

---

## 阶段 7: cloudflared — ✅ 完成

| 项 | 值 |
|---|---|
| **cloudflared 版本** | **2026.5.0**(2026-05-13 build) |
| 安装方式 | apt(`pkg.cloudflare.com/cloudflared`) |
| 软件源 GPG | `/usr/share/keyrings/cloudflare-main.gpg` |
| sources.list | `/etc/apt/sources.list.d/cloudflared.list` |
| 二进制 | `/usr/bin/cloudflared` (38 MB) |
| systemd unit | 尚未注册(待 Stage 8 `service install <token>`) |

---

## 阶段 8: CF Tunnel 配置 — ✅ 完成

### Tunnel 元信息

| 项 | 值 |
|---|---|
| Tunnel name | `aws-sydney-tunnel` |
| **Tunnel ID** | `e7b1e381-f44f-4165-a856-37d8d4bb56e3` |
| Connector ID | `cb6da332-0e8b-4769-becc-31902fe6c3c1` |
| cloudflared version | 2026.5.0 |
| Edge locations(4 路冗余) | mel01, syd05, mel02, syd06 |
| Protocol | QUIC |
| Status | Healthy |

### Public hostname route(最终版,只有 1 条)

| Field | Value |
|---|---|
| Hostname | **`marketingblogs.org`**(apex,无子域名) |
| Path | (空,匹配所有) |
| **Service URL** | **`http://localhost:8080`**(必须显式 `http://`)|

### 自动创建的 DNS 记录

| Type | Name | Target |
|---|---|---|
| CNAME(flattened) | `marketingblogs.org`(apex) | `e7b1e381-f44f-4165-a856-37d8d4bb56e3.cfargotunnel.com` |

### 踩过的坑 #1:Service URL 必须显式 `http://`

CF Dashboard 默认会给 `localhost:8080` **自动补 `https://` 前缀**。
但 nginx 在 8080 只听明文 HTTP(TLS 由 CF 在边缘做了),所以填 `https://` 时 cloudflared 会跑 TLS 握手 → 失败 → 502。

**修复:** Routes → Edit → Service URL = `http://localhost:8080`(显式带 `http://`)。

完整技术理由(三段加密边界、为什么 loopback 不需要 TLS)见 `domain.md` 的 "Cloudflare Tunnel 配置" 一节。

### 踩过的坑 #2:`analytics.` 子域伪装是过度设计

曾经的路线是 `analytics.marketingblogs.org` 当节点入口,主域留给博客。后来意识到:
- 子域上挂"假端点 stub" → 欲盖弥彰,反而像在解释什么
- 子域上挂博客 → 逻辑不通(分析端点上怎么有博客?)
- **直接用 apex,所有路径默认走博客 + 秘密 WS path 走 Xray** → 看着就是个普通博客,这才是最自然的伪装

**修复:** 删掉 analytics Tunnel route + 加 apex Tunnel route + nginx 简化为单 server_name `_` catch-all。最终架构见 `domain.md` 的 "域名架构" 一节。

---

## 客户端连接信息(最终,apex 版)

| 字段 | 值 |
|---|---|
| 协议 | VLESS |
| 地址 | **`marketingblogs.org`** |
| 端口 | 443 |
| UUID | `dc4a1417-7ba3-4079-b40b-fd528ffebd9e` |
| Encryption | none |
| Transport | ws |
| WS path | `/2f9a853f07e82681` |
| Host(ws header) | `marketingblogs.org` |
| TLS | tls(由 CF 提供 universal cert) |
| SNI | `marketingblogs.org` |
| Fingerprint (uTLS) | chrome |
| ALPN | h2,http/1.1 |
| Allow Insecure | false |

**节点 URI(直接导入客户端):**

```
vless://dc4a1417-7ba3-4079-b40b-fd528ffebd9e@marketingblogs.org:443?encryption=none&security=tls&sni=marketingblogs.org&fp=chrome&type=ws&host=marketingblogs.org&path=%2F2f9a853f07e82681#sydney-vpn
```

---

## 服务速查

| 服务 | systemd unit | 端口 | 状态 |
|---|---|---|---|
| nginx | `nginx.service` | 127.0.0.1:8080 (v4+v6) | active |
| Xray | `xray.service` | 127.0.0.1:8090 | active |
| cloudflared | `cloudflared.service` | (出站,无监听) | 待注册 |
| fail2ban | `fail2ban.service` | — | active |
| ufw | `ufw.service` | — | active |

## 关键文件

| 路径 | 说明 |
|---|---|
| `/usr/local/etc/xray/config.json` | Xray 配置 |
| `/usr/local/etc/xray/.uuid` | UUID 备份 |
| `/usr/local/etc/xray/.wspath` | WS path 备份 |
| `/etc/nginx/sites-available/default` | nginx 配置 |
| `/var/log/xray/{access,error}.log` | Xray 日志 |
| `/var/log/nginx/{access,error}.log` | nginx 日志 |
