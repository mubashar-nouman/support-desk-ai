/* Support Desk AI - single-screen workspace.
   Upload a document and it opens side by side with the assistant. */

const $ = sel => document.querySelector(sel);

const uploadView = $('#upload-view');
const workspace = $('#workspace');
const overlay = $('#overlay');
const addDoc = $('#add-doc');
const overlayClose = $('#overlay-close');
const docStatus = $('#doc-status');
const docCount = $('#doc-count');

const docSelect = $('#doc-select');
const docBody = $('#doc-body');
const docMeta = $('#doc-meta');
const docSearch = $('#doc-search');
const findCount = $('#find-count');
const findPrev = $('#find-prev');
const findNext = $('#find-next');
const divider = $('#divider');

const form = $('#chat-form');
const input = $('#message');
const sendButton = form.querySelector('button');
const messages = $('#messages');
const suggestions = $('#suggestions');
const clear = $('#clear');

const SUPPORTED = ['.txt', '.md', '.csv', '.json', '.log', '.pdf'];
const kb = bytes => `${Math.max(1, Math.ceil(bytes / 1024))} KB`;
const extOf = name => name.slice(name.lastIndexOf('.')).toLowerCase();

let docText = '';
let matches = [];
let activeMatch = 0;

// ===============================================================
// Boot
// ===============================================================
async function boot() {
  let data = { ready: false, files: [] };
  try {
    data = await (await fetch('/knowledge/status')).json();
  } catch {
    // Server unreachable - fall through to the upload screen.
  }

  if (!data.files.length) {
    uploadView.hidden = false;
    workspace.hidden = true;
    docStatus.hidden = true;
    addDoc.hidden = true;
    return;
  }

  uploadView.hidden = true;
  workspace.hidden = false;
  docStatus.hidden = false;
  addDoc.hidden = false;
  docCount.textContent = `${data.files.length} document${data.files.length === 1 ? '' : 's'}`;

  docSelect.innerHTML = data.files
    .map(f => `<option value="${encodeURIComponent(f)}">${f}</option>`).join('');

  const remembered = sessionStorage.getItem('activeDoc');
  const target = remembered && data.files.includes(remembered) ? remembered : data.files[0];
  docSelect.value = encodeURIComponent(target);

  if (!messages.children.length) resetChat(target);
  await loadDocument(docSelect.value);
  restoreSplit();
}

// ===============================================================
// Document viewer
// ===============================================================
async function loadDocument(encodedName) {
  docBody.innerHTML = '<span class="doc-placeholder">Loading document…</span>';
  docMeta.textContent = '';
  try {
    const response = await fetch(`/knowledge/document/${encodedName}`);
    if (!response.ok) throw new Error('Could not load document');
    const doc = await response.json();
    docText = doc.content;
    sessionStorage.setItem('activeDoc', doc.filename);
    renderDocument();
    const words = docText.trim() ? docText.trim().split(/\s+/).length : 0;
    docMeta.innerHTML = `<span>${doc.size_kb} KB</span><span>${words.toLocaleString()} words</span>` +
      `<span>${doc.characters.toLocaleString()} characters</span>`;
    buildSuggestions();
  } catch {
    docText = '';
    docBody.innerHTML = '<span class="doc-placeholder">This document could not be loaded.</span>';
    docMeta.textContent = '';
  }
}

// Render document text, wrapping search hits in <mark>. Content is inserted as
// text nodes so it can never be interpreted as HTML.
function renderDocument() {
  const query = docSearch.value.trim();
  matches = [];

  if (!docText) {
    docBody.innerHTML = '<span class="doc-placeholder">This document is empty.</span>';
    return updateFindUI();
  }
  if (!query) {
    docBody.textContent = docText;
    return updateFindUI();
  }

  const fragment = document.createDocumentFragment();
  const needle = query.toLowerCase();
  const haystack = docText.toLowerCase();
  let cursor = 0;

  for (let at = haystack.indexOf(needle); at !== -1; at = haystack.indexOf(needle, cursor)) {
    fragment.append(docText.slice(cursor, at));
    const mark = document.createElement('mark');
    mark.textContent = docText.slice(at, at + query.length);
    fragment.append(mark);
    matches.push(mark);
    cursor = at + query.length;
  }
  fragment.append(docText.slice(cursor));

  docBody.replaceChildren(fragment);
  if (activeMatch >= matches.length) activeMatch = 0;
  focusMatch(false);
  updateFindUI();
}

