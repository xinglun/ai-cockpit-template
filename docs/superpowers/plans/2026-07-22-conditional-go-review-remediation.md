---
author: Ray
title: "Conditional GO Review Remediation Execution Plan"
description: "基于 2026-07-22 全面审查结论的能力真实性、Adopter Runtime 和生命周期整改计划。"
keywords:
  - conditional-go
  - capability-truth
  - adopter-runtime
  - review-remediation
  - work-item-lifecycle
---
# Conditional GO 全面评审整改执行计划

**Status:** historical; WI1–WI10 completed and WI11 is the final documentation-cleanup Work Item owned by `conditional_go_plan_cleanup`.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
**Goal:** 把本次 `Conditional GO` 评审转化为一组有依赖、可验证、严格串行的 Work Item，并在每个 Work Item 完成 PR 合并、归档、分支清理和主分支同步后循环进入下一个，直到最后的“清理执行计划文档”工单完成。
**Architecture:** AI Cockpit 继续保持 Repository Governance Layer 边界，不扩展为 Agent Runtime、Workflow Engine 或 Security Sandbox。先建立 Capability Truth Matrix，明确 implemented / template-only / adopter-installed / planned，再按安装 Runtime、Quick Install、Calibration、Inventory、Bootstrap/Update Lifecycle、CI Evidence、Complexity 和 Installer 结构逐项实现；文档和发布只接受已经由命令、测试、PR 和 Release Evidence 支撑的声明。
**Tech Stack:** Python 3.10+、pytest、Make、JSON/YAML、Markdown、GitHub PR、AI Cockpit Work Item Contract v2。

## Global Constraints

- 评审基准：用户提供的《全面审查结论》，结论为 `Conditional GO`；该材料指出 `main`、Release `v0.5.38` 和当前已知的模板/Adopter 能力错位。
- 一个工单对应一个 Contract v2、一个专用工作分支、一个 PR 和一组可追溯的 Summary/Archive Evidence；不得将独立工单合并到同一 PR。
- 每个工单都必须从执行时最新远端默认分支创建，并记录 `baseRemote`、`baseBranch`、`baseCommit`；不得从旧计划分支或移动中的模板分支开始。
- 每个工单必须完成：Contract → Preflight → 实现/文档 → 验证 → Summary → `ai-finish`/archive → push → PR → PR merge → `ai-close-work-item` → 本地/远端分支清理 → 默认分支同步。
- 前一个工单没有得到 `ready for next Work Item` 以前，不得创建、实现或并行启动下一个工单；失败留在当前工单修复，或创建新的单一修复工单并重新走完整流程。
- `needs_human_confirmation`、`not_ready`、Unknown、Stale、Invalid、缺失 Evidence、未验证 Scenario 和不一致的 Capability Claim 必须 fail closed；不得用聊天授权替代执行证据。
- 用户已明确授权：修改代码、测试、Schema、治理配置、CI、示例和文档；创建/推送/评审/合并每个 PR；执行 `ai-finish`、归档、`ai-close-work-item`；清理本地和远端 Work Item 分支；必要时发布新版本；最后清理执行计划文档。该授权已经得到，不需在每个工单前重复确认。
- 授权只代表操作许可，不代表 PR、测试、Release、合并、分支删除或主分支同步已经发生；这些必须以实际命令输出、Provider 记录、SHA、Digest 和 Archive Evidence 为准。
- 不删除 Contract、Summary、Cockpit Status、评审材料、发布证据、测试、快照或仍被引用的设计文档；最后一个工单只在完成链接扫描和引用审查后清理计划文件。
## Audit closure map

