const canvas = document.getElementById("roll");
const ctx = canvas.getContext("2d");

// ===== 設定 =====
let cols = 64;
let rows = 120;
const cellW = 25;
const cellH = 16;
let BPM = 120;

const BPM_box = document.getElementById("BPM");

// ===== 楽器 =====
let currentInstrument = "default";

document.getElementById("instrument").addEventListener("change", e => {
  currentInstrument = e.target.value;
});

// ===== タイトル =====
let projectName = "MyProject";

const title_box = document.getElementById("title");

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
drawKeys();
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
let pianoBuffer = null;

async function loaddefault(){
  const sample = await fetch("default.wav")
  .then(r => r.arrayBuffer())
  .then(b => offline.decodeAudioData(b));
}
async function loadpiano(){
  const sample = await fetch("piano.wav")
  .then(r => r.arrayBuffer())
  .then(b => offline.decodeAudioData(b));
}

loaddefault();
loadpiano();

// ===== 音 =====
function playInstrument(inst, freq, time, duration){
  if(inst === "default"){
    playBuffer(defaultBuffer, freq, time, duration);
  }
  if(inst === "piano"){
    playBuffer(pianoBuffer, freq, time, duration);
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
function setBPM(val){
  if(!isFinite(val) || val <= 0) return;
  BPM = val;
  nextTime = audio.currentTime;
}

// ===== WAV書き出し =====
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

  writeString("RIFF");
  view.setUint32(offset, 36 + buffer.length * 2, true); offset += 4;
  writeString("WAVE");

  writeString("fmt ");
  view.setUint32(offset, 16, true); offset += 4;
  view.setUint16(offset, 1, true); offset += 2;
  view.setUint16(offset, numOfChan, true); offset += 2;
  view.setUint32(offset, buffer.sampleRate, true); offset += 4;
  view.setUint32(offset, buffer.sampleRate * 2, true); offset += 4;
  view.setUint16(offset, numOfChan * 2, true); offset += 2;
  view.setUint16(offset, 16, true); offset += 2;

  writeString("data");
  view.setUint32(offset, buffer.length * 2, true); offset += 4;

  for (let i = 0; i < numOfChan; i++) {
    write16BitPCM(buffer.getChannelData(i));
  }

  return bufferArray;
}

async function exportWav(){
  const length = cols * (60/BPM/4);
  const sampleRate = 44100;

  const offline = new OfflineAudioContext(1, length * sampleRate, sampleRate);

  for(let track of tracks){
    for(let step=0; step<cols; step++){
      const time = step * (60/BPM/4);

      for(let y=0;y<rows;y++){
        let note = track.grid[y][step];

        if(note){
          const duration = note.length * (60/BPM/4);

          if(!sampleBuffer) continue;

            const source = offline.createBufferSource();
            const gain = offline.createGain();

            source.buffer = sampleBuffer;

            // ピッチ変更（重要）
            const baseFreq = 440; // A4基準
            const freq = pitchToFreq(120 - y);
            source.playbackRate.value = freq / baseFreq;

            gain.gain.value = 0.2;

            source.connect(gain);
            gain.connect(offline.destination);

            source.start(time);
            source.stop(time + duration);
        }
      }
    }
  }

  const buffer = await offline.startRendering();
  const wav = audioBufferToWav(buffer);
  const blob = new Blob([wav], {type: "audio/wav"});

  const name = safeName(projectName.trim() || "song");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name + ".wav";
  a.click();
}

// ===== MIPJ書き出し =====
function midiToNote(midi){
  const notes = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
  const name = notes[midi % 12];
  const octave = Math.floor(midi / 12) - 1;
  return name + octave;
}

function exportMIPJ(){
  let text = "";

  text += `$Project="${projectName}";\n\n`;

  text += `$BPM=(\n1.1.0=${BPM}!\n);\n\n`;
  text += `$Beat=(\n1.1.0=4/4!\n);\n\n`;

  tracks.forEach(track => {
    text += `$[${track.name}:${track.instrument}]=(\n`;

    for(let y=0;y<rows;y++){
      for(let x=0;x<cols;x++){
        let note = track.grid[y][x];

        if(note){
          const midi = 120 - y;
          const noteName = midiToNote(midi);
          const beat = Math.floor(x / 4) + 1;
          const tick = x % 4;

          text += `1.${beat}.${tick}_${noteName},${note.length}_vol="100"!\n`;
        }
      }
    }

    text += `);\n\n`;
  });

  const blob = new Blob([text], {type:"text/plain"});
  const name = safeName(projectName.trim() || "project");

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name + ".mipj";
  a.click();
}

function noteToMidi(note){
  const map = {
    "C":0,"C#":1,"D":2,"D#":3,"E":4,
    "F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11
  };

  const match = note.match(/^([A-G]#?)(\d)$/);
  if(!match) return 60;

  const pitch = map[match[1]];
  const octave = Number(match[2]);

  return pitch + (octave + 1) * 12;
}

function importMIPJ(text){
  tracks = [];

  const trackRegex = /\$\[(.+?):(.+?)\]=\(([\s\S]*?)\);/g;
  let match;

  while((match = trackRegex.exec(text))){
    const name = match[1];
    const instrument = match[2];
    const body = match[3];

    const grid = Array.from({length: rows}, () => Array(cols).fill(null));

    const lines = body.split("!").map(l => l.trim()).filter(Boolean);

    for(let line of lines){
      // 例: 1.1.0_C4,4_vol="100"
      const m = line.match(/(\d+)\.(\d+)\.(\d+)_([A-G]#?\d),(\d+)/);
      if(!m) continue;

      const beat = Number(m[2]);
      const tick = Number(m[3]);
      const noteName = m[4];
      const length = Number(m[5]);

      const x = (beat - 1) * 4 + tick;
      const midi = noteToMidi(noteName);
      const y = 120 - midi;

      if(y >= 0 && y < rows && x >= 0 && x < cols){
        grid[y][x] = {
          length,
          instrument
        };
      }
    }

    tracks.push({ name, instrument, grid });
  }

  const projectN = text.match(/\$Project="(.+?)";/);
  if(projectN){
    projectName = projectN[1];

    if(title_box){
      title_box.value = projectName;
    }
  }

  const projectB = text.match(/\$BPM=\(\s*1\.1\.0=(\d+)!/);
  if(projectB){
    BPM = Number(projectB[1]);

    if(BPM_box){
      BPM_box.value = BPM;
    }
  }
  
  draw();
}

// ===== イベント =====
document.getElementById("BPM").addEventListener("input", e => {
  const val = Number(e.target.value);
  if(!isFinite(val) || val <= 0) return;
  setBPM(val);
});

document.getElementById("wavEx").addEventListener("click", exportWav);
document.getElementById("mipjEx").addEventListener("click", exportMIPJ);
document.getElementById("mipjIm").addEventListener("change", e => {
  const file = e.target.files[0];
  if(!file) return;

  const reader = new FileReader();

  reader.onload = ev => {
    importMIPJ(ev.target.result);
  };

  reader.readAsText(file);
});

canvas.addEventListener("contextmenu", e => {
  e.preventDefault();
});