function focusMatch(scroll = true) {
  matches.forEach(m => m.classList.remove('active'));
  const current = matches[activeMatch];
  if (!current) return;
  current.classList.add('active');
  if (scroll) current.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

function updateFindUI() {
  const active = docSearch.value.trim().length > 0;
  findCount.textContent = active ? (matches.length ? `${activeMatch + 1}/${matches.length}` : '0') : '';
  findPrev.disabled = findNext.disabled = matches.length < 2;
}

function step(delta) {
  if (!matches.length) return;
  activeMatch = (activeMatch + delta + matches.length) % matches.length;
  focusMatch();
  updateFindUI();
}

docSelect.addEventListener('change', async () => {
  docSearch.value = '';
  activeMatch = 0;
  const name = decodeURIComponent(docSelect.value);
  await loadDocument(docSelect.value);
  if (messages.children.length) {
    const note = document.createElement('div');
    note.className = 'context-note';
    note.textContent = `Now reading ${name}`;
    messages.append(note);
    messages.scrollTop = messages.scrollHeight;
  } else {
    resetChat(name);
  }
});

let searchTimer;
docSearch.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { activeMatch = 0; renderDocument(); }, 120);
});
docSearch.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); step(e.shiftKey ? -1 : 1); }
  if (e.key === 'Escape') { docSearch.value = ''; renderDocument(); }
});
findNext.addEventListener('click', () => step(1));
findPrev.addEventListener('click', () => step(-1));

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'f' && !workspace.hidden) {
    e.preventDefault();
    docSearch.focus();
    docSearch.select();
  }
  if (e.key === 'Escape' && !overlay.hidden) closeOverlay();
});

// ===============================================================
// Divider
// ===============================================================
const MIN_RATIO = 0.2, MAX_RATIO = 0.8;

function applySplit(ratio) {
  const clamped = Math.min(MAX_RATIO, Math.max(MIN_RATIO, ratio));
  workspace.style.setProperty('--split', `${clamped * 100}%`);
  localStorage.setItem('splitRatio', String(clamped));
}
function restoreSplit() {
  const saved = parseFloat(localStorage.getItem('splitRatio'));
  if (saved) applySplit(saved);
}

divider.addEventListener('pointerdown', e => {
  if (window.matchMedia('(max-width: 900px)').matches) return;
  e.preventDefault();
  divider.setPointerCapture(e.pointerId);
  divider.classList.add('dragging');
  document.body.classList.add('resizing');

  const rect = workspace.getBoundingClientRect();
  const onMove = ev => applySplit((ev.clientX - rect.left) / rect.width);
  const onUp = () => {
    divider.classList.remove('dragging');
    document.body.classList.remove('resizing');
    divider.removeEventListener('pointermove', onMove);
    divider.removeEventListener('pointerup', onUp);
  };
  divider.addEventListener('pointermove', onMove);
  divider.addEventListener('pointerup', onUp);
});
divider.addEventListener('dblclick', () => applySplit(0.5));
divider.addEventListener('keydown', e => {
  const current = parseFloat(localStorage.getItem('splitRatio')) || 0.5;
  if (e.key === 'ArrowLeft') { e.preventDefault(); applySplit(current - 0.02); }
  if (e.key === 'ArrowRight') { e.preventDefault(); applySplit(current + 0.02); }
  if (e.key === 'Home') { e.preventDefault(); applySplit(0.5); }
});

