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

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.10 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.10/install.sh)" -- --stack rust --update-makefile --create-adoption
```

## 2. 開発環境の品質ゲート設定 (`Makefile.ai.stack`)

リポジトリで以下の Make 変数を設定します。これらは `make ai-cockpit-quality` 実行時に呼び出され、フォーマット、テスト、および Clippy による静的解析の結果を AI エージェントの完了条件として検証します。

```make
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings
```

---

## 3. カバレッジポリシーの設定 (`.ai/guards/coverage_policy.yaml`)

Coverage Guard は Git の変更パスだけを解析するため、`src/lib.rs` 内の `#[cfg(test)]` インラインテスト追加を本番コード変更と区別できません。インラインテストだけで完結する変更では、この Guard を対応テストの証明として扱わないでください。独立した `tests/` ファイルへテストを追加する、対象パスを明示的に除外して Guard を advisory にする、または `cargo test` を独立した必須品質チェックとして使用してください。

パス単位の関連付けを使う場合は、次のように本番パスと統合テストパスを明示します。

```yaml
production:
  include:
    - "src/**"
  exclude:
    - "tests/**"

tests:
  include:
    - "tests/**"

associations:
  rustModules:
    production:
      - "src/**/*.rs"
      - "src/*.rs"
    tests:
      - "tests/{stem}_test.rs"
      - "tests/test_{stem}.rs"
```

---

## 4. 実践的な Rust 用 Contract 設計例 (`*.contract.json` 抜粋)

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

## 5. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

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
