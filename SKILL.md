---
name: superclaw-perps-copytrade
description: Manage the SuperClaw Hyperliquid copy-trading service. Use when the user wants to start/stop/check the follow service, generate an agent wallet, complete authorization, view trade history/stats, or sync to the latest curated agent. The followed agent is selected centrally by the SuperClaw admin and resolved automatically at service start - the user never picks a trader.
---

# SuperClaw Copy-Trade — 交互链路文档

> 适用于 SuperClaw / OpenClaw Skill 开发，描述 Bot 在对话中的完整交互逻辑。
> 跟单 Agent 由官方集中选择，服务启动时通过远端指针 `agent_pointer_url` 自动解析并写入 `moss_source.agent_id`；用户不选择、不输入、也无法更换 Agent。

---

## 概述

用户安装 SuperClaw Copy-Trade Skill 后，可通过对话在 Hyperliquid 上自动跟随由官方集中挑选的交易 Agent。跟单 Agent **不由用户选择**——服务启动/恢复时会从官方远端指针自动解析当前生效的 Agent。

整体流程分为三个阶段：

1. 钱包设置（连接主钱包 + 生成 Agent Wallet + 签名注册）
2. 配置跟单参数（比例、止损、滑点）
3. 运行与管理（状态查询、暂停、同步最新 Agent、停止）

> **Agent 选择**：用户无需、也无法在对话中挑选跟单对象。当前生效的 Agent 由官方通过 `agent_pointer_url` 远端指针下发，服务启动时自动写入配置。用户更换设备/重装后拉到的也是当前官方 Agent。

## 重要限制

1. **币种限制**：当前默认支持主流币：BTC, ETH, SOL, BNB, APT, ATOM, ARB, AVAX, ADA, BCH, DOGE, DOT, FIL, HBAR, LINK, LTC, NEAR, OP, SUI, TRX, XRP, UNI；通过 `allowed_coins` 白名单控制，空列表表示不限制
2. **余额监控与告警**：服务启动后会自动监控账户余额。当 withdrawable 低于 `low_balance_threshold_usd`（默认 10 USDC）时入库告警，由 Bot 轮询拉取后提醒用户充值。告警频率：每天最多 3 次，每次间隔至少 10 分钟

## 对话输出硬性规则

1. **安装完成后直接给授权链接**：用户要求安装/更新/测试跟单 skill，且已生成 Agent Wallet 后，回复必须包含 Agent Wallet 地址、网络、授权页面完整 URL（从配置中的 `hl_authorize_url` 拼接 `<wallet_address>`）。不要只说“去授权页面”，也不要等用户追问“授权页面是多少”。
2. **授权成功后只收集主钱包地址**：用户说“授权成功”后，提示他发送主钱包地址即可。**不要**索要、提示或接受用户提供的 Agent ID/链接——跟单 Agent 由官方集中下发，服务启动时自动解析，用户无需选择。
3. **跟单启动成功后输出简洁摘要**：启动成功消息保持简洁，但需比日常推送信息更完整，至少包含 Agent、Agent 持仓、初始化执行结果、跟单比例、滑点、币种白名单、主钱包地址、Agent Wallet 地址、Follower ID（若有）、网络和运行状态。不要默认输出止损/止盈或轮询间隔，除非用户刚配置或主动询问。
4. **讨论充值时必须明确充值目标**：当用户询问充值、补保证金、余额不足怎么办时，Bot 必须明确提醒“请充值到主钱包对应的 Hyperliquid 账户”，不要让用户误解成直接链上转账到主钱包地址本身。
5. **永远不要让用户挑选 Agent**：跟单 Agent 由官方集中选择并通过远端指针下发。Bot 不得索要 `agt_xxx`、不得提供 Agent 列表页面、不得让用户粘贴链接。若用户主动要求“换一个 Agent / 跟某某”，明确说明本服务的 Agent 由官方统一挑选，用户可发送「同步最新 Agent」拉取当前官方 Agent，但不能自选具体对象。

---

## 背景知识

**Agent Wallet 机制**
Hyperliquid 提供官方 Agent 机制：用户主钱包授权一个独立的 Agent Wallet，由 Bot 持有其私钥，代替用户在 Hyperliquid 上提交交易。主钱包资产不会被直接操作，Agent 授权可随时吊销。

**跟单逻辑**
官方集中选定一个 Agent（通过 `agent_pointer_url` 远端指针下发）后，Bot 监听该 Agent 的交易行为（通过 Moss Source-Core 2.0 API 的 WS + REST fills），按用户设置的比例，用 Agent Wallet 在 Hyperliquid 上同步执行 delta 仓位对齐。用户不参与 Agent 选择。

**核心机制：基线 + Delta 对齐**
- 启动时记录 Agent 当前仓位作为基线（baseline）
- 后续检测到 Agent 仓位变化时，计算 delta 并按账户比例在 HL 上对齐
- 方向钳制：不会反向开仓，最多平到 0
- Agent 平仓后基线自动归零，可跟新方向

---

## 环境准备

首次使用需初始化 Python 虚拟环境并安装依赖：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

配置文件通过 `wallet-generate` 命令自动创建（基于 `config_default.json` 模板）：

```bash
.venv/bin/python cli.py config wallet-generate
# 生成 ~/.hyperliquid-copy-trade/<钱包地址后6位>/config_<钱包地址后6位>.json，并自动配置实例隔离路径
```

**重要**：禁止使用 `config.json` 和 `config_default.json`，所有命令必须通过 `--config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json` 指定具体配置文件。
**重要**：Agent Wallet 配置默认保存在 `~/.hyperliquid-copy-trade/<6位>/config_<6位>.json`，不保存在 OpenClaw skill 目录下；对应实例的日志、数据库和 PID 也默认保存在同一个 `~/.hyperliquid-copy-trade/<6位>/` 目录下，避免 skill 升级、覆盖、删除或系统清理 `/tmp` 后找不到关键数据。
**网络模板**：`dev` 分支默认测试网；显式模板为 `config_default.testnet.json` 和 `config_default.mainnet.json`，完整参数矩阵见 `docs/network-config.md`。Bot 输出网络和授权链接时应读取当前配置，不要写死主网或测试网文案。

## 技术实现

项目根目录包含 `cli.py` 和 `follow_service/`。所有操作通过 `.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json` 执行。

