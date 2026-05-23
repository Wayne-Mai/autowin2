# VPN 自建教程(2026 版 · Tunnel 终极版)

**栈:** AWS Lightsail (Sydney) + Cloudflare 域名 + **Cloudflare Tunnel** + Xray + VLESS + ws
**预计耗时:** 90 分钟
**月成本:** ≈ $5.87
**核心特点:** VPS **零入站端口**,真实 IP 物理上无法泄漏

---

## 概念澄清(看完再动手)

| 名词 | 是什么 | 类比 |
|---|---|---|
| **Xray** | 服务端 / 客户端**软件**(一个二进制) | Nginx |
| **VLESS** | 一种**协议**(传输规范) | HTTP/2 |
| **VMess / Trojan / Shadowsocks** | 其他协议,Xray 同样能讲 | HTTP/1.1 / SPDY |
| **Cloudflare Tunnel** | CF 的反向代理服务,VPS 主动向 CF 拨号 | ngrok / frp |

"用 Xray + VLESS" = 用 Xray 软件讲 VLESS 协议,不是二选一。

---

## 目标架构

```
你的客户端 (uTLS=chrome)
    │  vless + ws + tls,SNI=vpn.yourdomain.com
    ▼
Cloudflare 边缘 (TLS 由 CF 自动签发的证书终止)
    │  CF 内部加密 Tunnel(QUIC)
    ▼
VPS 上的 cloudflared 进程 (主动出站,无监听端口)
    │  http,127.0.0.1:8080
    ▼
VPS 上的 Xray 进程 (vless + ws,纯 http,只听 localhost)
    │  freedom outbound
    ▼
目标网站
```

**关键变化(vs 老式自建):**

- VPS **不再监听 443** — Xray 只听 `127.0.0.1`
- VPS **不再需要 TLS 证书** — TLS 由 CF 边缘处理
- VPS **防火墙只允许出站** — 22 SSH 之外全关
- **DNS 是 CNAME → tunnel**,不是 A → VPS IP — VPS IP 永远不出现在 DNS 里

---

## 阻拦者(GFW)观测视角

假设你在中国大陆出差,墙在 [客户端] 和 [CF 边缘] 之间。它能看到 / 看不到什么:

```
[你] ━━━━[GFW 👁]━━━━ [CF 边缘 IP] ━━━加密 tunnel,VPS 主动出站━━━ [Sydney VPS]
 客户端                                              ↑
                                       这一段在墙外发生,GFW 完全看不到
```

### GFW 能看到 → 是否触发阻断 → 我们的对策

| 观测层 | GFW 看到的内容 | 是否触发阻断 | 对策 |
|---|---|---|---|
| **DNS 解析** | 你查 `vpn.yourdomain.com`,返回某个 CF IP | 不直接断,但可能污染返错 IP | 客户端用 **DoH**(`1.1.1.1` over https)或 **预置优选 IP**,绕过本地 DNS |
| **TCP 三次握手** | 目标:某 CF IP:443 | CF anycast 全球十几亿网站共用,目的 IP 本身无罪 | 已配 |
| **TLS Client Hello — SNI** | 默认明文:`vpn.yourdomain.com` | 若该域名进过黑名单 → **整个连接被 RST** | **开 ECH**(已在阶段 9 配置),SNI 加密,墙看不到目标域名 |
| **TLS Client Hello — JA3/JA4 指纹** | 客户端 TLS 库的指纹 | Go/Rust 等非浏览器指纹 → **触发主动探测或限速** | **uTLS = chrome**(已在阶段 10 配置),强制伪装 Chrome 指纹 |
| **TLS Client Hello — ALPN** | `h2, http/1.1` | 与浏览器一致,正常 | 已配 |
| **TLS 应用数据** | 完全密文 | 无法解析协议层 | TLS 本身保护 |
| **服务器证书** | 看到一张 CF Universal SSL 证书,签发给 `vpn.yourdomain.com` | 与任何 CF 网站一致,正常 | 自动 |
| **流量模式 / 时长** | 长连接,双向稳定流量 | **AI 行为分析有可能识别**(非确定性) | 难完全规避;低强度用、避免单连接挂数小时 |
| **GFW 主动探测**(墙重放你的 TCP/TLS 握手到 CF) | CF 边缘正常 HTTPS 响应;若打到 ws 路径以外,fallback 到 nginx 伪装页 | 若响应像代理服务 → 加入黑名单 | CF 边缘 + 伪装页让 CF IP **看起来就是个普通网站** |
| **IP-level 黑名单** | 该 CF IP 在不在墙的 IP 黑名单 | 若在 → **直接黑洞** | **CloudflareST 优选 IP**,绕开被针对的段 |

