import streamlit as st
import numpy as np
import os
import sentencepiece as spm

# LiteRT (TensorFlow Lite) のインポート
try:
    import litert
except ImportError:
    from tensorflow import lite as litert

# ==========================================
# [変更なし] あなたのトークナイザークラス
# ==========================================
class SPTokenizer:
    def __init__(self, model_path):
        self.sp = spm.SentencePieceProcessor(model_file=model_path)
    def encode(self, text: str):
        return self.sp.encode_as_ids(text)
    def decode(self, ids: list):
        return self.sp.decode_ids(ids)
    def vocab_size(self):
        return self.sp.get_piece_size()

# パラメータ設定（お使いの数値に合わせてね）
MAX_SEQ_LEN = 128     
MODEL_PATH = "/ai_model.tflite"       # あなたのTFLiteファイル名
TOKENIZER_MODEL = "/ai_spm.model" # あなたのmodelファイル名

# ==========================================
# [変更なし] あなたのオリジナルの推論コード
# ==========================================
def generate_response_tflite(interpreter, tokenizer, raw_q, max_len=200, temperature=0.8):
    # シグネチャ情報の取得
    prediction_fn = interpreter.get_signature_runner()
    signature_list = interpreter.get_signature_list()

    # 入出力のキー名を取得
    sig_key = list(signature_list.keys())[0]
    input_name = signature_list[sig_key]['inputs'][0]
    output_key = signature_list[sig_key]['outputs'][0]

    # ユーザー入力をタグで整形
    prompt = f"<in>{raw_q}</in><out>"
    input_ids = tokenizer.encode(prompt)
    generated_ids = []

    # 最大 max_len 回繰り返して文章を生成する
    for _ in range(max_len):
        # 現在の入力（プロンプト + 生成済みトークン）
        current_seq = input_ids + generated_ids

        # モデルの最大長(MAX_SEQ_LEN)に合わせるパディング処理
        if len(current_seq) > MAX_SEQ_LEN:
            current_seq = current_seq[-MAX_SEQ_LEN:]

        pad_len = MAX_SEQ_LEN - len(current_seq)
        padded_ids = current_seq + [0] * pad_len # 0はパディング/EOS想定

        # 推論の実行
        input_np = np.array([padded_ids], dtype=np.int64)
        output = prediction_fn(**{input_name: input_np})
        logits = output[output_key]

        # 「最後に入力した文字」に対する次の単語の予測(ロジット)を取得
        last_token_pos = len(current_seq) - 1
        next_token_logits = logits[0, last_token_pos] / max(1e-9, temperature)

        # サンプリング
        exp_logits = np.exp(next_token_logits - np.max(next_token_logits))
        probs = exp_logits / np.sum(exp_logits)
        next_token_id = int(np.random.choice(len(probs), p=probs))

        # 終了判定: 文末タグ </out> または SentencePieceのEOSを引いたら終了
        next_text = tokenizer.decode([next_token_id])
        if "</out>" in next_text or next_token_id == 0:
            break

        generated_ids.append(next_token_id)

    # 全てつなげてデコードし、余計なタグを除去して返す
    full_res = tokenizer.decode(generated_ids)
    return full_res.replace("<out>", "").replace("</out>", "").strip()


# ==========================================
# 3. ウェブ表示用の処理 (ここだけ追加)
# ==========================================
st.title("🤖 藍 - AI Chatbot")
st.caption("TFLite自作モデルがウェブで動いているのだ！")

# 起動時に一度だけモデルを読み込む設定
@st.cache_resource
def load_ai():
    interpreter = litert.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    tokenizer = SPTokenizer(TOKENIZER_MODEL)
    return interpreter, tokenizer

interpreter, tokenizer = load_ai()

# 会話履歴を保存する箱
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去の会話を画面に描画
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ユーザーが文字を入力したとき
if prompt := st.chat_input("メッセージを入力してね..."):
    # ユーザーの入力を画面に表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # あなたの推論コードをそのまま呼び出す！
    with st.chat_message("assistant"):
        with st.spinner("藍が考えているのだ..."): # 考え中のぐるぐる表示
            res = generate_response_tflite(interpreter, tokenizer, prompt)
            
            # image_model の条件分岐もそのまま再現
            if "image_model" in res:
                res = "（画像を処理中なのだ…）" # 必要に応じてメッセージを変えてね
        
        # 画面に結果を表示
        st.markdown(res)
        
        # AIの返答を履歴に保存
        st.session_state.messages.append({"role": "assistant", "content": res})
