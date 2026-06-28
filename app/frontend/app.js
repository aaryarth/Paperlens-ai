/* ─── PaperLens AI – Frontend Application ───────────────────────────────── */

const API = '';  // same origin; set to http://localhost:8000 for dev

/* ──────────────────────────────────────────────────────────────────────────── */
/*  STATE                                                                       */
/* ──────────────────────────────────────────────────────────────────────────── */
const state = {
  documents: [],         // DocumentMeta[]
  selectedDocIds: [],    // for multi-select operations
  mediaRecorder: null,
  audioChunks: [],
  isRecording: false,
  isSpeaking: false,
  currentUtterance: null,
};

/* ──────────────────────────────────────────────────────────────────────────── */
/*  DOM REFS                                                                     */
/* ──────────────────────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const DOM = {
  fileInput:        $('fileInput'),
  uploadZone:       $('uploadZone'),
  uploadProgress:   $('uploadProgress'),
  progressFill:     $('progressFill'),
  progressText:     $('progressText'),
  docList:          $('docList'),
  chatMessages:     $('chatMessages'),
  chatInput:        $('chatInput'),
  btnSend:          $('btnSend'),
  btnVoice:         $('btnVoice'),
  voiceBar:         $('voiceBar'),
  toastContainer:   $('toastContainer'),
  statusDot:        $('statusDot'),
  statusLabel:      $('statusLabel'),
  navTabs:          document.querySelectorAll('.nav-tab'),
  tabPanels:        document.querySelectorAll('.tab-panel'),
};

/* ──────────────────────────────────────────────────────────────────────────── */
/*  INIT                                                                        */
/* ──────────────────────────────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', async () => {
  bindEvents();
  await checkHealth();
  await loadDocuments();
});

function bindEvents() {
  // Nav tabs
  DOM.navTabs.forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  // Upload zone
  DOM.uploadZone.addEventListener('click', () => DOM.fileInput.click());
  DOM.fileInput.addEventListener('change', e => handleFileSelect(e.target.files));

  DOM.uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    DOM.uploadZone.classList.add('drag-over');
  });
  DOM.uploadZone.addEventListener('dragleave', () => DOM.uploadZone.classList.remove('drag-over'));
  DOM.uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    DOM.uploadZone.classList.remove('drag-over');
    handleFileSelect(e.dataTransfer.files);
  });

  // Chat
  DOM.chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  DOM.chatInput.addEventListener('input', () => {
    DOM.chatInput.style.height = 'auto';
    DOM.chatInput.style.height = Math.min(DOM.chatInput.scrollHeight, 120) + 'px';
  });
  DOM.btnSend.addEventListener('click', sendMessage);
  DOM.btnVoice.addEventListener('click', toggleRecording);

  // Analysis forms
  $('btnAskAnalysis').addEventListener('click', runAsk);
  $('btnCompare').addEventListener('click', runCompare);
  $('btnSummary').addEventListener('click', runSummary);
  $('btnGaps').addEventListener('click', runGaps);
  $('btnLitReview').addEventListener('click', runLitReview);

  // Dashboard refresh
  $('btnRefreshDash').addEventListener('click', loadDashboard);
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  TABS                                                                        */
/* ──────────────────────────────────────────────────────────────────────────── */
function switchTab(tabName) {
  DOM.navTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
  DOM.tabPanels.forEach(p => {
    p.classList.toggle('active', p.dataset.panel === tabName);
  });
  if (tabName === 'dashboard') loadDashboard();
  if (tabName === 'analysis') populateAnalysisDocLists();
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  HEALTH CHECK                                                                */
/* ──────────────────────────────────────────────────────────────────────────── */
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    if (r.ok) {
      const d = await r.json();
      DOM.statusDot.classList.add('online');
      DOM.statusLabel.textContent = `${d.llm_provider} · ${d.embedding_model}`;
    }
  } catch {
    DOM.statusLabel.textContent = 'Server offline';
  }
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  DOCUMENTS                                                                   */
/* ──────────────────────────────────────────────────────────────────────────── */
async function loadDocuments() {
  try {
    const r = await fetch(`${API}/upload/documents`);
    const data = await r.json();
    state.documents = data.documents || [];
    renderDocList();
  } catch (e) {
    console.error('Load documents error:', e);
  }
}

