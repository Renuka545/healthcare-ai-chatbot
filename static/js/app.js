document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadToolsRegistry();
    fetchPatientHistory();
});

// Navigation between Tabs
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            navButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.add('hidden'));

            btn.classList.add('active');
            const activePane = document.getElementById(targetTab);
            if (activePane) activePane.classList.remove('hidden');

            const titles = {
                'chat-tab': ['Healthcare AI Chatbot', 'Intelligent Tool Selection, Action Modal & Patient History'],
                'compare-tab': ['Intent Benchmarker', 'Side-by-Side Comparison of Rule vs LLM vs Hybrid Approaches'],
                'eval-tab': ['Dataset Evaluator', 'Automated Performance Benchmarks & Pass/Fail Metrics'],
                'rag-tab': ['RAG Knowledge Base', 'Semantic Vector Search over Clinical Guidelines'],
                'tools-tab': ['Tool Registry', 'Registered FastMCP Healthcare Tools Portfolio']
            };
            if (titles[targetTab]) {
                document.getElementById('tab-title').innerText = titles[targetTab][0];
                document.getElementById('tab-subtitle').innerText = titles[targetTab][1];
            }
        });
    });
}

// Switch Right Sidebar Panels (Tool Tracer vs. History & Activity)
function switchRightPanel(tab) {
    const btnTracer = document.getElementById('tab-btn-tracer');
    const btnHistory = document.getElementById('tab-btn-history');
    const panelTracer = document.getElementById('panel-tracer');
    const panelHistory = document.getElementById('panel-history');

    if (tab === 'history') {
        btnTracer.classList.remove('active');
        btnHistory.classList.add('active');
        panelTracer.classList.add('hidden');
        panelHistory.classList.remove('hidden');
        fetchPatientHistory();
    } else {
        btnHistory.classList.remove('active');
        btnTracer.classList.add('active');
        panelHistory.classList.add('hidden');
        panelTracer.classList.remove('hidden');
    }
}

// Chat functions
function handleKeyPress(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
}

function sendPreset(text) {
    document.getElementById('user-input').value = text;
    sendMessage();
}

async function sendMessage() {
    const inputEl = document.getElementById('user-input');
    const query = inputEl.value.trim();
    if (!query) return;

    inputEl.value = '';
    appendMessage('user', query);
    showInspectorLoading();

    const mode = document.getElementById('classifier-select').value;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, patient_id: 'P-1001', classifier_mode: mode })
        });

        const data = await response.json();

        // Generic modal handling for any tool that requires additional user input
        if (data.action_requires_modal && data.modal_payload) {
            appendMessage('bot', data.final_response, false, true, data.modal_payload);
            openGenericModal(data.modal_payload);
        } else {
            appendMessage('bot', data.final_response, data.intent_info.is_emergency);
        }

        updateInspector(data);
        fetchPatientHistory(); // Refresh history panel
    } catch (err) {
        appendMessage('bot', '⚠️ Error connecting to Healthcare AI API backend.');
    }
}

