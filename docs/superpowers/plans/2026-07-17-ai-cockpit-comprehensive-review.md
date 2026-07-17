---
author: Codex
title: "AI Cockpit 全面评审整改实施计划"
description: "基于模板维护、安装对象和人机协作分离评审的循环实施计划。"
keywords:
  - ai-cockpit
  - governance
  - implementation-plan
  - human-agent-collaboration
---

# AI Cockpit 全面评审整改实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Every step uses checkbox (`- [ ]`) syntax. The execution loop below is mandatory.
**Goal:** 将评审确认的 Conditional GO 结论转化为 17 个可独立验收的整改 Work Item，并在全部整改完成后发布新版本、清理本计划文档。
**Architecture:** AI Cockpit 继续分为三个边界：模板维护工程、安装对象工程、Human-Agent Collaboration。每个整改项遵循“一项工单、一个专用分支、一个 PR”的生命周期；先修复人机决策与证据闭环，再修复模板发布与采用方升级，最后发布版本。
**Tech Stack:** Python、pytest、Make、GitHub Actions、JSON/YAML、Markdown、AI Cockpit Work Item Contract/Summary。

## Global Constraints

- 模板维护工程按单人维护模式治理：允许个人 CODEOWNER 和维护者发布决定，不宣称独立双人审核或组织级身份信任边界。
- 安装对象工程的 Review Policy、CI、Coverage、Quality、Release Policy 和审批人数由采用方校准，模板只提供配置入口、检查能力和 Adapter。
- 每个整改项必须从最新远程默认分支创建专用分支，并使用一个 Contract、一个 Summary、一个 PR；不得把独立整改项合并到同一 PR。
- 每个整改项必须执行：Contract → Preflight → 实现/文档 → Verification → Summary → `ai-finish`/Archive → Push → PR → Merge → `ai-close-work-item`。
- 任何 `needs_human_confirmation`、`not_ready`、验证失败、范围越界、证据缺失或 PR 归属失败都必须 fail closed，暂停当前循环并记录原因；不得默默进入下一工单。
- 用户已明确授权本计划范围内的分支创建、文件修改、测试、提交、推送、PR、合并、版本发布、分支清理和最后清理计划文档等操作；需要额外扩大范围、改变产品行为或增加外部平台权限时，必须再次取得授权。
- 第 17 项是最后一个实现/发布 Work Item；第 18 项只有在第 1–17 项均已归档、合并且验证通过后才可执行。
- 第 18 项执行后删除本计划文档；不得删除任何 Contract、Summary、Archive、Release Evidence 或历史审计记录。

## 评审结论

同意用户提供的全面评审结论：

- 模板维护工程为 **Conditional GO**：可以继续单人维护、内部迭代和公共模板发展；当前发布链仍需补强 Source Identity、时间可信性、Acceptance 证据绑定和人类决策交接；企业级密码学可信发布尚未成立。
- 安装对象工程为 **Adoption GO，Production Conditional GO**：首次安装可继续使用，但安装成功不等于项目已完成质量、CI、Coverage、Review 和 Release 校准。
- Human-Agent Collaboration 方向正确但交接协议不足：`needs_human_confirmation` 必须从通用诊断状态升级为结构化 Human Decision Request，并具备可验证的 Decision Evidence 和 Resume Protocol。
- 模板不强制所有采用方双人审批；采用方按自身组织和风险决定单人、双人或更严格政策。
## 工单总表

