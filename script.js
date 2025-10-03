const video = document.getElementById("video");
const canvas = document.getElementById("glcanvas");
const gl = canvas.getContext("webgl");
const fileInput = document.getElementById("file");
const webcamBtn = document.getElementById("webcam");
const colsInput = document.getElementById("cols");
const charsetSelect = document.getElementById("charset");

let asciiCharset = charsetSelect.value;
let cols = parseInt(colsInput.value,10);

function resizeCanvasToVideo() {
  if (video.videoWidth && video.videoHeight) {
    const videoAspect = video.videoWidth / video.videoHeight;
    const windowAspect = window.innerWidth / window.innerHeight;
    if (windowAspect > videoAspect) {
      canvas.height = window.innerHeight;
      canvas.width = Math.floor(canvas.height * videoAspect);
    } else {
      canvas.width = window.innerWidth;
      canvas.height = Math.floor(canvas.width / videoAspect);
    }
  } else {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  gl.viewport(0, 0, canvas.width, canvas.height);
}
resizeCanvasToVideo();

// Update UI
colsInput.addEventListener('change', ()=>cols = parseInt(colsInput.value)||120);
charsetSelect.addEventListener('change', ()=>{ asciiCharset=charsetSelect.value; buildGlyphAtlas(); });

// Video selection
fileInput.addEventListener('change', e => {
  const f = e.target.files[0];
  if(!f) return;
  const url = URL.createObjectURL(f);
  stopWebcam();
  video.src = url;
  video.muted = false; // Ensure sound is enabled
  video.play().catch(() => {
    // If autoplay is blocked, wait for user interaction
    video.addEventListener('click', () => video.play(), { once: true });
  });
});

let webcamStream = null;
webcamBtn.addEventListener('click', async ()=>{
  stopWebcam();
  try{
    webcamStream = await navigator.mediaDevices.getUserMedia({video:true, audio:false});
    video.srcObject = webcamStream;
    video.muted = false; // Ensure sound is enabled
    video.play().catch(() => {
      video.addEventListener('click', () => video.play(), { once: true });
    });
  }catch(err){alert("Webcam error: "+err);}
});

function stopWebcam(){
  if(webcamStream){webcamStream.getTracks().forEach(t=>t.stop()); webcamStream=null;}
}

// Shaders
const vs = `
  attribute vec2 a_pos;
  varying vec2 v_uv;
  void main(){
    v_uv = a_pos*0.5+0.5;
    gl_Position = vec4(a_pos,0.0,1.0);
  }
`;
const fs = `
  precision mediump float;
  varying vec2 v_uv;
  uniform sampler2D u_video;
  uniform sampler2D u_glyph;
  uniform vec2 u_resolution;
  uniform vec2 u_grid;
  uniform vec2 u_glyphSize;
  uniform float u_charsetLen;

  float lum(vec3 c){return dot(c, vec3(0.299,0.587,0.114));}

  void main(){
    vec2 pixelPos = v_uv*u_resolution;
    vec2 cellSize = u_resolution/u_grid;
    vec2 cell = floor(pixelPos/cellSize);
    vec2 local = fract(pixelPos/cellSize);

    vec2 videoUV = (cell+0.5)/u_grid;
    
    vec3 col = texture2D(u_video, vec2(videoUV.x, 1.0 - videoUV.y)).rgb;

    float b = lum(col);
    float idxF = floor(b*(u_charsetLen-1.0)+0.0001);
    float idx = clamp(idxF,0.0,u_charsetLen-1.0);

    float atlasCols = u_glyphSize.x;
    float glyphX = mod(idx, atlasCols);
    float glyphY = floor(idx/atlasCols);
    vec2 glyphUV = vec2(
      (glyphX+local.x)/atlasCols,
      (glyphY+(1.0-local.y))/u_glyphSize.y
    );
    vec4 glyphSample = texture2D(u_glyph,glyphUV);
    float a = glyphSample.a;
    gl_FragColor = vec4(vec3(a),1.0);
  }
`;

function createShader(type,src){
  const s = gl.createShader(type);
  gl.shaderSource(s,src);
  gl.compileShader(s);
  if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(s);
  return s;
}

function createProgram(vsSrc,fsSrc){
  const p = gl.createProgram();
  gl.attachShader(p, createShader(gl.VERTEX_SHADER,vsSrc));
  gl.attachShader(p, createShader(gl.FRAGMENT_SHADER,fsSrc));
  gl.linkProgram(p);
  if(!gl.getProgramParameter(p, gl.LINK_STATUS)) throw gl.getProgramInfoLog(p);
  return p;
}

const program = createProgram(vs,fs);
gl.useProgram(program);
const posLoc = gl.getAttribLocation(program,"a_pos");
const posBuf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER,posBuf);
gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
gl.enableVertexAttribArray(posLoc);
gl.vertexAttribPointer(posLoc,2,gl.FLOAT,false,0,0);