### GFW 完全看不到的

- 你的 Sydney VPS 的 IP — 流量根本不流向那里,客户端只连 CF
- 这个连接是个"代理"而非"普通网站访问"
- WebSocket 的 path(`/abc12345`)— 在 TLS 里
- UUID — 在 ws frame 里,被 TLS 包了
- **"Cloudflare Tunnel"存在** — 它是 VPS 出站到 CF 的,在 Sydney 那一头握手,墙看不到这一段

### 哪些情况会失败(即便配置完美)

| 失败原因 | 解释 | 缓解 |
|---|---|---|
| 你用的那个 CF IP 被 QoS / 黑洞 | 部分运营商定期处理 CF IP 段 | 优选 IP,定期换 |
| 敏感日期大面积扫荡 | 党代会 / 六月初 / 国庆,墙会针对 CF | 备用线路或等过 |
| 同一域名访问行为太规律 | AI 行为模型识别 | 不要 7×24 挂着 |
| 域名本身进了 SNI 黑名单 | 域名被举报或挂代理时间太久 | 换子域名,或开 ECH(防 SNI 暴露) |

### 安全边界总结

- ✅ **真实 IP**:物理上不可能泄漏 — 不出现在 DNS,VPS 没入站端口可扫
- ✅ **协议指纹**:VLESS + TLS + uTLS 在密文里,墙只能看出"你在和 CF 通信"
- ✅ **主动探测**:伪装页兜底
- ⚠️ **流量行为**:统计学上仍可能被识别为"非浏览行为",这是所有 CDN 代理的共同弱点
- ⚠️ **CF IP 可达性**:取决于墙当天对 CF 的态度,有概率性

---

## 中国大陆出差使用指南

### 出发前必做

1. **本地跑 CloudflareST,导出最快的 10-20 个 IP**,存到客户端 hosts 或 Mihomo `dns.nameserver-policy`
2. **客户端开 DoH** — `1.1.1.1` over HTTPS,绕过本地 DNS 污染
3. **准备备用线路**(可选但建议):见下文
4. **测试一次** — 用 VPN 模拟"假装在国内",看看能不能连(可以临时把客户端 DNS 切到一个国内服务,模拟下污染场景)

### 备用线路建议(可选,与本方案不冲突)

如果 CF 在国内抽风,你需要一条不经过 CF 的备用路径:

- **方案 A**:在同一台 Sydney VPS 上额外跑一个 **VLESS + REALITY** 直连服务,监听某个高端口(比如 23456)
  - 仅对你出差期间的中国 IP 段开防火墙(精确到运营商出口)
  - REALITY 借用真实大网站的 TLS 证书(如 `www.microsoft.com`),无证书无需续期
  - 缺点:暴露了 VPS 真实 IP(只对中国 IP 暴露,有限风险)
- **方案 B**:再租一台不同区域的小机(比如 Hetzner Helsinki + Sing-box Hysteria2),做完全独立的备线

我建议方案 A,成本零增加。

### 实战检查清单(到酒店打开 Wi-Fi 时)

- [ ] DoH 开了
- [ ] hosts 里有优选 IP
- [ ] 客户端 SNI = `vpn.yourdomain.com`,uTLS = chrome
- [ ] 测试访问 `https://www.google.com` 通
- [ ] 不通?切到优选 IP 列表第 2、3 个
- [ ] 都不通?启动备用线路

---

## 组件职责

| 组件 | 干什么 |
|---|---|
| AWS Lightsail Sydney | 真实出口服务器(澳洲 IP) |
| Cloudflare 域名 | DNS 接入 + 给 Tunnel 挂域名 |
| Cloudflare Tunnel | VPS 与 CF 之间的加密反向通道 |
| cloudflared | 跑在 VPS 上的 Tunnel 客户端,主动连 CF |
| Xray | 讲 VLESS 协议的服务端,只听 localhost |
| nginx | 伪装站,fallback 目标 |