// ===============================================================
// Chat
// ===============================================================
function resetChat(filename) {
  const name = filename || decodeURIComponent(docSelect.value || '');
  messages.innerHTML = '';
  const welcome = document.createElement('div');
  welcome.className = 'welcome';
  welcome.innerHTML = '<div class="avatar">✦</div><div><strong>Ready when you are.</strong>' +
    '<p></p></div>';
  welcome.querySelector('p').textContent = name
    ? `Ask me anything about ${name} and I'll answer from what's in it.`
    : "Ask me anything about your document and I'll answer from what's in it.";
  messages.append(welcome);
}

// Offer a few openers drawn from the document's own headings.
function buildSuggestions() {
  suggestions.innerHTML = '';
  if (!docText) return;
  const headings = docText
    .split(/\n\s*\n/)
    .map(block => block.trim().split('\n')[0].trim())
    .filter(line => line && line.length < 60 && !/^\[Page \d+\]$/.test(line) && /[a-zA-Z]/.test(line))
    .slice(0, 6);

  const seen = new Set();
  headings.filter(h => !seen.has(h.toLowerCase()) && seen.add(h.toLowerCase()))
    .slice(0, 3)
    .forEach(heading => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.textContent = `What does this say about ${heading.replace(/[:.]+$/, '')}?`;
      chip.addEventListener('click', () => { input.value = chip.textContent; form.requestSubmit(); });
      suggestions.append(chip);
    });
}

function addMessage(text, user = false) {
  const el = document.createElement('div');
  el.className = 'bubble ' + (user ? 'user' : '');
  el.innerHTML = `${user ? '' : '<div class="avatar">✦</div>'}<div class="body"></div>`;
  el.querySelector('.body').textContent = text;
  messages.append(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || sendButton.disabled) return;

  addMessage(text, true);
  input.value = '';
  input.style.height = 'auto';
  sendButton.disabled = true;
  suggestions.innerHTML = '';

  const pending = addMessage('Thinking…');
  pending.classList.add('pending');

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, active_file: sessionStorage.getItem('activeDoc') }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed');
    pending.classList.remove('pending');
    pending.querySelector('.body').textContent = data.content;
  } catch (err) {
    pending.classList.remove('pending');
    pending.classList.add('error');
    pending.querySelector('.body').textContent =
      err.message || 'Sorry, I could not reach the assistant. Please try again.';
  } finally {
    sendButton.disabled = false;
    messages.scrollTop = messages.scrollHeight;
    input.focus();
  }
});

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 150) + 'px';
});
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
});
clear.addEventListener('click', () => { resetChat(); buildSuggestions(); input.focus(); });

