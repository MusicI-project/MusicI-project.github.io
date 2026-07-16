import streamlit as st
import numpy as np
import os
import sentencepiece as spm

# LiteRT (TensorFlow Lite) のインポート
try:
    import litert
except ImportError:
    from tensorflow import lite as litert

# =====================================================================
# 🛠️ フォルダ内のファイルパスの基本設定
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_SEQ_LEN = 128                 # あなたのモデルの最大長に合わせてね

# =====================================================================
# 🎭 キャラクターたちのプロフィール設定（ここを自由に変えてね！）
# =====================================================================
# 💡 ここにキャラクターの設定を登録するだけで、何人でも増やせるのだ！
AI_CHARACTERS = {
    "ai": {
        "name": "藍 - Music I Chat Model",
        "caption": "コードに特化したAIモデルと会話ができるのだ。",
        "icon": "aicon.png"  # 📂 藍ちゃんのイラスト画像名
    },
    "ROA": {
        "name": "ROA - Music I Chat Model",
        "caption": "コードは苦手だけど、木管楽器のアンサンブルが得意なのだ",
        "icon": "ROA"
    }
}

# ユーザー（あなた）のアイコン画像名
USER_ICON_NAME = "user_icon.png"

# =====================================================================
# 🎛️ サイドバーでAIを切り替える仕組み
# =====================================================================
st.sidebar.title("🛠️ キャラクターチェンジ")

# 登録されているキャラクターのキー（"ai", "music", "chat"）を選択肢にするのだ
selected_key = st.sidebar.selectbox("お話しするAIを選ぶのだ：", list(AI_CHARACTERS.keys()))

# いま選ばれているキャラクターの情報をシュッと取り出すのだ！
current_ai = AI_CHARACTERS[selected_key]

# 選択された名前に合わせてファイルパスを自動生成
MODEL_PATH = os.path.join(BASE_DIR, f"model_{selected_key}.tflite")       
TOKENIZER_MODEL = os.path.join(BASE_DIR, f"spm_{selected_key}.model")

st.sidebar.info(f"現在ロード中: model_{selected_key}.tflite")

# =====================================================================
# あなたのトークナイザークラス（変更なし）
# =====================================================================
class SPTokenizer:
    def __init__(self, model_path):
        self.sp = spm.SentencePieceProcessor(model_file=model_path)
    def encode(self, text: str):
        return self.sp.encode_as_ids(text)
    def decode(self, ids: list):
        return self.sp.decode_ids(ids)
    def vocab_size(self):
        return self.sp.get_piece_size()

@st.cache_resource
def load_ai(model_path, tokenizer_path):
    if not os.path.exists(model_path) or not os.path.exists(tokenizer_path):
        st.error(f"ファイルが見つからないのだ！ {os.path.basename(model_path)} と {os.path.basename(tokenizer_path)} が同じフォルダにあるか確認してね。")
        st.stop()
        
    interpreter = litert.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    tokenizer = SPTokenizer(tokenizer_path)
    return interpreter, tokenizer


# =====================================================================
# あなたのオリジナルの推論コード（変更なし）
# =====================================================================
def generate_response_tflite(interpreter, tokenizer, raw_q, max_len=200, temperature=0.8):
    prediction_fn = interpreter.get_signature_runner()
    signature_list = interpreter.get_signature_list()

    sig_key = list(signature_list.keys())
    input_name = signature_list[sig_key]['inputs']
    output_key = signature_list[sig_key]['outputs']

    prompt = f"<in>{raw_q}</in><out>"
    input_ids = tokenizer.encode(prompt)
    generated_ids = []

    for _ in range(max_len):
        current_seq = input_ids + generated_ids

        if len(current_seq) > MAX_SEQ_LEN:
            current_seq = current_seq[-MAX_SEQ_LEN:]

        pad_len = MAX_SEQ_LEN - len(current_seq)
        padded_ids = current_seq + * pad_len

        input_np = np.array([padded_ids], dtype=np.int64)
        output = prediction_fn(**{input_name: input_np})
        logits = output[output_key]

        last_token_pos = len(current_seq) - 1
        next_token_logits = logits[0, last_token_pos] / max(1e-9, temperature)

        exp_logits = np.exp(next_token_logits - np.max(next_token_logits))
        probs = exp_logits / np.sum(exp_logits)
        next_token_id = int(np.random.choice(len(probs), p=probs))

        next_text = tokenizer.decode([next_token_id])
        if "</out>" in next_text or next_token_id == 0:
            break

        generated_ids.append(next_token_id)

    full_res = tokenizer.decode(generated_ids)
    return full_res.replace("<out>", "").replace("</out>", "").strip()


# =====================================================================
# 🎭 チャット画面の表示処理（選んだAIのプロフィールに自動変身！）
# =====================================================================
# 💡 タイトルと説明文を選ばれたAIのデータに書き換えるのだ！
st.title(f"🎵 {current_ai['name']}")
st.caption(current_ai['caption'])

interpreter, tokenizer = load_ai(MODEL_PATH, TOKENIZER_MODEL)

# モデルごとにチャット履歴の部屋を分けるのだ
session_key = f"messages_{selected_key}"
if session_key not in st.session_state:
    st.session_state[session_key] = []

# パスを安全に解決するための設定
# 💡 画像があれば使い、なければ名前の最初の1文字を自動でアイコンにする魔法のコードなのだ！
target_icon_path = os.path.join(BASE_DIR, current_ai['icon'])

if os.path.exists(target_icon_path) and current_ai['icon'] != "":
    ai_icon_path = target_icon_path  # イラスト画像があるからそれを使うのだ！
else:
    ai_icon_path = current_ai['name'][0]  # 画像がないから名前の「最初の1文字」をアイコンにするのだ！

user_icon_path = "👤"

# 過去のメッセージを表示
for msg in st.session_state[session_key]:
    current_avatar = ai_icon_path if msg["role"] == "assistant" else user_icon_path
    with st.chat_message(msg["role"], avatar=current_avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input(f"{current_ai['name']} にメッセージを入力してね..."):
    st.session_state[session_key].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=user_icon_path):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ai_icon_path):
        with st.spinner(f"{current_ai['name']} が一生懸命考えているのだ...🎵"):
            try:
                res = generate_response_tflite(interpreter, tokenizer, prompt)
                if "image_model" in res:
                    res = f"🎵「ごめんね、いまは画像ステージの準備中なのだ！もう少し待っててね！」"
            except Exception as e:
                res = f"ごめんね、うまくお話しできなかったのだ…（エラー原因: {e}）"
        
        st.markdown(res)
        st.session_state[session_key].append({"role": "assistant", "content": res})
