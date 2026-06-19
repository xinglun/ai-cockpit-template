---
author: Ray
title: "Rust Adaptation Example"
description: Rust stack adaptation example for AI Cockpit.
keywords:
  - rust
  - ai-cockpit
  - ai-agents
  - governance
---

# Rust 開発における適用例 (Rust Stack Example)

Rust 開発で本フレームワークを利用する場合、以下の設定を推奨します。

## 1. 開発環境の品質ゲート設定 (`Makefile.ai.stack`)

リポジトリで以下の Make 変数を設定します。これらは `make quality` 実行時に呼び出され、フォーマット、テスト、および Clippy による静的解析の結果を AI エージェントの完了条件として検証します。

```make
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings
```

---

## 2. カバレッジポリシーの設定 (`.ai/guards/coverage_policy.yaml`)

Rust ではテストコードが `tests/` ディレクトリと `src/` 配下のインラインモジュール（`#[cfg(test)]`）の両方に存在することが多いため、以下のようにパターンを設定します。

```yaml
production:
  include:
    - "src/**"
  exclude:
    - "tests/**"
    - "src/**/*test*.rs"

tests:
  include:
    - "tests/**"
    - "src/**/*test*.rs"
```

---

## 3. 実践的な Rust 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Rust 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_cargo_feature",
  "mode": "code",
  "scope": [
    "Cargo.toml",
    "src/lib.rs",
    "src/features/auth.rs",
    "tests/auth_test.rs"
  ],
  "guidelines": [
    "clippy::pedantic を満たし、警告が発生しないこと",
    "unsafe コードの導入は禁止。すべて safe rust で記述すること"
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

上記のガイドラインに適合したことを証明する要約（Summary）の記述例です。

```json
{
  "guidelinesCompliance": [
    {
      "guideline": "clippy::pedantic を満たし、警告が発生しないこと",
      "compliant": true,
      "evidence": "cargo clippy --all-targets -- -D warnings が正常にパスすることを確認しました。"
    },
    {
      "guideline": "unsafe コードの導入は禁止。すべて safe rust で記述すること",
      "compliant": true,
      "evidence": "変更コード内に unsafe キーワードが存在しないことを目視および grep で確認しました。"
    }
  ]
}
```