function renderDocList() {
  const container = DOM.docList;
  if (!state.documents.length) {
    container.innerHTML = `<div class="doc-empty">📄 No documents yet.<br>Upload PDFs to get started.</div>`;
    return;
  }

  container.innerHTML = state.documents.map(doc => `
    <div class="doc-item" data-id="${doc.id}" title="${doc.filename}">
      <span class="doc-icon">📄</span>
      <div class="doc-info">
        <div class="doc-name">${escHtml(doc.filename)}</div>
        <div class="doc-meta">${doc.page_count} pages · ${doc.chunk_count} chunks · ${doc.file_size_mb} MB</div>
      </div>
      <button class="doc-delete" onclick="deleteDocument('${doc.id}', event)" title="Delete">🗑</button>
    </div>
  `).join('');
}

async function handleFileSelect(files) {
  if (!files || !files.length) return;
  const pdfs = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
  if (!pdfs.length) { toast('Please select PDF files only.', 'error'); return; }

  const form = new FormData();
  pdfs.forEach(f => form.append('files', f));

  showProgress(true, 'Uploading…');
  try {
    const r = await fetch(`${API}/upload`, { method: 'POST', body: form });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Upload failed');

    const count = Array.isArray(data) ? data.length : 1;
    toast(`✅ Uploaded ${count} document(s) and indexed into vector store!`, 'success');
    await loadDocuments();
    populateAnalysisDocLists();
    DOM.fileInput.value = '';
  } catch (e) {
    toast(`Upload failed: ${e.message}`, 'error');
  } finally {
    showProgress(false);
  }
}

window.deleteDocument = async (docId, e) => {
  e.stopPropagation();
  const doc = state.documents.find(d => d.id === docId);
  if (!confirm(`Delete "${doc?.filename}"?`)) return;

  try {
    const r = await fetch(`${API}/upload/documents/${docId}`, { method: 'DELETE' });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);
    toast(`🗑 ${data.filename} deleted.`, 'info');
    await loadDocuments();
    populateAnalysisDocLists();
  } catch (e) {
    toast(`Delete failed: ${e.message}`, 'error');
  }
};

