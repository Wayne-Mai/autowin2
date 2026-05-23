# 2026 升级 VPS + Cloudflare 代理 — 完整可执行流程

> 本文档是一份按顺序复制粘贴即可执行的运行手册（runbook），不是对比文档。
> 主路径已预选：**VLESS + ws + TLS + Cloudflared Tunnel + acme.sh LE 证书 + uTLS Chrome 指纹**。
> ECH / Open-443 / 3x-ui / REALITY 放在附录，按需启用。
> 全文 `<占位>` 在 §0 决策表里查。

---

## §0. 一次性决策表（动手前必须填完）

| 编号 | 项 | 默认 / 推荐 | 你的值 |
|------|----|-------------|--------|
| D1 | 代理域名 | — | `<your.domain.com>` |
| D2 | CF 账号邮箱 | — | `<email@example.com>` |
| D3 | CF API Token（权限：`Zone:DNS:Edit`；若开 ECH 再加 `Zone:Zone Settings:Edit`；Zone Resources 选 D1 zone） | — | `<dXXXX...>` |
| D4 | CF Zone ID（域名 Overview 右下角） | — | `<32 字符 hex>` |
| D5 | CF Account ID（同上一栏） | — | `<32 字符 hex>` |
| D6 | VPS 厂商 | Hetzner CAX11 / Oracle Free / 现有 VPS 都行（draft 不强制 AWS） | `<vendor>` |
| D7 | VPS 公网 IP（v4） | — | `<a.b.c.d>` |
| D8 | UUID（**新生成**，不要复用 VMess 的） | `uuidgen` 或 `xray uuid` | `<uuid>` |
| D9 | ws path（含开头 `/`） | `/ws-` + 一段随机串 | `<ws-path>` |
| D10 | 主客户端平台 | — | macOS / iOS / Windows / Android / Linux |
| D11 | 是否启用 ECH（附录 B） | 先不开（下界） | 是 / 否 |
| D12 | 是否装 3x-ui 面板（附录 C） | 不装 | 否 / 是 |

> 12 项全部填完再继续。下文任何 `<...>` 都直接替换为这张表的值。

---

## §1. 浏览器侧 — 准备 Cloudflare

1. 把 D1 域名加入 CF 账号 → DNS 改到 CF nameservers → Overview 显示 `Active`
2. 给 D1 加一条 A 记录指向 D7，**橙色云朵 = ON**（启用代理）
3. My Profile → API Tokens → Create Token → 自定义：
   - Permissions: `Zone` → `DNS` → `Edit`
   - 如 D11 = 是，再加 `Zone` → `Zone Settings` → `Edit`
   - Zone Resources: `Include` → `Specific zone` → D1
   - 保存 token 串 → 填到 D3
4. 在 D1 的 Overview 页面右下复制 Zone ID → D4；Account ID → D5

---

## §2. SSH 进 VPS — 基础准备

```bash
ssh root@<D7>

# Debian/Ubuntu 系
apt update && apt install -y curl jq socat tcpdump ufw uuid-runtime ca-certificates
# CentOS/RHEL 系替换为：dnf install -y curl jq socat tcpdump firewalld util-linux

# 时间同步（VLESS 不强制，仍建议）
timedatectl set-ntp true && timedatectl status

# 防火墙打底：只放 SSH
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw --force enable
ufw status verbose

# 在 VPS 厂商面板做一次磁盘快照（兜底回滚）
```

---

## §3. 装 Xray-core

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
xray version
systemctl status xray   # 此刻无配置，应该是 inactive 或 failed，正常
```

预期：`/usr/local/bin/xray` 已就位，配置目录 `/usr/local/etc/xray/`。

---

## §4. 申请 Let's Encrypt 证书（acme.sh + dns_cf）

```bash
# 装 acme.sh
curl https://get.acme.sh | sh -s email=<D2>
source ~/.bashrc

# 默认 CA 切到 LE
~/.acme.sh/acme.sh --set-default-ca --server letsencrypt

# 注入 CF 凭证
export CF_Token="<D3>"
export CF_Account_ID="<D5>"
export CF_Zone_ID="<D4>"