| 顺序 | 优先级 | Work Item | 依赖 | 完成标志 |
| --- | --- | --- | --- | --- |
| 1 | P0 | Human Decision Request Schema | 无 | 能生成结构化请求，包含发生了什么、重要性、选项、推荐、问题和恢复条件 |
| 2 | P0 | Human Decision Gate 与 Resume Protocol | 1 | Decision Evidence 与当前 Preflight Hash 绑定，重新计算为 `ready` 后才能恢复 |
| 3 | P0 | Acceptance-to-Evidence Traceability | 无 | 每项 Acceptance 有 ID、证据映射，引用测试存在且在本次 Verification 中执行 |
| 4 | P0 | Work Item Start Receipt | 无 | 实现变更前写入不可变 Start Receipt，记录基线、时间、Scope Digest 和 Contract Skeleton Digest |
| 5 | P0 | Release Source Default-Branch Binding | 无 | Release Source Commit 必须等于远程默认分支 HEAD，未知默认分支 fail closed |
| 6 | P1 | Review Readiness Finalization | 3 | Stabilization 和最终 Summary 校验完成后才提升 Readiness |
| 7 | P1 | Lockfile Reproducibility Runtime Fix | 无 | Clean Runner 真正执行 `$(PYTHON) -m piptools compile` 并验证锁文件可复现 |
| 8 | P1 | Published Release / Candidate Release 分离 | 5 | Quick Install 只消费已发布 `release.json`，候选版本使用独立文件 |
| 9 | P1 | Release Workflow Run Correlation | 5 | Release Evidence 绑定唯一 Workflow Run、Source Commit、Tag 和生成物 |
| 10 | P0 | Safe Upgrade Work Item Lifecycle | 无 | Upgrade 自动建立分支、Contract、Summary、Diff、Verification 和 PR 生命周期 |
| 11 | P0 | Project-owned Guard Preservation | 10 | Upgrade 对采用方 Guard 做归属识别和保护，不直接覆盖项目拥有的配置 |
| 12 | P1 | Default Branch Discovery Fail-closed | 10 | 有 Remote 但无法识别默认分支时阻止 Upgrade，要求显式 Base 参数或 API 证据 |
| 13 | P1 | Upgrade Conflict Report | 10、11 | 输出 Template-owned、Project-owned、Diverged 和需人工确认的冲突报告 |
| 14 | P1 | Organization Review Policy Adapter | 无 | 提供采用方可配置的单人、团队、双人和高风险 Review Policy Adapter |
| 15 | P1 | Adoption Readiness / Production Readiness 分离 | 10、14 | 安装完成、校准完成、生产就绪三种状态明确分离并有检查命令 |
| 16 | P2 | Action SHA Fail-closed、Archive Sequence、Complexity 增量指标 | 5、10 | 补强 Action 固定、Archive 顺序和治理复杂度增量报告，所有回归测试通过 |
| 17 | 发布 | 发布新版本 | 1–16 | 所有前置工单已合并、归档、验证通过；从允许的默认分支 Source 发布新版本 |
| 18 | 收尾 | 清理实施计划文档 | 17 | 删除本文件，保留所有实施工单的历史证据和发布证据 |

## 执行循环与授权

### 每个 Work Item 的强制循环

对工单 1–17，按以下循环执行；一次循环只推进一个工单：

1. `git fetch` 远程默认分支，记录 `baseRemote`、`baseBranch`、`baseCommit`，创建 `codex/<work-item>` 专用分支。
2. 执行 `make ai-start TASK=<task> TITLE="..." MODE=code`，补全 Contract 的 `scope`、`outOfScope`、`sources`、`acceptance`、`verification`、`intent`、风险、Agent 能力和执行决定。
3. 执行 `make ai-preflight`。若状态不是 `ready`，立即向用户报告 Preflight Review；未获得有效 Human Decision Evidence 前不得编码。
4. 先写失败测试或验证脚本，再做最小实现；只修改 Contract Scope 内文件。
5. 执行 Contract 声明的项目检查和 AI 检查，特别是 Acceptance 对应的证据命令。
6. 执行 `make ai-checkpoint ... STAGE=before_finish`，记录漂移检查和剩余风险。
7. 更新 Summary：`changedFiles`、`verification`、`guidelinesCompliance`、`checkpointEvidence`、`reviewReadiness`、`residualRisks`、`knownGaps` 和 `intentAlignment`。
8. 执行 `make ai-finish TASK=<task>`，确认 Archive、Cockpit Status 和 PR Ownership 证据生成成功。
9. 推送专用分支，创建并合并 PR；不得在本地直接合并到 base 分支，也不得提前删除 Work Item 分支。
10. PR 合并后执行 `make ai-close-work-item TASK=<task>`，确认分支、Work Item、PR、远程 base、干净 worktree 全部闭环。
11. 重新读取评审结果和仓库状态，选择下一个依赖已满足的工单；重复本循环。

