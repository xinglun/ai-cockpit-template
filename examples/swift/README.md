---
author: Ray
title: "Swift Adaptation Example"
description: Swift stack adaptation example for AI Cockpit.
keywords:
  - swift
  - ai-cockpit
  - ai-agents
  - governance
---

# Swift Adaptation Example

> **注意:** `examples/` は参照用です。インストール時にターゲットリポジトリへコピーされません。採用側は本 README を手動で参照し、`configure_ai_cockpit` Work Item 内でプロジェクトに合わせて書き換えてください。

この例は **Swift Package Manager (SPM)** 向けです。テンプレートの `STACK=swift` preset も SPM を前提とし、ホステッド検証（`mobile-stack-quality`）は最小 SPM fixture のみを対象とします。

Xcode プロジェクト、workspace、CocoaPods など非 SPM レイアウトでは、インストール後に `configure_ai_cockpit` Work Item で Project Calibration が必須です。preset を起点として `Makefile.ai.stack` の品質コマンド、`project_profile.yaml` の境界、Coverage Guard、CI をプロジェクトに合わせて置き換えてください。`STACK=generic` は preset が誤解を招く場合の推奨選択肢です。

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.16 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.16/install.sh)" -- --stack swift --update-makefile --create-adoption
```

## 2. 品質ゲートとガード設定

Swift Package Manager リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

非 SPM レイアウト（Xcode / workspace / CocoaPods）では、上記をそのまま使わず、Project Calibration で `xcodebuild` 等のプロジェクト固有コマンドに置き換えてください。doctor は事実を報告するのみで、`xcodebuild` 引数は自動生成しません。

```make
PROJECT_FORMAT_CHECK = swift format lint --recursive .
PROJECT_TEST = swift test
PROJECT_LINT = swift build -Xswiftc -warnings-as-errors
```

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "Sources/**"
  exclude:
    - "Tests/**"

tests:
  include:
    - "Tests/**"
```

---

## 3. Xcode / workspace 適応（手動キャリブレーション例）

CocoaPods + Xcode workspace など非 SPM レイアウト向けの中立例です。プロジェクト名は `MyApp` プレースホルダとします。AI Cockpit は `pod install` や `xcodebuild` を自動実行しません。

### 3.1 事前準備

```sh
# 依存解決はプロジェクト側で実施（例）
pod install
```

### 3.2 Makefile.ai.stack（品質コマンド例）

workspace がある場合は `-workspace` を使います。scheme・configuration・destination はリポジトリに合わせて置き換えてください。

```make
PROJECT_FORMAT_CHECK = swift format lint --recursive MyApp
PROJECT_LINT = xcodebuild build \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  CODE_SIGNING_ALLOWED=NO
PROJECT_TEST = xcodebuild test \
  -workspace MyApp.xcworkspace \
  -scheme MyApp \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  CODE_SIGNING_ALLOWED=NO
```

`.xcodeproj` のみ（workspace なし）の場合は `-workspace` を `-project MyApp.xcodeproj` に読み替えます。

### 3.3 Coverage Guard（Xcode / CocoaPods 向け例）

テンプレート本体の `coverage_policy.yaml` デフォルトは広いまま維持されます。採用側は `configure_ai_cockpit` で次のような **例** を起点に絞り込み、最初は `reportOnly: true` から始めることを推奨します。

```yaml
reportOnly: true

production:
  include:
    - "MyApp/**"
  exclude:
    - "MyAppTests/**"
    - "Pods/**"
    - "DerivedData/**"
    - "**/*.generated.swift"

tests:
  include:
    - "MyAppTests/**"
    - "MyApp/**/*Tests.swift"
  exclude:
    - "Pods/**"
```

境界が安定したら `reportOnly: false` と `adoptionReviewed: true` を段階的に設定してください。

---

## 4. 実践的な Swift 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Swift 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_network_client",
  "mode": "code",
  "scope": [
    "Package.swift",
    "Sources/NetworkClient.swift",
    "Tests/NetworkClientTests.swift"
  ],
  "guidelines": [
    "非同期処理は可能な限り async/await を使用し、コールバック形式を避けること"
  ],
  "verification": [
    { "check": "aiWorkItem", "required": true },
    { "check": "aiScope", "required": true },
    { "check": "aiGuidelines", "required": true },
    { "check": "quality", "required": true }
  ]
}
```

---

## 5. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

上記ガイドラインに適合したことを証明する要約（Summary）の記述例です。

```json
{
  "guidelinesCompliance": [
    {
      "guideline": "非同期処理は可能な限り async/await を使用し、コールバック形式を避けること",
      "compliant": true,
      "evidence": "NetworkClient.swift の fetch メソッドを async throws 関数として実装しました。"
    }
  ]
}
```