const u_resolution = gl.getUniformLocation(program,"u_resolution");
const u_grid = gl.getUniformLocation(program,"u_grid");
const u_glyphSize = gl.getUniformLocation(program,"u_glyphSize");
const u_charsetLen = gl.getUniformLocation(program,"u_charsetLen");
const u_video = gl.getUniformLocation(program,"u_video");
const u_glyph = gl.getUniformLocation(program,"u_glyph");

// Textures
const videoTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, videoTex);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

const glyphTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, glyphTex);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

let atlasCols=0, atlasRows=0, glyphW=0, glyphH=0;
function buildGlyphAtlas(){
  const n = asciiCharset.length;
  atlasCols = Math.min(16,n);
  atlasRows = Math.ceil(n/atlasCols);
  glyphW = Math.max(6, Math.floor(canvas.width/cols));
  glyphH = Math.floor(glyphW*1.6);

  const gcanvas = document.createElement("canvas");
  gcanvas.width = atlasCols*glyphW;
  gcanvas.height = atlasRows*glyphH;
  const gctx = gcanvas.getContext("2d");
  gctx.clearRect(0,0,gcanvas.width,gcanvas.height);
  gctx.fillStyle="rgba(255,255,255,1)";
  gctx.textBaseline="middle";
  gctx.textAlign="center";
  gctx.font=`${Math.floor(glyphH*0.9)}px monospace`;
  for(let i=0;i<n;i++){
    const ch = asciiCharset[i];
    const cx = (i%atlasCols)*glyphW + glyphW/2;
    const cy = Math.floor(i/atlasCols)*glyphH + glyphH/2;
    gctx.fillText(ch,cx,cy);
  }

  gl.bindTexture(gl.TEXTURE_2D,glyphTex);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,gcanvas);
  gl.useProgram(program);
  gl.uniform2f(u_glyphSize,atlasCols,atlasRows);
  gl.uniform1f(u_charsetLen,n);
}

buildGlyphAtlas();

// render loop
function render(){
  requestAnimationFrame(render);
  if(video.readyState<2) return;

  // Update video texture
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, videoTex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, video);

  // Bind glyph texture to texture unit 1
  gl.activeTexture(gl.TEXTURE1);
  gl.bindTexture(gl.TEXTURE_2D, glyphTex);

  // Set uniforms
  gl.useProgram(program);
  gl.uniform2f(u_resolution, canvas.width, canvas.height);

  // Maintain video aspect ratio for grid rows
  const videoAspect = video.videoWidth && video.videoHeight ? video.videoHeight / video.videoWidth : canvas.height / canvas.width;
  gl.uniform2f(u_grid, cols, Math.floor(cols * videoAspect));
  gl.uniform1i(u_video, 0); // Texture unit 0
  gl.uniform1i(u_glyph, 1); // Texture unit 1

  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}
render();

window.addEventListener("resize",()=>{
  canvas.width=window.innerWidth;
  canvas.height=window.innerHeight;
  buildGlyphAtlas();
});
