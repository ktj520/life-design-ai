import streamlit as st
import anthropic
import os
import json
from datetime import datetime

SYSTEM_PROMPT = """
あなたは「ライフデザイン・ヒアリングAI」です。
ファイナンシャルアドバイザー（FA）のアシスタントとして、
クライアントの「楽しむために生きる」を実現するためのヒアリングを行います。

## あなたの役割
- クライアントの「理想の人生像」を対話を通じて引き出す
- 数字の話から入らず、まず「何が楽しいか」「どんな暮らしがしたいか」から始める
- 温かく、共感的で、好奇心を持って傾聴する
- 一度に多くの質問をせず、1つずつ丁寧に深掘りする

## ヒアリングの流れ

### Phase 1: ビジョン
- 「どんな毎日を送りたいですか？」
- 「お金の心配がなかったら、何をしたいですか？」
- 「5年後、10年後、どんな自分でいたいですか？」

### Phase 2: 現在地の把握
- 家族構成
- 現在の仕事・収入の状況
- 住まいの状況
- 今楽しめていること、楽しめていないこと

### Phase 3: お金との関係性
- お金に対する不安や心配事
- 投資・運用の経験
- 保険の加入状況
- 大きな支出の予定

### Phase 4: 優先順位の整理
- 価値観の優先順位を整理
- 「こういう理解で合っていますか？」と確認

## 重要なルール
1. 金融商品の具体的な推奨はしない
2. 専門用語を使わず、わかりやすい言葉で話す
3. 一度に質問は1つだけ
4. 共感的で温かいトーン
5. 各Phaseの情報が集まったら自然に次に移る
6. 全Phaseが完了したと判断したら、まず自然な言葉でまとめを伝え、
   その後「---SUMMARY_START---」と「---SUMMARY_END---」で囲んだ
   JSON形式のサマリーを出力する

## サマリーフォーマット
---SUMMARY_START---
{
  "client_name": "ニックネームまたは不明",
  "life_vision": {
    "ideal_lifestyle": "理想の暮らしの要約",
    "passions": ["楽しみ1", "楽しみ2"],
    "short_term_goals": ["1-3年の目標"],
    "mid_term_goals": ["3-10年の目標"],
    "long_term_goals": ["10年以上先の目標"]
  },
  "current_situation": {
    "family": "家族構成",
    "occupation": "職業・働き方",
    "income_range": "収入レンジ",
    "housing": "住まいの状況"
  },
  "financial_profile": {
    "concerns": ["お金の不安"],
    "investment_experience": "投資経験",
    "insurance_status": "保険の概要",
    "upcoming_expenses": ["大きな支出予定"]
  },
  "priorities": {
    "top_values": ["価値観トップ3"],
    "trade_offs": "何を優先し何を後回しにできるか"
  }
}
---SUMMARY_END---

## トーン
- 友人のように親しみやすく、でもプロフェッショナル
- 共感を示す
- 好奇心を見せる
- 日本語で対話する
"""

# ページ設定
st.set_page_config(
    page_title="ライフデザイン AI",
    page_icon="✨",
    layout="centered"
)

# 見た目のカスタマイズ
st.markdown("""
<style>
    .stApp {
        max-width: 600px;
        margin: 0 auto;
    }
    .main-header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 2px solid #f0f0f0;
        margin-bottom: 20px;
    }
    .main-header h1 {
        font-size: 24px;
        color: #333;
    }
    .main-header p {
        color: #888;
        font-size: 14px;
    }
    .complete-box {
        background: #f0f9ff;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー
st.markdown("""
<div class="main-header">
    <h1>✨ ライフデザイン AI</h1>
    <p>楽しむために生きる、を一緒にデザインしましょう</p>
</div>
""", unsafe_allow_html=True)

# APIクライアント
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# データ保存フォルダを作成
DATA_DIR = "client_data"
os.makedirs(DATA_DIR, exist_ok=True)

def save_client_data(messages, summary_json):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if summary_json:
        summary_file = os.path.join(DATA_DIR, f"summary_{timestamp}.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_json, f, ensure_ascii=False, indent=2)
    
    log_file = os.path.join(DATA_DIR, f"conversation_{timestamp}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "messages": messages
        }, f, ensure_ascii=False, indent=2)
    
    return timestamp

def extract_summary(text):
    if "---SUMMARY_START---" in text and "---SUMMARY_END---" in text:
        start = text.index("---SUMMARY_START---") + len("---SUMMARY_START---")
        end = text.index("---SUMMARY_END---")
        json_str = text[start:end].strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None

def get_display_text(text):
    if "---SUMMARY_START---" in text:
        return text[:text.index("---SUMMARY_START---")].strip()
    return text

# セッション初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.completed = False
    st.session_state.summary = None

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": "初めてのクライアントとの対話を開始してください。最初の挨拶と問いかけをお願いします。"
        }]
    )
    first_message = response.content[0].text
    st.session_state.messages.append({
        "role": "assistant",
        "content": first_message
    })

# 会話履歴を表示
for message in st.session_state.messages:
    display_text = get_display_text(message["content"])
    if message["role"] == "assistant":
        with st.chat_message("assistant", avatar="✨"):
            st.write(display_text)
    else:
        with st.chat_message("user", avatar="😊"):
            st.write(display_text)

# ヒアリング完了済みの場合
if st.session_state.completed:
    st.markdown("""
    <div class="complete-box">
        <h3>ヒアリングが完了しました</h3>
        <p>担当アドバイザーがあなたの想いをもとに<br>
        ライフプランをデザインいたします。<br><br>
        後日ご連絡させていただきます。</p>
    </div>
    """, unsafe_allow_html=True)

# 未完了の場合は入力欄を表示
else:
    if user_input := st.chat_input("メッセージを入力してください"):

        with st.chat_message("user", avatar="😊"):
            st.write(user_input)
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("考え中..."):
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=st.session_state.messages
                )
                assistant_message = response.content[0].text

                display_text = get_display_text(assistant_message)
                st.write(display_text)

        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

        # サマリーが含まれているかチェック
        summary = extract_summary(assistant_message)
        if summary:
            st.session_state.completed = True
            st.session_state.summary = summary
            save_client_data(st.session_state.messages, summary)
            st.rerun()