---

## 阶段 0: 准备清单

- [ ] AWS 账号 + 国际信用卡
- [ ] Cloudflare 账号
- [ ] 邮箱
- [ ] 本地 SSH 客户端
- [ ] 本地客户端 App
  - Mac: **Mihomo Party**
  - iOS: **Shadowrocket**($2.99) 或 **Streisand**(免费)
  - Windows: **v2rayN with Xray-core**

---

## 阶段 1: 在 Cloudflare 注册域名

### 为什么用 CF 注册

- 成本价(`.com` ≈ $10.44/年)
- WHOIS 隐私默认开
- 注册后直接在 CF DNS,Tunnel 配置时自动可选

### 步骤

1. `dash.cloudflare.com` → **Domain Registration → Register Domains**
2. 搜索域名 → 选 `.com / .net / .me`
3. 填注册人 + 付款
4. 几分钟后域名出现在 **Websites** 列表
5. 后文以 `vpn.yourdomain.com` 指代你要用的子域名

> 避免 `.tk / .ml / .ga`,易被吊销和 SNI 针对。

---

## 阶段 2: 开 AWS Lightsail (Sydney)

### Region 锁定 **ap-southeast-2 Sydney**

- 澳洲本土访问: < 30ms,无敌
- 中国大陆访问: 130-200ms(走美西回程或 PCCW)
- 东南亚: 80-150ms
- 美国: 150-180ms

> 用 Tunnel 后,**客户端实际连的是 CF 边缘(就近),不是 VPS** — Sydney 的物理位置只影响"从 VPS 出口访问目标网站"的那一段。所以如果你主要访问澳洲 / 大洋洲服务,Sydney 完美;访问美国服务也还行。

### 为什么选 Lightsail 而不是 EC2

| | Lightsail | EC2 |
|---|---|---|
| 计费 | 固定月费 | 按时 + 按流量 |
| 出站流量 | 包含 1-7TB | $0.114/GB(Sydney 区,更贵) |
| 配置 | 网页几下 | 复杂 |

EC2 Sydney 区 egress 比美国还贵,**个人 VPN 绝不能用 EC2**。

### 实例规格(Sydney 区)

| 月费 | RAM | vCPU | SSD | 流量 |
|---|---|---|---|---|
| **$5** | 2 GB | 1 | 60 GB | 2 TB | ⭐ 甜点 |
| $3.5 | 512 MB | 1 | 20 GB | 1 TB | OOM 风险 |
| $10 | 4 GB | 2 | 80 GB | 3 TB | 个人浪费 |

- **系统:** Ubuntu 24.04 LTS
- 不要选 Amazon Linux(软件源生态差)

### 静态 IP

- Lightsail console → **Networking → Create static IP** → 绑定实例
- **为什么:** 即便 Tunnel 不暴露这个 IP,VPS 重启后 IP 变化会让 SSH 接入麻烦

### 防火墙(Lightsail Firewall)

**重要:Tunnel 模式下只开 22,其他全关。**

| Port | Protocol | Source | 用途 |
|---|---|---|---|
| 22 | TCP | **My IP** | SSH(最好锁自己) |

**不要开 80/443** — Tunnel 是出站连接,不需要任何入站端口。这是 Tunnel 的核心安全收益。

---

## 阶段 3: VPS 初始化

### SSH 进入

1. Lightsail console → 实例 → **Connect using SSH**(网页 shell)先确认能进
2. 长期用本地:
   - Account → SSH keys → 下载默认 `.pem`
   - `chmod 400 ~/Downloads/LightsailDefaultKey-*.pem`
   - `ssh -i ~/Downloads/LightsailDefaultKey-*.pem ubuntu@<静态IP>`

### 系统加固

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl socat ufw fail2ban

# ufw:OS 层防火墙,与 Lightsail 防火墙叠加
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw --force enable
# 注意:这里只开 22,80/443 都不开 — Tunnel 不需要

sudo systemctl enable --now fail2ban
```

### SSH 密钥升级(可选)

```bash
# 本地:
ssh-keygen -t ed25519 -C "vpn-vps"
ssh-copy-id -i ~/.ssh/id_ed25519.pub -o "IdentityFile ~/Downloads/LightsailDefaultKey-*.pem" ubuntu@<IP>