function showProgress(show, text = '') {
  DOM.uploadProgress.style.display = show ? 'block' : 'none';
  DOM.progressText.textContent = text;
  DOM.progressFill.style.width = show ? '60%' : '0%';
  if (!show) setTimeout(() => { DOM.progressFill.style.width = '0%'; }, 300);
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  CHAT                                                                        */
/* ──────────────────────────────────────────────────────────────────────────── */
async function sendMessage() {
  const question = DOM.chatInput.value.trim();
  if (!question) return;
  if (!state.documents.length) {
    toast('Upload documents first!', 'error');
    return;
  }

  appendMessage('user', question);
  DOM.chatInput.value = '';
  DOM.chatInput.style.height = 'auto';
  DOM.btnSend.disabled = true;

  const typing = appendTyping();

  try {
    const r = await fetch(`${API}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: 5 }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Request failed');

    typing.remove();
    appendMessage('assistant', data.answer, data.citations);
    speakText(data.answer);
  } catch (e) {
    typing.remove();
    appendMessage('assistant', `❌ Error: ${e.message}`);
  } finally {
    DOM.btnSend.disabled = false;
  }
}

function appendMessage(role, text, citations = []) {
  const avatar = role === 'user' ? '👤' : '🔬';
  const formattedText = role === 'assistant' ? formatMarkdown(text) : escHtml(text);

  const citHtml = citations.length ? `
    <div class="citations">
      <div class="citation-label">📚 Sources</div>
      ${citations.map(c => `
        <div class="citation-badge">
          <strong>${escHtml(c.filename)} · p.${c.page}</strong>
          <span>${escHtml(c.excerpt)}</span>
        </div>
      `).join('')}
    </div>
  ` : '';

  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-bubble">
      ${formattedText}
      ${citHtml}
    </div>
  `;
  DOM.chatMessages.appendChild(el);
  DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
  return el;
}

function appendTyping() {
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.innerHTML = `
    <div class="message-avatar">🔬</div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  DOM.chatMessages.appendChild(el);
  DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
  return el;
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  VOICE                                                                       */
/* ──────────────────────────────────────────────────────────────────────────── */
async function toggleRecording() {
  if (state.isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];

    const options = MediaRecorder.isTypeSupported('audio/webm')
      ? { mimeType: 'audio/webm' }
      : {};

    state.mediaRecorder = new MediaRecorder(stream, options);
    state.mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };
    state.mediaRecorder.onstop = processVoiceQuery;
    state.mediaRecorder.start(200);
    state.isRecording = true;

    DOM.btnVoice.classList.add('recording');
    DOM.btnVoice.title = 'Click to stop recording';
    DOM.voiceBar.classList.add('active');
    toast('🎙 Recording… Click mic to stop', 'info');
  } catch (e) {
    toast(`Microphone access denied: ${e.message}`, 'error');
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.isRecording) {
    state.mediaRecorder.stop();
    state.mediaRecorder.stream.getTracks().forEach(t => t.stop());
    state.isRecording = false;
    DOM.btnVoice.classList.remove('recording');
    DOM.btnVoice.title = 'Voice query';
    DOM.voiceBar.classList.remove('active');
  }
}

async function processVoiceQuery() {
  if (!state.audioChunks.length) return;
  if (!state.documents.length) {
    toast('Upload documents first!', 'error');
    return;
  }

  const mimeType = state.audioChunks[0]?.type || 'audio/webm';
  const ext = mimeType.includes('webm') ? '.webm' : mimeType.includes('ogg') ? '.ogg' : '.wav';
  const blob = new Blob(state.audioChunks, { type: mimeType });
  const form = new FormData();
  form.append('audio', blob, `voice_query${ext}`);

  const typing = appendTyping();
  toast('🎙 Processing voice query…', 'info');

  try {
    const r = await fetch(`${API}/voice/voice-query`, { method: 'POST', body: form });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Voice query failed');

    typing.remove();

    // Show transcript + answer in chat
    const el = document.createElement('div');
    el.className = 'message user';
    el.innerHTML = `
      <div class="message-avatar">🎙</div>
      <div class="message-bubble">
        <div class="voice-transcript-label">🎙 Voice Query</div>
        ${escHtml(data.transcript)}
      </div>
    `;
    DOM.chatMessages.appendChild(el);

    appendMessage('assistant', data.answer, data.citations);
    speakText(data.answer);
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
  } catch (e) {
    typing.remove();
    appendMessage('assistant', `❌ Voice error: ${e.message}`);
  }
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  TEXT-TO-SPEECH (Browser Speech Synthesis API)                               */
/* ──────────────────────────────────────────────────────────────────────────── */
function speakText(text) {
  if (!window.speechSynthesis) return;

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  // Truncate for TTS (don't read massive walls of text)
  const ttsText = text.length > 1200 ? text.substring(0, 1200) + '...' : text;

  const utterance = new SpeechSynthesisUtterance(ttsText);
  utterance.rate = 0.95;
  utterance.pitch = 1;
  utterance.volume = 1;

  // Try to find a clear English voice
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Neural') || v.name.includes('Natural'))
  ) || voices.find(v => v.lang.startsWith('en')) || null;

  if (preferred) utterance.voice = preferred;

  state.currentUtterance = utterance;
  state.isSpeaking = true;
  utterance.onend = () => { state.isSpeaking = false; };
  window.speechSynthesis.speak(utterance);
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  ANALYSIS PANEL                                                              */
/* ──────────────────────────────────────────────────────────────────────────── */
function populateAnalysisDocLists() {
  // Compare checkboxes
  const compareList = $('compareDocList');
  const gapList = $('gapDocList');
  const litList = $('litDocList');

  const items = state.documents.map(d => `
    <label class="checkbox-item">
      <input type="checkbox" value="${d.id}" name="compareDoc">
      <span>${escHtml(d.filename)}</span>
    </label>
  `).join('') || '<span style="color:var(--text3);font-size:0.8rem;">No documents uploaded.</span>';

  if (compareList) compareList.innerHTML = items;
  if (gapList) gapList.innerHTML = items.replace(/name="compareDoc"/g, 'name="gapDoc"');
  if (litList) litList.innerHTML = items.replace(/name="compareDoc"/g, 'name="litDoc"');

  // Summary doc select
  const summarySelect = $('summaryDocSelect');
  if (summarySelect) {
    summarySelect.innerHTML = state.documents.length
      ? state.documents.map(d => `<option value="${d.id}">${escHtml(d.filename)}</option>`).join('')
      : '<option value="">No documents</option>';
  }
}

function getCheckedIds(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(el => el.value);
}

async function runAsk() {
  const question = $('analysisQuestion').value.trim();
  if (!question) { toast('Enter a question.', 'error'); return; }
  if (!state.documents.length) { toast('Upload documents first!', 'error'); return; }

  const btn = $('btnAskAnalysis');
  setLoading(btn, true);
  $('askResult').innerHTML = '';

  try {
    const r = await fetch(`${API}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: 5 }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);

    const citHtml = data.citations.map(c =>
      `<div class="citation-badge"><strong>${escHtml(c.filename)} · p.${c.page}</strong><span>${escHtml(c.excerpt)}</span></div>`
    ).join('');

    $('askResult').innerHTML = `
      <div class="result-card">
        <h3>💡 Answer</h3>
        <div class="result-text">${formatMarkdown(data.answer)}</div>
        ${data.citations.length ? `<div class="citations"><div class="citation-label">📚 Sources</div>${citHtml}</div>` : ''}
        <div style="margin-top:10px;font-size:0.72rem;color:var(--text3)">Model: ${data.model_used}</div>
      </div>
    `;
  } catch (e) {
    $('askResult').innerHTML = `<div class="result-card" style="border-color:var(--danger)">❌ ${escHtml(e.message)}</div>`;
  } finally {
    setLoading(btn, false);
  }
}

