# investingOS フォルダ地図 — 2026-09-20（照合済み）

## 結論
**正本 = `~/Desktop/investing_os`（このフォルダ）**。
`~/Documents/Codex/2026-09-13/investingos-google-csv-csv-ai-artifact` は **v4.3時点のスナップショット**（実質バックアップ）。
CSV台帳は両者で完全一致しており、**二重管理は発生していない**。

## 照合結果（2026-09-20 実施、diff -rq）

### データ：完全一致
- `data/current.json` → 両方とも version `04b75059d20045b5a7495b55b82b5b8e`
- `data/revisions/` 配下のCSV 12種：差分なし（.DS_Store を除く）

### アプリ・ナレッジ：Desktop側が新しい（= v4.4）
Desktop にのみ存在:
- `app/catalog.py` `app/falsify.py` `app/fundscreen.py` `app/quotes.py`
- `knowledge/26-fundamental-screening.md` `27-falsification.md` `28-quotes.md`
- `audit/QA-V4.4.md` `audit/pre-v4.4-20260920/` `examples/` `tests/test_upgrades.py`

内容が異なる（Desktop が 2026-09-20 更新）:
`app/app.js` `app/insights.js` `app/insights.py` `app/server.py` `app/store.py`
`app/index.html` `app/style.css` `README.md` `PROJECT-INSTRUCTIONS.md` `AGENTS.md`

Codex側にのみ存在（＝Desktopでは _archive へ退避済み。原本はCodex側に健在）:
`reference/` `PROJECT-INSTRUCTIONS-v4.2.md` `outputs/investingOS_ChatGPT-update/` `work/pycache/`

## 未解消のリスク（要対応）
**古いポインタが2つ、Codex側（v4.3）を指したまま**:
1. `_archive/.../investingOS_ChatGPT-update/APP-LOCATION.md`
   → 「アプリとデータの保存先」として Codex 側パスを明記
2. `_archive/.../investingOS_ChatGPT-update/起動.command`
   → Codex 側の絶対パスを直書き

この2つを信じて起動すると **v4.3の古いアプリが立ち上がる**。ChatGPT側の入口フォルダ
`~/Desktop/investingOS_ChatGPT/` にも同じ内容が配置済み（2026-09-13 VERIFIED）のため、
そちらの修正も必要。

## 取り扱い方針
- Codexフォルダ：**削除しない**。v4.3バックアップとして凍結。必要な素材はコピーで取り出す。
- Desktop/investing_os：運用正本。更新はここだけ。
- `_archive/2026-09-20/`：退避物。原本はCodex側にあるため復元可能。

## 現行の台帳
`outputs/investingOS-v4.2/data/current.json` → `04b75059d20045b5a7495b55b82b5b8e`
→ CSV 12種（holdings, theses, research, exposures, plans, plan_items,
checks, decisions, analyses, news, sources, targets）

## 名前と実体のずれ（未対応）
フォルダ名 `investingOS-v4.2` に対し中身は **v4.4**。リネームは上記ポインタ修正と
同時に行う（`起動.command` は相対パス `${0:A:h}` なので本体は影響を受けない）。