function appendMessage(sender, text, isEmergency = false, showModalBtn = false, modalPayload = null) {
    const chatContainer = document.getElementById('chat-messages');

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-msg`;

    const avatarIcon = sender === 'user' ? 'fa-user' : (isEmergency ? 'fa-triangle-exclamation' : 'fa-user-doctor');

    let formattedText = text.replace(/\n/g, '<br>');
    if (isEmergency) {
        msgDiv.classList.add('emergency-alert-msg');
    }

    let extraHTML = '';
    if (showModalBtn && modalPayload) {
        extraHTML = `
            <button class="open-modal-trigger-btn" onclick='openAppointmentModal(${JSON.stringify(modalPayload)})'>
                <i class="fa-solid fa-calendar-plus"></i> Open Appointment Booking Screen
            </button>
        `;
    }

    msgDiv.innerHTML = `
        <div class="avatar"><i class="fa-solid ${avatarIcon}"></i></div>
        <div class="msg-content">
            <p>${formattedText}</p>
            ${extraHTML}
        </div>
    `;

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// POP-UP APPOINTMENT MODAL LOGIC
function openGenericModal(payload = null) {
    const overlay = document.getElementById('appointment-modal-overlay');
    overlay.classList.remove('hidden');

    // Clear previous dynamic content
    const dynamicContainer = document.getElementById('modal-dynamic-content');
    if (dynamicContainer) dynamicContainer.innerHTML = '';

    // Populate fields based on payload content
    if (payload) {
        // If payload is for appointment, reuse existing fields
        if (payload.specialty) document.getElementById('modal-specialty').value = payload.specialty;
        if (payload.doctor_name) document.getElementById('modal-doctor').value = payload.doctor_name;
        if (payload.reason) document.getElementById('modal-reason').value = payload.reason;
        if (payload.preferred_date) document.getElementById('modal-date').value = payload.preferred_date;
        if (payload.preferred_time) document.getElementById('modal-time').value = payload.preferred_time;

        // Generic message handling
        if (payload.message) {
            const msgDiv = document.createElement('div');
            msgDiv.id = 'modal-generic-message';
            msgDiv.innerText = payload.message;
            msgDiv.style.marginBottom = '12px';
            overlay.querySelector('.modal-content')?.appendChild(msgDiv);
        }
    }
}

// Refresh button logic – clears chat and resets UI
function handleRefresh() {
    // Clear chat messages
    const chatContainer = document.getElementById('chat-messages');
    if (chatContainer) chatContainer.innerHTML = '';

    // Reset inspector placeholders
    document.getElementById('inspector-placeholder').classList.remove('hidden');
    document.getElementById('inspector-content').classList.add('hidden');

    // Clear history panel
    const historyContainer = document.getElementById('history-timeline-container');
    if (historyContainer) historyContainer.innerHTML = '';

    // Optionally, you could reset any session state on the backend
    // For now we just clear UI state
    console.log('Chat refreshed');
}

// Bind refresh button event after DOM loads
function bindRefreshButton() {
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', handleRefresh);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadToolsRegistry();
    fetchPatientHistory();
    bindRefreshButton();
});

function closeAppointmentModal() {
    document.getElementById('appointment-modal-overlay').classList.add('hidden');
}

function onSpecialtyChange() {
    const spec = document.getElementById('modal-specialty').value;
    const docSelect = document.getElementById('modal-doctor');
    
    const docMap = {
        'Cardiology': 'Dr. Emily Vance',
        'Internal Medicine': 'Dr. Marcus Thorne',
        'Dermatology': 'Dr. Sarah Jenkins',
        'Orthopedics': 'Dr. Alan Grant',
        'Neurology': 'Dr. Vance (Neurology)',
        'Pediatrics': 'Dr. Thorne (Pediatrics)'
    };
    
    if (docMap[spec]) {
        docSelect.value = docMap[spec];
    }
}

async function confirmAppointmentBooking() {
    const specialty = document.getElementById('modal-specialty').value;
    const doctor = document.getElementById('modal-doctor').value;
    const reason = document.getElementById('modal-reason').value.trim() || 'General Consultation';
    const date = document.getElementById('modal-date').value;
    const time = document.getElementById('modal-time').value;

    closeAppointmentModal();
    appendMessage('user', `Confirmed Booking: ${specialty} with ${doctor} for ${date} ${time}. Health Problem: ${reason}`);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: `Book appointment with ${doctor} (${specialty}) on ${date} at ${time} for ${reason}`,
                patient_id: 'P-1001',
                classifier_mode: 'rule'
            })
        });

        const data = await response.json();
        appendMessage('bot', `🎉 ${data.final_response}`);
        updateInspector(data);
        fetchPatientHistory();
        switchRightPanel('history'); // Automatically switch to timeline panel to show booked appointment!

    } catch (e) {
        appendMessage('bot', '⚠️ Error confirming appointment booking.');
    }
}

// PATIENT ACTION & APPOINTMENT HISTORY TIMELINE
async function fetchPatientHistory() {
    const container = document.getElementById('history-timeline-container');
    if (!container) return;

    try {
        const res = await fetch('/api/history?patient_id=P-1001');
        const data = await res.json();
        renderHistoryTimeline(data);
    } catch (e) {
        container.innerHTML = `<p style="color:var(--text-muted)">Unable to load history.</p>`;
    }
}

function renderHistoryTimeline(data) {
    const container = document.getElementById('history-timeline-container');
    container.innerHTML = '';

    const apts = data.appointments || [];
    const labs = data.lab_results || [];
    const rxs = data.prescriptions || [];
    const tickets = data.tickets || [];

    if (apts.length === 0 && labs.length === 0 && rxs.length === 0 && tickets.length === 0) {
        container.innerHTML = `<p style="color:var(--text-muted);font-size:12px">No patient history recorded yet.</p>`;
        return;
    }

    // Render Appointments
    apts.forEach(apt => {
        const card = document.createElement('div');
        card.className = 'history-card apt-card';
        const isCancelled = apt.status === 'Cancelled';
        const statusBadge = isCancelled ? 
            `<span class="status-tag cancelled">Cancelled</span>` : 
            `<span class="status-tag confirmed">Confirmed</span>`;

        let cancelBtn = '';
        if (!isCancelled) {
            cancelBtn = `<button class="cancel-apt-btn" onclick="cancelAppointmentById('${apt.appointment_id}')"><i class="fa-solid fa-xmark"></i> Cancel Appointment</button>`;
        }

        card.innerHTML = `
            <div class="card-top">
                <span class="card-title-text"><i class="fa-solid fa-calendar-check" style="color:var(--primary)"></i> ${apt.doctor_name}</span>
                ${statusBadge}
            </div>
            <div class="card-meta">
                <span><strong>Specialty:</strong> ${apt.specialty}</span>
                <span><strong>Date & Time:</strong> ${apt.date_time}</span>
                <span><strong>Reason:</strong> ${apt.reason}</span>
            </div>
            ${cancelBtn}
        `;
        container.appendChild(card);
    });

    // Render Labs
    labs.forEach(lab => {
        const card = document.createElement('div');
        card.className = 'history-card lab-card';
        card.innerHTML = `
            <div class="card-top">
                <span class="card-title-text"><i class="fa-solid fa-vial" style="color:var(--secondary)"></i> ${lab.test_name}</span>
                <span class="badge confidence">${lab.date}</span>
            </div>
            <div class="card-meta">
                <span>${lab.summary}</span>
            </div>
        `;
        container.appendChild(card);
    });

    // Render Prescriptions
    rxs.forEach(rx => {
        const card = document.createElement('div');
        card.className = 'history-card rx-card';
        card.innerHTML = `
            <div class="card-top">
                <span class="card-title-text"><i class="fa-solid fa-pills" style="color:var(--accent)"></i> ${rx.medication}</span>
                <span class="badge">${rx.refills_remaining} Refills Left</span>
            </div>
            <div class="card-meta">
                <span><strong>Pharmacy:</strong> ${rx.pharmacy}</span>
                <span><strong>Dosage:</strong> ${rx.dosage}</span>
            </div>
        `;
        container.appendChild(card);
    });

    // Render Tickets
    tickets.forEach(tck => {
        const card = document.createElement('div');
        card.className = 'history-card tck-card';
        card.innerHTML = `
            <div class="card-top">
                <span class="card-title-text"><i class="fa-solid fa-ticket" style="color:var(--warning)"></i> Ticket #${tck.ticket_id}</span>
                <span class="badge">${tck.status}</span>
            </div>
            <div class="card-meta">
                <span><strong>Category:</strong> ${tck.category}</span>
                <span><strong>Subject:</strong> ${tck.subject}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

async function cancelAppointmentById(aptId) {
    if (!confirm(`Are you sure you want to cancel appointment #${aptId}?`)) return;

    try {
        const res = await fetch('/api/appointments/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appointment_id: aptId, patient_id: 'P-1001' })
        });
        const data = await res.json();
        alert(data.message);
        fetchPatientHistory();
    } catch (e) {
        alert('Error cancelling appointment.');
    }
}