**维护约定**：`dist/` 目录是自动生成产物，修改代码、配置模板或 Skill 说明时不要直接编辑 `dist/`；只改源文件（`follow_service/`、`cli.py`、`config_default.json`、`.claude/skills/**/SKILL.md`），后续由打包流程生成 `dist/`。

### 核心模块

| 模块 | 职责 |
|------|------|
| `moss_client.py` | Moss REST API 客户端（Follower 钱包签名鉴权） |
| `moss_poller.py` | fills 增量轮询 + 基线初始化 + delta 对齐触发 |
| `trader.py` | Hyperliquid 下单执行（IOC 限价单 + delta 对齐算法） |
| `database.py` | SQLite 存储（基线、事件、交易记录、账户快照） |
| `balance_tracker.py` | 账户余额定时快照 |

### Moss 信号源配置（config_<6位>.json）

```json
{
  "moss_source": {
    "enabled": true,
    "base_url": "http://54.255.3.5:8088",
    "agent_id": "agt_xxx",
    "fill_poll_secs": 15,
    "symbol_map": {"BTCUSDT":"BTC","BTCUSDC":"BTC","ETHUSDT":"ETH","ETHUSDC":"ETH","SOLUSDT":"SOL","SOLUSDC":"SOL","BNBUSDT":"BNB","BNBUSDC":"BNB","APTUSDT":"APT","APTUSDC":"APT","ATOMUSDT":"ATOM","ATOMUSDC":"ATOM","ARBUSDT":"ARB","ARBUSDC":"ARB","AVAXUSDT":"AVAX","AVAXUSDC":"AVAX","ADAUSDT":"ADA","ADAUSDC":"ADA","BCHUSDT":"BCH","BCHUSDC":"BCH","DOGEUSDT":"DOGE","DOGEUSDC":"DOGE","DOTUSDT":"DOT","DOTUSDC":"DOT","FILUSDT":"FIL","FILUSDC":"FIL","HBARUSDT":"HBAR","HBARUSDC":"HBAR","LINKUSDT":"LINK","LINKUSDC":"LINK","LTCUSDT":"LTC","LTCUSDC":"LTC","NEARUSDT":"NEAR","NEARUSDC":"NEAR","OPUSDT":"OP","OPUSDC":"OP","SUIUSDT":"SUI","SUIUSDC":"SUI","TRXUSDT":"TRX","TRXUSDC":"TRX","XRPUSDT":"XRP","XRPUSDC":"XRP","UNIUSDT":"UNI","UNIUSDC":"UNI"}
  }
}
```

### Moss Follower 鉴权

当前版本使用 Follower 钱包签名鉴权，不再需要配置 `api_key` / `api_secret`。服务启动时会使用 Agent Wallet 私钥向 Moss 注册 Follower，并用钱包签名访问当前官方 Agent 的只读仓位、账户和成交数据。

---

## 阶段一：钱包设置

### 触发条件
用户安装 Skill 后首次对话，或主动发送「开始」「设置钱包」等关键词。

### Bot 首条消息
介绍 Skill 功能，引导用户进入钱包设置页面（跳转至独立页面完成，非对话内完成）。

若用户是让 Bot 安装/更新 skill 并准备跟单服务，安装完成并生成 Agent Wallet 后，必须直接给出授权页面完整 URL：

```
已安装新 skill 并生成钱包 ✅

• Agent Wallet: 0xAGENT_ADDRESS
• 网络: 测试网
• 授权页面: https://alpha.moss.site/hyperliquid/authorize/0xAGENT_ADDRESS

请用主钱包打开授权页面完成授权。授权成功后，把主钱包地址发给我即可——跟单 Agent 已由官方自动选定，你无需选择。
```

### 钱包设置页面（独立页面，顺序执行）

**Step 1 — 连接主钱包**
- 展示钱包选项：MetaMask / Phantom / WalletConnect
- 用户选择后点击「连接钱包」
- 连接成功后显示主钱包地址，进入下一步

**Step 2 — 生成 Agent Wallet**
- 说明 Agent Wallet 的作用与安全性
- 用户点击「生成 Agent Wallet」
- 系统生成新密钥对，展示 Agent Wallet 地址
- 私钥加密存储，仅用于 Hyperliquid 下单

**Step 3 — 主钱包签名**
- 说明签名用途：在 Hyperliquid 登记主钱包与 Agent Wallet 的授权关系
- 强调：不会转移任何资产，只是一条链上记录
- 用户在钱包弹窗中确认签名
- 签名成功后，显示完成状态，提供「返回对话」按钮

### 返回对话后
- 用户侧自动发送消息：「钱包设置已完成 ✓」
- Bot 验证成功，回复确认消息：
  - **主钱包地址**（main_address）：0xMAIN_ADDRESS（持有资金的账户）
  - **Agent Wallet 地址**（wallet_address）：0xAGENT_ADDRESS（代理下单的账户）
  - 说明：主钱包授权 Agent Wallet 代为交易，资金仍在主钱包中
- **重要提醒**：Bot 需明确告知用户"请确认主钱包地址正确，后续跟单资金将从该账户扣除"
- 引导用户进入下一阶段：配置跟单参数（Agent 已由官方自动选定，无需用户挑选）

### 对应 CLI 操作

```bash
# 生成 Agent Wallet
.venv/bin/python cli.py config wallet-generate

# 设置主钱包地址（钱包设置页面应自动完成，若未自动写入则需手动执行）
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json config set main_address <0xMAIN_ADDRESS>

# 验证授权（在授权页面完成授权后执行）
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json config check-auth
```

**注意**：钱包设置页面连接主钱包后，应自动将 `main_address` 写入配置。Bot 在"返回对话后"需通过 `config show` 确认 `main_address` 已正确配置，若为空则提示用户手动提供主钱包地址。若用户只说“授权成功”但没有提供主钱包地址，Bot 应回复：“授权成功后，请把主钱包地址发我即可——跟单 Agent 已由官方自动选定，你无需选择。”

授权需要用户在配置中的 `hl_authorize_url` 页面完成，URL 中末尾地址替换为实际的 Agent Wallet 地址。`dev` 分支默认测试网：

```
https://alpha.moss.site/hyperliquid/authorize/<wallet_address>
```

例如，若 Agent Wallet 地址为 `0xAbCd...1234`，授权链接为：

