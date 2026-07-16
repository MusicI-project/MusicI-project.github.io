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
# 🎛️ サイドバーでモデルを切り替える仕組みなのだ！
# =====================================================================
st.sidebar.title("🛠️ モデルチェンジ設定")

# 💡 選択肢にしたいモデルの名前をここに増やすだけで、何個でも追加できるのだ！
model_options = ["ai","ROA"] 
selected_model = st.sidebar.selectbox("動かすAIを選ぶのだ：", model_options)

# 選択された名前に合わせてファイルパスを自動生成するのだ
MODEL_PATH = os.path.join(BASE_DIR, f"model_{selected_model}.tflite")       
TOKENIZER_MODEL = os.path.join(BASE_DIR, f"spm_{selected_model}.model")

st.sidebar.info(f"現在ロード中: model_{selected_model}.tflite")

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

# 💡 モデル名（selected_model）ごとにキャッシュを分けて、切り替えを高速化するのだ！
@st.cache_resource
def load_ai(model_path, tokenizer_path):
    # ファイルが存在するかチェックする安全装置なのだ
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

    sig_key = list(signature_list.keys())[0]
    input_name = signature_list[sig_key]['inputs'][0]
    output_key = signature_list[sig_key]['outputs'][0]

    prompt = f"<in>{raw_q}</in><out>"
    input_ids = tokenizer.encode(prompt)
    generated_ids = []

    for _ in range(max_len):
        current_seq = input_ids + generated_ids

        if len(current_seq) > MAX_SEQ_LEN:
            current_seq = current_seq[-MAX_SEQ_LEN:]

        pad_len = MAX_SEQ_LEN - len(current_seq)
        padded_ids = current_seq + [0] * pad_len

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
# チャット画面の表示処理
# =====================================================================
st.title("🎵 藍 - Music I Chat Model")
st.caption("通常の自作AIモデルと会話ができるのだ。")

# 引数に選ばれたパスを渡すようにしたのだ
interpreter, tokenizer = load_ai(MODEL_PATH, TOKENIZER_MODEL)

# 💡 モデルをチェンジした時に、前のモデルのチャット履歴が混ざらないように部屋を分けるのだ！
session_key = f"messages_{selected_model}"
if session_key not in st.session_state:
    st.session_state[session_key] = []

for msg in st.session_state[session_key]:
    current_avatar = "🎵" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=current_avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input("藍にメッセージを入力してね..."):
    st.session_state[session_key].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🎵"):
        with st.spinner("藍が一生懸命考えているのだ...🎵"):
            try:
                res = generate_response_tflite(interpreter, tokenizer, prompt)
                if "image_model" in res:
                    res = "🎵「ごめんね、いまは画像ステージの準備中なのだ！もう少し待っててね！」"
            except Exception as e:
                res = f"ごめんね、うまくお話しできなかったのだ…（エラー原因: {e}）"
        
        st.markdown(res)
        st.session_state[session_key].append({"role": "assistant", "content": res})
