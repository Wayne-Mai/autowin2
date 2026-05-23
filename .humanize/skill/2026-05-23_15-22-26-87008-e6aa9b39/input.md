# Ask Codex Input

## Question

You are a senior infrastructure / proxy-tunneling architect doing a FIRST-PASS planning review of a Chinese-language draft (translated context below). The draft is an upgrade plan for a personal VPS+Cloudflare proxy stack, going from a 2020-era V2Ray+Nginx+VMess+CF Origin CA setup to a 2026 stack. The target deployment is described as "AWS" (the repo directory is named `aws/`) but the draft itself mentions multiple VPS options (Oracle, Hetzner, RackNerd, BandwagonHost, CloudCone). Repository state: a brand-new `/Users/wayne/Documents/Trade` repo with only `aws/aws_draft.md` and no other files, no CLAUDE.md, no README, no existing config.

Things the draft requires KEEPING (immutable):
- Own VPS as real egress (dedicated IP)
- Cloudflare CDN in front to hide real IP
- WebSocket + TLS transport (to ride CDN 443)
- Own domain managed by Cloudflare DNS
- "Fallback to camouflage site" idea (probes get a normal webpage)

Things the draft proposes to UPGRADE (ranked by claimed payoff):
1. Protocol: VMess → VLESS (or Trojan). Migration claimed trivial: same ws path, same TLS cert, same CDN config — only change `protocol` field in inbound.
2. Core: V2Ray-core → Xray-core via official Xray-install script.
3. Remove Nginx — let Xray's `fallbacks` handle TLS termination on :443 + fallback to local :80 camouflage site.
4. Cert: CF Origin CA → acme.sh + Let's Encrypt with DNS-01 via Cloudflare API. Quote: `acme.sh --issue --dns dns_cf -d yourdomain.com`.
5. TLS fingerprint: add `"fingerprint": "chrome"` (uTLS) on the client side to evade JA3/JA4 detection.
6. ECH (Encrypted Client Hello) — client adds `"echConfig": "..."`, CF handles server side.
7. Inbound: open :443 → Cloudflared Tunnel. VPS exposes NO inbound ports; cloudflared opens an outbound connection to CF. Closes all firewall ports.
8. Client ecosystem refresh per platform (v2rayN/Nekoray/Mihomo Party/Shadowrocket/Stash/Streisand/v2rayNG/NekoBox/Surfboard/Sing-box/Clash Meta).
9. Optional: 3x-ui web panel (extra attack surface).
10. VPS choice: Oracle Free / Hetzner CAX11 / RackNerd / BandwagonHost CN2 / CloudCone. Note: under CDN, line quality of VPS doesn't matter much.

Final architecture: client (uTLS=chrome, ECH on) → CF edge → cloudflared Tunnel → Xray@VPS (VLESS+ws+TLS, fallbacks to camouflage) → target.

Changes summary: DELETE Nginx, CF Origin CA, VMess, firewall rules; SWAP V2Ray→Xray, VMess→VLESS; ADD uTLS, ECH, Cloudflared Tunnel, acme.sh; KEEP own VPS, CF CDN, ws+TLS, camouflage idea, dedicated egress IP.

Critique this draft as a planning input. Your job is NOT to write a plan — it is to surface assumptions, missing requirements, technical gaps, viable alternatives, decisions the user must make, and candidate acceptance criteria. Be specific and concrete.

Output EXACTLY in this format, with these labels on their own lines (no markdown headers, just labels):

CORE_RISKS:
- <highest-risk assumption or failure mode #1>
- <#2>
...

MISSING_REQUIREMENTS:
- <likely omitted requirement / edge case #1>
- ...

TECHNICAL_GAPS:
- <feasibility or architecture gap #1>
- ...

ALTERNATIVE_DIRECTIONS:
- <alternative #1 with tradeoff>
- ...

QUESTIONS_FOR_USER:
- <question that needs a human decision #1>
- ...

CANDIDATE_CRITERIA:
- <candidate acceptance criterion #1, including positive/negative tests if possible>
- ...

Be thorough but each bullet should be one or two tight sentences.

## Configuration

- Model: gpt-5.5
- Effort: high
- Timeout: 3600s
- Timestamp: 2026-05-23_15-22-26
- Tool: codex