# 签发 ECC 证书（更小更快）
~/.acme.sh/acme.sh --issue --dns dns_cf -d <D1> --keylength ec-256

# 安装到 Xray 路径 + reload 钩子
mkdir -p /etc/xray/cert
~/.acme.sh/acme.sh --install-cert -d <D1> --ecc \
  --key-file       /etc/xray/cert/key.pem  \
  --fullchain-file /etc/xray/cert/cert.pem \
  --reloadcmd      "systemctl restart xray"

# 校验
ls -l /etc/xray/cert/
~/.acme.sh/acme.sh --list                                   # 看到 LetsEncrypt + Renew 日期
~/.acme.sh/acme.sh --renew -d <D1> --ecc --force --dry-run  # 续期 dry-run 应通过
```

---

## §5. 写伪装站（本地回环 :8080，不暴露公网）

```bash
apt install -y nginx-light    # 这里 nginx-light 只跑伪装站，不参与 TLS、不反代 Xray

cat > /etc/nginx/sites-available/decoy <<'EOF'
server {
    listen 127.0.0.1:8080 default_server;
    listen [::1]:8080 default_server;
    root /var/www/decoy;
    index index.html;
    server_name _;
    add_header X-Content-Type-Options nosniff;
}
EOF
ln -sf /etc/nginx/sites-available/decoy /etc/nginx/sites-enabled/decoy
rm -f /etc/nginx/sites-enabled/default

mkdir -p /var/www/decoy
cat > /var/www/decoy/index.html <<'EOF'
<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Personal Page</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
</head><body>
<h1>Hello.</h1>
<p>This site is intentionally minimal.</p>
</body></html>
EOF

systemctl restart nginx
curl -sI http://127.0.0.1:8080/ | head -1     # HTTP/1.1 200 OK
ss -tlnp | grep ':8080'                       # 只在回环口监听
```

> 替代方案：若坚持完全不要 nginx，可用 `python3 -m http.server 8080 --bind 127.0.0.1`，不过生产不推荐。

---

## §6. 写 Xray 配置（VLESS + ws + fallbacks，监听回环 10443）

```bash
cat > /usr/local/etc/xray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "tag": "vless-in",
      "listen": "127.0.0.1",
      "port": 10443,
      "protocol": "vless",
      "settings": {
        "clients": [{ "id": "<D8>", "level": 0 }],
        "decryption": "none",
        "fallbacks": [
          { "dest": "127.0.0.1:8080", "xver": 0 }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": { "path": "<D9>" },
        "security": "none"
      },
      "sniffing": { "enabled": true, "destOverride": ["http","tls"] }
    }
  ],
  "outbounds": [
    { "tag": "direct",  "protocol": "freedom"   },
    { "tag": "blocked", "protocol": "blackhole" }
  ]
}
EOF

# 配置语法自检
xray test -config /usr/local/etc/xray/config.json

systemctl restart xray
systemctl status xray
journalctl -u xray -n 50 --no-pager
ss -tlnp | grep ':10443'      # xray 在 127.0.0.1:10443 上
```

> 设计说明：
> - **TLS 终结在 CF 边缘**，cloudflared 在 VPS 内回环回源到 `127.0.0.1:10443` 走明文 ws。因此 Xray inbound 不开 TLS。
> - **不匹配的 ws path / 没认证** 的请求由 `fallbacks` 回落到 `127.0.0.1:8080` 伪装站。
> - 如果走附录 A 的 Open-443 模式，需要把 inbound 改成 `0.0.0.0:443` 并加 `tlsSettings`，见附录。

---

## §7. 装 cloudflared 建 Tunnel

```bash
# 安装（amd64；arm64 把 -linux-amd64 改成 -linux-arm64）
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
dpkg -i /tmp/cloudflared.deb
cloudflared --version

# 登录（输出一个 URL，浏览器打开，选 D1 所在 zone 授权）
cloudflared tunnel login