# VPS 上禁用密码登录:
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

---

## 阶段 4: 安装 Xray

### 一键安装

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

### 验证

```bash
xray version
sudo systemctl status xray   # 还没配,可能报错,正常
```

### 为什么 Xray 不是 V2Ray

- V2Ray-core 维护慢,Xray 是活跃 fork
- Xray 支持 uTLS / fallbacks / 更新的协议变体
- 配置语法 99% 兼容,无痛迁移

---

## 阶段 5: 安装 nginx 伪装站(localhost 监听)

```bash
sudo apt install -y nginx-light
sudo systemctl enable --now nginx

# 改 nginx 监听到 127.0.0.1:8081(不对外暴露)
sudo tee /etc/nginx/sites-available/default > /dev/null <<'EOF'
server {
    listen 127.0.0.1:8081 default_server;
    server_name _;
    root /var/www/html;
    index index.nginx-debian.html;
    location / { try_files $uri $uri/ =404; }
}
EOF
sudo systemctl restart nginx
```

**作用:** 万一 Xray 收到非 ws 路径的请求,fallback 到这个伪装页,看起来像个普通网站。

---

## 阶段 6: 配置 Xray(localhost 监听)

### 生成 UUID + 随机 path

```bash
UUID=$(xray uuid)
WS_PATH="/$(openssl rand -hex 8)"
echo "UUID = $UUID"
echo "WS_PATH = $WS_PATH"
```

**记下这两个值,客户端要用。**

### 写 `/usr/local/etc/xray/config.json`

```bash
sudo tee /usr/local/etc/xray/config.json > /dev/null <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "127.0.0.1",
      "port": 8080,
      "protocol": "vless",
      "settings": {
        "clients": [
          { "id": "$UUID" }
        ],
        "decryption": "none",
        "fallbacks": [
          { "dest": "127.0.0.1:8081" }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "$WS_PATH"
        }
      }
    }
  ],
  "outbounds": [
    { "protocol": "freedom" }
  ]
}
EOF
```

### 字段含义

| 字段 | 作用 |
|---|---|
| `listen: 127.0.0.1` | **只在本地监听** — 外网完全访问不到 |
| `port: 8080` | 本地 http 端口,等下 cloudflared 转给它 |
| `protocol: vless` | 用 VLESS,无时间戳、无双层加密 |
| `decryption: none` | VLESS 不自带加密 |
| `streamSettings.network: ws` | WebSocket,Tunnel 才能转发 |
| **无 TLS 字段** | 因为 TLS 在 CF 边缘做了,VPS 本地不用搞证书 |
| `fallbacks → 8081` | 非 ws 请求回落到 nginx 伪装站 |

### 启动

```bash
sudo systemctl restart xray
sudo systemctl status xray
sudo journalctl -u xray -n 30 --no-pager
```

### 本地预检

```bash
curl http://127.0.0.1:8080/   # 应该返回 nginx 默认页(fallback 生效)
curl -s http://127.0.0.1:8081/   # 应该返回 nginx 默认页(伪装站直连)
```

---

## 阶段 7: 安装 cloudflared

```bash
# 添加 CF 软件源
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt update
sudo apt install -y cloudflared
cloudflared --version
```

---

## 阶段 8: 在 Cloudflare 创建 Tunnel

### Dashboard 操作

1. `one.dash.cloudflare.com`(Zero Trust 入口,首次访问会让你创建一个"team"名,随便起,免费)
2. 左侧 **Networks → Tunnels → Create a tunnel**
3. Connector 类型选 **Cloudflared** → Next
4. Tunnel 名字: `vpn-sydney`(任意)→ Save
5. 进入安装页 — 选 **Debian** → 复制那条 `cloudflared service install eyJ...` 的命令

### 在 VPS 上跑这条命令

```bash
sudo cloudflared service install eyJ...(从 CF 网页复制的整串)
sudo systemctl status cloudflared
# 应该显示 active (running),并已注册为 systemd 服务
```

### 回 CF 网页继续

6. CF 网页上的"Connectors"列表应该出现你的 VPS,绿色 healthy
7. Next → **Route Tunnel** 配置:

| 字段 | 值 |
|---|---|
| Subdomain | `vpn` |
| Domain | `yourdomain.com`(下拉选) |
| Path | 留空 |
| Service Type | **HTTP** |
| URL | `localhost:8080` |