### 失败、暂停和恢复规则

- 同一工单任何一个硬门失败时，保持该工单 active，不创建下一个工单，不伪造 Summary，不降低检查门槛。
- 失败信息必须包含：失败命令、实际输出、影响范围、推荐修复、是否需要用户决定、恢复条件。
- 若需要用户决定，写入 Human Decision Request/Decision Evidence；重新运行 Preflight，只有 `ready` 才能恢复。
- 若发现评审结论需要新增文件或超出当前 Contract，先更新 Contract 并重新执行 Scope/Preflight；不得直接越界修改。
- 用户已授权上述正常工程流程，但授权不覆盖秘密、凭据、外部组织审批或未经说明的破坏性数据删除；这些事项仍必须暂停并请求明确授权。

### 全部完成后的顺序

工单 17 发布新版本前，必须确认工单 1–16 的 PR 已合并、Archive Evidence 完整、`make check-ai-pr` 和项目质量检查通过。发布成功后，执行工单 18 删除本计划文档；删除前必须确认新版本 Tag、Release Evidence、Published Release 文件和安装验证均成功。工单 18 只删除计划文档，不删除任何 Work Item 历史记录。
## 工单 1：Human Decision Request Schema

**目标：** 把 `needs_human_confirmation` 从通用 Recommendation 升级为结构化决策请求。
**文件：** 修改 `scripts/ai_preflight_review.py`、`scripts/ai_governance_compression.py`、`.ai/guards/preflight_review_policy.yaml`；测试 `tests/test_preflight_review.py`、`tests/test_governance_compression.py`；更新 `docs/contract-fields.md` 和 `.ai/cockpit/README.md`。
**步骤：**
- [ ] 为 `needs_human_confirmation` 增加失败测试，断言输出包含 `decisionId`、`whatHappened`、`whyItMatters`、`options`、`recommendedOption`、`recommendationReason`、`question`、`resumeCondition`。
- [ ] 执行 `pytest -q tests/test_preflight_review.py tests/test_governance_compression.py`，确认新测试先失败。
- [ ] 实现稳定、可序列化的 Schema 和从现有 Signals/Decision Drivers 到人类可读内容的映射；缺少证据时保持保守状态。
- [ ] 增加 Schema 校验和字段文档；执行上述测试、`make check-ai-preflight-review`、`make check-ai-status`。
- [ ] 完成该 Work Item 的标准生命周期循环。
## 工单 2：Human Decision Gate 与 Resume Protocol

**目标：** 没有与当前 Preflight Hash 绑定的有效人类决定时，Agent 不得从 Human Decision State 进入 Implementation State。
**文件：** 修改 `scripts/ai_preflight_review.py`、`scripts/ai_start.py`、`scripts/ai_finish.py`、`scripts/ai_common.py`、`.ai/guards/preflight_review_policy.yaml`、`.ai/cockpit/README.md`；测试 `tests/test_preflight_review.py`、`tests/test_start_and_archive.py`、`tests/test_finish_e2e.py`。
**步骤：**
- [ ] 增加无 Decision、过期 Hash、错误 Contract Hash、未重新 Preflight 时的失败测试。
- [ ] 实现 Decision Evidence 的读取、Hash 校验、`human_decision_recorded` 状态和重新 Preflight 的恢复路径。
- [ ] 让 `ai-start`/`ai-preflight` 在 Gate 开启时 fail closed，并保留用户已授权的当前流程配置语义。
- [ ] 验证 `ready → implementation → ready_for_review` 及 `not_ready/needs_human_confirmation → decision → ready` 状态转换。
- [ ] 完成标准生命周期循环，并把暂停/恢复证据写入 Summary。
## 工单 3：Acceptance-to-Evidence Traceability

