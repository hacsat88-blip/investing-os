# 70 AI運用と健康状態 v4.4

AI運用先は中立（Claude・ChatGPTいずれも可、併用も可）。正本は単一のCSV台帳。AIとの会話は調査・提案・確認の窓口であり、旧AI側DB（Claude Artifact等）やGoogle Sheetsへの同期を要求しない。
クラウドのAIサービス（ChatGPT Project、Claude Project等）にファイルを置くだけでは、Mac上のCSVへ直接アクセスできると仮定しない。アクセスできない環境では「AI用データ出力」→AIへ提示→version/tables/reasonを含む提案JSON→アプリ取込→差分承認保存を使う。ローカル接続が許可された環境のみapp/store.py read/proposalを利用する。サービスの内部DBや未提供ツールに依存しない。
根拠：OpenAI公式「プロジェクトとチャット」 https://learn.chatgpt.com/ja-JP/docs/projects （2026-09-13確認）。本指示を作成したことと、AIサービス側のProjectへ登録したことは別。

## 健康状態の判断
checks.csvのsubjectはHOLDINGS/NOTIFICATION/EXTERNAL_BACKUP、checkStatusはUNKNOWN/CONFIRMED/FAILED。確認日時と根拠を記録。記入された確認済みは自己申告の記録であり、アプリが口座や通知先へ接続した証拠ではない。
価格・評価日付は行ごとに表示。7暦日超は要更新の目安（市場カレンダー未適用）。保存日時を価格基準日や保有確認日にすり替えない。
Macバックアップは現在版ZIPを開き、CSVのSHA-256を現在版と照合する。設定済みだけで検証済みにしない。別媒体バックアップは別の確認欄にする。

## 監視状態ファイル
monitoring/state.jsonは次の契約とする。lastAttemptAt、lastSuccessAtはタイムゾーン付きISO日時。lastStatusはSUCCESS/PARTIAL/FAILED/SKIPPED。reportPathはmonitoring/からの相対パスで、実在する当該回のレポートを指定。detailに取得範囲・欠測を短く記載。未実行ならファイルを成功状態で初期化しない。
lastAttemptAtは各回を記録。lastSuccessAtは必要範囲を確認できた回のみ更新し、PARTIAL/FAILEDで直近成功を上書きしない。銘柄別/経路別カーソルは別キーcursorsに保持し、取得失敗で進めない。
実行レポートがない状態や形式不正は未検証。定期登録済みと実行成功とスマホ到達は別。アプリを開いている間は健康表示を更新する。接続断時は読込エラーを表示し、古い表示を現在の成功結果としない。
自動監視の処理はAI側（ChatGPTのタスク、Claudeの定期実行、Codex等）の定期タスクに依存する。アプリ自体にはAIや市場データAPIを内蔵していない。
