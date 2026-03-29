/**
 * Voice Widget — connects browser to AI voice agent via Twilio Client SDK.
 * UI text is loaded from /api/config (language + company_name from config.yaml).
 */

const callBtn = document.getElementById('call-btn');
const phoneBtn = document.getElementById('phone-btn');
const statusEl = document.getElementById('status');
const identityInput = document.getElementById('identity');
const projectSelect = document.getElementById('project');
const phoneInput = document.getElementById('phone');

let device = null;
let activeCall = null;

// --- i18n ---

const UI_TEXTS = {
    hu: {
        title: 'AI Asszisztens',
        projectLabel: 'Projekt',
        projectLoading: 'Betöltés...',
        projectSelect: '-- Válasszon projektet --',
        projectError: 'Hiba a betöltéskor',
        namePlaceholder: 'Az Ön neve (opcionális)',
        phonePlaceholder: 'Telefonszám (opcionális, pl. +36...)',
        browserLabel: 'Böngésző',
        phoneLabel: 'Telefon',
        initializing: 'Inicializálás...',
        ready: 'Kész — válasszon projektet és nyomja meg a gombot',
        connecting: 'Kapcsolódás...',
        inCall: 'Beszélgetés folyamatban...',
        callEnded: 'Hívás befejezve — nyomja meg újra a híváshoz',
        callCancelled: 'Hívás megszakítva',
        dialing: 'Tárcsázás...',
        callStarted: 'Hívás indítva:',
        enterPhone: 'Adjon meg telefonszámot!',
        indexing: 'Projekt indexelése...',
        readyToCall: 'Kész a hívásra',
        error: 'Hiba:',
        callError: 'Hívás hiba:',
        connectionError: 'Kapcsolódási hiba:',
    },
    en: {
        title: 'AI Assistant',
        projectLabel: 'Project',
        projectLoading: 'Loading...',
        projectSelect: '-- Select a project --',
        projectError: 'Error loading projects',
        namePlaceholder: 'Your name (optional)',
        phonePlaceholder: 'Phone number (optional, e.g. +1...)',
        browserLabel: 'Browser',
        phoneLabel: 'Phone',
        initializing: 'Initializing...',
        ready: 'Ready — select a project and press the button',
        connecting: 'Connecting...',
        inCall: 'Call in progress...',
        callEnded: 'Call ended — press again to call',
        callCancelled: 'Call cancelled',
        dialing: 'Dialing...',
        callStarted: 'Call started:',
        enterPhone: 'Please enter a phone number!',
        indexing: 'Indexing project...',
        readyToCall: 'Ready to call',
        error: 'Error:',
        callError: 'Call error:',
        connectionError: 'Connection error:',
    },
};

let t = UI_TEXTS.en; // default, overwritten by /api/config

async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        const data = await resp.json();
        const lang = data.language || 'en';
        t = UI_TEXTS[lang] || UI_TEXTS.en;

        document.documentElement.lang = lang === 'hu' ? 'hu' : 'en';
        document.getElementById('title').textContent = t.title;
        document.getElementById('company-name').textContent = data.company_name || '';
        document.getElementById('project-label').textContent = t.projectLabel;
        document.getElementById('project-loading').textContent = t.projectLoading;
        identityInput.placeholder = t.namePlaceholder;
        phoneInput.placeholder = t.phonePlaceholder;
        document.getElementById('browser-label').textContent = t.browserLabel;
        document.getElementById('phone-label').textContent = t.phoneLabel;
        statusEl.textContent = t.initializing;
    } catch (err) {
        console.warn('Config load failed, using English defaults:', err);
    }
}

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
        projectSelect.innerHTML = `<option value="">${t.projectSelect}</option>`;
        for (const p of data.projects) {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.label;
            projectSelect.appendChild(opt);
        }
    } catch (err) {
        projectSelect.innerHTML = `<option value="">${t.projectError}</option>`;
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
            setStatus(t.ready);
            callBtn.disabled = false;
        });

        device.on('error', (err) => {
            setStatus(`${t.error} ${err.message}`, 'error');
            setButtonState('');
        });

        await device.register();
    } catch (err) {
        setStatus(`${t.connectionError} ${err.message}`, 'error');
    }
}

async function startCall() {
    if (activeCall) {
        activeCall.disconnect();
        return;
    }

    try {
        setButtonState('connecting');
        setStatus(t.connecting);

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
            setStatus(t.inCall, 'active');
        });

        activeCall.on('disconnect', () => {
            activeCall = null;
            setButtonState('');
            setStatus(t.callEnded);
        });

        activeCall.on('cancel', () => {
            activeCall = null;
            setButtonState('');
            setStatus(t.callCancelled);
        });

        activeCall.on('error', (err) => {
            activeCall = null;
            setButtonState('');
            setStatus(`${t.error} ${err.message}`, 'error');
        });

    } catch (err) {
        setButtonState('');
        setStatus(`${t.callError} ${err.message}`, 'error');
    }
}

callBtn.addEventListener('click', startCall);

async function startPhoneCall() {
    const phone = phoneInput.value.trim();
    if (!phone) {
        setStatus(t.enterPhone, 'error');
        return;
    }

    const project = projectSelect.value;
    const identity = identityInput.value.trim() || 'browser-user';

    phoneBtn.disabled = true;
    phoneBtn.style.background = '#f59e0b';
    setStatus(t.dialing, '');

    try {
        const resp = await fetch('/api/call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, project, identity }),
        });
        const data = await resp.json();
        if (data.error) {
            setStatus(`${t.error} ${data.error}`, 'error');
            phoneBtn.disabled = false;
            phoneBtn.style.background = '#3b82f6';
        } else {
            setStatus(`${t.callStarted} ${phone}`, 'active');
            phoneBtn.style.background = '#ef4444';
            phoneBtn.disabled = false;
            setTimeout(() => {
                phoneBtn.style.background = '#3b82f6';
                setStatus(t.ready);
            }, 60000);
        }
    } catch (err) {
        setStatus(`${t.error} ${err.message}`, 'error');
        phoneBtn.disabled = false;
        phoneBtn.style.background = '#3b82f6';
    }
}

phoneBtn.addEventListener('click', startPhoneCall);

phoneInput.addEventListener('input', () => {
    phoneBtn.disabled = !phoneInput.value.trim();
});

projectSelect.addEventListener('change', async () => {
    const projectId = projectSelect.value;
    if (!projectId) return;
    try {
        const resp = await fetch('/api/index-project', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({project: projectId}),
        });
        const data = await resp.json();
        if (data.status === 'indexing') {
            setStatus(t.indexing, 'info');
            setTimeout(() => {
                if (statusEl.textContent === t.indexing) {
                    setStatus(t.readyToCall, 'success');
                }
            }, 4000);
        } else if (data.status === 'cached') {
            setStatus(t.readyToCall, 'success');
        }
    } catch (err) {
        console.warn('Index trigger failed:', err);
    }
});

// Initialize — load config first, then projects and device
loadConfig().then(() => {
    loadProjects();
    initDevice();
});