**目标：** 让每项 Acceptance 具备可执行且可追溯的证据，不再只验证“有命令输出”。
**文件：** 修改 `scripts/ai_acceptance_policy.py`、`scripts/ai_check_summary.py`、`scripts/ai_finish.py`、`.ai/guards/summary_policy.yaml`；测试 `tests/test_acceptance_policy.py`、`tests/test_ai_check_summary.py`、`tests/test_finish_readiness.py`；更新 `docs/contract-fields.md`。
**步骤：**
- [ ] 增加缺少 Acceptance ID、缺证据、测试路径不存在、测试未执行和 Bug Fix 缺少失败场景的失败测试。
- [ ] 实现 Acceptance Evidence Mapping 校验，并让高风险项要求人工 Review 标记。
- [ ] 将映射结果写入 Summary 和 Archive Evidence；保持旧 Contract v1 只读兼容。
- [ ] 执行 `pytest -q tests/test_acceptance_policy.py tests/test_ai_check_summary.py tests/test_finish_readiness.py` 及 `make quality`。
## 工单 4：Work Item Start Receipt

**目标：** 用不可变 Receipt 证明 Work Item 起始时间早于实现变更。
**文件：** 新增 `scripts/ai_start_receipt.py`；修改 `scripts/ai_start.py`、`scripts/ai_check_work_item.py`、`scripts/ai_check_pr.py`、`Makefile`；新增/修改 `tests/test_start_and_archive.py`、`tests/test_ai_check_work_item.py`、`tests/test_pr_aggregate.py`；更新 `docs/reference/repository-workflow.md`。
**步骤：**
- [ ] 增加 Start Receipt 结构、Digest 和 Git-tracked path 的测试，覆盖 Receipt 缺失、篡改、基线不一致。
- [ ] 让 `ai-start` 在实现变更前创建 `.ai/work-items/starts/<work-item-id>.json`，记录 Work Item ID、Base Commit、Start Timestamp、Initial Scope Digest、Contract Skeleton Digest。
- [ ] 让 PR 检查验证 Receipt 的不可变性和与 Contract/分支基线的绑定。
- [ ] 通过 `make ai-start`、`pytest`、`make check-ai-pr AI_BASE_COMMIT=origin/main` 验证完整路径。
## 工单 5：Release Source Default-Branch Binding

**目标：** Release 只能来自远程默认分支的明确 HEAD。
**文件：** 修改 `.github/workflows/release.yml`、`scripts/check_release_distribution.py`、`scripts/ai_common.py`、`tests/test_workflows.py`、`tests/test_release_distribution.py`、`docs/distribution.md`。
**步骤：**
- [ ] 增加功能分支 Source、默认分支 Source、Remote HEAD 缺失和显式 Base 参数的失败/成功测试。
- [ ] 在 Release Workflow 中 fetch 远程默认分支并验证 `SOURCE_COMMIT == origin/<default-branch>`；无法解析时 fail closed。
- [ ] 将 Source Commit、Remote、Default Branch 和 Run ID 写入 Release Evidence。
- [ ] 执行 Workflow 静态检查、`pytest -q tests/test_workflows.py tests/test_release_distribution.py`、`make check-release-evidence`。
## 工单 6：Review Readiness Finalization

