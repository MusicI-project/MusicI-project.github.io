const canvas = document.getElementById("roll");
const ctx = canvas.getContext("2d");

// 設定
let cols = 64;
let rows = 120;
const cellW = 25;
const cellH = 16;
let BPM = 120;
let grid = Array.from({length: rows}, () => Array(cols).fill(null));
let isMouseDown = false;
let startX, startY;
const audio = new AudioContext();
let currentStep = 0;
let nextTime = 0;
let isPlaying = false;
const container = document.getElementById("roll_container");

const keysCanvas = document.getElementById("keys");
const keysCtx = keysCanvas.getContext("2d");

keysCanvas.height = 400;
keysCanvas.width = 80;

function drawKeys(scrollY){
  keysCtx.clearRect(0,0,keysCanvas.width,keysCanvas.height);

  const startRow = Math.floor(scrollY / cellH);
  const visibleRows = Math.ceil(keysCanvas.height / cellH);

  for(let i=0;i<visibleRows;i++){
    let y = startRow + i;

    if(y >= rows) continue; // ←これ重要

    const note = (120 - y + 11) % 12;
    const isBlack = [1,3,6,8,10].includes(note);

    keysCtx.fillStyle = isBlack ? "#111" : "#ddd";
    keysCtx.fillRect(0, i*cellH, 80, cellH);
  }
}

// 描画
function draw() {
 ctx.clearRect(0,0,canvas.width,canvas.height);

  for(let y=0;y<rows;y++){
    for(let x=0;x<cols;x++){
      ctx.strokeStyle = "#333";
      ctx.strokeRect(x*cellW, y*cellH, cellW, cellH);

      if(grid[y][x]){
        ctx.fillStyle = "#0f0";
        ctx.fillRect(
        x * cellW,
        y * cellH,
        grid[y][x].length * cellW,
        cellH
        );
      }
    }
  }

  ctx.strokeStyle = "red";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(currentStep * cellW, 0);
  ctx.lineTo(currentStep * cellW, rows * cellH);
  ctx.stroke();
}

function resize() {
  canvas.width = cols * cellW;
  canvas.height = rows * cellH;
}

drawKeys(0);
resize();
draw();

// ===== ノート入力（ドラッグ対応） =====
container.addEventListener("scroll", () => {
  drawKeys(container.scrollTop);
});

canvas.addEventListener("mousedown", e => {
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / cellW);
  const y = Math.floor((e.clientY - rect.top) / cellH);

  if(e.button === 2){ // ←右クリック
    grid[y][x] = null;
    draw();
    return;
  }

  // 左クリック（今までの処理）
  isMouseDown = true;
  startX = x;
  startY = y;
});

canvas.addEventListener("mouseup", e => {
  if(!isMouseDown) return;
  isMouseDown = false;

  const rect = canvas.getBoundingClientRect();
  const endX = Math.floor((e.clientX - rect.left) / cellW);

  const length = Math.max(1, endX - startX + 1);

  grid[startY][startX] = { length };

  draw();
});

// 音

function playFreqAtTime(freq, time, duration){
  const osc = audio.createOscillator();
  const gain = audio.createGain();

  osc.frequency.setValueAtTime(freq, time);
  gain.gain.setValueAtTime(0.1, time);

  osc.connect(gain);
  gain.connect(audio.destination);

  osc.start(time);
  osc.stop(time + duration); // ←ここ重要
}

// ピッチ変換
function pitchToFreq(p){
  return 440 * Math.pow(2, (p-69)/12);
}

// ===== BPM同期再生 =====


function scheduler() {
    if(!isPlaying) return;

  const secondsPerBeat = 60 / BPM;
  const stepTime = secondsPerBeat / 4;

  while (nextTime < audio.currentTime + 0.1) {
    playStep(currentStep, nextTime);

    nextTime += stepTime;
    currentStep = (currentStep + 1) % cols;
  }

  draw();

  requestAnimationFrame(scheduler);
}

function playStep(step, time) {
  const secondsPerBeat = 60 / BPM;
  const stepTime = secondsPerBeat / 4;

  for(let y=0;y<rows;y++){
    let note = grid[y][step];

    if(note){
      const duration = note.length * stepTime;

      if(!isFinite(duration) || duration <= 0) continue;

      playFreqAtTime(
        pitchToFreq(120 - y),
        time,
        duration
      );
    }
  }
}

function audioBufferToWav(buffer) {
  const numOfChan = buffer.numberOfChannels;
  const length = buffer.length * numOfChan * 2 + 44;
  const bufferArray = new ArrayBuffer(length);
  const view = new DataView(bufferArray);
  let offset = 0;

  function writeString(s) {
    for (let i = 0; i < s.length; i++) {
      view.setUint8(offset++, s.charCodeAt(i));
    }
  }

  function write16BitPCM(input) {
    for (let i = 0; i < input.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
  }

  // RIFFヘッダ
  writeString("RIFF");
  view.setUint32(offset, 36 + buffer.length * 2, true); offset += 4;
  writeString("WAVE");

  // fmt
  writeString("fmt ");
  view.setUint32(offset, 16, true); offset += 4;
  view.setUint16(offset, 1, true); offset += 2;
  view.setUint16(offset, numOfChan, true); offset += 2;
  view.setUint32(offset, buffer.sampleRate, true); offset += 4;
  view.setUint32(offset, buffer.sampleRate * 2, true); offset += 4;
  view.setUint16(offset, numOfChan * 2, true); offset += 2;
  view.setUint16(offset, 16, true); offset += 2;

  // data
  writeString("data");
  view.setUint32(offset, buffer.length * 2, true); offset += 4;

  // 書き込み
  for (let i = 0; i < numOfChan; i++) {
    write16BitPCM(buffer.getChannelData(i));
  }

  return bufferArray;
}

// 再生
function play(){
  if(isPlaying) return;

  if(audio.state === "suspended"){
    audio.resume();
  }
  
  isPlaying = true;
  currentStep = 0;
  nextTime = audio.currentTime;

  scheduler();
}

// 停止
function stop(){
  isPlaying = false;
}

// BPM変更（UI用）
function setBPM(val){
  if(!isFinite(val) || val <= 0) return; // ←これ追加

  BPM = val;
  nextTime = audio.currentTime;
}

async function exportWav(){
  const length = cols * (60/BPM/4);
  const sampleRate = 44100;

  const offline = new OfflineAudioContext(1, length * sampleRate, sampleRate);

  for(let step=0; step<cols; step++){
    const time = step * (60/BPM/4);

    for(let y=0;y<rows;y++){
      let note = grid[y][step];

      if(note){
        const duration = note.length * (60/BPM/4);

        const osc = offline.createOscillator();
        const gain = offline.createGain();

        osc.frequency.value = pitchToFreq(120 - y);
        gain.gain.value = 0.1;

        osc.connect(gain);
        gain.connect(offline.destination);

        osc.start(time);
        osc.stop(time + duration);
      }
    }
  }

  const buffer = await offline.startRendering();

  const wav = audioBufferToWav(buffer);
  const blob = new Blob([wav], {type: "audio/wav"});

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "song.wav";
  a.click();
}

document.getElementById("BPM").addEventListener("input", e => {
  const val = Number(e.target.value);

  if(!isFinite(val) || val <= 0) return;

  setBPM(val);
});

document.getElementById("wavEx").addEventListener("click", () => {
  exportWav();
});