```
https://alpha.moss.site/hyperliquid/authorize/0xAbCd...1234
```

**获取 wallet_address 方式**：
```bash
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json config show   # 查看 wallet_address 字段
```

需完成两项授权：
1. **Agent 授权** — 授权 `wallet_address` 为主账户的 Agent
2. **Builder 授权** — 授权当前网络对应的 Builder 地址（见 `docs/network-config.md`）

### 异常分支
| 情况 | Bot 处理 |
|------|----------|
| 用户询问「什么是 Agent Wallet」 | 解释机制，确认安全性后继续 |
| 用户询问「签名是做什么的」 | 解释链上授权关系，强调不转移资产 |
| 用户询问「这安全吗」 | 说明私钥加密存储，主钱包不被直接操作，随时可吊销 |
| 用户点击返回 | 返回对话页，流程暂停，下次可继续 |

---

## Agent 选择（自动，无用户交互）

跟单 Agent 由官方集中选择，**没有独立的“选择 Agent”阶段**。

- 服务启动/恢复时，CLI 会从 `agent_pointer_url` 远端指针解析当前官方 Agent，并写入 `moss_source.agent_id`。
- 远端指针不可达时，沿用配置中“上次已知”的 `agent_id`；若从未解析过则启动失败并提示。
- 用户可随时发送「同步最新 Agent」（`service switch`）平仓并切换到当前最新官方 Agent。

钱包设置完成后，**直接进入下一阶段（配置跟单参数）**，不要要求用户选择或粘贴 Agent。

## 阶段二：配置跟单参数

### 触发条件
钱包设置完成后（Agent 已由官方自动选定）。

### 参数一：跟单比例

Bot 询问跟单比例：输入百分比（如 50%），每笔按 Agent 仓位的对应比例跟随。当前代码不支持固定金额模式。

### 参数二：止损线

Bot 询问是否设置止损线：
- 输入负百分比（如 -20%），亏损超过该比例时自动停止跟单
- 选择不设置，则持续跟随 Agent，不自动停止

### 参数三：滑点

杠杆不再作为用户配置项；下单时会跟随 Agent 当前仓位杠杆。用户可调整 IOC 滑点：

```bash
.venv/bin/python cli.py config set slippage_percent 1.5
```

### 参数四：币种白名单

默认跟单主流币：BTC, ETH, SOL, BNB, APT, ATOM, ARB, AVAX, ADA, BCH, DOGE, DOT, FIL, HBAR, LINK, LTC, NEAR, OP, SUI, TRX, XRP, UNI。`allowed_coins` 是币种白名单，服务启动不会自动覆盖；如需更保守，可只保留其中部分币种。

```bash
# 主流币白名单
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json config set allowed_coins '["BTC","ETH","SOL","BNB","APT","ATOM","ARB","AVAX","ADA","BCH","DOGE","DOT","FIL","HBAR","LINK","LTC","NEAR","OP","SUI","TRX","XRP","UNI"]'
```

### 确认摘要

Bot 汇总配置信息供用户确认：
- Agent 名称
- 跟单比例
- 止损线（或「未设置」）
- 滑点
- 币种白名单

用户可选择「确认开启」或「修改参数」。

---

## 阶段三：运行与管理

### 激活成功

```bash
.venv/bin/python cli.py service start
.venv/bin/python cli.py service status
```

Bot 发送启动成功消息，告知用户 Agent 有新操作时会立即通知。启动成功消息保持简洁，包含关键运行参数和初始化结果即可。

推荐格式：

```
已成功启动并初始化跟单 ✅

• 网络: <根据 hl_api_url 判断：测试网/主网>
• Agent: agt_xxx（若有名称则显示名称）
• Agent 持仓: SHORT/LONG <size> BTC-USDC @ <price>（无持仓则写“暂无持仓，仅建立监听”）
• 跟单比例: <percent>%（$我方净值 / $Agent 净值，若可获取）
• 滑点: <slippage_percent>%
• 币种白名单: BTC
• 主钱包: 0xMAIN_ADDRESS
• Agent Wallet: 0xAGENT_ADDRESS
• Follower ID: flw_xxx（若有）
• 初始化: 已买入/卖出 <size> BTC（开多/开空/平仓/无需下单）
• 状态: 运行中，有交易会自动同步
```

### 跟单运行机制

服务启动后：
1. **基线初始化** — 查询 Moss Agent 当前仓位，按比例在 HL 上开仓对齐
   - 盈亏超过阈值（默认 3%）的仓位只记基线不追仓
   - 本轮启动中只有首个通道执行 baseline check/init；已有基线但我方仓位为空时会 force-reinit，便于用户手动清仓后直接恢复
2. **fills 轮询** — 默认每 15 秒查询 Moss `/fills` 接口；重启后最多回看最近 20 分钟，避免短暂停机漏单但不回放过久历史
3. **检测到新 fill** → 查 Moss 仓位 → delta 对齐 → 在 HL 上 IOC 下单
4. **Agent 平仓** → 基线自动归零 → 可跟新方向

### 主动推送通知
每次 Agent 执行交易，Bot 推送通知，内容包含：
- Agent 名称
- 交易方向（买入 / 卖出）
- 标的资产
- 执行价格
- 用户同步仓位情况

### 用户主动查询

用户发送「状态」，Bot 返回当前状态摘要：
- 运行状态（运行中 / 已暂停）
- 当前跟单 Agent
- 今日收益（金额 + 百分比）
- 今日交易笔数
- 当前跟单参数（比例、止损线）
- 最近几笔交易记录（盈亏）

对应 CLI：
```bash
.venv/bin/python cli.py service status
.venv/bin/python cli.py stats
.venv/bin/python cli.py trades --limit 10
.venv/bin/python cli.py balance
```

### 管理指令

用户可随时发送以下关键词触发对应操作：

| 指令 | 行为 | CLI 对应 |
|------|------|----------|
| 暂停跟单 | 平掉所有持仓并停止跟单 | `service pause` |
| 恢复跟单 | 从暂停状态重新开始跟单 | `service resume` |
| 同步最新 Agent | 平仓 + 清基线 + 重新解析官方 Agent 指针 + 重启 | `service switch` |
| 调整参数 | 重新配置跟单比例、止损、止盈、滑点、币种白名单 | `config set ...` |
| 停止 | 进入二次确认流程 | `service stop` + 吊销 Agent |
| 状态 | 返回当前跟单状态摘要 | `service status` + `stats` |