**目标：** Readiness 只在 Stabilization、Summary 和最终 Status 校验全部通过后提升。
**文件：** 修改 `scripts/ai_finish.py`、`scripts/ai_generate_status.py`、`scripts/ai_check_status.py`；测试 `tests/test_finish_readiness.py`、`tests/test_finish_e2e.py`、`tests/test_guards_and_status.py`。
**步骤：**
- [ ] 增加后续 Stabilization 失败时 Readiness 保持 `not_ready` 的回归测试。
- [ ] 调整执行顺序为 `Declared Verification → Stabilization → Final Summary Validation → Promote Review Readiness → Final Status Generation → Final Status Consistency`。
- [ ] 验证任何中间失败都不会留下过期的正向 Readiness。
- [ ] 执行相关 pytest、`make ai-finish` 演练和 `make check-ai-status-consistency`。
## 工单 7：Lockfile Reproducibility Runtime Fix

**目标：** Clean Runner 实际运行锁文件可复现命令，并修复无 `.venv` 时的解释器路径问题。
**文件：** 修改 `Makefile`、`.github/workflows/compatibility.yml` 或对应 Clean Runner Workflow、`tests/test_makefile.py`；更新 `docs/distribution.md`。
**步骤：**
- [ ] 增加测试断言 Target 使用 `$(PYTHON) -m piptools compile`，而非从 `$(dir $(abspath $(PYTHON)))` 查找可执行文件。
- [ ] 修改 Make Target 和 Clean Runner，使其在干净环境中真正执行该 Target。
- [ ] 使用项目提供的 Python 环境运行锁文件检查，记录缺失依赖时的明确失败信息。
- [ ] 执行 `pytest -q tests/test_makefile.py`、锁文件 Target、`make quality`。
## 工单 8：Published Release / Candidate Release 分离

**目标：** Quick Install 永远只读取已发布版本，候选版本不污染安装入口。
**文件：** 修改 `release.json`、发布准备脚本/Workflow、`install.sh`、`scripts/install_ai_cockpit.py`、`tests/test_install_sh.py`、`tests/test_install_script.py`、`tests/test_release_distribution.py`；更新 `docs/installation.md`、`docs/upgrade.md`。
**步骤：**
- [ ] 增加候选 Tag 尚未发布时 Quick Install 仍使用已发布 `release.json` 的回归测试。
- [ ] 引入 `next-release.json` 作为候选版本元数据，明确其不能被 Quick Install 消费。
- [ ] 校验已发布 Tag、Digest、Manifest 和安装入口之间的一致性。
- [ ] 执行安装测试、发布证据测试和 `make check-ai-adoption-ready`。
## 工单 9：Release Workflow Run Correlation

**目标：** 让 Release Evidence 能唯一关联 Workflow Run、Source Commit、Tag 和生成物。
**文件：** 修改 `.github/workflows/release.yml`、`scripts/check_release_distribution.py`、`.ai/cockpit/release-digests.json`；测试 `tests/test_release_distribution.py`、`tests/test_workflows.py`；更新 `docs/distribution.md`。
**步骤：**
- [ ] 增加缺 Run ID、Run SHA 与 Source 不一致、Tag 不一致和 Artifact Digest 不一致的失败测试。
- [ ] 生成并校验不可歧义的 Release Correlation Record。
- [ ] 将 Correlation Record 接入发布检查和安装验证。
- [ ] 执行发布证据测试、Workflow 检查和 `make check-release-evidence`。
## 工单 10：Safe Upgrade Work Item Lifecycle

**目标：** `--upgrade` 与首次 Adoption 享有同等级的 Work Item、分支、验证和 PR 治理。
**文件：** 修改 `scripts/install_ai_cockpit.py`、`scripts/ai_start.py`、`Makefile`；测试 `tests/test_installer.py`、`tests/test_adoption_e2e.py`、`tests/test_install_script.py`；更新 `docs/upgrade.md`、`docs/reference/upgrade.md`。
**步骤：**
- [ ] 增加 Upgrade 创建分支、Contract、Summary、Template Version Diff 和 PR Ownership 的失败测试。
- [ ] 实现 Upgrade Work Item 生命周期；有 Active Work Item 时保持默认阻止。
- [ ] 将升级前后版本、Managed File Diff 和恢复点写入 Contract/Summary。
- [ ] 执行 Adoption/Upgrade 测试、`make check-ai-adoption-ready` 和完整质量检查。
## 工单 11：Project-owned Guard Preservation

