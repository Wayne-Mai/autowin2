# VPN 客户端配置

**节点说明:** Sydney AWS Lightsail · VLESS + WS + TLS · 走 Cloudflare Tunnel · 入口 `marketingblogs.org:443`

---

## 节点 URI(直接导入用)

⚠️ **当作密码处理** — 这串里有 UUID + 秘密 WS path,泄漏 = 别人能用你的节点。不要发到任何公开地方(GitHub / Slack / Telegram 公开群)。

```
vless://dc4a1417-7ba3-4079-b40b-fd528ffebd9e@marketingblogs.org:443?encryption=none&security=tls&sni=marketingblogs.org&fp=chrome&type=ws&host=marketingblogs.org&path=%2F2f9a853f07e82681#sydney-vpn
```

参数拆解:

| 参数 | 值 | 含义 |
|---|---|---|
| UUID | `dc4a1417-7ba3-4079-b40b-fd528ffebd9e` | Xray 客户端身份 |
| host | `marketingblogs.org` | 连接地址 |
| port | `443` | HTTPS |
| security | `tls` | TLS 加密(CF Universal SSL) |
| sni | `marketingblogs.org` | TLS Server Name Indication |
| fp | `chrome` | **uTLS 指纹伪装 — 必须 chrome,过 JA3 检测** |
| type | `ws` | WebSocket transport |
| path | `/2f9a853f07e82681` | 秘密 WS path |
| (无) encryption | `none` | VLESS 不带加密层,靠外层 TLS |

---

## 推荐客户端

### macOS — Mihomo Party ⭐

**为什么:** 免费、活跃、原生支持 VLESS + uTLS 指纹 + WS,Mac 上最稳的 Clash Meta(mihomo)前端。

**安装:**

```bash
brew install --cask mihomo-party
# 或从 GitHub 下 arm64 dmg:https://github.com/mihomo-party-org/mihomo-party/releases/latest
```

**导入步骤(场景化双 profile,推荐):**

我们在 `mihomo-profiles/` 目录维护了两套配置,按场景切换。详见 `mihomo-profiles/README.md`。简要:

| Profile 名 | 文件 | 适用 |
|---|---|---|
| `Saudi` | `mihomo-profiles/saudi.yaml` | 沙特日常 — 白名单代理(只代理几个被限制的服务) |
| `China` | `mihomo-profiles/china.yaml` | 中国出差 — 反向白名单(只直连国内站) |

**导入步骤:**

1. 打开 Mihomo Party
2. 左侧 **Profiles**(订阅)→ 右上 **+ New Profile** → 选 **Local Profile**
3. 名字 `Saudi`,粘 `mihomo-profiles/saudi.yaml` 全文 → Save
4. 重复一遍,名字 `China`,粘 `mihomo-profiles/china.yaml` 全文 → Save
5. 日常 Profiles tab 里点 `Saudi` 激活;出差前切到 `China`

切换是即时的,Mihomo Party 会自动 reload,不用重启 app 或重连节点。

---

**(备用)单 profile / 快速测试用:** 如果只想先跑通基本连接、不分场景,把下面这段最小 YAML 粘进一个 profile:

```yaml
proxies:
  - name: sydney-vpn
    type: vless
    server: marketingblogs.org
    port: 443
    uuid: dc4a1417-7ba3-4079-b40b-fd528ffebd9e
    network: ws
    tls: true
    udp: true
    servername: marketingblogs.org
    client-fingerprint: chrome
    skip-cert-verify: false
    ws-opts:
      path: /2f9a853f07e82681
      headers:
        Host: marketingblogs.org

proxy-groups:
  - name: PROXY
    type: select
    proxies:
      - sydney-vpn
      - DIRECT

rules:
  - DOMAIN-SUFFIX,cn,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
```

5. 保存,激活这条配置
6. 顶部模式选 **Rule**(规则分流)或 **Global**(全部走代理)
7. 右上角开总开关
8. **macOS 系统代理** 可在 app 里一键启用(会要求授权一次)

### iOS — Shadowrocket($2.99 App Store)

1. App Store 买 Shadowrocket
2. 右上 **+** → 类型 **VLESS** → 复制完整 URI 粘进去(或扫二维码)
3. 启用节点 → 主开关 ON

### Android — NekoBox(免费,Github)

1. 装 NekoBox
2. 右上 **+** → 从剪贴板导入 → 把 URI 粘上
3. 启用

### Windows — v2rayN

