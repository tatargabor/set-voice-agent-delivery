/**
 * Voice Widget — connects browser to AI voice agent via Twilio Client SDK.
 */

const callBtn = document.getElementById('call-btn');
const phoneBtn = document.getElementById('phone-btn');
const statusEl = document.getElementById('status');
const identityInput = document.getElementById('identity');
const projectSelect = document.getElementById('project');
const phoneInput = document.getElementById('phone');

let device = null;
let activeCall = null;

function setStatus(text, className = '') {
    statusEl.textContent = text;
    statusEl.className = className;
}

function setButtonState(state) {
    callBtn.className = state;
    callBtn.disabled = state === 'connecting';
    callBtn.innerHTML = state === 'active' ? '&#x1F6D1;' : '&#x1F3A4;';
}

async function loadProjects() {
    try {
        const resp = await fetch('/api/projects');
        const data = await resp.json();
        projectSelect.innerHTML = '<option value="">-- Válasszon projektet --</option>';
        for (const p of data.projects) {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.label;
            projectSelect.appendChild(opt);
        }
    } catch (err) {
        projectSelect.innerHTML = '<option value="">Hiba a betöltéskor</option>';
    }
}

async function initDevice() {
    try {
        const identity = identityInput.value.trim() || 'browser-user';
        const resp = await fetch(`/twilio/token?identity=${encodeURIComponent(identity)}`);
        const data = await resp.json();

        if (data.error) {
            setStatus(data.error, 'error');
            return;
        }

        device = new Twilio.Device(data.token, {
            codecPreferences: ['opus', 'pcmu'],
            edge: 'ashburn',
        });

        device.on('registered', () => {
            setStatus('Kész — válasszon projektet és nyomja meg a gombot');
            callBtn.disabled = false;
        });

        device.on('error', (err) => {
            setStatus(`Hiba: ${err.message}`, 'error');
            setButtonState('');
        });

        await device.register();
    } catch (err) {
        setStatus(`Kapcsolódási hiba: ${err.message}`, 'error');
    }
}

async function startCall() {
    if (activeCall) {
        activeCall.disconnect();
        return;
    }

    try {
        setButtonState('connecting');
        setStatus('Kapcsolódás...');

        const identity = identityInput.value.trim() || 'browser-user';
        const project = projectSelect.value;
        const phone = phoneInput.value.trim();

        if (!device) {
            await initDevice();
        }

        activeCall = await device.connect({
            params: {
                To: 'voice-agent',
                Identity: identity,
                project: project,
            }
        });

        activeCall.on('accept', () => {
            setButtonState('active');
            setStatus('Beszélgetés folyamatban...', 'active');
        });

        activeCall.on('disconnect', () => {
            activeCall = null;
            setButtonState('');
            setStatus('Hívás befejezve — nyomja meg újra a híváshoz');
        });

        activeCall.on('cancel', () => {
            activeCall = null;
            setButtonState('');
            setStatus('Hívás megszakítva');
        });

        activeCall.on('error', (err) => {
            activeCall = null;
            setButtonState('');
            setStatus(`Hiba: ${err.message}`, 'error');
        });

    } catch (err) {
        setButtonState('');
        setStatus(`Hívás hiba: ${err.message}`, 'error');
    }
}

callBtn.addEventListener('click', startCall);

async function startPhoneCall() {
    const phone = phoneInput.value.trim();
    if (!phone) {
        setStatus('Adjon meg telefonszámot!', 'error');
        return;
    }

    const project = projectSelect.value;
    const identity = identityInput.value.trim() || 'browser-user';

    phoneBtn.disabled = true;
    phoneBtn.style.background = '#f59e0b';
    setStatus('Tárcsázás...', '');

    try {
        const resp = await fetch('/api/call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, project, identity }),
        });
        const data = await resp.json();
        if (data.error) {
            setStatus(`Hiba: ${data.error}`, 'error');
            phoneBtn.disabled = false;
            phoneBtn.style.background = '#3b82f6';
        } else {
            setStatus(`Hívás indítva: ${phone}`, 'active');
            phoneBtn.style.background = '#ef4444';
            phoneBtn.disabled = false;
            // Reset after 60s
            setTimeout(() => {
                phoneBtn.style.background = '#3b82f6';
                setStatus('Kész — válasszon projektet és nyomja meg a gombot');
            }, 60000);
        }
    } catch (err) {
        setStatus(`Hiba: ${err.message}`, 'error');
        phoneBtn.disabled = false;
        phoneBtn.style.background = '#3b82f6';
    }
}

phoneBtn.addEventListener('click', startPhoneCall);

// Enable phone button when phone input has value
phoneInput.addEventListener('input', () => {
    phoneBtn.disabled = !phoneInput.value.trim();
});

// Initialize
loadProjects();
initDevice();
