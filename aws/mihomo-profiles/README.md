# Mihomo Profiles — 多场景规则切换

两套**完全相反策略**的 Mihomo (Clash Meta) 规则文件,根据你人在哪里切换。

| 文件 | 策略 | 用在哪 |
|---|---|---|
| `saudi.yaml` | **白名单代理** — 默认直连,少数域名才走代理 | 沙特 / KAUST 校园 / 大部分日常 |
| `china.yaml` | **反向白名单** — 默认代理,中国域名才直连 | 中国出差期间 |

两套都连同一个节点 `sydney-vpn`(Sydney AWS),差别只在 `rules:` 段。

---

## 为什么不用一套规则两边都跑

| 场景 | "全代理"策略 | "全直连+白名单"策略 |
|---|---|---|
| 沙特日常 | 浪费 — 沙特能直连的网站很多,绕一圈 Sydney 平添延迟 + VPS 流量消耗 | ✅ 最优,只代理需要的 |
| 中国出差 | ✅ 必须,因为 GFW 屏蔽太多无法列白名单 | ❌ 行不通,白名单永远漏 |

两种策略**根本不兼容**,所以分两个文件。

---

## 怎么在 Mihomo Party 切换

### 一次性导入两个 Profile

1. Mihomo Party → **Profiles** tab → 右上 **+ New Profile** → **Local**
2. 名字 `Saudi`,粘 `saudi.yaml` 全文 → Save
3. 重复一遍,名字 `China`,粘 `china.yaml` 全文 → Save

### 日常切换

Mihomo Party → **Profiles** → 点想用的那个(`Saudi` / `China`)→ 它会变成激活状态(蓝色高亮)。

Mihomo 会自动 reload 配置,**不用重启 app,不用重连**。已有的连接会保持。

> 也可以从命令行查当前激活的 profile,但 UI 切换最方便。

---

## 怎么添加 / 删除走代理的网站(沙特模式)

编辑 `saudi.yaml` 的 `rules:` 段,在"白名单"区域加一行:

```yaml
- DOMAIN-SUFFIX,example.com,PROXY
```

保存后:
- 如果你在 Mihomo Party 里是直接编辑 Profile(不是引用本文件)→ 改完 Save,自动 reload
- 如果你从本目录复制粘贴的(我们当前做法)→ 重新粘一遍 YAML 到 Mihomo Party

> 想完全实时同步:Mihomo Party 也能用 `file://` 协议引用本地文件,但跨设备就不方便了。
> 简单做法:本目录是"源",改完再粘一次。

### 常见规则类型

| 写法 | 含义 |
|---|---|
| `DOMAIN-SUFFIX,foo.com,PROXY` | 匹配 `foo.com` 及所有子域(`x.foo.com`, `a.b.foo.com`)|
| `DOMAIN-KEYWORD,foo,PROXY` | URL 包含 `foo` 的所有域名(慎用,容易误中)|
| `DOMAIN,exactfoo.com,PROXY` | 精确匹配,子域不算 |
| `IP-CIDR,1.2.3.0/24,PROXY` | IP 段(`no-resolve` 防 Mihomo 反查 DNS)|
| `GEOIP,US,PROXY` | 国家 IP 段(需要 GeoIP 数据)|
| `MATCH,PROXY` | 兜底,放最后一条 |

---

## 怎么添加 / 删除走直连的网站(中国模式)

`china.yaml` 反过来 — 默认走代理,需要补充的是**新发现的中国站**(代理走绕远):

```yaml
- DOMAIN-SUFFIX,bilibili.com,DIRECT
```

加在 `# === 中国域名 / IP 直连 ===` 区域。

---

## YAML 字段说明(都两个文件共享的部分)

| 段 | 作用 |
|---|---|
| `mixed-port: 7890` | Mihomo 本地代理端口(HTTP + SOCKS5)|
| `mode: rule` | 启用规则分流模式(其他可选:`global`, `direct`) |
| `dns: ...` | DNS 解析配置,**fake-ip 模式 + DoH 是绕过 GFW DNS 污染的核心** |
| `proxies: ...` | 节点定义,可以加多个 |
| `proxy-groups: ...` | 节点分组,UI 上可选 |
| `rules: ...` | 流量分流规则 |

### 关键安全相关字段

- `client-fingerprint: chrome` — uTLS 把 TLS Client Hello 伪装成 Chrome,过 JA3 检测(中国模式核心)
- `tls: true` + `servername: marketingblogs.org` — TLS 加密,SNI 用真实域名(配合 ECH 加密)
- `skip-cert-verify: false` — 必须校验证书,防 MITM

---

## 进阶:URL 订阅自动同步

如果你想把这两个 YAML 放到 GitHub / Gist / 自己 VPS 的 web 目录上,Mihomo Party 可以**通过 URL 订阅**自动拉,改动后下次启动自动 reload。

但**节点 URI 是敏感信息**(UUID + 秘密 path),公开 URL = 节点泄漏。要做的话至少:
- 用 GitHub Private Gist
- 或自己 VPS 上加 nginx basic auth
- 或开 CF Access(零信任,需要登录才能拿)

懒省事直接复制粘贴是最稳的。

---

## 节点轮换 / 应急

两个 YAML 里都只有一个节点 `sydney-vpn`。**未来如果加多节点:**

- 多 VPS:在 `proxies:` 段加新条目,`proxy-groups` 里把新节点也加入 PROXY group
- 自动选最快:把 `PROXY` group 类型从 `select` 改成 `url-test`,Mihomo 会自己测速选最优
- 故障切换:`fallback` 类型,主节点挂了自动切备用

---

## 如何彻底搞懂规则匹配

[Mihomo 官方文档 Rules 章节](https://wiki.metacubex.one/config/rules/) 是最权威的。要点:

1. 规则**自上而下**匹配,**第一条匹配的就生效**,后面不看
2. `MATCH` 是兜底,必须放最后
3. `IP-CIDR` 默认会反查 DNS,加 `no-resolve` 防止泄漏 DNS 给 ISP
4. `GEOIP,CN` 比 `DOMAIN-SUFFIX,cn` 覆盖广(很多中国网站不是 `.cn`)
5. 改了 YAML 之后 Mihomo Party 自动检测变化并 reload,但偶尔不灵 — 手动点一下 profile 强制 reload
