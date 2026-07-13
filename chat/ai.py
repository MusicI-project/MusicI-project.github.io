import streamlit as st
import numpy as np
import os
import re
import urllib.request
import sentencepiece as spm

try:
    import litert
except ImportError:
    from tensorflow import lite as litert

DRIVE_URL_MODEL = "https://drive.google.com/uc?export=download&id=1CuPH1549BwfLokUlEWq945B_I6_wE4UL"
DRIVE_URL_TOKENIZER = "https://drive.google.com/uc?export=download&id=1gPG71HJZ4WXMSELHXMbbepXvUnzFzgbn"

MODEL_PATH = "ai_model.tflite"
TOKENIZER_MODEL = "ai_spm.model"
MAX_SEQ_LEN = 128     # あなたのモデルの最大長に合わせてね

def get_drive_id(url):
    match = re.search(r'/d/([^/]+)', url)
    return match.group(1) if match else url

@st.cache_resource
def load_ai():
    try:
        model_id = get_drive_id(DRIVE_URL_MODEL)
        tokenizer_id = get_drive_id(DRIVE_URL_TOKENIZER)
        
        model_download_url = f"https://google.com{model_id}"
        tokenizer_download_url = f"https://google.com{tokenizer_id}"
        
        if not os.path.exists(MODEL_PATH):
            with st.spinner("藍のファイルを準備中なのだ...少々お待ちを🎵"):
                urllib.request.urlretrieve(model_download_url, MODEL_PATH)
                
        if not os.path.exists(TOKENIZER_MODEL):
            with st.spinner("トークナイザーを準備中なのだ...🎵"):
                urllib.request.urlretrieve(tokenizer_download_url, TOKENIZER_MODEL)
    except Exception as e:
        st.error(f"Googleドライブからのダウンロードに失敗したのだ。共有設定が『全員』になっているか確認してね：{e}")

    interpreter = litert.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    tokenizer = SPTokenizer(TOKENIZER_MODEL)
    return interpreter, tokenizer


class SPTokenizer:
    def __init__(self, model_path):
        self.sp = spm.SentencePieceProcessor(model_file=model_path)
    def encode(self, text: str):
        return self.sp.encode_as_ids(text)
    def decode(self, ids: list):
        return self.sp.decode_ids(ids)
    def vocab_size(self):
        return self.sp.get_piece_size()


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
