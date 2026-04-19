# Prompt Optimizer Workbench

LangMem の prompt optimizer を使って、評価データからプロンプトを継続改善する Streamlit アプリです。

## できること

- 左側に prompt version の履歴を表示
- 各 prompt version ごとに変化点と unified diff を確認
- 右側で会話を継続しながら出力を生成
- 最新 output に対して Good / Bad と description を保存
- 保存済み評価を LangMem optimizer に渡して新しい prompt version を作成

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_openai_api_key
streamlit run app.py
```

## デフォルト設定

- 生成モデル: `gpt-5.2-mini`
- 最適化モデル: `openai:gpt-5.2-mini`
- 最適化戦略: `gradient`

## 保存先

アプリの状態は `data/state.json` に保存されます。

## 補足

- 会話を続けた状態で評価を保存できます。
- Optimize 実行時は、その prompt version に紐づく評価履歴をすべて LangMem に渡します。
- 新しい prompt version を作ると、親 version との差分を保存します。