1. https://github.com/2dust/v2rayN/releases 下最新 zip(选带 Xray-core 的)
2. 解压运行 v2rayN.exe
3. 右键托盘图标 → 服务器 → 从剪贴板导入 vless URI

---

## 验证连接

### 1. 看 IP 是不是变了

启用代理后浏览器开:
- `https://ipinfo.io/json` — 应该显示 `org: CLOUDFLARENET` 或类似(不是你 KAUST/eduroam IP)
- `https://ifconfig.me/ip` — 显示一个 CF IP

> 注意:你看到的 IP 是 **CF 边缘 IP**,不是 VPS Sydney IP — 因为流量从 CF 边缘出站。这是 Tunnel 模式的特性,完全符合预期。

### 2. 测延迟

Mihomo Party 左侧 **Proxies** 标签 → 点 sydney-vpn → 显示当前延迟。
- 校园 eduroam → CF: 50-200 ms,正常
- 校园 eduroam → 加 Sydney VPS 那段:全程会 +100-200 ms
- 总延迟:200-400 ms 算正常,1000 ms 以上说明 CF IP 选得不好

### 3. 测能不能访问被墙网站(在 KAUST 应该不需要,但作为代理可用性测试)

- 浏览器开 https://www.google.com — 通
- https://chat.openai.com — 通(但 OpenAI 经常封 CF IP,可能不让你登录)
- https://www.netflix.com — 看得到首页,但**几乎肯定无法播放**(Netflix 黑 CF IP 段)

---

## 出差中国前的准备清单

| 项 | 做没做 |
|---|---|
| [ ] 跑 CloudflareST 优选最快的 CF IP | 把最快 10-20 个 IP 存到客户端 hosts |
| [ ] 客户端开 DoH(`1.1.1.1` over HTTPS) | 见各客户端的 DNS 设置 |
| [ ] 验证 Mihomo 在国内能用 | 让朋友在国内 VPN 模拟测试,或用 VPS 在国内的反向测试 |
| [ ] 备用线路(可选) | 同一台 Sydney VPS 上加 VLESS+REALITY 直连,只对你出差期间的 IP 段开端口 |

> 详见 `domain.md` 的 "出差中国前必做" 和 `vpn_build_plan.md` 阶段 11 的相关讨论。

---

## 常见问题

### 连上了但浏览器还是打不开网页

- 检查 Mihomo Party 是否启用了 **系统代理 / TUN 模式**(光启动 app 不够,要让 Mac 流量真的走它)
- 看 `Connections` 标签有没有连接记录;有 = app 在工作,没 = 系统没把流量导给它

### 延迟 > 1000ms 或频繁断流

- CF 当前 IP 段被 KAUST / 当地运营商限速
- 用 CloudflareST 跑优选 IP,把好的 IP 加到本机 `/etc/hosts`(`<ip> marketingblogs.org`)
- 或在 Mihomo 配置里覆盖 DNS

### Mihomo Party 启动后看到 "core not running"

- 第一次启动需要授权安装 helper(macOS Privileged Helper)
- 重启 app,弹窗时点 OK 输密码

### 怀疑 KAUST 网拦截了 marketingblogs.org

- 浏览器直接访问 https://marketingblogs.org/ 看博客能不能打开
- 打开 = DNS + TLS 都通,问题在 VPN client 配置
- 打不开 = 域名层面被拦(参考 domain.md 里"DNS / IP 过滤"那节)

### 节点泄漏 / 怀疑 UUID 被人偷了

1. SSH 进 VPS,跑 `xray uuid` 生成新 UUID
2. 改 `/usr/local/etc/xray/config.json` 里的 `clients[0].id`
3. `sudo systemctl restart xray`
4. 同步更新本文件 + 所有客户端
5. 老 URI 失效

---

## 服务端架构速查(用客户端时不需要,排错才看)

```
[你的 Mac/iPhone] ─ vless+ws+tls ─> [CF 边缘] ─ Tunnel ─> [cloudflared] ─ http ─> [nginx :8080]
                                                                                       │
                                                                          ┌────────────┴────────────┐
                                                                          ▼                          ▼
                                                                 GET /2f9a853f07e82681       GET / (其他)
                                                                 + Upgrade:websocket
                                                                          │                          │
                                                                          ▼                          ▼
                                                               proxy_pass → Xray :8090     /var/www/html (Hugo)
                                                                          │
                                                                          ▼
                                                                 freedom outbound → 互联网
```

完整说明见 `domain.md` 的 "浏览器访问 vs VPN 客户端访问 — 对比" 一节。