function showInspectorLoading() {
    document.getElementById('inspector-placeholder').classList.add('hidden');
    document.getElementById('inspector-content').classList.remove('hidden');

    document.getElementById('trace-intent').innerText = 'Classifying Intent...';
    document.getElementById('trace-tool').innerText = 'Selecting Tool...';
}

function updateInspector(data) {
    const intentInfo = data.intent_info;

    document.getElementById('trace-intent').innerText = intentInfo.intent;
    document.getElementById('trace-method').innerText = intentInfo.method_used.toUpperCase();
    document.getElementById('trace-confidence').innerText = Math.round(intentInfo.confidence * 100) + '%';
    document.getElementById('trace-speed').innerText = intentInfo.execution_time_ms.toFixed(1) + ' ms';

    document.getElementById('trace-tool').innerText = intentInfo.tool_name;
    document.getElementById('trace-reasoning').innerText = intentInfo.reasoning;

    document.getElementById('trace-params').innerText = JSON.stringify(intentInfo.parameters, null, 2);

    const phiBadge = document.getElementById('audit-phi');
    if (intentInfo.phi_detected) {
        phiBadge.innerText = 'PHI: REDACTED (HIPAA Compliant)';
        phiBadge.style.color = '#f87171';
        phiBadge.style.borderColor = 'rgba(239,68,68,0.4)';
    } else {
        phiBadge.innerText = 'PHI: Clear';
        phiBadge.style.color = '#34d399';
        phiBadge.style.borderColor = 'rgba(16,185,129,0.3)';
    }

    const emergBadge = document.getElementById('audit-emergency');
    if (intentInfo.is_emergency) {
        emergBadge.innerText = 'Triage: CRITICAL EMERGENCY';
        emergBadge.style.color = '#f87171';
        emergBadge.style.borderColor = 'rgba(239,68,68,0.4)';
    } else {
        emergBadge.innerText = 'Triage: Routine / Normal';
        emergBadge.style.color = '#38bdf8';
        emergBadge.style.borderColor = 'rgba(56,189,248,0.3)';
    }
}

