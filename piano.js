const canvas = document.getElementById("roll");
const ctx = canvas.getContext("2d");
canvas.height = rows * cellH;
// 設定
let cols = 32;
let rows = 120;
const cellW = 25;
const cellH = 16;


// BPM
let BPM = 120;

// データ
let grid = Array.from({length: rows}, () => Array(cols).fill(0));

// 描画
function draw() {
  ctx.clearRect(0,0,canvas.width,canvas.height);

  for(let y=0;y<rows;y++){
    for(let x=0;x<cols;x++){
      ctx.strokeStyle = "#333";
      ctx.strokeRect(x*cellW, y*cellH, cellW, cellH);

      if(grid[y][x]){
        ctx.fillStyle = "#0f0";
        ctx.fillRect(x*cellW, y*cellH, cellW, cellH);
      }
    }
  }
}
draw();

function resize() {
  canvas.width = cols * cellW;
  canvas.height = rows * cellH;
  draw();
}

resize();

// クリック
canvas.addEventListener("click", e => {
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / cellW);
  const y = Math.floor((e.clientY - rect.top) / cellH);

  grid[y][x] ^= 1;
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
  const stepTime = secondsPerBeat / 4; // 16分音符
  
  while (nextTime < audio.currentTime + 0.1) {
    playStep(currentStep, nextTime);

    nextTime += stepTime;
    currentStep = (currentStep + 1) % cols;
  }

  requestAnimationFrame(scheduler);
}

function playStep(step, time) {
  for(let y=0;y<rows;y++){
    if(grid[y][step]){
      playFreqAtTime(pitchToFreq(120 - y), time);
    }
  }
}

// 再生
function play(){
  if(isPlaying) return;

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
}

document.getElementById("BPM").addEventListener("input", e => {
  setBPM(Number(e.target.value));
});