8. Save Tunnel

### CF 自动做了什么

- 在 DNS 区里加了 `vpn.yourdomain.com` 的 CNAME → `<tunnel-uuid>.cfargotunnel.com`(自动 Proxied)
- 给该子域名签发 universal SSL 证书
- 把外部访问 `https://vpn.yourdomain.com` 的流量经 tunnel 转发到 VPS 的 `localhost:8080`

### 预检

```bash
# 在你的 Mac 本地或任何机器:
curl -v https://vpn.yourdomain.com/
# 应返回 nginx 默认页(走通了 CF → tunnel → Xray fallbacks → nginx)
```

---

## 阶段 9: CF SSL/TLS 设置

### 必要设置

CF dashboard → 你的域名 → **SSL/TLS**

| 设置 | 值 |
|---|---|
| Overview → Encryption mode | **Full**(Tunnel 模式不需要 strict,Tunnel 内部加密由 CF 处理) |
| Edge Certificates → Always Use HTTPS | On |
| Edge Certificates → Minimum TLS | 1.2 |
| Edge Certificates → TLS 1.3 | On |
| Edge Certificates → ECH | On |
| Network → WebSockets | On(默认) |

> **注意:** Tunnel 模式下 Encryption mode 选 **Full** 即可,不需要 Strict — 因为 VPS 本地是 http,但 cloudflared ↔ CF 那段是自动加密的。**不要选 Flexible**(那是 CF 用 http 回源,不安全)。

---

## 阶段 10: 客户端配置

### 节点参数

| 字段 | 值 |
|---|---|
| 协议 | VLESS |
| 地址 | `vpn.yourdomain.com` |
| 端口 | **443** |
| UUID | 阶段 6 生成的 |
| Encryption | none |
| Transport | ws |
| Path | 阶段 6 生成的 `/xxxxxxxx` |
| Host (ws header) | `vpn.yourdomain.com` |
| TLS | tls |
| SNI | `vpn.yourdomain.com` |
| ALPN | `h2,http/1.1` |
| **Fingerprint (uTLS)** | **chrome** |
| Allow Insecure | **false** |

### 为什么这些值

- **端口 443**:CF 边缘是 https,所以客户端连 443
- **TLS = tls**:外层走 TLS(由 CF 证书提供)
- **uTLS = chrome**:TLS 指纹伪装 Chrome,过 JA3/JA4 检测
- **SNI = 完整域名**:让 CF 边缘正确路由到你的 zone

### 节点 URI(直接导入客户端)

```
vless://<UUID>@vpn.yourdomain.com:443?encryption=none&security=tls&sni=vpn.yourdomain.com&fp=chrome&type=ws&host=vpn.yourdomain.com&path=<URL编码后的WS_PATH>#我的节点
```

`/abc12345` 这种 path 在 URL 里写成 `%2Fabc12345`。

---

## 阶段 11: 验证

### 检查清单

- [ ] `curl https://vpn.yourdomain.com/` 返 nginx 默认页(fallback 通)
- [ ] 客户端连接成功,延迟 < 300ms
- [ ] 开代理后访问 `google.com` 通
- [ ] `https://ipinfo.io/json` 显示 Cloudflare 的 IP,**不是 Lightsail Sydney IP**
- [ ] 在外部 ping/扫描你的 Lightsail 静态 IP 的 80/443 — **都拒绝**(zero exposure)

### Lightsail IP 隐身验证

```bash
# 从你的 Mac 本地:
nmap -p 22,80,443 <你的 Lightsail 静态 IP>
# 期望: 22 视 SSH 锁源策略而定,80/443 都 filtered/closed
```

### 优选 IP(国内用户用)

```bash
# 本地装 CloudflareST
brew install --cask cloudflarest   # 或 github.com/XIU2/CloudflareSpeedTest 下载
cloudflarest -n 200 -t 4 -dn 10 -p 10
```

得到的最快 IP 写进客户端的"自定义 hosts",SNI 保持域名。

---

## 排错手册

