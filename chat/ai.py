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
# 🛠️ ファイル名の確認（GitHubにアップロードした本物の名前に合わせてね）
# =====================================================================
MODEL_PATH = "model.tflite"       # 💡もし「藍.tflite」とかならその名前に変えてね！
TOKENIZER_MODEL = "spm.model"     # 💡もしファイル名が違ったらその名前に変えてね！
MAX_SEQ_LEN = 128                 # あなたのモデルの最大長に合わせてね

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
def load_ai():
    # GitHubから直接ロードするからエラーが起きないし爆速なのだ！
    interpreter = litert.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    tokenizer = SPTokenizer(TOKENIZER_MODEL)
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

interpreter, tokenizer = load_ai()

if "messages_A" not in st.session_state:
    st.session_state.messages_A = []

for msg in st.session_state.messages_A:
    current_avatar = "🎵" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=current_avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input("藍にメッセージを入力してね..."):
    st.session_state.messages_A.append({"role": "user", "content": prompt})
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
        st.session_state.messages_A.append({"role": "assistant", "content": res})