async function runCompare() {
  const ids = getCheckedIds('compareDoc');
  if (ids.length < 2) { toast('Select at least 2 documents.', 'error'); return; }

  const aspect = $('compareAspect').value;
  const btn = $('btnCompare');
  setLoading(btn, true);
  $('compareResult').innerHTML = '';

  try {
    const r = await fetch(`${API}/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: ids, aspect }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);

    $('compareResult').innerHTML = `
      <div class="result-card">
        <h3>⚖️ Comparison: ${escHtml(data.aspect)}</h3>
        <div class="result-text">${formatMarkdown(data.comparison)}</div>
        <div style="margin-top:10px;font-size:0.72rem;color:var(--text3)">Model: ${data.model_used}</div>
      </div>
    `;
  } catch (e) {
    $('compareResult').innerHTML = `<div class="result-card" style="border-color:var(--danger)">❌ ${escHtml(e.message)}</div>`;
  } finally {
    setLoading(btn, false);
  }
}

async function runSummary() {
  const doc_id = $('summaryDocSelect').value;
  const summary_type = $('summaryType').value;
  if (!doc_id) { toast('Select a document.', 'error'); return; }

  const btn = $('btnSummary');
  setLoading(btn, true);
  $('summaryResult').innerHTML = '';

  try {
    const r = await fetch(`${API}/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: doc_id, summary_type }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);

    $('summaryResult').innerHTML = `
      <div class="result-card">
        <h3>📝 ${escHtml(data.summary_type)} Summary – ${escHtml(data.filename)}</h3>
        <div class="result-text">${formatMarkdown(data.summary)}</div>
        <div style="margin-top:10px;font-size:0.72rem;color:var(--text3)">Model: ${data.model_used}</div>
      </div>
    `;
  } catch (e) {
    $('summaryResult').innerHTML = `<div class="result-card" style="border-color:var(--danger)">❌ ${escHtml(e.message)}</div>`;
  } finally {
    setLoading(btn, false);
  }
}