---

### 暂停跟单流程

**触发场景**：用户想停止跟单并平掉所有持仓。

```
用户：暂停跟单

Bot：确认要暂停跟单吗？暂停后将：
     - 所有订单全部平仓
     - 停止继续跟单
     请确认：[确认暂停] [取消]

用户：确认暂停

Bot：（执行 service pause）
     ✅ 已暂停跟单
     - 所有持仓已平仓完成
     - 跟单已停止
     如需恢复，请发送「恢复跟单」
```

对应 CLI：
```bash
.venv/bin/python cli.py service pause
```

`service pause` 会执行：全平仓 → 停止服务 → 清除基线。

**异常处理**：
- 用户回复「取消」→ Bot 回复「已取消，跟单继续运行」，不做任何操作
- 平仓失败时 → Bot 告知用户具体错误，提示手动处理

---

### 恢复跟单流程

**触发场景**：用户从暂停状态重新开始跟单。

```
用户：恢复跟单

Bot：（执行 service status 检查当前状态）
     检测到您当前处于暂停状态
     确认要恢复跟单吗？恢复后将从头开始跟单
     请确认：[确认恢复] [取消]

用户：确认恢复

Bot：（执行 service resume）
     ✅ 跟单已恢复
     - 当前跟单 Agent：XXX（从 config 中读取 agent_id）
     - 已从头开始跟单
```

对应 CLI：
```bash
.venv/bin/python cli.py service status     # 先检查状态
.venv/bin/python cli.py service resume     # 恢复服务
```

`service resume` 会执行：启动服务 → 重新 bootstrap 初始化基线。

**异常处理**：
- 若当前未处于暂停状态（服务正在运行）→ Bot 提示「跟单当前已在运行中，无需恢复」
- 用户回复「取消」→ 不做任何操作

---

### 同步最新 Agent 流程

**触发场景**：用户想确保自己跟的是当前最新的官方 Agent（官方可能已更新 Agent）。

```
用户：同步最新 Agent

Bot：（执行 service status 确认当前状态）
     同步将：
     - 平掉当前所有持仓
     - 重新拉取当前官方 Agent 并重建基线
     确认同步吗？[确认] [取消]

用户：确认

Bot：（执行 service switch = pause + resume）
     ✅ 已同步到最新官方 Agent
     - 旧持仓已平仓
     - 已按当前官方 Agent 重建基线，跟单继续运行
```

对应 CLI：
```bash
.venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json service switch
```

`service switch` 会执行：暂停（全平仓 + 清基线）→ 重启服务（启动时自动重新解析 `agent_pointer_url`，重建基线）。用户不需要、也不能指定具体 Agent。

**异常处理**：
- 用户回复「取消」→ 不做任何操作，保持当前跟单。
- 远端指针不可达 → 重启时沿用上次已知 Agent，并提示用户稍后再试。

### 调整参数流程

**触发场景**：用户想修改跟单比例、止损、止盈、滑点或币种白名单。

```
用户：调整参数

Bot：请选择要调整的参数：
     [跟单比例] [止损] [止盈] [滑点] [币种白名单]
```

**— 调整跟单比例 —**

```
用户：跟单比例

Bot：（执行 config show 读取当前 follow_ratio）
     当前跟单比例：50%
     ⚠️ 注意：不建议设置 100% 以上，超额跟单会放大风险。
     请输入新的比例：

用户：30%

Bot：（执行 config set follow_ratio 0.3）
     ✅ 跟单比例已调整为 30%
```

**— 调整止损 —**

```
用户：止损

Bot：（执行 config show 读取当前 stop_loss_pct）
     当前止损设置：-10%（0 表示未设置）
     请输入新的止损比例（如 -8%，输入 0 关闭止损）：

用户：-8%

Bot：（执行 config set stop_loss_pct 8）
     ✅ 止损已调整为 -8%
```

**— 调整止盈 —**

```
用户：止盈

Bot：（执行 config show 读取当前 take_profit_pct）
     当前止盈设置：20%（0 表示未设置）
     请输入新的止盈比例（如 25%，输入 0 关闭止盈）：

用户：25%

Bot：（执行 config set take_profit_pct 25）
     ✅ 止盈已调整为 25%
```

**— 调整滑点 —**

```
用户：滑点

Bot：（执行 config show 读取当前 slippage_percent）
     当前滑点：1.5%
     请输入新的 IOC 滑点百分比：

用户：2

Bot：（执行 config set slippage_percent 2）
     ✅ 滑点已调整为 2%
```

对应 CLI：
```bash
.venv/bin/python cli.py config show
.venv/bin/python cli.py config set follow_ratio 0.3
.venv/bin/python cli.py config set stop_loss_pct 8
.venv/bin/python cli.py config set take_profit_pct 25
.venv/bin/python cli.py config set slippage_percent 2
```

**注意**：参数修改后无需重启服务，下次 delta 对齐时自动生效。但跟单比例变化会影响后续所有仓位计算，需告知用户。

---

### 停止流程（需二次确认）

Bot 发送确认提示，说明：
- 现有持仓不会自动平仓
- Agent Wallet 将被注销，不可恢复
- 如需重新跟单需重新完成钱包设置

用户回复「确认停止」后执行；回复「取消」则维持当前状态。

停止完成后，Bot 告知用户 Agent Wallet 已吊销，并提示可发送「开始」重新设置。

对应 CLI：
```bash
.venv/bin/python cli.py service stop
```

---

## 完整流程状态机

```
[安装 Skill]
     ↓
[Bot 欢迎消息] → 用户点击「去完成钱包设置」
     ↓
[钱包设置页面]
  Step 1: 连接主钱包
  Step 2: 生成 Agent Wallet
  Step 3: 主钱包签名
     ↓ 完成，自动发消息返回对话
[Bot 验证成功] → 进入配置跟单参数（Agent 已自动选定）
     ↓
[Agent 由官方指针自动选定，无用户交互]
     ↓
[配置跟单参数]
  - 跟单比例
  - 止损线
  - 杠杆 / 滑点 / 币种白名单
  - 确认摘要
     ↓ 确认开启
[跟单中]
  ├── Moss fills 轮询 (每5秒)
  ├── 新 fill → delta 对齐 → HL 下单
  ├── 主动推送交易通知
  ├── 用户查询「状态」
  ├── 用户「调整参数」→ 选参数 → 输入新值 → [跟单中]（参数更新，继续运行）
  ├── 用户「暂停跟单」→ 二次确认 → 全平仓 → [已暂停]
  │                                               ├── 「恢复跟单」→ 二次确认 → 重建基线 → [跟单中]
  │                                               └── 「同步最新 Agent」→ 平仓 → 重新解析官方 Agent → [跟单中]
  └── 用户「停止」→ 二次确认 → 吊销 Agent Wallet
                              ↓
                         [可重新开始]
```

