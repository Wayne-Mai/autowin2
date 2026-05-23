# VPN VPS 构建进度

**构建日期:** 2026-05-23
**对应教程:** [vpn_build_plan.md](../vpn_build_plan.md)

---

## 基本信息

| 项 | 值 |
|---|---|
| Provider | AWS Lightsail |
| Region | `ap-southeast-2` (Sydney) |
| Plan | $7 USD/月(头 90 天免费) |
| 资源 | 1 GB RAM · 2 vCPU · 40 GB SSD · 1 TB transfer |
| OS | Ubuntu 24.04 LTS |
| Network | Dual-stack(IPv4 + IPv6) |
| 实例名 | `auto-win-ubuntu-sydney` |
| Static IP (IPv4) | **`52.64.70.157`** (Static IP 名:`sydney-static`) |
| IPv6 | `2406:da1c:69:2200:f22e:50a7:91fd:ce75` |
| Private IPv4 | `172.26.12.191` |
| Username | `ubuntu` |
| 防火墙(完成调整后) | TCP 22 (Any) · IPv6 同 · HTTP 80 已删除 |
| Default SSH key | `/Users/wayne/Documents/Trade/aws/LightsailDefaultKey-ap-southeast-2.pem` |
| 域名 | _待填_ |

---

## 阶段 3: 系统初始化

状态: ⏸ 待开始

- [ ] `apt update && apt upgrade -y`
- [ ] 安装 `curl socat ufw fail2ban`
- [ ] ufw 规则:`deny incoming` / `allow outgoing` / 仅放行 22
- [ ] fail2ban enable
- [ ] (可选) ed25519 SSH 密钥升级 + 禁用密码登录

**记录:**
- 内核版本:_待填_
- 系统更新前后包数量变化:_待填_

---

## 阶段 4: Xray 安装

状态: ⏸ 待开始

| 项 | 值 |
|---|---|
| Xray 版本 | _待填_ |
| 安装路径 | `/usr/local/bin/xray` |
| 配置目录 | `/usr/local/etc/xray/` |
| systemd unit | `xray.service` |

---

## 阶段 5: nginx 伪装站

状态: ⏸ 待开始

| 项 | 值 |
|---|---|
| nginx 版本 | _待填_ |
| 监听 | `127.0.0.1:8081`(仅本地) |
| 默认页 | nginx welcome(后续可替换 Hugo 静态站) |

---

## 阶段 6: Xray 配置

状态: ⏸ 待开始

| 项 | 值 |
|---|---|
| 监听 | `127.0.0.1:8080` |
| 协议 | VLESS over WebSocket(无 TLS,TLS 在 CF 边缘) |
| UUID | _待生成_ |
| WS path | _待生成_ |
| Fallback | `127.0.0.1:8081` → nginx 伪装站 |

---

## 阶段 7: cloudflared

状态: ⏸ 待开始

| 项 | 值 |
|---|---|
| cloudflared 版本 | _待填_ |
| 安装方式 | apt(`pkg.cloudflare.com`) |
| systemd unit | `cloudflared.service` |

---

## 阶段 8: CF Tunnel 配置

状态: ⏸ 待开始(需用户在 CF Dashboard 操作)

| 项 | 值 |
|---|---|
| Tunnel name | _待填_ |
| Tunnel ID | _待填_ |
| Connector status | _待填_ |
| Public hostname | _待填_ |
| Service URL | `http://localhost:8080` |

**用户需完成:**
1. 登录 `one.dash.cloudflare.com` → Networks → Tunnels → Create
2. 拿到 `cloudflared service install eyJ...` 命令(Debian 版)
3. 把那串 token 粘给我,我在 VPS 上跑

---

## 客户端连接信息(全部完成后填)

| 字段 | 值 |
|---|---|
| 协议 | VLESS |
| 地址 | `vpn.<your-domain>` |
| 端口 | 443 |
| UUID | _待填_ |
| Transport | ws |
| WS path | _待填_ |
| TLS | tls(由 CF 提供) |
| SNI | `vpn.<your-domain>` |
| Fingerprint (uTLS) | chrome |
| ALPN | h2,http/1.1 |

---

## 日志区

(每个阶段执行时追加关键命令输出)