**目标：** Upgrade 识别并保留采用方拥有的 Guard、Coverage、Risk 和 Scope 校准。
**文件：** 修改 `scripts/install_ai_cockpit.py`、`scripts/ai_project_profile.py`、`.ai/project_profile.yaml` 或其模板；测试 `tests/test_installer.py`、`tests/test_project_governance.py`、`tests/test_adoption_e2e.py`；更新 `docs/getting-started/adopter-configuration.md`、`docs/reference/upgrade.md`。
**步骤：**
- [ ] 增加 Project-owned Guard 被覆盖、模板未改动 Guard 可升级、Diverged Guard 需确认三类测试。
- [ ] 建立 Template-owned / Project-owned / Diverged 文件归属判定。
- [ ] 对项目拥有文件执行保留或冲突报告，不直接覆盖；记录每个决定。
- [ ] 执行 Installer 回归测试和完整 Adoption 检查。
## 工单 12：Default Branch Discovery Fail-closed

**目标：** 区分无 Remote 与 Remote 存在但默认分支未知，后者不得静默按 Local-only 继续。
**文件：** 修改 `scripts/install_ai_cockpit.py`、`scripts/ai_common.py`、`Makefile`；测试 `tests/test_installer.py`、`tests/test_install_script.py`、`tests/test_adoption_e2e.py`；更新 `docs/reference/upgrade.md`。
**步骤：**
- [ ] 增加 Remote 缺失、Remote HEAD 已知、Remote HEAD 缺失但显式 `--base-remote/--base-branch` 和两者都缺失的测试。
- [ ] 实现默认分支解析优先级：Remote API/HEAD 证据，其次显式参数；无证据时 fail closed。
- [ ] 将 Base Remote、Base Branch、Base Commit 写入 Adoption/Upgrade Contract。
- [ ] 执行 Installer 测试和 `make check-ai-status-consistency`。
## 工单 13：Upgrade Conflict Report

**目标：** 让 Upgrade 在 Diverged Managed File 或 Project-owned 冲突时输出可供人决定的报告。
**文件：** 新增 `scripts/ai_upgrade_conflict_report.py`；修改 `scripts/install_ai_cockpit.py`、`scripts/ai_preflight_review.py`；测试 `tests/test_installer.py`、`tests/test_preflight_review.py`、`tests/test_adoption_e2e.py`；更新 `docs/reference/upgrade.md`。
**步骤：**
- [ ] 增加冲突报告结构和报告缺失、路径归属错误、未确认继续的失败测试。
- [ ] 输出每个文件的 Template-owned、Project-owned、Diverged、Human Confirmation Required 分类、差异摘要和建议。
- [ ] 将需要人决定的冲突接入工单 1–2 的 Decision Request/Gate；未确认时不应用升级。
- [ ] 执行冲突场景测试、完整 Installer 测试和质量检查。
## 工单 14：Organization Review Policy Adapter

**目标：** 提供采用方按风险配置 Review Policy 的 Adapter，而不是把双人审批写死在模板中。
**文件：** 修改 `.ai/guards/ai_review_policy.yaml`、`scripts/ai_check_review_policy.py`、`scripts/ai_project_profile.py`；测试 `tests/test_project_governance.py`、`tests/test_governance_compression.py`、`tests/test_adoption_ready.py`；更新 `docs/getting-started/adopter-configuration.md`、`docs/reference/repository-workflow.md`。
**步骤：**
- [ ] 增加单人维护、团队 CODEOWNERS、双人审批和高风险保护环境的配置矩阵测试。
- [ ] 实现 Adapter 配置入口、Doctor 检查和 Readiness 报告；模板维护工程保持诚实的 single-maintainer 声明。
- [ ] 验证模板不会把采用方政策误报为模板自身的独立审核证明。
- [ ] 执行 Review Policy、Adoption Readiness 和项目治理测试。
## 工单 15：Adoption Readiness / Production Readiness 分离