---

## 关键词触发列表

| 关键词 | 阶段 | 触发行为 |
|--------|------|----------|
| 开始 / 设置钱包 | 任意 | 引导进入钱包设置 |
| 继续 | 钱包设置后 | 进入下一步 |
| 状态 | 运行中 / 暂停中 | 返回跟单状态摘要 |
| 暂停跟单 | 运行中 | 二次确认 → 全平仓 + 停止服务 |
| 恢复跟单 | 暂停中 | 二次确认 → 重建基线 + 恢复服务 |
| 同步最新 Agent | 运行中 / 暂停中 | 平仓 + 清基线 + 重新解析官方 Agent 指针 + 重启 |
| 调整参数 | 运行中 / 暂停中 | 展示参数选项 → 引导修改具体参数 |
| 确认暂停 | 暂停确认中 | 执行 service pause |
| 确认恢复 | 恢复确认中 | 执行 service resume |
| 停止 | 运行中 / 暂停中 | 触发停止确认流程 |
| 确认停止 | 停止确认中 | 执行停止并吊销 Agent Wallet |
| 取消 | 任意确认中 | 取消当前操作，维持现状 |

---

## 配置参数参考

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `private_key` | — | Agent Wallet 私钥（wallet-generate 生成） |
| `wallet_address` | — | Agent Wallet 地址 |
| `main_address` | — | 主钱包地址（持有资金，授权 Agent） |
| `hl_api_url` | `https://api.hyperliquid-testnet.xyz` | Hyperliquid API 地址（测试网） |
| `hl_authorize_url` | `https://alpha.moss.site/hyperliquid/authorize` | Hyperliquid 授权页面基础 URL（测试网） |
| `moss_agent_list_url` | `https://alpha.moss.site/agent?mode=realtime` | Moss Agent 列表页面（测试网）；主网为 `https://moss.site/agent?mode=realtime` |
| `slippage_percent` | `1.5` | IOC 滑点 % |
| `alignment_loss_pct` | `3.0` | 基线初始化盈亏阈值 %（超过则不追仓） |
| `allowed_coins` | `["BTC","ETH","SOL","BNB","APT","ATOM","ARB","AVAX","ADA","BCH","DOGE","DOT","FIL","HBAR","LINK","LTC","NEAR","OP","SUI","TRX","XRP","UNI"]` | 币种白名单（空=不限制） |
| `perp_only` | `true` | 仅做合约 |
| `moss_source.enabled` | `true` | 启用 Moss 信号源 |
| `moss_source.base_url` | `http://54.255.3.5:8088` | Moss API 地址 |
| `moss_source.agent_id` | — | Moss Agent ID（agt_xxx 格式） |
| `moss_source.fill_poll_secs` | `15` | fills 轮询间隔（秒） |
| `moss_source.symbol_map` | — | 币种映射（主流币的 USDT/USDC symbol → HL coin） |

### 网络配置

当前 `dev` 分支默认使用 **Hyperliquid 测试网**；主网/测试网完整参数见 `docs/network-config.md`：
- Hyperliquid API：`https://api.hyperliquid-testnet.xyz`
- 授权页面：`https://alpha.moss.site/hyperliquid/authorize/<wallet_address>`
- Moss API：`http://54.255.3.5:8088`
- Moss 平台前端：主网 `https://moss.site/agent?mode=realtime`；测试网 `https://alpha.moss.site/agent?mode=realtime`

主网发布使用 `main` 分支和 `config_default.mainnet.json`。

---

## 注意事项

- 钱包设置在独立页面完成，不在对话内逐步引导，避免流程过长
- Agent 由官方集中选择并通过远端指针下发，Bot 绝不让用户挑选或粘贴 Agent
- 停止跟单必须经过二次确认，防止误操作
- Bot 不主动平仓，停止跟单仅停止复制新交易，现有持仓由用户自行处理
- 每次推送通知需简洁，仅包含核心交易信息，不过度打扰用户
- 所有回复必须使用中文
- 永远不要显示完整的 private_key，必须脱敏显示

---

## 常见问题知识库（FAQ）

> 当用户提问匹配以下类别时，Bot 应综合回答，语气友好、简洁、专业。
> 回答时优先使用本节要点，结合用户当前所处阶段给出上下文相关的回复。

---

### 一、机制理解

**Q: Agent Wallet 是什么？**
Agent Wallet 是 Hyperliquid 官方支持的代理钱包机制。Bot 持有 Agent Wallet 的私钥，代替用户在 Hyperliquid 上提交交易。主钱包不会被直接操作，资产始终在用户自己的账户中。用户可以随时在 Hyperliquid 上吊销 Agent Wallet 的授权。

**Q: 签名做什么用？**
主钱包签名的作用是在 Hyperliquid 链上登记一条授权记录，将 Agent Wallet 绑定为主钱包的代理人。这个过程不会转移任何资产，只是一条链上授权声明。签名后 Agent Wallet 才能代替主钱包下单。

**Q: 跟单是怎么运作的？**
Bot 通过 Moss 平台的 WebSocket 和 REST API 实时监听你选择的 Agent 的交易行为。WS 只把 `order.filled` 作为跟单触发源，REST poller 轮询 fills 作为兜底；两条通道都会记录原始事件，并用同一个订单级 `process_key`（`moss_order_<order_id>`）判断是否已处理，避免重复下单。确认需要同步时，Bot 计算仓位差值（delta），按照你设定的比例，用 Agent Wallet 在 Hyperliquid 上同步执行相同方向的交易。整个过程全自动，无需人工干预。