# 创建 tunnel
cloudflared tunnel create proxy-2026
TUNNEL_ID=$(cloudflared tunnel list | awk '/proxy-2026/ {print $1}')
echo "TUNNEL_ID=${TUNNEL_ID}"

# 写 ingress 规则
mkdir -p /etc/cloudflared
cat > /etc/cloudflared/config.yml <<EOF
tunnel: ${TUNNEL_ID}
credentials-file: /root/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: <D1>
    service: http://127.0.0.1:10443
    originRequest:
      noTLSVerify: true
      connectTimeout: 10s
  - service: http_status:404
EOF

# 自动覆盖 D1 的 DNS 为 tunnel CNAME（替换 §1.2 临时 A 记录）
cloudflared tunnel route dns proxy-2026 <D1>

# 装成 systemd 服务
cloudflared service install
systemctl enable --now cloudflared
systemctl status cloudflared

# 验证
cloudflared tunnel info proxy-2026     # 所有 connector 都 healthy
journalctl -u cloudflared -n 30 --no-pager
```

---

## §8. 收尾 — 清理旧栈

```bash
# 卸载老 V2Ray
systemctl stop v2ray 2>/dev/null || true
systemctl disable v2ray 2>/dev/null || true
which v2ray && bash <(curl -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh) --remove
apt purge -y v2ray 2>/dev/null || true

# 老 CF Origin CA 证书
find / -name 'origin-ca*' -o -name '*.cf-origin*' 2>/dev/null
# 找到后 rm -f；再去 CF 控制台 → SSL/TLS → Origin Server → Revoke 老证书

# 老 nginx 反代配置（若之前用 nginx 终结 TLS 反代 V2Ray）
# 现在 §5 只用 nginx-light 跑回环伪装站，反代相关 vhost 已经在 §5 用 rm sites-enabled/default 清掉
# 如果你之前是单独装的 full nginx 且没有别的真站，可整体卸载然后重做 §5：
# apt purge -y nginx nginx-common && bash <跑一遍 §5>

# 关掉公网 443（Tunnel 模式不需要）
ufw status numbered
ufw delete allow 443/tcp 2>/dev/null || true
ufw status
```

---

## §9. 客户端配置（按 D10）

通用 VLESS+ws+TLS+uTLS 分享链接：

```
vless://<D8>@<D1>:443?encryption=none&security=tls&sni=<D1>&fp=chrome&type=ws&host=<D1>&path=<URL-encoded D9>#proxy-2026
```

> `path` 必须 URL-encode：`/` → `%2F`。例如 `/ws-abc` → `%2Fws-abc`。

按平台：

| 平台 | 客户端推荐（2026） | 关键字段 |
|------|---------------------|---------|
| macOS | Mihomo Party / Stash | `client-fingerprint: chrome` |
| iOS | Shadowrocket / Stash / Streisand | `Allow Insecure: OFF`、`Fingerprint: chrome` |
| Windows | v2rayN(Xray core) / Nekoray / Mihomo Party | `fp = chrome` |
| Android | v2rayNG / NekoBox / Surfboard | `Fingerprint: chrome` |
| Linux/路由器 | Sing-box / Clash Meta (mihomo) | YAML 里 `client-fingerprint: chrome` |

Xray-JSON 片段（v2rayN / Nekoray / Sing-box 通用）：

```json
{
  "outbounds": [{
    "tag": "proxy-2026",
    "protocol": "vless",
    "settings": {
      "vnext": [{
        "address": "<D1>",
        "port": 443,
        "users": [{ "id": "<D8>", "encryption": "none", "level": 0 }]
      }]
    },
    "streamSettings": {
      "network": "ws",
      "security": "tls",
      "tlsSettings": {
        "serverName": "<D1>",
        "fingerprint": "chrome",
        "allowInsecure": false
      },
      "wsSettings": {
        "path": "<D9>",
        "headers": { "Host": "<D1>" }
      }
    }
  }]
}
```

Clash/Mihomo YAML 片段：

```yaml
proxies:
  - name: proxy-2026
    type: vless
    server: <D1>
    port: 443
    uuid: <D8>
    network: ws
    tls: true
    servername: <D1>
    client-fingerprint: chrome
    ws-opts:
      path: <D9>
      headers:
        Host: <D1>
    udp: true
