# <Plan Title>

## Goal Description
<Clear, direct description of what needs to be accomplished>

## Acceptance Criteria

Following TDD philosophy, each criterion includes positive and negative tests for deterministic verification.

- AC-1: <First criterion>
  - Positive Tests (expected to PASS):
    - <Test case that should succeed when criterion is met>
    - <Another success case>
  - Negative Tests (expected to FAIL):
    - <Test case that should fail/be rejected when working correctly>
    - <Another failure/rejection case>
  - AC-1.1: <Sub-criterion if needed>
    - Positive: <...>
    - Negative: <...>
- AC-2: <Second criterion>
  - Positive Tests: <...>
  - Negative Tests: <...>
...

## Path Boundaries

Path boundaries define the acceptable range of implementation quality and choices.

### Upper Bound (Maximum Acceptable Scope)
<Affirmative description of the most comprehensive acceptable implementation>
<This represents completing the goal without over-engineering>
Example: "The implementation includes X, Y, and Z features with full test coverage"

### Lower Bound (Minimum Acceptable Scope)
<Affirmative description of the minimum viable implementation>
<This represents the least effort that still satisfies all acceptance criteria>
Example: "The implementation includes core feature X with basic validation"

### Allowed Choices
<Options that are acceptable for implementation decisions>
- Can use: <technologies, approaches, patterns that are allowed>
- Cannot use: <technologies, approaches, patterns that are prohibited>

> **Note on Deterministic Designs**: If the draft specifies a highly deterministic design with no choices (e.g., "must use JSON format", "must use algorithm X"), then the path boundaries should reflect this narrow constraint. In such cases, upper and lower bounds may converge to the same point, and "Allowed Choices" should explicitly state that the choice is fixed per the draft specification.

## Feasibility Hints and Suggestions

> **Note**: This section is for reference and understanding only. These are conceptual suggestions, not prescriptive requirements.

### Conceptual Approach
<Text description, pseudocode, or diagrams showing ONE possible implementation path>

### Relevant References
<Code paths and concepts that might be useful>
- <path/to/relevant/component> - <brief description>

## Dependencies and Sequence

### Milestones
1. <Milestone 1>: <Description>
   - Phase A: <...>
   - Phase B: <...>
2. <Milestone 2>: <Description>
   - Step 1: <...>
   - Step 2: <...>

<Describe relative dependencies between components, not time estimates>

## Task Breakdown

Each task must include exactly one routing tag:
- `coding`: implemented by Claude
- `analyze`: executed via Codex (`/humanize:ask-codex`)

| Task ID | Description | Target AC | Tag (`coding`/`analyze`) | Depends On |
|---------|-------------|-----------|----------------------------|------------|
| task1 | <...> | AC-1 | coding | - |
| task2 | <...> | AC-2 | analyze | task1 |

## Claude-Codex Deliberation

### Agreements
- <Point both sides agree on>

### Resolved Disagreements
- <Topic>: Claude vs Codex summary, chosen resolution, and rationale

### Convergence Status
- Final Status: `converged` or `partially_converged`

## Pending User Decisions

- DEC-1: <Decision topic>
  - Claude Position: <...>
  - Codex Position: <...>
  - Tradeoff Summary: <...>
  - Decision Status: `PENDING` or `<User's final decision>`

## Implementation Notes

### Code Style Requirements
- Implementation code and comments must NOT contain plan-specific terminology such as "AC-", "Milestone", "Step", "Phase", or similar workflow markers
- These terms are for plan documentation only, not for the resulting codebase
- Use descriptive, domain-appropriate naming in code instead

## Output File Convention

This template is used to produce the main output file (e.g., `plan.md`).

### Translated Language Variant

When `alternative_plan_language` resolves to a supported language name through merged config loading, a translated variant of the output file is also written after the main file. Humanize loads config from merged layers in this order: default config, optional user config, then optional project config; `alternative_plan_language` may be set at any of those layers. The variant filename is constructed by inserting `_<code>` (the ISO 639-1 code from the built-in mapping table) immediately before the file extension:

- `plan.md` becomes `plan_<code>.md` (e.g. `plan_zh.md` for Chinese, `plan_ko.md` for Korean)
- `docs/my-plan.md` becomes `docs/my-plan_<code>.md`
- `output` (no extension) becomes `output_<code>`

The translated variant file contains a full translation of the main plan file's current content in the configured language. All identifiers (`AC-*`, task IDs, file paths, API names, command flags) remain unchanged, as they are language-neutral.

When `alternative_plan_language` is empty, absent, set to `"English"`, or set to an unsupported language, no translated variant is written. Humanize does not auto-create `.humanize/config.json` when no project config file is present.

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