**目标：** 明确区分安装完成、校准完成和生产就绪。
**文件：** 修改 `scripts/ai_readiness_policy.py`、`scripts/ai_check_adoption_ready.py`、`scripts/ai_onboard.py`、`.ai/cockpit/adoption.md`；测试 `tests/test_adoption_ready.py`、`tests/test_ai_onboard.py`、`tests/test_onboard_e2e.py`；更新 `docs/getting-started/installation.md`、`docs/getting-started/first-work-item.md`。
**步骤：**
- [ ] 增加“安装成功但质量/CI/Review 未校准”不得标记 Production Ready 的测试。
- [ ] 建立 Adoption Installed、Calibration Complete、Production Ready 的状态和必需证据。
- [ ] 将 Profile、Guard、Quality Command、CI、Review Policy、Release Policy 纳入采用方检查。
- [ ] 执行 Onboarding/Adoption 测试、`make ai-onboard` 和 `make check-ai-adoption-ready`。
## 工单 16：Action SHA、Archive Sequence 与 Complexity 增量指标

**目标：** 完成剩余 P2 稳定化工作，并保持历史 Archive 不可变。
**文件：** 修改 `.github/workflows/*.yml`、`scripts/ai_archive_work_item.py`、`scripts/check_governance_complexity.py`、相关 `.ai/guards/*.yaml`；测试 `tests/test_workflows.py`、`tests/test_ai_archive_work_item.py`、`tests/test_governance_complexity.py`；更新 `docs/reference/governance-complexity.md`、`docs/reference/work-item-lifecycle-closure.md`。
**步骤：**
- [ ] 增加 Action 未固定 SHA、Archive 顺序错误、历史计数阻塞当前任务、复杂度增量异常的失败测试。
- [ ] 对第三方 Action 使用固定 SHA；修正 Archive 顺序并确保历史记录只增不改；增加当前变更的复杂度增量报告。
- [ ] 执行 Workflow 静态检查、Archive/Complexity 测试、`make quality` 和 PR 聚合检查。
- [ ] 只有所有 P0/P1 工单完成且本项通过后，才进入发布工单。
## 工单 17：发布新版本

**目标：** 在工单 1–16 全部完成、合并和归档后，从已验证的远程默认分支发布新版本。
**文件：** 修改 `release.json`、`.ai/cockpit/version.json`、`.ai/cockpit/release-digests.json`、发布 Workflow/Manifest；测试 `tests/test_release_distribution.py`、`tests/test_workflows.py`、安装 Smoke/Compatibility 测试。
**前置条件：**
- [ ] 确认工单 1–16 的 Archive Contract/Summary 完整，所有 PR 已合并，所有 `make ai-close-work-item` 成功。
- [ ] 确认 `origin/<default-branch>`、Source Commit、Smoke、Compatibility、Release Evidence 和 Candidate/Published 文件一致。
- [ ] 确认版本号、变更摘要和发布内容已经由本计划范围内的验证证据支持。
**执行步骤：**
- [ ] 从最新远程默认分支创建唯一发布准备 Work Item 分支并执行 `make ai-start`/`make ai-preflight`。
- [ ] 先运行完整项目质量检查、Smoke、Compatibility、Release Evidence 和安装验证；任何失败都不发布。
- [ ] 生成候选 Release Evidence，验证 Source Default-Branch Binding 和 Workflow Run Correlation。
- [ ] 创建并合并发布 PR，按项目 Release Workflow 创建新版本 Tag/Release。
- [ ] 使用 Quick Install 和 Upgrade Smoke 验证已发布版本；记录 Tag、Digest、Run ID、Source Commit 和生成物。
- [ ] 执行标准 Work Item 归档和 `make ai-close-work-item`；发布成功是进入工单 18 的唯一条件。
## 工单 18：完成后清理计划文档