// ===============================================================
// Uploading - shared by the upload screen and the overlay
// ===============================================================
function wireUploader({ zone, picker, list, button, status, onDone }) {
  let selected = [];

  const render = () => {
    list.innerHTML = selected.map((f, i) => `
      <div class="file-row">
        <span class="file-icon"></span>
        <span class="file-name"></span>
        <small>${kb(f.size)}</small>
        <button class="row-remove" data-index="${i}" aria-label="Remove">✕</button>
      </div>`).join('');
    // Set names as text so a crafted filename cannot inject markup.
    list.querySelectorAll('.file-name').forEach((el, i) => { el.textContent = selected[i].name; });
    list.querySelectorAll('.file-icon').forEach((el, i) => {
      el.textContent = extOf(selected[i].name).slice(1, 4).toUpperCase();
    });
    button.disabled = !selected.length;
    button.textContent = selected.length
      ? `Upload and open ${selected.length} file${selected.length === 1 ? '' : 's'}`
      : 'Upload and open';
  };

  list.addEventListener('click', e => {
    const remove = e.target.closest('.row-remove');
    if (!remove) return;
    selected.splice(Number(remove.dataset.index), 1);
    render();
  });

  picker.addEventListener('change', () => {
    selected = [...picker.files].filter(f => SUPPORTED.includes(extOf(f.name)));
    status.textContent = '';
    status.className = 'upload-status';
    render();
  });

  ['dragenter', 'dragover'].forEach(t =>
    zone.addEventListener(t, e => { e.preventDefault(); zone.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach(t =>
    zone.addEventListener(t, e => { e.preventDefault(); zone.classList.remove('dragover'); }));
  zone.addEventListener('drop', e => {
    const dropped = [...e.dataTransfer.files].filter(f => SUPPORTED.includes(extOf(f.name)));
    if (!dropped.length) {
      status.textContent = 'Unsupported file type. Use TXT, MD, CSV, JSON, LOG, or PDF.';
      status.className = 'upload-status error';
      return;
    }
    selected = dropped;
    status.textContent = '';
    status.className = 'upload-status';
    render();
  });

  button.addEventListener('click', async () => {
    button.disabled = true;
    status.className = 'upload-status';
    let last = null;

    for (const [i, file] of selected.entries()) {
      status.textContent = `Indexing ${file.name} (${i + 1} of ${selected.length})…`;
      const body = new FormData();
      body.append('file', file);
      try {
        const response = await fetch('/knowledge/upload', { method: 'POST', body });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Upload failed');
        last = data.filename;
      } catch (err) {
        status.textContent = err.message;
        status.className = 'upload-status error';
        button.disabled = false;
        return;
      }
    }

    status.textContent = 'Opening your workspace…';
    status.className = 'upload-status success';
    selected = [];
    picker.value = '';
    render();
    // Open the document that was just uploaded.
    if (last) sessionStorage.setItem('activeDoc', last);
    await onDone(last);
    status.textContent = '';
  });

  return { render };
}

// Upload screen -> straight into the workspace
wireUploader({
  zone: $('#dropzone'), picker: $('#files'), list: $('#file-list'),
  button: $('#upload'), status: $('#status'),
  onDone: async name => { resetChat(name); await boot(); },
});

// Overlay -> add more documents without leaving the workspace
wireUploader({
  zone: $('#dropzone2'), picker: $('#files2'), list: $('#file-list2'),
  button: $('#upload2'), status: $('#status2'),
  onDone: async () => { closeOverlay(); await boot(); },
});

// ===============================================================
// Overlay
// ===============================================================
async function openOverlay() {
  overlay.hidden = false;
  const sheetDocs = $('#sheet-docs');
  sheetDocs.innerHTML = '';
  try {
    const data = await (await fetch('/knowledge/status')).json();
    if (!data.files.length) return;
    const head = document.createElement('div');
    head.className = 'existing-head';
    head.textContent = 'IN YOUR KNOWLEDGE BASE';
    sheetDocs.append(head);

    const box = document.createElement('div');
    box.className = 'file-list-box';
    sheetDocs.append(box);

    data.files.forEach(name => {
      const row = document.createElement('div');
      row.className = 'file-row';
      row.innerHTML = '<span class="file-icon"></span><span class="file-name"></span>' +
        '<button class="row-open">Open</button><button class="row-remove" aria-label="Remove">✕</button>';
      row.querySelector('.file-name').textContent = name;
      row.querySelector('.file-icon').textContent = extOf(name).slice(1, 4).toUpperCase();

      row.querySelector('.row-open').addEventListener('click', async () => {
        sessionStorage.setItem('activeDoc', name);
        closeOverlay();
        await boot();
      });

      row.querySelector('.row-remove').addEventListener('click', async e => {
        e.target.disabled = true;
        try {
          const res = await fetch(`/knowledge/document/${encodeURIComponent(name)}`, { method: 'DELETE' });
          if (!res.ok) throw new Error();
          if (sessionStorage.getItem('activeDoc') === name) sessionStorage.removeItem('activeDoc');
          messages.innerHTML = '';
          await openOverlay();
          await boot();
          if (workspace.hidden) closeOverlay();
        } catch {
          e.target.disabled = false;
        }
      });

      box.append(row);
    });
  } catch {
    // Leave the list empty when the status call fails.
  }
}
function closeOverlay() { overlay.hidden = true; }

addDoc.addEventListener('click', openOverlay);
overlayClose.addEventListener('click', closeOverlay);
overlay.addEventListener('click', e => { if (e.target === overlay) closeOverlay(); });

boot();
