const canvas = document.getElementById("roll");
const ctx = canvas.getContext("2d");

// 設定
let cols = 64;
let rows = 120;
const cellW = 25;
const cellH = 16;

canvas.height = rows * cellH;

// BPM
let BPM = 120;

// データ
let grid = Array.from({length: rows}, () => Array(cols).fill(null));

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

resize();
draw();

// ===== ノート入力（ドラッグ対応） =====

let isMouseDown = false;
let startX, startY;

canvas.addEventListener("mousedown", e => {
  isMouseDown = true;

  const rect = canvas.getBoundingClientRect();
  startX = Math.floor((e.clientX - rect.left) / cellW);
  startY = Math.floor((e.clientY - rect.top) / cellH);
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
const audio = new AudioContext();

function playFreqAtTime(freq, time){
  const osc = audio.createOscillator();
  const gain = audio.createGain();

  osc.frequency.setValueAtTime(freq, time);
  gain.gain.setValueAtTime(0.1, time);

  osc.connect(gain);
  gain.connect(audio.destination);

  osc.start(time);
  osc.stop(time + 0.2);
}

// ピッチ変換
function pitchToFreq(p){
  return 440 * Math.pow(2, (p-69)/12);
}

// ===== BPM同期再生 =====

let currentStep = 0;
let nextTime = 0;
let isPlaying = false;

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
  for(let y=0;y<rows;y++){
    let note = grid[y][step];

    if(note){
      playFreqAtTime(pitchToFreq(120 - y), time);
    }
  }
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
  BPM = val;
  nextTime = audio.currentTime;
}

document.getElementById("BPM").addEventListener("input", e => {
  setBPM(Number(e.target.value));
});