// Side-by-Side Comparison
async function runComparison() {
    const query = document.getElementById('compare-query-input').value.trim();
    if (!query) return;

    try {
        const response = await fetch('/api/intents/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();

        document.getElementById('rule-tool').innerText = data.rule_based.tool_name;
        document.getElementById('rule-conf').innerText = Math.round(data.rule_based.confidence * 100) + '%';
        document.getElementById('rule-speed').innerText = data.rule_based.execution_time_ms.toFixed(1) + ' ms';
        document.getElementById('rule-reasoning').innerText = data.rule_based.reasoning;

        document.getElementById('llm-tool').innerText = data.llm_based.tool_name;
        document.getElementById('llm-conf').innerText = Math.round(data.llm_based.confidence * 100) + '%';
        document.getElementById('llm-speed').innerText = data.llm_based.execution_time_ms.toFixed(1) + ' ms';
        document.getElementById('llm-reasoning').innerText = data.llm_based.reasoning;

        document.getElementById('hybrid-tool').innerText = data.hybrid.tool_name;
        document.getElementById('hybrid-conf').innerText = Math.round(data.hybrid.confidence * 100) + '%';
        document.getElementById('hybrid-speed').innerText = data.hybrid.execution_time_ms.toFixed(1) + ' ms';
        document.getElementById('hybrid-reasoning').innerText = data.hybrid.reasoning;

    } catch (e) {
        alert('Error benchmarking intent methods');
    }
}

// Dataset Evaluator Execution
async function executeFullEvaluation() {
    const tbody = document.getElementById('eval-table-body');
    tbody.innerHTML = `<tr><td colspan="7" class="loading-td"><i class="fa-solid fa-spinner fa-spin"></i> Running full dataset evaluation benchmark...</td></tr>`;

    try {
        const response = await fetch('/api/evaluate?method=hybrid');
        const data = await response.json();

        document.getElementById('stat-cases').innerText = data.total_cases;
        document.getElementById('stat-intent-acc').innerText = data.intent_accuracy + '%';
        document.getElementById('stat-tool-acc').innerText = data.tool_accuracy + '%';
        document.getElementById('stat-latency').innerText = data.avg_latency_ms + ' ms';
        document.getElementById('stat-quality').innerText = data.avg_quality_score + ' / 1.0';

        tbody.innerHTML = '';
        data.test_results.forEach(res => {
            const tr = document.createElement('tr');
            const matchBadge = res.intent_correct ?
                `<span class="badge" style="background:rgba(16,185,129,0.2);color:#34d399;">PASSED</span>` :
                `<span class="badge" style="background:rgba(239,68,68,0.2);color:#f87171;">FAILED</span>`;

            tr.innerHTML = `
                <td><strong>${res.test_id}</strong></td>
                <td><span class="badge">${res.category}</span></td>
                <td>${res.query}</td>
                <td><code>${res.expected_tool}</code></td>
                <td><code>${res.detected_tool}</code></td>
                <td>${matchBadge}</td>
                <td>${res.latency_ms} ms</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading-td" style="color:#f87171">Error running dataset evaluation</td></tr>`;
    }
}

// RAG Search Execution
async function executeRAGSearch() {
    const query = document.getElementById('rag-query-input').value.trim();
    if (!query) return;

    const container = document.getElementById('rag-results-container');
    container.innerHTML = `<p style="color:var(--text-muted)">Searching vectors...</p>`;

    try {
        const res = await fetch(`/api/rag/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        container.innerHTML = `
            <div class="rag-card" style="border-color:var(--primary)">
                <h4>AI Synthesized Answer</h4>
                <p style="white-space:pre-wrap;color:#fff">${data.answer}</p>
            </div>
            <h4 style="margin-top:12px;font-family:var(--font-heading)">Retrieved Context Source Chunks:</h4>
        `;

        if (data.sources && data.sources.length > 0) {
            data.sources.forEach(src => {
                const card = document.createElement('div');
                card.className = 'rag-card';
                card.innerHTML = `
                    <h4>${src.title} <span class="badge">${src.category}</span> <span class="badge confidence">Score: ${src.relevance_score}</span></h4>
                    <p>${src.content}</p>
                `;
                container.appendChild(card);
            });
        }
    } catch (e) {
        container.innerHTML = `<p style="color:#f87171">Error performing RAG search</p>`;
    }
}

// Load Registered Tools
async function loadToolsRegistry() {
    const grid = document.getElementById('tools-grid');
    if (!grid) return;

    try {
        const res = await fetch('/api/tools');
        const data = await res.json();

        grid.innerHTML = '';
        data.tools.forEach(tool => {
            const card = document.createElement('div');
            card.className = 'tool-card';
            const paramsHTML = tool.parameters.map(p => `<span class="param-pill">${p}</span>`).join('');

            card.innerHTML = `
                <h3>${tool.name}()</h3>
                <p>${tool.description}</p>
                <div>${paramsHTML}</div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = `<p style="color:var(--text-muted)">Failed to load tools registry.</p>`;
    }
}