| 症状 | 排查 |
|---|---|
| `curl https://vpn.yourdomain.com/` 502 | cloudflared 服务挂了 / Xray 没在 8080 听 / nginx fallback 没在 8081 听 |
| `curl` 域名失败 (DNS) | Tunnel 创建后 CF 自动加了 CNAME,等 1-2 分钟 |
| 客户端握手成功但没流量 | WS path 不对 / Host header 不对 / UUID 错了 |
| Connector 在 CF 网页显示 offline | `sudo systemctl status cloudflared` 看日志,通常是 token 错或网络出站被挡 |
| 速度慢 | 没用优选 IP / Sydney 区到目标网站绕远 |
| Xray crashloop | `journalctl -u xray -n 100` 看,通常是 JSON 语法 |

### 关键日志

```bash
sudo journalctl -u xray -f          # Xray
sudo journalctl -u cloudflared -f   # Tunnel
sudo tail -f /var/log/nginx/access.log  # 伪装站
```

---

## 成本估算

| 项目 | 月成本 |
|---|---|
| Lightsail Sydney $5 plan | $5.00 |
| Cloudflare 域名摊销 | ≈ $0.87(.com $10.44/年) |
| Cloudflare CDN / Tunnel / TLS | $0 |
| **合计** | **≈ $5.87 / 月** |

> CF Tunnel 个人使用完全免费,Cloudflare One 免费版可挂 50 个用户、无流量限制。

---

## 维护清单

| 周期 | 操作 |
|---|---|
| 每周 | `sudo apt upgrade -y` |
| 每月 | CF dashboard 看 Tunnel healthy 状态 |
| 每季度 | 升级 Xray: `bash -c "$(curl -L .../install-release.sh)" @ install` |
| 半年 | 换 UUID + ws path(防长期被指纹) |
| `cloudflared` 自更新 | `sudo apt upgrade cloudflared` 即可 |

---

## 后续可选升级

### A. 多节点冗余

- 在 Tokyo 区再开一台 Lightsail,装 cloudflared 加入**同一个** Tunnel
- CF 自动在两个 connector 之间负载均衡 + failover
- 一台挂了另一台无感接管

### B. CF Access 加身份验证

- Tunnel 上方挂 CF Access policy,要求登录才能访问
- 即使 UUID 泄漏,没你的邮箱认证打不进来

### C. 用 sing-box 替代 Xray

- sing-box 是新一代,协议支持更广(Hysteria2 / TUIC / Reality 一体)
- 配置 JSON 风格不同,但概念一致

### D. Hysteria2 / TUIC 副线路

- 走 UDP/QUIC,不经过 CF Tunnel(CF 不代理 UDP)
- 直连 VPS:443 UDP,弱网下比 ws 快
- 需要 VPS 单独开 443/udp 入站(破坏"零入站"原则,自行权衡)

---

## 完整命令速查

```bash
# === 在 VPS 上 ===
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl socat ufw fail2ban nginx-light
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow 22/tcp && sudo ufw --force enable
sudo systemctl enable --now fail2ban

# Xray
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

# nginx 改 127.0.0.1:8081(见阶段 5)
# Xray config(见阶段 6)
UUID=$(xray uuid); WS_PATH="/$(openssl rand -hex 8)"
# ... sudo tee /usr/local/etc/xray/config.json ...
sudo systemctl restart xray

# cloudflared
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# 接下来去 CF 网页创建 Tunnel,粘贴 install 命令回 VPS 跑
# 然后在 CF 网页配置 public hostname → http://localhost:8080
```

---

## 架构对比(老 vs 新)

| 维度 | 老教程 (Eric Close 2020) | 本教程 (2026 Tunnel) |
|---|---|---|
| VPS 入站端口 | 80 + 443 开放 | **全关,只留 22** |
| TLS 证书 | 自签 / Let's Encrypt 自己签 | **CF 自动给,完全免管** |
| Nginx | 反代 + TLS 终止(必须) | 仅作伪装站(localhost) |
| 协议 | VMess + ws + TLS | VLESS + ws(TLS 在 CF 边缘) |
| 真实 IP 泄漏面 | DNS 直查 / Nginx 错误页 / 配置漏导致绕过 CF | **零** — IP 不出现在 DNS,无入站端口可扫 |
| CF 角色 | 仅 CDN(可选) | 必须组件,承担 TLS + Tunnel |
| 续证书 | acme.sh / certbot 维护 | 不需要 |
| 部署复杂度 | 中(Nginx + cert + V2Ray) | 中(Tunnel 替代 cert,等价) |