Every completed item has its own PR, merge SHA, archived Contract/Summary/manifest, successful `ai-close-work-item`, and synchronized default branch. Evidence: WI1 [#242](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/242) `8c874e7f44fd25ae179bcc698b7708df2ebfba13` (`conditional_go_review_execution_plan`); WI2 [#244](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/244) `632461de90cc465f34c0258208706b8970b6279d` (`conditional_go_capability_truth_matrix`); WI3 [#246](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/246) `202893b0274319a5eaeb87eaa8265a4030f2ba79` (`conditional_go_installed_runtime_parity`); WI4 [#247](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/247) `2f9502a34c8b35cd502d6f3bd7c1c70fb152a49b` (`conditional_go_verified_quick_install`); WI5 [#248](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/248) `97161ce318699a394ec9b36e4ff2c87b728f676d` (`conditional_go_calibration_scaffold_core`); WI6 [#249](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/249) `6343df4f5522f696673c75430b641eb7958db47c` (`conditional_go_calibration_inventory_status_matrix`); WI7 [#251](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/251) `a1d1b8158ab2671e34723bf2941eff3f378e665f` (`conditional_go_bootstrap_lifecycle_schema`); WI8 [#252](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/252) `188ac82937ba45889c5d470970a8b0c618e8b367` (`conditional_go_ownership_installed_lifecycle`); WI9 [#253](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/253) `7100ee8820fb9f04b439dbd94905d1f621fab477` (`conditional_go_ci_release_evidence`); WI10 [#254](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/254) `a865305c31563742d327b448ecabe3e4c557a62c` (`conditional_go_complexity_installer`). WI11 is this cleanup Work Item; its PR, merge SHA, and closure manifest are recorded by lifecycle evidence.
## 1. 评审收查与总结

### 1.1 当前结论

| 判断对象 | 结论 |
| --- | --- |
| 模板仓库治理框架 | GO；Work Item 生命周期、Evidence、Scope/Backtrack/Coverage/Scenario Guard、事务回滚和回归意识已经成立 |
| 内部试点工具 | Conditional GO；可继续开发，但必须先补齐安装到 Adopter 后的事实链 |
| 对外宣称“完整安装、校准、更新、回滚、卸载生命周期” | NO-GO；README/设计叙述领先于实际 Installed Runtime |
| 企业级身份、权限、隔离、不可篡改审计与合规证明 | 仍不在 AI Cockpit 证据范围内，不能因本计划完成而改为 GO |

### 1.2 已确认的优势

- 产品边界已收敛为 Repository Governance Layer，明确不是 Agent Runtime、Workflow Engine 或 Security Sandbox。
- Work Item 已覆盖 Remote Base、Dedicated Branch、Contract、Preflight、Implementation、Verification、Summary、Archive、PR、Merge、Close、Base Sync 和 Branch Cleanup。
- Contract/Summary/Status、Serial Order、Budget Impact、Scope、Guard、Agent Risk、Review Policy、Backtrack、Coverage、Scenario 和 Guidelines 已形成较完整的证据层。
- Installer 已具备 Conflict Detection、Dirty Worktree Warning、Adoption Branch、事务性回滚和模板/Adopter 证据边界意识。
- Adoption Readiness 已检查 Project Profile、Quality Command、Coverage Review、Guard/CI、CODEOWNERS、SECURITY 等真实配置，而不是只检查文件存在。
- 测试、质量、SBOM、Provenance、Secret Scan、Trust Guard 和 Critical Domain 回归意识较强。

### 1.3 必须修正的真实性问题

| 优先级 | 评审发现 | 事实边界 |
| --- | --- | --- |
| P0 | README 宣称十阶段 Calibration、Candidate/Active 原子激活和 Impact Assessment，但 `ai_calibrate.py` 目前主要生成/校验 Project Profile | 目标能力必须先标为 planned，或由后续工单实现并测试 |
| P0 | Adopter 安装的 `templates/make/Makefile.ai` 与 `SCRIPT_NAMES` 没有完整 Update/Lifecycle 命令和脚本 | 模板仓库自身能力不等于 Installed Runtime 能力 |
| P0 | Quick Install 读取 Tag 但不默认读取和验证 Release Archive Digest | `sha256ArchiveVerificationSupported` 不能写成默认已验证 |
| P1 | Bootstrap 不是交互式 Wizard，且 Adoption Record 与标准 Work Item 的 Schema 边界不清 | 需要显式 Bootstrap lifecycleType/creationMode 和人工确认状态 |
| P1 | 缺少逐文件 Ownership/Managed Region Manifest | Update、Uninstall、Project-modified 文件无法长期可靠判定 |
| P1 | Update Proposal/Apply 尚未统一接入标准 Work Item、Summary、PR、Rollback Evidence | Update 必须成为受治理的 Work Item，而不是裸命令 |
| P1 | Calibration Inventory 分散在多个检查器 | 必须统一 complete / warning / incomplete / unknown / not_applicable 状态 |
| P1 | 本次审查无法独立证明 PR #241 的 CI Green 状态 | Release/PR Evidence 必须记录 Workflow Run、Head SHA、Job、Conclusion、Artifact Digest |
| P2 | Complexity Budget 通过重复 repayment 记录持续抬高 | 在新增预算前必须有可量化的实际偿还 |
| P2 | `install_ai_cockpit.py` 过于集中 | 应拆分 repository/detection/transaction/ownership/bootstrap/upgrade/managed_regions/evidence |
| P2 | Calibration Proposal 固定 `repositoryRole: template` | Adopter Proposal 默认应为 `adopted` 或 `proposed` |
| P2 | README 过长且未来设计混入当前能力 | README 只保留当前边界、Quick Start、状态和导航，细节下沉到专题文档 |

## 2. 每个工单的完整强制流程

以下 13 步是每一个工单的完成定义，不能只在计划工单执行。任何一步失败，当前工单保持未完成；下一工单不得开始。

1. **更新基线：**发现远端、默认分支和最新提交，记录 `baseRemote`、`baseBranch`、`baseCommit`；确认工作树没有无关修改。
2. **建立边界：**创建专用 `codex/<task>` 分支，运行 `make ai-start TASK=<task> TITLE="..." MODE=code`，补齐 Contract v2 和成对 Summary。
3. **完成 Preflight：**读取 `.ai/cockpit/README.md`、`.ai/README.md`、`.ai/glossary.md` 和相关设计；填写 Intent、Raw Request、Requested Operation、Scope、Out of Scope、Sources、Unknowns、Acceptance、Scenario Coverage、Verification、Risk 和 Agent Capability。
4. **处理人工确认：**若 Preflight 为 `needs_human_confirmation` 或 `not_ready`，暂停实现并向用户报告；用户决定后重新计算 Contract/Preflight Hash，不能复用旧证据。此计划已取得用户对整个串行执行范围的授权，但具体阻塞决策仍以实际 Contract Evidence 为准。
5. **先测后改：**在当前 Contract scope 内先写失败测试，再做最小实现；文档工单必须先建立可扫描的事实矩阵/链接/命令验证，再写声明。
6. **执行验证：**运行针对性测试、项目质量命令、所有 Contract `verification` 和本计划要求的生命周期检查。不可执行的外部检查必须记录 `not_run`/`ci_only`/`unavailable` 及原因。
7. **记录 Summary：**填充 `changedFiles`、Acceptance→Evidence 映射、Scenario Coverage、Guidelines Compliance、Intent Alignment、Boundary Checks、Known Gaps、Residual Risks 和 Overclaim Prevention。
8. **完成 Finish Gate：**运行 `make ai-checkpoint ... STAGE=before_finish` 以及全部必需 `check-ai-*`；失败则修复当前工单，不得把失败写成通过。
9. **归档但不关闭：**运行 `make ai-finish TASK=<task>`，确认 Contract、Summary、Cockpit Status 和执行证据已进入 Archive；在 PR 合并前不得删除工作分支。
10. **创建并合并 PR：**推送专用分支，创建唯一对应 PR，完成评审和 CI；PR 必须引用 Work Item、Contract、Summary 和验证结果，不得用本地直接合并替代 PR。
11. **执行生命周期关闭：**PR 合并后运行 `make ai-close-work-item TASK=<task>`，确认 Archive Evidence、PR/分支一对一归属、快进同步、工作树清洁和远端分支删除。
12. **同步基线：**验证本地默认分支与远端默认分支一致，记录合并 SHA、删除结果和 `ready for next Work Item` 输出。
13. **循环：**只有第 12 步全部成功，才从最新默认分支创建下一个工单；直到最终“清理执行计划文档”工单完成。

```text
Work Item N
  → Contract/Preflight
  → Implement/Verify/Summary
  → ai-finish/archive
  → push/PR/review/merge
  → ai-close-work-item
  → local + remote branch cleanup
  → base synchronization
  → ready for next Work Item
  → Work Item N+1
```

## 3. 有序 Work Item 列表

工单必须按下列顺序串行执行。每项都要产生独立 PR 和独立关闭证据；后项不得提前实现前项的范围。

### 工单 1：完成本执行计划文档（当前工单，P0）

**目标：**收查用户提供的评审，形成当前能力矩阵、Conditional GO 总结、P0/P1/P2 整改清单、依赖顺序、授权记录和完整生命周期流程。

**范围：**本计划文档、计划索引、当前 Work Item Contract/Summary/Status/Start Receipt。当前工单不实现后续 Runtime 功能。

**验收：**文档准确区分 implemented、template-only、adopter-installed、planned；覆盖评审每个发现；列表最后是“清理执行计划文档”；明确每个工单必须经过 PR、merge、`ai-close-work-item`、分支清理和 base sync；索引将本计划标为当前计划，旧计划保留为历史。

**验证：**`make ai-preflight`、`make check-ai-contract`、`make check-ai-scope`、`make check-ai-change-summary`、`make check-ai-status-consistency`、文档链接/元数据检查、P0/P1/P2 标题扫描和人工审阅。

### 工单 2：Capability Truth Matrix 与文档真实性对齐（P0）

**目标：**建立唯一 Capability Matrix，修正 README、Installation、Upgrade、Calibration、Lifecycle、CLI Reference 和多语言文档中把未来设计写成当前能力的内容。

**验收：**每项能力标注 `implemented`、`template_only`、`adopter_installed` 或 `planned`，并链接 command、source、test、release evidence；`repositoryRole` 默认事实不再误导为 template；未实现的十阶段 Calibration、Candidate Activation、Wizard、Ownership Manifest、Disable/Uninstall 明确为 planned；文档扫描阻止未经证据的当前能力声明。

### 工单 3：Installed Runtime Parity（P0）

**目标：**让 Adopter 实际安装后获得模板根 Makefile 已声明的 Update/Lifecycle Runtime Surface。

**范围：**`templates/make/Makefile.ai`、Installer `SCRIPT_NAMES`/copy map、`ai_install_status.py`、`ai_upgrade_proposal.py`、`ai_upgrade_apply.py`、`ai_lifecycle_facts.py`、Rollback/Disable/Uninstall 入口、`.ai/cockpit/checks.yaml`、CLI 文档和安装/升级测试。

**验收：**真实 Adopter Fixture 能运行 Update Status、Proposal、Apply、Lifecycle Facts、Rollback、Disable/Enable 和 Uninstall/Preserve Evidence；模板清单、Makefile、Checks、文档和测试来自同一事实源；未安装或不可用命令不会被 Readiness 宣称为 complete。

### 工单 4：Verified Quick Install 与 Release Archive Digest（P0）

**目标：**让 Quick Install 默认绑定 Tag、Source Commit、Installer Digest 和 Source Archive SHA256。

**验收：**`release.json` 提供 `releaseArchive.sha256`、`sourceCommit`、`assetName`；Quick Install 读取并强制验证 Release Tag 指向的 Commit、Installer Digest、Source Archive Digest 和 Release Asset；缺 digest、tag mismatch、archive mismatch 均 fail closed；Capability Flag 改为准确的 supported/verified 语义；匿名/干净环境测试提供原始输出和 Digest。

### 工单 5：Calibration Scaffold Core（P0/P1）

**目标：**实现首次校准的可暂停、可恢复、可回顾 Session，而不是只生成 Project Profile Proposal。

**验收：**支持十个 Stage 的 Session/Checklist、日语默认、Y/N、Alternative/Input、Unknown、Not Applicable（必须有理由）、Back、Review、Pause、Resume、Dependency Stale；Stage Self-check、Full Self-check、Governance Simulation 和两阶段人工确认全部有状态与证据；Candidate 成功激活前旧 Active 保持有效；Adopter Fixture 可执行完整 Session。

### 工单 6：Calibration Inventory 与 Status Matrix（P1）

**目标：**将 Profile、Guard、Quality、Coverage、Complexity、Review、Security、CI、Installed Lifecycle、Documentation 的结果统一到 Calibration Inventory。

**验收：**每一项区分 `complete`、`warning`、`incomplete`、`unknown`、`not_applicable`，并记录 source、confirmation、evidence、staleAt、owner 和 blocking reason；Adoption Readiness、Cockpit Status、文档和 CI 消费同一矩阵；默认值、人工确认值、静态通过和真实命令通过不能混淆。

### 工单 7：Bootstrap Wizard 与生命周期 Schema（P1）

**目标：**把安装、Bootstrap Adoption、Calibration 和 Governed Development 区分为明确生命周期。

**验收：**Bootstrap 流程支持 Detect → Propose → Y/N → Select/Input → Review → Drift Revalidation → Confirm → Write，并支持 Back/Cancel/Resume；生成的记录使用 `lifecycleType: bootstrap_adoption`、`creationMode: bootstrap_installer`，不冒充标准开发 Work Item；Bootstrap 不得宣称 Ready；只有 Calibration Confirmation 和 Adoption Readiness 通过后才进入 Governed Development。

### 工单 8：Ownership Manifest 与完整 Installed Lifecycle（P1）

**目标：**建立逐文件/区域的 Template-owned、Project-owned、Shared、Generated、Historical 事实，支撑 Update、Rollback、Disable、Enable、Uninstall。

**验收：**Adopter 生成 `.ai/install/manifest.json`、`managed-regions.json`、`rollback-baseline.json`，记录 installed/current digest 和 project modification；Update Proposal/Apply 先进入标准 Work Item，包含 Snapshot、Migration、Recalibration Impact、Summary、PR 和 Rollback Evidence；Uninstall 保留 Evidence、支持 Detached Uninstaller、Purge Export 和 Final Receipt；冲突、漂移、半激活和回滚失败均 fail closed。

### 工单 9：CI/Release Evidence 独立可验证（P1）

**目标：**解决“PR 描述写 passed 但审查无法独立证明 CI Green”的证据缺口。

**验收：**Release/PR Evidence 至少记录 Workflow Run ID、Head SHA、Required Job Names、Conclusion、Artifact Digests、SBOM、Provenance 和失败原因；`release.json`/canonical state 不接受只写在 PR Body 的通过声明；缺 Run 或 SHA 绑定时不能宣称 published/verified；CI 在 PR Head 与 Merge Commit 的关系可解释，相关命令和测试有回归证据。

### 工单 10：Complexity Repayment 与 Installer 分解（P2）

**目标：**停止通过不断抬高上限解决复杂度问题，并把 Installer 从单体拆成可验证边界。

**验收：**先交付一个可量化 repayment（合并重复 Protocol Fields、压缩 Archive Index、合并重复文档或拆分模块之一），并设置“没有实际偿还不得新增预算”的门；将 `install_ai_cockpit.py` 拆为 repository、detection、transaction、ownership、bootstrap、upgrade、managed_regions、evidence 模块，保留薄入口；复杂度报告、repayment record、测试和文档一致。

### 工单 11：清理执行计划文档（最后工单，P2）

**目标：**在工单 1–10 全部完成并关闭、最终 Release Evidence 归档后，清理重复、过时或误导性的执行计划，同时保留审计历史。

**验收：**逐份计划标记“当前执行 / 已完成需审计 / 已被替代 / 可安全删除”；完成链接、重复内容、状态和引用扫描；删除仅限没有审计价值且没有引用的计划副本，删除理由写入当前 Summary；保留所有 Contract、Summary、Cockpit Status、评审材料、发布证据和仍被引用的设计；本计划最后标记为历史保留并链接每个工单的 PR、合并 SHA、Archive 和关闭证据；关闭后不再创建新的整改工单。

## 4. 计划级完成定义

本计划只有在工单 1–11 严格按顺序完成后才算完成。每个工单必须至少具有：

- Contract v2、Raw Request/Intent/Scope/Sources/Acceptance/Scenario/Verification；
- 通过的 Preflight、目标测试、项目检查和 AI Cockpit 检查；
- Summary、Intent Alignment、Acceptance→Evidence 映射、Residual Risk 和 Archive Evidence；
- 唯一对应 PR、实际评审/合并记录、合并 SHA；
- `make ai-close-work-item TASK=<task>` 成功输出；
- 本地/远端分支删除、工作树清洁、默认分支与远端一致、`ready for next Work Item` 证据。

最终工单完成前，重新运行并记录至少：

```text
make check-ai-contract
make check-ai-scope
make check-ai-guards
make ai-checkpoint ... STAGE=before_finish
make check-ai-agent-risk
make check-ai-review-policy
make check-ai-backtrack
make check-ai-coverage-guard
make check-ai-guidelines
make check-ai-change-summary
make generate-cockpit-status
make check-ai-status
make check-ai-status-consistency
make check-ai-pr AI_BASE_COMMIT=<merge-base>
```

计划完成不会改变企业级安全/合规 NO-GO，也不会产生“能理解所有未知危险意图”的承诺。若未来要改变这些边界，必须另有外部身份、权限、隔离、秘密管理、不可篡改审计和合规证据。