```

---

## §10. 端到端验证（按顺序勾选）

| # | 检查项 | 命令 / 操作 | 通过标准（Positive） | 失败信号（Negative） |
|---|--------|------------|---------------------|---------------------|
| 1 | Xray 进程 | `systemctl is-active xray` | `active` | — |
| 2 | 老 V2Ray 已死 | `which v2ray && systemctl is-active v2ray` | 全部"无输出 / inactive" | 任一存在则未清理干净 |
| 3 | cloudflared 健康 | `cloudflared tunnel info proxy-2026` | 至少一个 connector healthy | — |
| 4 | 入站只剩 SSH | `ufw status` | 只有 `22/tcp ALLOW` | 出现 `443/tcp ALLOW` 即说明 §8 没清完 |
| 5 | 公网 IP 不可达 :443 | 从外网（手机 4G 也行）跑 `nc -vz <D7> 443` | refused / timeout | 可连即 §8 未关 |
| 6 | DNS 指向 CF | `dig +short <D1>` | 全是 CF 段（104.x / 172.x / 188.x 等） | 出现 D7 即 DNS 没换 |
| 7 | 公网证书是 CF 终结 | `openssl s_client -connect <D1>:443 -servername <D1> </dev/null 2>/dev/null \| openssl x509 -noout -issuer` | CF 自家证书链（不是 LE，因为 LE 是 origin 用的） | — |
| 8 | 客户端连通 | 客户端连上后 `curl -x socks5://127.0.0.1:<本地端口> https://www.google.com -I` | `HTTP/2 200` | 连不上看 §13 附录 E |
| 9 | 伪装回落（无 path） | 浏览器打 `https://<D1>/` | §5 的 Hello 页 | TLS alert / RST / 503 |
| 10 | 伪装回落（错 path） | `curl -I https://<D1>/random-path` | 仍是 §5 的页面，HTTP 200/404 | TLS 错误或异常状态码 |
| 11 | JA3/JA4 = Chrome | 客户端访问 `https://tls.peet.ws/api/all`，看 `ja3_hash` / `ja4` | 与主流 Chrome 一致 | Go 默认指纹即 `fp=chrome` 没生效 |
| 12 | LE 续期 dry-run | `~/.acme.sh/acme.sh --renew -d <D1> --ecc --force --dry-run` | 成功 | — |
| 13 | UUID 已换新 | `grep '<旧VMess UUID>' /usr/local/etc/xray/config.json` | 无匹配 | 有匹配即没生成新 UUID |

12 项全 PASS = §10 完成。

---

## §11. 回滚

**紧急回滚**（客户端连不上 → 5 分钟内恢复服务）：

```bash
systemctl stop cloudflared
systemctl stop xray
# CF 控制台：把 D1 DNS 从 tunnel CNAME 改回 A 记录指向 D7（橙色云朵保持 ON）
ufw allow 443/tcp
# 如果老 V2Ray 还在，systemctl start v2ray；否则使用 VPS 快照
```

**完整回到 2020 老栈**：

1. 恢复 §2 拍的磁盘快照 → 直接结束
2. 或手动：
   - `systemctl disable --now cloudflared xray`
   - `apt purge -y cloudflared`
   - 重装 V2Ray + Nginx 反代
   - CF 控制台 SSL/TLS → Origin Server → 重新签 CF Origin CA
   - VMess inbound 写回 V2Ray，UUID 用旧值
   - 开 ufw 443

**完整移除**（不要代理了）：

```bash
systemctl disable --now cloudflared xray nginx
apt purge -y cloudflared nginx-light
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ remove
~/.acme.sh/acme.sh --uninstall
~/.acme.sh/acme.sh --revoke -d <D1> --ecc
rm -rf /etc/xray /etc/cloudflared /var/www/decoy ~/.cloudflared ~/.acme.sh
# CF 控制台：删 D1 的 tunnel route / DNS 记录 / API Token
```