async function runGaps() {
  const ids = getCheckedIds('gapDoc');
  const btn = $('btnGaps');
  setLoading(btn, true);
  $('gapResult').innerHTML = '';

  try {
    const body = ids.length ? { document_ids: ids } : {};
    const r = await fetch(`${API}/research-gaps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);

    const listHtml = (items) => items.map(i => `<li>${escHtml(i)}</li>`).join('');

    $('gapResult').innerHTML = `
      <div class="result-card">
        <h3>🔍 Research Gap Analysis</h3>
        <div class="gap-grid">
          <div class="gap-card"><h4>🕳 Gaps</h4><ul>${listHtml(data.gaps)}</ul></div>
          <div class="gap-card"><h4>⚠️ Limitations</h4><ul>${listHtml(data.limitations)}</ul></div>
          <div class="gap-card"><h4>🔭 Future Work</h4><ul>${listHtml(data.future_work)}</ul></div>
          <div class="gap-card"><h4>💡 Opportunities</h4><ul>${listHtml(data.opportunities)}</ul></div>
        </div>
        <div class="result-text">${formatMarkdown(data.full_analysis)}</div>
        <div style="margin-top:10px;font-size:0.72rem;color:var(--text3)">Model: ${data.model_used}</div>
      </div>
    `;
  } catch (e) {
    $('gapResult').innerHTML = `<div class="result-card" style="border-color:var(--danger)">❌ ${escHtml(e.message)}</div>`;
  } finally {
    setLoading(btn, false);
  }
}

async function runLitReview() {
  const ids = getCheckedIds('litDoc');
  const focus = $('litFocus').value.trim();
  const btn = $('btnLitReview');
  setLoading(btn, true);
  $('litResult').innerHTML = '';

  try {
    const r = await fetch(`${API}/literature-review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: ids.length ? ids : null, focus_topic: focus || null }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);

    const themes = data.themes.map(t =>
      `<span class="theme-tag">${escHtml(t)}</span>`
    ).join('');

    $('litResult').innerHTML = `
      <div class="result-card">
        <h3>📖 Literature Review</h3>
        ${data.themes.length ? `<div class="theme-tags">${themes}</div>` : ''}
        <div class="result-text">${formatMarkdown(data.review)}</div>
        <div style="margin-top:10px;font-size:0.72rem;color:var(--text3)">Model: ${data.model_used}</div>
      </div>
    `;
  } catch (e) {
    $('litResult').innerHTML = `<div class="result-card" style="border-color:var(--danger)">❌ ${escHtml(e.message)}</div>`;
  } finally {
    setLoading(btn, false);
  }
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  DASHBOARD                                                                   */
/* ──────────────────────────────────────────────────────────────────────────── */
async function loadDashboard() {
  try {
    const r = await fetch(`${API}/dashboard`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail);

    $('statDocs').textContent = data.total_documents;
    $('statChunks').textContent = data.total_chunks;
    $('statEmbed').textContent = data.total_embeddings;
    $('statModel').textContent = data.llm_provider;

    const qHist = $('queryHistoryList');
    qHist.innerHTML = data.query_history.length
      ? data.query_history.map(q => `
          <div class="history-item">
            <div class="history-q">❓ ${escHtml(q.question)}</div>
            <div class="history-a">${escHtml(q.answer_excerpt)}</div>
            <div class="history-meta">${formatDate(q.timestamp)}</div>
          </div>
        `).join('')
      : '<div class="doc-empty">No queries yet.</div>';

    const sHist = $('summaryHistoryList');
    sHist.innerHTML = data.summary_history.length
      ? data.summary_history.map(s => `
          <div class="history-item">
            <div class="history-q">📝 ${escHtml(s.filename)}</div>
            <div class="history-a">Type: ${s.summary_type}</div>
            <div class="history-meta">${formatDate(s.timestamp)}</div>
          </div>
        `).join('')
      : '<div class="doc-empty">No summaries yet.</div>';

  } catch (e) {
    toast(`Dashboard error: ${e.message}`, 'error');
  }
}

/* ──────────────────────────────────────────────────────────────────────────── */
/*  HELPERS                                                                     */
/* ──────────────────────────────────────────────────────────────────────────── */
function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatMarkdown(text) {
  return escHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^#{1,3}\s(.+)$/gm, '<h3>$1</h3>')
    .replace(/^\s*[-•]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function toast(message, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${message}</span>`;
  DOM.toastContainer.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function setLoading(btn, loading) {
  if (loading) {
    btn.dataset.originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';
    btn.disabled = true;
  } else {
    btn.textContent = btn.dataset.originalText || 'Run';
    btn.disabled = false;
  }
}
