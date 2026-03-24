/**
 * Voice Widget — connects browser to AI voice agent via Twilio Client SDK.
 */

const callBtn = document.getElementById('call-btn');
const statusEl = document.getElementById('status');
const identityInput = document.getElementById('identity');
const projectSelect = document.getElementById('project');

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

// Initialize
loadProjects();
initDevice();