---

## §12. 任务分工（Claude / Codex）

| ID | 任务 | 章节 | tag |
|----|------|-----|-----|
| task1 | 现状盘点写入 `aws/inventory.md`（旧 V2Ray 版本、ws path、UUID、Nginx vhost、防火墙、CF Origin CA 路径） | §0 准备 | analyze |
| task2 | 跑 §2 基础准备 + 快照 | §2 | coding |
| task3 | 跑 §3 装 Xray | §3 | coding |
| task4 | 跑 §4 申请并安装 LE 证书 | §4 | coding |
| task5 | 跑 §5 伪装站 | §5 | coding |
| task6 | 写 `/usr/local/etc/xray/config.json` | §6 | coding |
| task7 | 跑 §7 装 cloudflared 并建 tunnel | §7 | coding |
| task8 | 跑 §8 清理旧栈 + 关 443 | §8 | coding |
| task9 | 按 D10 生成客户端配置 + 分享链接，写入 `aws/clients/<D10>.md` | §9 | coding |
| task10 | 跑 §10 验证清单，结果写入 `aws/verify.md`（13 项全列） | §10 | analyze |
| task11 | 把本文件复制成 `aws/runbook.md` | — | coding |
| task12 | 写 `aws/rollback.md`（搬运 §11） | §11 | coding |
| task13 | (可选 D11=是) 跑附录 B 启用 ECH | 附录 B | coding |
| task14 | (可选) 切附录 A Open-443 模式 | 附录 A | coding |
| task15 | (可选 D12=是) 跑附录 C 装 3x-ui | 附录 C | coding |
| task16 | (可选) 评估附录 D REALITY/XTLS | 附录 D | analyze |

> tag：`coding` = Claude 实施；`analyze` = Codex（`/humanize:ask-codex`）做分析或核对。

---

## §13. 附录

### 附录 A — Open-443 模式（不用 Tunnel 时）

适用：你不想跑 cloudflared，让 Xray 直接监听公网 :443。代价：一旦 ufw 配错就直接暴露 IP。

1. §6 inbound 改成：
   ```jsonc
   "listen": "0.0.0.0",
   "port": 443,
   "streamSettings": {
     "network": "ws",
     "wsSettings": { "path": "<D9>" },
     "security": "tls",
     "tlsSettings": {
       "alpn": ["http/1.1"],
       "certificates": [{
         "certificateFile": "/etc/xray/cert/cert.pem",
         "keyFile":         "/etc/xray/cert/key.pem"
       }]
     }
   }
   ```
2. ufw 只放 SSH + 443 from CF IP 段：
   ```bash
   for ip in $(curl -s https://www.cloudflare.com/ips-v4); do
     ufw allow proto tcp from $ip to any port 443
   done
   for ip in $(curl -s https://www.cloudflare.com/ips-v6); do
     ufw allow proto tcp from $ip to any port 443
   done
   ufw reload && ufw status
   ```
3. 跳过 §7（不装 cloudflared），CF DNS 保留 A 记录指向 D7、橙色云朵 ON
4. 写个 cron 每月刷新 CF IP 段：
   ```bash
   cat > /etc/cron.monthly/refresh-cf-ips <<'EOF'
   #!/usr/bin/env bash
   # 重建 ufw CF 白名单
   ufw status numbered | grep 'Cloudflare-IP' | awk -F'[][]' '{print $2}' | sort -rn | xargs -I{} ufw --force delete {}
   for ip in $(curl -s https://www.cloudflare.com/ips-v4); do
     ufw allow proto tcp from $ip to any port 443 comment 'Cloudflare-IP'
   done
   for ip in $(curl -s https://www.cloudflare.com/ips-v6); do
     ufw allow proto tcp from $ip to any port 443 comment 'Cloudflare-IP'
   done
   ufw reload
   EOF
   chmod +x /etc/cron.monthly/refresh-cf-ips
   ```

### 附录 B — 启用 ECH