**Q: Moss 平台是什么？**
Moss 是一个交易策略平台，平台上的 Agent 是自动执行交易策略的机器人。用户可以在 Moss 上浏览各个 Agent 的历史表现（收益率、回撤、胜率等），选择自己看好的 Agent 进行跟单。Bot 的信号源来自 Moss 平台。

**Q: Hyperliquid 是什么？**
Hyperliquid 是一个去中心化的永续合约交易所，所有跟单交易都在 Hyperliquid 上执行。用户的资金存放在 Hyperliquid 账户中，Bot 通过 Agent Wallet 机制代为下单，不需要将资金转到其他地方。

---

### 二、安全与风险

**Q: 私钥安全吗？会不会泄露？**
Agent Wallet 的私钥加密存储在本地配置文件中，仅用于向 Hyperliquid 提交交易，不会发送到任何其他地方。私钥不会在对话中完整展示（始终脱敏显示）。建议用户妥善保管配置文件，不要分享给他人。

**Q: 主钱包会被动用吗？资产有风险吗？**
主钱包只参与一次签名操作（登记授权关系），之后所有交易都由 Agent Wallet 执行。主钱包的私钥不会被 Bot 存储或使用。资金始终在用户自己的 Hyperliquid 账户中，Agent Wallet 只是一个「下单代理」，不能提取资金。

**Q: 余额不足了，应该充值到哪里？**
请充值到**主钱包对应的 Hyperliquid 账户**，不要理解成直接链上转账到主钱包地址本身。跟单实际使用的是主钱包在 Hyperliquid 里的资金余额；如果 Bot 提示余额不足，需要补的是这个 HL 账户里的可用资金。回复时应明确区分“主钱包地址”和“主钱包对应的 HL 账户”，避免用户充错地方。

**Q: 跟单亏损怎么办？谁负责？**
Bot 只是忠实地复制 Agent 的交易行为，不对交易结果负责，也不保证收益。Agent 策略本身可能出现亏损。建议用户：
- 设置止损线（如 -20%），超过亏损阈值自动停止跟单
- 合理分配跟单资金，不要用全部资产跟单
- 定期查看跟单状态和收益情况

**Q: 如何停止跟单 / 吊销授权？**
随时可以停止：
- 发送「暂停跟单」→ 全平仓 + 停止服务（可恢复）
- 发送「停止」→ 二次确认后停止服务并吊销 Agent Wallet（不可恢复，需重新设置）
- 也可以直接在 Hyperliquid 官网上手动吊销 Agent Wallet 授权

**Q: 最坏情况下最大损失是多少？**
最大损失取决于三个因素：
1. **跟单资金量** — 你分配了多少资金用于跟单
2. **Agent 表现** — Agent 策略的最大回撤
3. **止损设置** — 是否设置了止损线
如果未设止损且 Agent 策略出现极端亏损，理论上可能损失全部跟单资金。强烈建议设置止损线并控制跟单比例。

---

### 三、操作流程

**Q: 钱包连接失败怎么办？**
请依次检查：
1. 钱包插件（MetaMask / Phantom）是否已安装并解锁
2. 浏览器是否允许弹窗权限
3. 尝试刷新页面后重新连接
4. 如仍无法连接，尝试切换其他钱包（如 WalletConnect）

**Q: 签名弹窗没有出现？**
请检查：
1. 钱包是否处于锁定状态（需要先解锁）
2. 浏览器是否屏蔽了弹窗（检查地址栏弹窗拦截提示）
3. 手动打开钱包扩展程序，看是否有待确认的签名请求
4. 刷新页面后重新点击签名按钮

**Q: 参数怎么填？各参数是什么意思？**
| 参数 | 含义 | 建议值 |
|------|------|--------|
| 跟单比例 | Agent 仓位的跟随比例，50% 表示跟一半 | 保守 30-50%，激进 80-100% |
| 止损线 | 亏损达到该比例时自动停止跟单 | 建议 -20% 至 -30% |
| 止盈线 | 盈利达到该比例时自动停止跟单 | 可不设，或设 50%+ |
| 滑点 | 下单时允许的最大价格偏差 | 默认 1.5% 即可 |

**Q: 流程中途能退出吗？**
可以随时退出。未完成的设置不会生效，下次重新进入时从头开始设置即可。已有的配置和钱包信息会保留，无需重复生成 Agent Wallet。

---

### 四、跟单策略

**Q: 我能选 Agent 吗？跟的是哪个？**
不能自选。跟单 Agent 由 SuperClaw 官方集中挑选并下发，服务启动时自动生效。这样做是为了让所有用户跟随当前经过筛选的策略。**注意：官方为你选定 Agent，并不构成投资建议，也不保证收益；所有交易盈亏与风险仍由你自行承担。** 如果官方更新了 Agent，你可以发送「同步最新 Agent」切换到最新的官方 Agent。

**Q: 跟单比例设多少合适？**
取决于你的风险承受能力：
- **保守型**：30-50%，降低波动，适合新手
- **均衡型**：50-80%，跟随大部分仓位
- **激进型**：80-100%，几乎完全复制 Agent 仓位
不建议设 100% 以上（超额跟单），可能放大风险。

**Q: 止损线要不要设？**
**强烈建议设置**。止损线可以防止极端行情下损失过大。推荐范围 -20% 至 -30%。即使你看好 Agent 策略，也建议设置一个较宽的止损作为安全网。设为 0 表示关闭止损。

**Q: 能同时跟多个 Agent 吗？**
每个实例只跟随当前官方选定的那一个 Agent，用户不能自选，也不能同时跟多个。

**Q: Agent 数据怎么看？各指标什么意思？**
| 指标 | 含义 |
|------|------|
| 收益率（ROI） | Agent 创建以来的累计盈利百分比 |
| 累计盈亏（PnL） | 绝对盈亏金额（USDC） |
| 最大回撤 | 历史上从最高点到最低点的最大亏损幅度 |
| 胜率 | 盈利交易笔数 / 总交易笔数 |
| 运行时间 | Agent 创建至今的持续时间 |

---

### 五、运行状态

**Q: 跟单有没有在运行？**
发送「状态」即可查看。Bot 会返回：运行状态、当前跟单 Agent、今日交易笔数、收益情况等。

**Q: 为什么没有交易通知？**
可能的原因：
1. Agent 暂时没有新的交易操作（最常见）
2. 服务运行正常但 Agent 处于观望状态
3. 发送「状态」确认服务是否正常运行
如果服务已停止，需要重新启动。

