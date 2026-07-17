import streamlit as st
import numpy as np
import os
import sentencepiece as spm
import gc  # 💡 メモリを強制的に掃除するための秘密兵器なのだ！


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
AI_CHARACTERS = {
    "ai": {
        "name": "藍 - Music I Chat Model",
        "caption": "コードに特化したAIモデルと会話ができるのだ。",
        "icon": "aicon.png",
        "temperature": "0.7"
    },
    "ROA": {
        "name": "ROA - Music I Chat Model",
        "caption": "コードは苦手だけど、木管楽器のアンサンブルが得意なのだ",
        "icon": "🎶",
        "temperature": "0.5"
    },
    "RIA": {
        "name": "RIA - Music I Chat Model",
        "caption": "弦楽器主体の壮大なオーケストラJ-popが得意だけどベースがとても苦手なのだ",
        "icon": "RIA",
        "temperature": "0.3"
    }
}

USER_ICON_NAME = "user_icon.png"
def generate_utau_speech(text, folder_name):
    voice_dir = os.path.join(BASE_DIR, folder_name)
    if not os.path.exists(voice_dir):
        return None

    # 1. pykakasiを使って、漢字・カタカナ混じりの文章を爆速でひらがなにするのだ！
    kks = pykakasi.kakasi()
    result = kks.convert(text)
    
    # 変換されたパーツ（ひらがな）をガチャンと1つの文章に合体させるのだ
    translated_text = "".join([item['hira'] for item in result])
    
    # 残った記号（！や...など）を消去して、純度100%のひらがなだけにするのだ
    clean_text = re.sub(r'[^ぁ-んー]', '', translated_text)

    # 2. 原音設定（oto.ini）を解析するのだ
    oto_config = {}
    oto_path = os.path.join(voice_dir, "oto.ini")
    
    if os.path.exists(oto_path):
        for encoding in ["shift_jis", "utf-8"]:
            try:
                with open(oto_path, "r", encoding=encoding) as f:
                    for line in f:
                        if "=" in line:
                            filename_part, params_part = line.strip().split("=", 1)
                            params = params_part.split(",")
                            alias = params if params else filename_part.replace(".wav", "")
                            left_blank = float(params) if len(params) > 1 and params else 0.0
                            right_blank = float(params) if len(params) > 3 and params else 0.0
                            
                            oto_config[alias] = {
                                "file": filename_part,
                                "left": left_blank,
                                "right": right_blank
                            }
                break
            except Exception:
                continue

    wav_bytes_list = []
    
    # 3. 1文字ずつ原音設定に合わせてノイズをカットして集めるのだ
    for char in clean_text:
        config = oto_config.get(char, {"file": f"{char}.wav", "left": 0.0, "right": 0.0})
        wav_path = os.path.join(voice_dir, config["file"])
        
        if os.path.exists(wav_path):
            try:
                with wave.open(wav_path, 'rb') as w:
                    params = w.getparams()
                    framerate = w.getframerate()
                    
                    left_frame = int((config["left"] / 1000.0) * framerate)
                    total_frames = w.getnframes()
                    if config["right"] >= 0:
                        right_frame = int((config["right"] / 1000.0) * framerate)
                        end_frame = total_frames - right_frame
                    else:
                        end_frame = left_frame + int((abs(config["right"]) / 1000.0) * framerate)
                    
                    left_frame = max(0, min(left_frame, total_frames))
                    end_frame = max(left_frame, min(end_frame, total_frames))
                    
                    w.setpos(left_frame)
                    frames_to_read = end_frame - left_frame
                    audio_data = w.readframes(frames_to_read)
                    
                    mem_wav = io.BytesIO()
                    with wave.open(mem_wav, 'wb') as temp_w:
                        temp_w.setparams(params)
                        temp_w.writeframes(audio_data)
                    wav_bytes_list.append(mem_wav.getvalue())
            except Exception:
                pass

    if not wav_bytes_list:
        return None

    # 4. 綺麗なパーツたちを1本にガチャンと合体して出力！
    output_io = io.BytesIO()
    try:
        with wave.open(io.BytesIO(wav_bytes_list), 'rb') as first_wav:
            wav_params = first_wav.getparams()
            with wave.open(output_io, 'wb') as output_wav:
                output_wav.setparams(wav_params)
                for wav_bytes in wav_bytes_list:
                    with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
                        output_wav.writeframes(w.readframes(w.getnframes()))
        return output_io.getvalue()
    except Exception:
        return None
# =====================================================================
# 🎛️ サイドバーでAIを切り替える仕組み
# =====================================================================
st.sidebar.title("🛠️ キャラクターチェンジ")

# 💡 前回選んだモデルを記憶しておいて、切り替わったかをチェックするのだ
if "last_selected_model" not in st.session_state:
    st.session_state.last_selected_model = "ai"

selected_key = st.sidebar.selectbox("お話しするAIを選ぶのだ：", list(AI_CHARACTERS.keys()))

# 💡 モデルが切り替わったら、古いモデルのキャッシュを完全に消去してメモリを空けるのだ！
if selected_key != st.session_state.last_selected_model:
    st.cache_resource.clear()  # 蓄積されたキャッシュを全削除
    gc.collect()              # メモリのゴミ集めを強制実行
    st.session_state.last_selected_model = selected_key

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
# あなたのオリジナルの推論コード（メモリ節約化）
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
# 🎭 チャット画面の表示処理（選んだAIのプロフィールに自動変身！）
# =====================================================================
st.title(f"🎵 {current_ai['name']}")
st.caption(current_ai['caption'])

interpreter, tokenizer = load_ai(MODEL_PATH, TOKENIZER_MODEL)

# モデルごとにチャット履歴の部屋を分けるのだ
session_key = f"messages_{selected_key}"
if session_key not in st.session_state:
    st.session_state[session_key] = []

# 画像があれば使い、なければ名前の最初の1文字を自動でアイコンにする設定なのだ！
target_icon_path = os.path.join(BASE_DIR, current_ai['icon'])
if os.path.exists(target_icon_path) and current_ai['icon'] != "":
    ai_icon_path = target_icon_path
else:
    ai_icon_path = "🎵"

user_icon_path = os.path.join(BASE_DIR, USER_ICON_NAME)
if not os.path.exists(user_icon_path):
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
                res = generate_response_tflite(
                    interpreter, 
                    tokenizer, 
                    prompt, 
                    temperature=float(current_ai['temperature'])
                )
                if "image_model" in res:
                    res = f"🎵「ごめんね、いまは画像ステージの準備中なのだ！もう少し待っててね！」"
            except Exception as e:
                res = f"ごめんね、うまくお話しできなかったのだ…（エラー原因: {e}）"
        
        st.markdown(res)
        st.session_state[session_key].append({"role": "assistant", "content": res})
        
        # 💡【音声の自動生成＆再生！】対応するフォルダが存在する場合だけ、自動で鳴り響くのだ！
        # （ここは半角スペース8マスで揃えるのが大正解なのだ！）
        utau_voice = generate_utau_speech(res, current_ai['voice_folder'])
        if utau_voice:
            st.audio(utau_voice, format="audio/wav", autoplay=True)  # 🔊 爆速自動再生！