1. CF 控制台 → 域名 → SSL/TLS → Edge Certificates → Encrypted Client Hello (ECH) → **ON**
2. 拿 ECH config：
   ```bash
   dig +short TYPE65 <D1> @1.1.1.1 | head    # 看到 ech= 段
   # 或浏览器访问 https://crypto.cloudflare.com/cdn-cgi/trace 找 sni= 字段
   ```
3. 客户端 streamSettings.tlsSettings 加（Xray-core ≥ 1.8.x）：
   ```json
   "echSettings": {
     "enabled": true,
     "config": "<base64-ech-config>"
   }
   ```
   - 字段名各客户端略有差异（Sing-box 是 `ech.enabled` / `ech.config`），参考所选客户端文档。
4. 抓包验证 Client Hello 含 `encrypted_client_hello` extension：
   ```bash
   # 在客户端本机
   tcpdump -i any -s 0 -w /tmp/ech.pcap host <D1> and port 443
   # 客户端连一次代理，Ctrl-C，用 Wireshark 打开 ech.pcap，过滤 tls.handshake.type==1
   ```

### 附录 C — 装 3x-ui 面板（D12 = 是）

> 仅当 D12=是。会额外开一个 web 端口，**是新增的攻击面**。

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
# 安装中按提示：
#  - 自定义端口（不要默认 2053）
#  - 强密码
#  - 改 /<random> 访问路径
#  - 启用 BBR
```

**不要**直接把 panel 端口暴露公网。访问方式：SSH 隧道。

```bash
# 在本地终端
ssh -L 12053:127.0.0.1:<3xui-port> root@<D7>
# 浏览器打开 http://127.0.0.1:12053/<random>
```

### 附录 D — REALITY / XTLS

REALITY 是 Xray 独有的反主动探测特性。**不走 CDN，直连 VPS**，与本流程的"CF 在前隐藏 IP"思路冲突。
建议：本主流程不要把 REALITY 替换为唯一入站；若想试，加一个**独立 REALITY 入站**作为 backup，监听一个非 443 端口，并接受 IP 不再被 CF 隐藏的代价。具体配置不在本 runbook 范围。

### 附录 E — 常见故障

| 症状 | 原因 | 处理 |
|------|------|------|
| 客户端 `handshake failed` | uTLS 没生效，或客户端版本太旧 | 检查 `fp=chrome` / 升级客户端 |
| 客户端连得上但没流量 | ws path 不一致 | §6 `wsSettings.path` 与客户端 `path` 必须 1:1 字节一致 |
| `cloudflared` 报 `403 forbidden host` | tunnel ingress 写错 hostname | 检查 §7 `config.yml` 里 `hostname:` 是 D1 |
| `acme.sh` 报 `Invalid response from cloudflare` | D3 权限不够 | D3 必须包含 `Zone:DNS:Edit` 且 Zone Resources 选中 D1 |
| `acme.sh` 报 `Zone not found` | D4/D5 错 | 重新从 CF Overview 复制 Zone ID / Account ID |
| 直连 D7 也能进代理 | DNS 是灰云朵 / 入站没关 | CF DNS 必须橙色云朵 + §8 `ufw delete allow 443` |
| LE 签发卡在 DNS challenge | NS 还没生效 | `dig NS <D1>` 看是不是 CF 的 NS；等 10–30 分钟再签 |
| `xray` 启动失败 | JSON 语法错 | `xray test -config /usr/local/etc/xray/config.json` 看具体行 |
| ECH 抓包看不到 `encrypted_client_hello` | CF 那边 ECH 没开 / 客户端不支持 | CF 控制台确认；客户端升级或换 Sing-box |
| cloudflared 偶尔断流 | connector 数太少 | `cloudflared tunnel run --protocol http2` 或者跑 2+ 个 connector |

---

## §14. 老栈 vs 新栈（**参考保留，动手只看 §1–§13**）

| 维度 | 老栈 (2020) | 新栈 (本流程) |
|------|------------|---------------|
| 核心 | V2Ray-core | Xray-core |
| 协议 | VMess + ws + TLS | VLESS + ws + TLS |
| TLS 终结 | Nginx 反代 :443 | CF 边缘（Tunnel 模式）/ Xray 自身（Open-443 模式，附录 A） |
| 证书 | CF Origin CA（仅 CF 内部信任，15 年）| Let's Encrypt via acme.sh + dns_cf（公开信任，90 天自动续）|
| 入站 | VPS :443 开放公网 | cloudflared Tunnel，VPS 入站只剩 SSH |
| TLS 指纹 | Go 默认（可被 JA3/JA4 识别）| uTLS = chrome |
| SNI | 明文 | 可选 ECH 加密（附录 B）|
| Nginx | 必须，做反代 | 可去；只在 §5 用 nginx-light 跑回环伪装站，**不**承担 TLS |
| 客户端 | v2rayN / V2rayU / Quantumult / V2Ray | v2rayN(Xray core) / Mihomo Party / Stash / Shadowrocket / NekoBox / Sing-box / Clash Meta |

---

## §15. 决策状态（仍待用户确认的项）

- D1, D2, D3, D4, D5, D7, D8, D9：**必填**（部署前必须有具体值）
- D6（VPS 厂商）：可保留现有 VPS；目录名 `aws/` 不强制 AWS
- D10：必填，决定 §9 走哪一行
- D11 (ECH)：默认 **否**（下界），愿意上界开启请走附录 B
- D12 (3x-ui)：默认 **否**，单用户单节点不需要

> 12 项全部敲定再开 §1。

---

--- Original Design Draft Start ---

老教程(https://ericclose.github.io/V2Ray-TLS-WebSocket-Nginx-with-Cloudflare.html#%E5%AE%89%E8%A3%85%E5%B9%B6%E9%85%8D%E7%BD%AE-V2Ray)在 2026 年可以升级的部分
核心 feature(必须保留,不动)
✅ 自己的 VPS 作为真实出口(独享 IP)
✅ Cloudflare CDN 套在前面隐藏真实 IP
✅ WebSocket + TLS 传输(才能走 CDN 的 443)
✅ 自有域名(CF DNS 接管)
✅ "回落到伪装站"思路(被主动探测时返回正常网页)
可以升级的部分(按收益排序)
1. 协议: VMess → VLESS 或 Trojan ⭐⭐⭐⭐⭐
项目	老 (VMess+ws+TLS)	新 (VLESS+ws+TLS)
时间戳校验	需要 NTP 同步,误差>90s 失败	无
双层加密 CPU 开销	有	无(只靠 TLS)
GFW 主动探测被识别记录	多	几乎无
客户端兼容	全部	全部
迁移成本极低:同一个 ws path、同一个 TLS 证书、同一个 CDN 配置,只改 inbound 的 protocol 字段即可。

2. 核心: V2Ray-core → Xray-core ⭐⭐⭐⭐⭐
Xray 是 V2Ray 的活跃 fork,2020 后所有新特性都在 Xray
配置语法 99% 兼容,无痛迁移
一键安装脚本:bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
解锁后续所有升级(REALITY / XTLS / uTLS / fallbacks)
3. Nginx → 可以彻底删掉 ⭐⭐⭐⭐
老教程让 Nginx 干两件事:TLS 终止 + 反代到 V2Ray。Xray 的 fallbacks 功能可以直接在 :443 监听,TLS 也由 Xray 处理,握手不匹配的请求回落到本地 :80 的伪装站(或者别的端口)。

结果:Nginx 完全不需要存在,少一层运维、少一份内存、少一个攻击面。

如果你仍想保留 Nginx(比如本来就跑着真实网站),可以保留;但 2026 年新建议是 Xray 一把梭。

4. 证书: CF Origin CA → acme.sh 自动签 Let's Encrypt ⭐⭐⭐
老教程用 CF Origin CA(15 年期、CF 内部签发)。问题:

只对 CF 边缘有效,不能被普通客户端校验
一旦客户端绕过 CDN 直连源站(调试用),证书会报错
升级方案:acme.sh + DNS-01 + Cloudflare API,自动签 LE 证书,90 天自动续期,一行命令搞定:

acme.sh --issue --dns dns_cf -d yourdomain.com
通用、公开、可被任何客户端校验。

5. TLS 指纹: 加 uTLS / utls fingerprint ⭐⭐⭐⭐
老教程没提 TLS 指纹。2026 年的 GFW 会看 JA3/JA4 指纹,Go 的默认 TLS 库指纹与浏览器不一样,容易被识别。

Xray 客户端侧加一行:"fingerprint": "chrome",把 TLS Client Hello 伪装成 Chrome。这一个改动可能比换协议还重要。

6. 加 ECH (Encrypted Client Hello) ⭐⭐⭐
Cloudflare 已支持 ECH。开启后 SNI 字段被加密,GFW 看不到你访问的域名。仓库里 yonggekkk 的方案就用了 ECH。在 Xray 客户端配置:"echConfig": "...",服务端 CF 自动处理。

7. 入站: 开 443 端口 → Cloudflare Tunnel(cloudflared) ⭐⭐⭐
更激进的"隐藏 IP"方式:VPS 完全不暴露任何入站端口,由 cloudflared 主动建立到 CF 的出站连接接收流量。

老方案 (开 443)	Tunnel 方案
VPS 防火墙	必开 443	全部关闭
真实 IP 暴露风险	一旦 CF 配置漏了就泄漏	无入站,无可扫
部署复杂度	简单	中等(要登录授权 cloudflared)
性能损耗	无	略增加延迟(多一跳)
如果只是个人用,强烈推荐 Tunnel — 这是老教程"Authenticated Origin Pulls"思路的完全体。

8. 客户端生态升级 ⭐⭐⭐
平台	老教程时代	2026 年推荐
Windows	v2rayN(老 core)	v2rayN(Xray core) / Nekoray / Mihomo Party
macOS	V2rayU	Mihomo Party / Stash
iOS	Quantumult / Shadowrocket	Shadowrocket / Stash / Streisand
Android	v2rayNG	v2rayNG / NekoBox / Surfboard
Linux/路由器	V2Ray	Sing-box / Clash Meta
订阅链接生成、节点分组、规则分流都是 Clash Meta / Mihomo 时代的产物,体验比 2020 年好得多。

9. 可选: 加一个 Web 管理面板 ⭐⭐
如果你不想每次都改 JSON:

3x-ui — Xray-core 的多用户管理面板,有流量统计、订阅链接、Telegram 通知
一键安装:bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
代价是多一个面板进程(可能成为攻击面),个人用如果只有一两个节点其实不需要。

10. VPS 选型: CloudCone → 2026 年的便宜机 ⭐⭐
选项	价格	特点
Oracle Cloud Free Tier	$0/月	ARM 4 vCPU + 24GB RAM 永久免费,但容易被回收
Hetzner CAX11(ARM)	€3.79/月	欧洲机房,性价比顶级,Xray ARM 二进制完美
RackNerd	$10-20/年	洛杉矶 DC,适合 CN 用户
BandwagonHost CN2 GIA	$50/年起	走 CN2 GIA 回国,绕过 CDN 直连最快
CloudCone	$3.71+/月	老教程那家还活着,但性价比不如以上
关键: 走 CF CDN 时 VPS 落地线路不重要(流量都经 CF);不走 CDN 直连时才需要 CN2/9929 优质线路。

推荐升级后的整体架构
你的客户端 (v2rayN/Sing-box, uTLS=chrome, ECH on)
        ↓
Cloudflare CDN 边缘 (优选 IP, ECH)
        ↓
cloudflared Tunnel (VPS 无入站端口)
        ↓
Xray @ VPS (VLESS + ws + TLS, 内置 fallbacks 回落伪装站)
        ↓
目标网站
对比老教程的改动量:

删: Nginx、CF Origin CA、VMess、防火墙规则
换: V2Ray-core → Xray-core,VMess → VLESS
加: uTLS 指纹、ECH、cloudflared Tunnel、acme.sh 证书自动化
保留不变: VPS 自有、CF 套 CDN、ws+TLS、伪装站思路、独享出口 IP
--- Original Design Draft End ---