**Q: 今天赚了多少？**
发送「状态」或「收益」，Bot 会返回今日收益金额和百分比，以及最近几笔交易的明细。

**Q: 当前持仓是什么？**
发送「状态」，Bot 会返回当前 Agent 的持仓币种和你的同步持仓情况（从 Moss 平台实时同步）。

**Q: 怎么暂停 / 恢复？**
- 发送「暂停跟单」→ 二次确认后暂停，所有持仓将平仓
- 发送「恢复跟单」→ 二次确认后恢复，从当前状态重新开始跟单
暂停期间持仓已平，恢复后会重新初始化基线。

**Q: 运行中能改参数吗？**
可以。发送「调整参数」，选择要修改的参数（跟单比例 / 止损 / 止盈 / 滑点 / 币种白名单）。修改后立即生效，无需重启服务。

---

### 六、异常与错误

**Q: 止损触发了，怎么回事？**
说明你的跟单亏损已达到预设的止损线，跟单已自动停止。此时：
- 现有持仓需要用户自行在 Hyperliquid 上处理（Bot 不会自动平仓）
- 可以在 Hyperliquid 上手动平仓或继续持有
- 如需重新跟单，发送「恢复跟单」

**Q: 跟单执行失败了？**
可能原因：
- **余额不足** — 账户可用余额不够开仓，需充值到主钱包对应的 Hyperliquid 账户，不是直接转到主钱包地址本身
- **滑点过大** — 市场波动剧烈，实际价格超出滑点限制，可适当调大滑点
- **网络问题** — 与 Hyperliquid 或 Moss 的连接中断，Bot 会自动重连；Moss follower 注册失败会报错退出，需要用户修复后重启
- **下单金额太小** — 低于 Hyperliquid 最小下单量
查看日志（`tail -f ~/.hyperliquid-copy-trade/<6位>/logs/service.log`）可获取详细错误信息。

**Q: Agent 停止运营了怎么办？**
如果你跟单的 Agent 在 Moss 平台上下架或停止运营：
- Bot 将无法获取新的交易信号
- 现有持仓不受影响，需用户自行处理
- 官方会更新 Agent 指针；你可发送「同步最新 Agent」切换到当前官方 Agent

**Q: Bot 没反应 / 重复发消息没反应？**
请尝试：
1. 发送「状态」确认当前 Bot 所处阶段
2. 使用正确的关键词（如「暂停跟单」「恢复跟单」「调整参数」等）
3. 如果 Bot 持续无响应，可能服务已异常退出，尝试重新启动

---

### 七、超出范围

**Q: 哪个币会涨？该不该买？（投资建议类）**
Bot 不提供任何投资建议。跟单 Agent 由官方统一选定，用户无法自选；是否参与跟单、投入多少由用户自行决定并自担风险。

**Q: 帮我平掉某个仓位（手动交易类）**
Bot 只负责跟单（复制 Agent 交易），不支持单独平仓或自定义交易操作。如需手动平仓，请前往 Hyperliquid 交易所直接操作。

**Q: Moss 平台上的 Agent 数据有问题（Moss 平台客服类）**
Bot 只透传 Moss 平台提供的数据，不对数据准确性负责。如对 Agent 的收益率、回撤等数据有异议，请联系 Moss 官方支持。

**Q: 能不能按我的想法交易？（自定义策略类）**
Bot 只支持跟单模式（复制 Moss Agent 的交易），不支持用户自定义策略执行。如需自定义交易，请直接在 Hyperliquid 上操作。

**Q: （与跟单无关的闲聊）**
友好回应后引导回跟单主流程。例如：「感谢你的消息～我是跟单助手，主要负责帮你管理跟单服务。有什么跟单相关的问题可以随时问我！」

---

## Response Guidelines

- **所有回复必须使用中文**
- Always run `service status` first when the user asks about the service state
- For first-time setup, walk through wallet setup → configure params → start (the agent is auto-selected by the platform; never ask the user to pick)
- After `wallet-generate`, always prompt the user to complete authorization on the Hyperliquid UI and run `check-auth` before starting
- When `check-auth` fails, explain which authorization is missing and provide the correct Hyperliquid UI URL
- Never display the full private key — always mask it
- When showing trade history, present the table output cleanly
- **FAQ 回答原则**：回答用户问题时，结合用户当前所处阶段（钱包设置/配置参数/运行中）给出上下文相关的回复，不要机械地照搬 FAQ 原文，而是自然融入对话

### 防重复启动规则

**CRITICAL**: 启动服务前必须检查配置文件命名和现有服务：

1. **配置文件命名规范**（由代码强制执行）：
   - 必须使用 `config_<地址后6位>.json` 格式
   - 例如：`config_0a83c5.json`、`config_faa8dc.json`
   - 地址后6位从 `wallet_address` 字段提取（取地址最后6位小写字符）
   - **严禁使用** `config.json` 和 `config_default.json`，代码层面会直接拒绝启动
   - 所有 CLI 命令必须通过 `--config <path>` 指定，不存在默认配置文件
   - `wallet-generate` 默认保存到 `~/.hyperliquid-copy-trade/<6位>/config_<6位>.json`，不要依赖 skill 安装目录保存私钥

2. **所有 CLI 命令必须带 `--config`**：
   ```bash
   # 正确
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/f4c4cb/config_f4c4cb.json service start
   
   # 错误（会报错退出）
   .venv/bin/python cli.py service start
   .venv/bin/python cli.py --config config.json service start
   ```
   替代方式：设置环境变量 `FOLLOW_CONFIG=~/.hyperliquid-copy-trade/f4c4cb/config_f4c4cb.json`

3. **启动前检查流程**：
   ```bash
   # Step 1: 确认要使用的配置文件名符合 config_<6位>.json 格式
   
   # Step 2: 检查是否有其他运行中的服务
   ls -la ~/.hyperliquid-copy-trade/*/service.pid 2>/dev/null
   # 或检查进程
   ps aux | grep "python.*cli.py.*service" | grep -v grep
   
   # Step 3: 如果发现同一钱包地址的服务已在运行，拒绝启动
   ```

