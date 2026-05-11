// ========== 1. BACKGROUND ENGINE ==========
let bgCanvas, bgCtx, bgAnimationId;
let mouseX = 0, mouseY = 0;
let particles = [];

function initBackground() {
    bgCanvas = document.getElementById("bg-canvas");
    if (!bgCanvas) return;
    bgCtx = bgCanvas.getContext("2d");
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
    
    window.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    window.addEventListener("resize", () => {
        bgCanvas.width = window.innerWidth;
        bgCanvas.height = window.innerHeight;
        initParticlesForPage();
    });
    
    const page = document.body.getAttribute("data-page") || 
                 (window.location.pathname.includes("index.html") ? "login" : "home");
    startBackground(page);
}

function startBackground(page) {
    if (bgAnimationId) cancelAnimationFrame(bgAnimationId);
    
    const animations = {
        login: drawMatrixRain,
        home: drawHomeParticles,
        cipher: drawCipherShapes,
        mode: drawModeNetwork,
        action: drawActionBubbles
    };
    const drawFunc = animations[page] || drawHomeParticles;
    initParticlesForPage(page);
    
    function animate() {
        drawFunc(bgCtx, bgCanvas.width, bgCanvas.height, mouseX, mouseY);
        bgAnimationId = requestAnimationFrame(animate);
    }
    animate();
}

function initParticlesForPage(page) {
    particles = [];
    const count = 80;
    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * bgCanvas.width,
            y: Math.random() * bgCanvas.height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            size: 3 + Math.random() * 4
        });
    }
}

// ---------- LOGIN PAGE: MATRIX RAIN ----------
let matrixDrops = [];
function drawMatrixRain(ctx, w, h, mx, my) {
    if (matrixDrops.length === 0) {
        const cols = Math.floor(w / 20);
        for (let i = 0; i < cols; i++) matrixDrops[i] = 1;
    }
    ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#0f0";
    ctx.font = "20px monospace";
    for (let i = 0; i < matrixDrops.length; i++) {
        const text = String.fromCharCode(0x30A0 + Math.random() * 96);
        ctx.fillText(text, i * 20, matrixDrops[i] * 20);
        if (matrixDrops[i] * 20 > h && Math.random() > 0.975) matrixDrops[i] = 0;
        matrixDrops[i]++;
    }
}

// ---------- HOME PAGE: GREEN PARTICLES ----------
function drawHomeParticles(ctx, w, h, mx, my) {
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < particles.length; i++) {
        let p = particles[i];
        let dx = mx - p.x, dy = my - p.y;
        let dist = Math.hypot(dx, dy);
        if (dist < 80) {
            p.vx += dx * 0.002;
            p.vy += dy * 0.002;
        }
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 255, 0, ${0.5 + Math.sin(Date.now() * 0.002 + i) * 0.3})`;
        ctx.fill();
    }
}

// ---------- CIPHER PAGE: CYAN SQUARES ----------
let squares = [];
function drawCipherShapes(ctx, w, h, mx, my) {
    if (squares.length === 0) {
        for (let i = 0; i < 40; i++) {
            squares.push({ x: Math.random() * w, y: Math.random() * h, angle: Math.random() * Math.PI * 2, size: 20 + Math.random() * 20 });
        }
    }
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, w, h);
    const time = Date.now() * 0.003;
    for (let s of squares) {
        s.angle += 0.01;
        ctx.save();
        ctx.translate(s.x, s.y);
        ctx.rotate(s.angle + time);
        ctx.fillStyle = `rgba(0, 255, 255, 0.7)`;
        ctx.fillRect(-s.size/2, -s.size/2, s.size, s.size);
        ctx.restore();
    }
}

// ---------- MODE PAGE: PURPLE NETWORK ----------
let nodes = [];
function drawModeNetwork(ctx, w, h, mx, my) {
    if (nodes.length === 0) {
        for (let i = 0; i < 30; i++) {
            nodes.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.5, vy: (Math.random() - 0.5) * 0.5 });
        }
    }
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, w, h);
    for (let n of nodes) {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0) n.x = w; if (n.x > w) n.x = 0;
        if (n.y < 0) n.y = h; if (n.y > h) n.y = 0;
        ctx.beginPath();
        ctx.arc(n.x, n.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#a0f";
        ctx.fill();
    }
    ctx.strokeStyle = "rgba(128, 0, 255, 0.5)";
    for (let i = 0; i < nodes.length; i++) {
        for (let j = i+1; j < nodes.length; j++) {
            let dist = Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y);
            if (dist < 100) {
                ctx.beginPath();
                ctx.moveTo(nodes[i].x, nodes[i].y);
                ctx.lineTo(nodes[j].x, nodes[j].y);
                ctx.stroke();
            }
        }
    }
}

// ---------- ACTION PAGE: ORANGE BUBBLES ----------
let balls = [];
function drawActionBubbles(ctx, w, h, mx, my) {
    if (balls.length === 0) {
        for (let i = 0; i < 50; i++) {
            balls.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 2, vy: (Math.random() - 0.5) * 2, radius: 8 + Math.random() * 10 });
        }
    }
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, w, h);
    for (let b of balls) {
        b.x += b.vx; b.y += b.vy;
        if (b.x < 0 || b.x > w) b.vx = -b.vx;
        if (b.y < 0 || b.y > h) b.vy = -b.vy;
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 100, 0, 0.8)`;
        ctx.fill();
        ctx.strokeStyle = "orange";
        ctx.stroke();
    }
}

