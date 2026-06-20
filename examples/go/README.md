---
author: Ray
title: "Go Adaptation Example"
description: Go stack adaptation example for AI Cockpit.
keywords:
  - go
  - ai-cockpit
  - ai-agents
  - governance
---

# Go Adaptation Example

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.9 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.9/install.sh)" -- --stack go --update-makefile --create-adoption
```

## 2. 品質ゲートとガード設定

Go リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = test -z "$$(gofmt -l .)"
PROJECT_TEST = go test ./...
PROJECT_LINT = go vet ./...
```

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "cmd/**"        # main パッケージ（エントリーポイント）
    - "pkg/**"        # 公開ライブラリパッケージ
    - "internal/**"   # 内部パッケージ
  exclude:
    - "**/*_test.go"  # Go のインラインテストファイル（命名規約）

tests:
  include:
    - "**/*_test.go"
```

---

## 3. 実践的な Go 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Go 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_user_handler",
  "mode": "code",
  "scope": [
    "go.mod",
    "pkg/handler/user.go",
    "pkg/handler/user_test.go"
  ],
  "guidelines": [
    "外部パッケージを導入する場合は go.mod に追加し go mod tidy を実行すること",
    "公開される構造体やメソッドには Go Doc 形式のコメントを記述すること"
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

## 4. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

上記ガイドラインに適合したことを証明する要約（Summary）の記述例です。

```json
{
  "guidelinesCompliance": [
    {
      "guideline": "外部パッケージを導入する場合は go.mod に追加し go mod tidy を実行すること",
      "compliant": true,
      "evidence": "追加ライブラリがないため go.mod は変更していません。"
    },
    {
      "guideline": "公開される構造体やメソッドには Go Doc 形式のコメントを記述すること",
      "compliant": true,
      "evidence": "pkg/handler/user.go 内のすべてのエクスポートオブジェクトに Go Doc を追加しました。"
    }
  ]
}
```
