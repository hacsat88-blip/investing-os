# テスト

```
python3 dev/tests/test_upgrades.py     # v4.4機能（fnd/・反証エンジン・相場台帳・台帳保存）32件
python3 dev/tests/test_screening.py    # scr/ スクリーニング 16件
```

## 設計方針（2026-09-21改修）
- **実データを読まない。** `fixtures/data/` の固定データ（10保有・quotes空・schemaVersion 4.3）を
  一時フォルダへ複製して実行する。運用台帳が変わってもテスト結果は変わらない
- **配置に依存しない。** `app/store.py` を持つ親を探して ROOT を決めるので、
  `tests/` を移動しても動く
- **台帳を書き換えない。** 保存系テストはすべて一時フォルダ内で完結する

## fixtures/data
2026-09-13保存の版 `04b75059…` の写し。`quotes` を持たない schemaVersion 4.3 なので、
「古い版を読むと quotes が空配列になる」互換動作の検証にそのまま使える。
**更新しないでください。** 期待値がこのデータに紐づいています。

## 改修前の問題（記録）
実データの `data/` を複製していたため、運用で保有やquotesが変わると5件が失敗していた。
また `ROOT = parents[1]` 固定だったため、`tests/` を `dev/tests/` へ移すと import が壊れた。