// ========== 2. UTILITY FUNCTIONS ==========
function typeText(text) {
    let el = document.getElementById("typing");
    if (!el) return;
    el.innerHTML = ""; 
    let i = 0;
    function typing() {
        if (i < text.length) {
            el.innerHTML += text.charAt(i);
            i++;
            setTimeout(typing, 50);
        }
    }
    typing();
}

function goPage(page) {
    document.body.style.opacity = "0";
    setTimeout(() => { window.location.href = page; }, 500);
}

// ========== OLD CHECKPASS FUNCTION ==========
function checkPass() {
    const passBox = document.getElementById("pass");
    const doveImg = document.getElementById("dove");
    const errorMsg = document.getElementById("error");

    // Allowed keys list
    const allowedKeys = [
        "THE-KHAN-PROTOCOL",
        "CYBER-CORE-X",
        "ENCRYPT-MASTER",
        "khan123",
        "NEO-SYSTEM-7",
        "HAZARA-CYBER-KING",
        "SECRET-SALT-256",
        "DECRYPT-THE-WORLD",
        "GHOST-OPERATOR",
        "g",
    ];

    if (passBox && allowedKeys.includes(passBox.value.trim())) {
        if (doveImg) doveImg.classList.add("fly-animation");
        
        if(passBox.value === "THE-KHAN-PROTOCOL") {
            typeText("PROTOCOL ACTIVATED... WELCOME COMMANDER KHAN.");
        } else {
            typeText("MESSAGE DELIVERED ... TAKING FLIGHT TO HAZARA.");
        }

        localStorage.setItem("musicStatus", "playing");
        setTimeout(() => { window.location.href = "home.html"; }, 5000); 
    } else if (errorMsg) {
        errorMsg.innerHTML = "❌ INVALID ACCESS KEY PLZ CONTACT WITH KHAN!";
        passBox.value = "";
    }
}

// ========== MAIN TOOL LOGIC ==========
async function runTool() {
    const messageInput = document.getElementById("messageInput");
    const fileInput = document.getElementById("fileInput");
    const keyInput = document.getElementById("keyInput");
    const outputField = document.getElementById("outputBox");

    const mainMode = localStorage.getItem("hackerMode") || "caesar";
    const subMode = localStorage.getItem("subMode") || "encrypt"; 
    const key = keyInput ? keyInput.value.trim() : "";
    const isFileMode = fileInput && fileInput.files.length > 0;
    
    if (isFileMode) {
        await sendFileToBackend(fileInput.files[0], mainMode, subMode, key);
    } else if (messageInput && messageInput.value.trim() !== "") {
        await sendToBackend(messageInput.value.trim(), mainMode, subMode, key);
    } else {
        if (outputField) outputField.value += "\n>> [!] ERROR: Input dain.";
    }
}

async function sendFileToBackend(file, cipher, action, key) {
    const outputField = document.getElementById("outputBox");
    const formData = new FormData();
    formData.append('cipher_type', cipher);
    formData.append('action', action);
    formData.append('key', key);
    formData.append('file_input', file);
    
    try {
        const response = await fetch('/process', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.status === "success") {
            outputField.value += `\n>> [${cipher.toUpperCase()} COMPLETED]\n>> [RESULT]: ${data.result}`;
            if (data.file_url && typeof window.setDownloadUrl === "function") {
                window.setDownloadUrl(window.location.origin + data.file_url);
            }
        }
    } catch (error) {
        outputField.value += "\n>> [!] CONNECTION FAILED.";
    }
    outputField.scrollTop = outputField.scrollHeight;
}

async function sendToBackend(text, cipher, action, key) {
    const outputField = document.getElementById("outputBox");
    const formData = new FormData();
    formData.append('cipher_type', cipher);
    formData.append('action', action);
    formData.append('message', text);
    formData.append('key', key);

    try {
        const response = await fetch('/process', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.status === "success") {
            outputField.value += `\n>> [${cipher.toUpperCase()} COMPLETED]\n>> [RESULT]: ${data.result}`;
        }
    } catch (error) {
        outputField.value += "\n>> [!] CONNECTION FAILED.";
    }
    outputField.scrollTop = outputField.scrollHeight;
}

// ========== MUSIC & LOAD ==========
function toggleMusic() {
    const music = document.getElementById("bgMusic");
    const icon = document.getElementById("musicIcon");
    if (!music) return;
    if (music.paused) {
        music.play();
        if (icon) icon.innerHTML = "🔊";
        localStorage.setItem("musicStatus", "playing");
    } else {
        music.pause();
        if (icon) icon.innerHTML = "🔇";
        localStorage.setItem("musicStatus", "paused");
    }
}

window.addEventListener("load", () => {
    initBackground();
    const music = document.getElementById("bgMusic");
    const status = localStorage.getItem("musicStatus");
    if (status === "playing" && music) music.play().catch(() => {});
});