**目标：** 仅在工单 1–17 全部完成并发布成功后，删除本实施计划文档，同时保留完整历史证据。
**文件：** 删除 `docs/superpowers/plans/2026-07-17-ai-cockpit-comprehensive-review.md`；新增本次清理 Work Item 的 Contract/Summary 并保留在 `.ai/work-items/archive/`；不得删除 `.ai/work-items/archive/**`、Release Evidence 或其他审计记录。
**前置条件：**
- [ ] 逐项核对工单 1–17 的 Work Item ID、Archive Contract、Archive Summary、合并 PR、关闭结果和验证记录。
- [ ] 核对工单 17 的版本 Tag、Published Release、Release Evidence、安装验证和远程默认分支 Source。
- [ ] 若任一核对项缺失，保持计划文档和当前清理工单 active，不执行删除。
**执行步骤：**
- [ ] 从最新远程默认分支创建清理 Work Item 分支，执行 `make ai-start TASK=ai-cockpit-review-plan-cleanup TITLE="Remove completed comprehensive review plan" MODE=code`。
- [ ] 执行清理前 checkpoint、Archive completeness 检查、`make check-ai-pr` 和 `git diff --check`。
- [ ] 删除计划文档，更新 Summary 说明删除原因是 1–17 已完成，并列出保留的历史证据。
- [ ] 执行全套 AI 检查和项目质量检查；确认计划路径确实被此 Work Item 单独拥有。
- [ ] 执行 `make ai-finish TASK=ai-cockpit-review-plan-cleanup`，创建并合并 PR，随后执行 `make ai-close-work-item TASK=ai-cockpit-review-plan-cleanup`。
- [ ] 最终确认仓库干净、远程默认分支同步、历史 Archive 未被删除；向用户报告全部循环完成、版本号和清理结果。
## 验收矩阵

| 评审缺口 | 覆盖工单 | 最终证据 |
| --- | --- | --- |
| Human Decision 不是完整决策请求 | 1、2、13 | Schema、Hash、Decision Evidence、Resume 测试 |
| Acceptance 不能证明行为 | 3 | Acceptance ID/Evidence Mapping 和执行记录 |
| Contract 时间关系不可信 | 4 | Git-tracked Start Receipt |
| Release Source 未绑定默认分支 | 5、9、17 | Source/Branch/Run/Tag/Artifact Correlation |
| Readiness 过早提升 | 6 | Stabilization 失败回归测试 |
| Lockfile Gate 未真正执行 | 7 | Clean Runner 实际命令输出 |
| Published 与 Candidate 混淆 | 8、17 | Quick Install Published Release 验证 |
| Upgrade 覆盖采用方配置 | 10、11、13 | 文件归属、冲突报告、人类确认测试 |
| Remote 默认分支未知仍继续 | 12 | Fail-closed 分支发现测试 |
| Review Policy 被模板写死 | 14 | 采用方 Adapter 和单人维护声明 |
| Adoption 被误当作 Production Ready | 15 | 分层 Readiness 检查 |
| Action/Archive/Complexity 余项 | 16 | SHA、顺序、增量指标回归测试 |
| 发布与计划收尾 | 17、18 | Published Release Evidence、计划删除和历史保留 |
## 最终完成标准

计划执行不得以“计划已写成”作为全部完成。只有以下条件全部满足，才可报告完成：

- 工单 1–16 均已独立完成、验证、PR 合并、Archive 和 Work Item Closure；
- 工单 17 已从允许的远程默认分支 Source 发布新版本，且安装验证成功；
- 工单 18 已在单独 Work Item 中清理本文件，保留全部历史治理与发布证据；
- 所有 Contract、Summary、Status、PR Ownership、Release Evidence 和项目检查均通过；
- 最终 base 分支与远程一致，worktree clean，且没有未记录的残余风险。
