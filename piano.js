const canvas = document.getElementById("roll");
const ctx = canvas.getContext("2d");

// 設定
const cols = 32;
const rows = 24;
const cellW = 25;
const cellH = 16;

// データ
let grid = Array.from({length: rows}, () => Array(cols).fill(0));

// 描画
function draw() {
  ctx.clearRect(0,0,canvas.width,canvas.height);

  for(let y=0;y<rows;y++){
    for(let x=0;x<cols;x++){
      // グリッド
      ctx.strokeStyle = "#333";
      ctx.strokeRect(x*cellW, y*cellH, cellW, cellH);

      // ノート
      if(grid[y][x]){
        ctx.fillStyle = "#0f0";
        ctx.fillRect(x*cellW, y*cellH, cellW, cellH);
      }
    }
  }
}

draw();

// クリックでON/OFF
canvas.addEventListener("click", e => {
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((e.clientX - rect.left) / cellW);
  const y = Math.floor((e.clientY - rect.top) / cellH);

  grid[y][x] ^= 1;
  draw();
});

// 音
const audio = new AudioContext();

function playFreq(freq){
  const osc = audio.createOscillator();
  const gain = audio.createGain();

  osc.frequency.value = freq;
  gain.gain.value = 0.1;

  osc.connect(gain);
  gain.connect(audio.destination);

  osc.start();
  osc.stop(audio.currentTime + 0.2);
}

// ピッチ変換
function pitchToFreq(p){
  return 440 * Math.pow(2, (p-69)/12);
}

// 再生
let step = 0;
let timer = null;

function play(){
  if(timer) return;

  timer = setInterval(()=>{
    for(let y=0;y<rows;y++){
      if(grid[y][step]){
        playFreq(pitchToFreq(80 - y));
      }
    }

    step = (step+1) % cols;
  },150);
}

function stop(){
  clearInterval(timer);
  timer = null;
}