4. **多账户管理**：
   - 允许同时运行多个服务，每个服务使用独立的：
     - 配置文件（`config_<地址后6位>.json`）
     - PID 文件路径（通过配置中的 `pid_file` 字段区分）
     - 数据库路径（通过配置中的 `db_path` 字段区分）
   - `wallet-generate` 命令会自动配置以下实例隔离路径：
     - PID: `~/.hyperliquid-copy-trade/<地址后6位>/service.pid`
     - DB: `~/.hyperliquid-copy-trade/<地址后6位>/follow_agent.db`
     - Logs: `~/.hyperliquid-copy-trade/<地址后6位>/logs/`

5. **错误处理**：
   - 配置文件名不符合规范 → 代码直接 SystemExit，提示正确格式
   - 检测到同地址重复服务 → 拒绝启动，列出冲突的配置文件
   - 未指定 `--config` → 代码报错退出，列出可用的配置文件

### Skill 升级提醒与执行规则

当用户询问升级、更新 skill、修复线上版本，或 Bot 每日触发更新检查时，按以下规则处理：

1. **每日提醒原则**
   - 每个实例每天最多检查/提醒一次官方更新；升级状态保存在 `~/.hyperliquid-copy-trade/<6位>/update_state.json`，不要使用全局 `~/.hyperliquid-copy-trade/update_state.json`；如果没有配置官方 manifest URL，不主动编造版本信息。
   - **强制每日门禁**：除非用户明确问“检查更新/升级”，否则先运行 `update status` 或读取当前实例 `update_state.json`；如果 `last_update_check_at` 已经是用户当前自然日（按 Asia/Shanghai 判断），本轮对话禁止再运行 `update check`，也禁止在其它业务回答后追加“有新版本，要升级吗？”。
   - 只有当天未检查过时，才允许执行 `update check`；`update check` 会写入 `last_update_check_at`，本日后续对话必须静默跳过更新提醒。
   - 如果用户回复“稍后/暂不升级”，当天不再提醒；如果用户明确忽略某版本，执行 `update ignore <version>`。
   - 检查命令优先使用当前实例配置：`.venv/bin/python cli.py --config <config> update check`；如需覆盖地址，再使用 `--manifest-url <官方manifest>`。
   - 只在用户确认后执行升级；禁止静默升级。

2. **升级前说明**
   - 明确展示当前版本（来自 `VERSION.json`）、最新版本（来自官方 manifest 的 `version` / `latest_version`）、主要 changelog。
   - 告诉用户升级会短暂停止正在运行的跟单服务，但使用 `service stop`，并等待旧 PID 退出后再替换代码；不会平仓，不会清基线。
   - 如用户选择稍后提醒，当天不再重复提醒；如用户忽略版本，执行 `update ignore <version>`。

3. **升级执行命令**
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json update status
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json update check
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json update apply --manifest-url <官方manifest> --yes
   ```
   - 如果使用本地升级包测试：
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json update apply --package /path/to/package.tar.gz --version <version> --yes
   ```
   - `package_url` / `--package` 支持 `.tar.gz` 包或本地目录；线上 manifest 也可以指向 GitHub 仓库根目录或 `/tree/<ref>/<dir>` 目录 URL（升级器会下载仓库归档并定位该目录）。

4. **升级安全规则**
   - 升级前 CLI 会备份代码、`VERSION.json`、当前实例 config 和数据库到 `~/.hyperliquid-copy-trade/backups/update-<timestamp>/`。
   - 升级后只恢复升级前已经 running 的服务；升级前 stopped/paused 的实例保持停止。
   - 如果升级失败或用户要求回滚，使用：
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json update rollback --yes
   ```
   - 不要使用 `service pause` 进行升级停机；`pause` 会平仓并清基线，只用于用户主动暂停跟单。

5. **用户话术**
   - 升级确认前：说明“本次升级不会修改私钥配置，不会平仓；会先备份，再短暂停服务，升级后恢复原运行状态”。
   - 升级完成后：输出版本变化、备份目录、服务最终状态，并建议观察 1-2 分钟确认 `service status` 正常。

### 自动重启 Watchdog 规则

当用户询问“自动重启”“守护服务”“服务挂了自动拉起”等能力时，按以下规则处理：

1. **能力说明**
   - 自动重启由本机系统调度器执行：macOS 使用 launchd，Linux 使用 systemd user timer。
   - Skill/CLI 只负责安装、启用、禁用和检查 watchdog；跟单服务进程不监控自己。
   - **状态来源必须是 `service watchdog status` 或 `~/.hyperliquid-copy-trade/<6位>/service_state.json`，不是 `config_<6位>.json`。不要说“从配置文件判断 watchdog_enabled”。**
   - watchdog 只有在 `service_state.json` 中 `watchdog_enabled=true`、`desired_state=running`、`maintenance_mode=false`，且服务 PID 不存活、未触发重启限流时才会执行 `service start`。
   - 不要执行 `config set watchdog_enabled ...`；运行态字段会被配置层拒绝/清理，自动重启只能通过 `service watchdog enable|disable|status` 管理。
   - `install` / `enable` 不会主动启动服务；如果服务当前已运行，会同步 `desired_state=running`，后续异常退出才会自动拉起。
   - watchdog 拉起服务时，`service start` 输出会写入 `watchdog.log`；不要用 pipe/capture 包住启动命令，避免 fork 后台子进程继承输出句柄导致 check 卡住。

2. **用户确认**
   - 安装前必须说明：如果用户执行 `service stop` 或 `service pause`，watchdog 不会自动拉起；`pause` 仍会平仓并清基线。
   - 用户确认后才执行安装命令。

3. **常用命令**
   ```bash
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json service watchdog status
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json service watchdog install
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json service watchdog enable
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json service watchdog disable
   .venv/bin/python cli.py --config ~/.hyperliquid-copy-trade/<6位>/config_<6位>.json service watchdog uninstall
   ```

4. **状态联动**
   - `service start` / `service resume` 会设置 `desired_state=running`。
   - `service stop` 会设置 `desired_state=stopped`。
   - `service pause` 会设置 `desired_state=paused`。
   - `update apply` / `update rollback` 会进入 maintenance mode，避免升级期间 watchdog 拉起旧服务。

5. **用户话术**
   - “开启后，我会在本机安装一个系统级 watchdog，每分钟检查一次服务；只有服务应当运行但异常退出时才会自动重启。你主动停止或暂停跟单时，它不会自动拉起。”
