const canvas = document.getElementById("roll");
const ctx = canvas.getContext("2d");

// ===== 設定 =====
let cols = 64;
let rows = 120;
const cellW = 25;
const cellH = 16;
let BPM = 120;

// ===== 楽器 =====
let currentInstrument = "default";

document.getElementById("instrument").addEventListener("change", e => {
  currentInstrument = e.target.value;
});

// ===== タイトル =====
let projectName = "MyProject";

function safeName(name){
  return name.replace(/[\\/:*?"<>|]/g, "_");
}

document.getElementById("title").addEventListener("input", e => {
  projectName = e.target.value || "MyProject";
});

// ===== トラック =====
let tracks = [
  {
    name: "Track1",
    instrument: "default",
    grid: Array.from({length: rows}, () => Array(cols).fill(null))
  }
];

let currentTrack = 0;

function getGrid(){
  return tracks[currentTrack].grid;
}

// ===== 状態 =====
let isMouseDown = false;
let startX, startY;
const audio = new AudioContext();
let currentStep = 0;
let nextTime = 0;
let isPlaying = false;

const container = document.getElementById("roll_container");

// ===== 鍵盤 =====
const keysCanvas = document.getElementById("keys");
const keysCtx = keysCanvas.getContext("2d");

keysCanvas.height = rows * cellH;
keysCanvas.width = 80;

function drawKeys(){
  keysCtx.clearRect(0,0,keysCanvas.width,keysCanvas.height);

  for(let y=0;y<rows;y++){
    const note = (120 - y + 11) % 12;
    const isBlack = [1,3,6,8,10].includes(note);

    keysCtx.fillStyle = isBlack ? "#111" : "#ddd";
    keysCtx.fillRect(0, y * cellH, 80, cellH);
  }
}
drawKeys();

// ===== 描画 =====
function getColor(inst){
  if(inst === "default") return "#0f0";
  if(inst === "voice") return "#0ff";
  return "#fff";
}

function draw() {
  ctx.clearRect(0,0,canvas.width,canvas.height);

  const grid = getGrid();

  for(let y=0;y<rows;y++){
    for(let x=0;x<cols;x++){
      ctx.strokeStyle = "#333";
      ctx.strokeRect(x*cellW, y*cellH, cellW, cellH);

      if(grid[y][x]){
        ctx.fillStyle = getColor(grid[y][x].instrument);

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
  ctx.beginPath();
  ctx.moveTo(currentStep * cellW, 0);
  ctx.lineTo(currentStep * cellW, rows * cellH);
  ctx.stroke();
}

function resize() {
  canvas.width = cols * cellW;
  canvas.height = rows * cellH;
}

resize();
draw();

// ===== 入力 =====
canvas.addEventListener("mousedown", e => {
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / cellW);
  const y = Math.floor((e.clientY - rect.top) / cellH);

  const grid = getGrid();

  if(e.button === 2){
    grid[y][x] = null;
    draw();
    return;
  }

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

  const grid = getGrid();
  grid[startY][startX] = {
    length,
    instrument: currentInstrument
  };

  draw();
});

// ===== 音源 =====
let defaultBuffer = null;
let voiceBuffer = null;

async function loaddefault(){
  const res = await fetch("default.wav");
  defaultBuffer = await audio.decodeAudioData(await res.arrayBuffer());
}
async function loadVoice(){
  const res = await fetch("voice.wav");
  voiceBuffer = await audio.decodeAudioData(await res.arrayBuffer());
}

loaddefault();
loadVoice();

// ===== 音 =====
function playInstrument(inst, freq, time, duration){
  if(inst === "default"){
    playBuffer(defaultBuffer, freq, time, duration);
  }
  if(inst === "voice"){
    playBuffer(voiceBuffer, freq, time, duration);
  }
}

function playBuffer(buffer, freq, time, duration){
  if(!buffer) return;

  const source = audio.createBufferSource();
  const gain = audio.createGain();

  source.buffer = buffer;

  const baseFreq = pitchToFreq(72); // C5
  source.playbackRate.setValueAtTime(freq / baseFreq, time);

  gain.gain.setValueAtTime(0.2, time);

  source.connect(gain);
  gain.connect(audio.destination);

  source.start(time);
  source.stop(time + duration);
}

function pitchToFreq(p){
  return 440 * Math.pow(2, (p-69)/12);
}

// ===== 再生 =====
function scheduler() {
  if(!isPlaying) return;

  const stepTime = (60 / BPM) / 4;

  while (nextTime < audio.currentTime + 0.1) {
    playStep(currentStep, nextTime);
    nextTime += stepTime;
    currentStep = (currentStep + 1) % cols;
  }

  draw();
  requestAnimationFrame(scheduler);
}

function playStep(step, time) {
  const stepTime = (60 / BPM) / 4;

  for(let track of tracks){
    for(let y=0;y<rows;y++){
      let note = track.grid[y][step];

      if(note){
        const duration = note.length * stepTime;

        if(!isFinite(duration) || duration <= 0) continue;

        playInstrument(
          note.instrument,
          pitchToFreq(120 - y),
          time,
          duration
        );
      }
    }
  }
}

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

function stop(){
  isPlaying = false;
}

// ===== 右クリック無効 =====
canvas.addEventListener("contextmenu", e => {
  e.preventDefault();
});
