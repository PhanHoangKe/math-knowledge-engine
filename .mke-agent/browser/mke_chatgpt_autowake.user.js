// ==UserScript==
// @name         MKE ChatGPT Auto-Wake
// @namespace    mke-datn
// @version      1.2.0
// @description  Wake the current ChatGPT conversation when a new MKE Bridge task reaches a terminal state.
// @match        https://chatgpt.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @connect      127.0.0.1
// @updateURL    http://127.0.0.1:8765/api/browser/autowake.user.js
// @downloadURL  http://127.0.0.1:8765/api/browser/autowake.user.js
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const ENDPOINT = 'http://127.0.0.1:8765/api/tasks/list';
  const DIAG_ENDPOINT = 'http://127.0.0.1:8765/api/browser-diagnostics';
  const POLL_MS = 5000;
  const TERMINAL = new Set(['SUCCESS', 'FAILED', 'CANCELLED']);
  const KEY = 'mke_autowake_handled_v1';

  function loadHandled() {
    try {
      const raw = GM_getValue(KEY, '[]');
      return new Set(JSON.parse(raw));
    } catch {
      return new Set();
    }
  }

  function saveHandled(set) {
    GM_setValue(KEY, JSON.stringify(Array.from(set).slice(-200)));
  }

  function taskKey(t) {
    return [t.task_id || '', t.status || '', t.finished_at || '', t.commit_sha || ''].join('|');
  }

  function requestTasks() {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url: ENDPOINT,
        timeout: 5000,
        onload: r => {
          if (r.status < 200 || r.status >= 300) return reject(new Error('HTTP ' + r.status));
          try { resolve(JSON.parse(r.responseText)); } catch (e) { reject(e); }
        },
        onerror: reject,
        ontimeout: () => reject(new Error('timeout'))
      });
    });
  }

  function setEditorText(text) {
    const el = getEditor();
    if (!el) return false;
    el.focus();

    if (el.tagName === 'TEXTAREA') {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      if (setter) setter.call(el, text);
      else el.value = text;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    try {
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      const ok = document.execCommand('insertText', false, text);
      if (!ok) {
        el.textContent = text;
        el.dispatchEvent(new InputEvent('input', {
          bubbles: true,
          inputType: 'insertText',
          data: text
        }));
      }
    } catch {
      el.textContent = text;
      el.dispatchEvent(new InputEvent('input', {
        bubbles: true,
        inputType: 'insertText',
        data: text
      }));
    }
    return editorText(el).trim().length > 0;
  }

  function getEditor() {
    return document.querySelector(
      '#prompt-textarea, textarea, div.ProseMirror[contenteditable="true"], div[contenteditable="true"]'
    );
  }

  function editorText(el) {
    if (!el) return '';
    return el.tagName === 'TEXTAREA' ? (el.value || '') : (el.innerText || el.textContent || '');
  }

  async function waitComposerCleared(originalText, timeoutMs = 5000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const el = getEditor();
      const current = editorText(el).trim();
      if (!current || current !== originalText.trim()) return true;
      await new Promise(r => setTimeout(r, 150));
    }
    return false;
  }

  function postDiagnostics(reason) {
    try {
      const editor = getEditor();
      const form = editor?.closest('form') || null;
      const buttons = Array.from((form || document).querySelectorAll('button')).slice(-40).map((b, idx) => ({
        idx,
        aria: b.getAttribute('aria-label'),
        testid: b.getAttribute('data-testid'),
        type: b.getAttribute('type'),
        disabled: !!b.disabled,
        text: (b.innerText || b.textContent || '').trim().slice(0, 120),
        className: String(b.className || '').slice(0, 300)
      }));
      const payload = {
        reason,
        href: location.href,
        ts: new Date().toISOString(),
        editor: editor ? {
          tag: editor.tagName,
          id: editor.id,
          className: String(editor.className || '').slice(0, 300),
          contenteditable: editor.getAttribute('contenteditable'),
          textLength: editorText(editor).length,
          aria: editor.getAttribute('aria-label')
        } : null,
        form: form ? {
          className: String(form.className || '').slice(0, 300),
          action: form.getAttribute('action'),
          method: form.getAttribute('method')
        } : null,
        activeElement: document.activeElement ? {
          tag: document.activeElement.tagName,
          id: document.activeElement.id,
          aria: document.activeElement.getAttribute?.('aria-label') || null
        } : null,
        buttons
      };
      GM_xmlhttpRequest({
        method: 'POST',
        url: DIAG_ENDPOINT,
        data: JSON.stringify(payload),
        headers: { 'Content-Type': 'application/json' },
        timeout: 3000
      });
    } catch (e) {
      console.debug('[MKE AUTO-WAKE] diagnostics failed', e);
    }
  }

  function findSendButton(editor) {
    const selectors = [
      'button[data-testid="send-button"]',
      'button[data-testid="composer-submit-button"]',
      'button[aria-label="Send message"]',
      'button[aria-label="Send prompt"]',
      'button[aria-label="Send"]',
      'button[aria-label="Gửi tin nhắn"]',
      'button[aria-label="Gửi lời nhắc"]',
      'button[type="submit"]'
    ];
    for (const selector of selectors) {
      const local = editor?.closest('form')?.querySelector(selector);
      if (local && !local.disabled) return local;
      const global = document.querySelector(selector);
      if (global && !global.disabled) return global;
    }
    return null;
  }

  async function trySubmit(text) {
    const editor = getEditor();
    if (!editor) return false;

    postDiagnostics('before-submit');

    const button = findSendButton(editor);
    if (button) {
      try {
        for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup']) {
          button.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
        }
        button.click();
      } catch (_) {
        try { button.click(); } catch (_) {}
      }
      if (await waitComposerCleared(text)) {
        postDiagnostics('submit-button-success');
        return true;
      }
    }

    const form = editor.closest('form');
    if (form && typeof form.requestSubmit === 'function') {
      try {
        form.requestSubmit();
        if (await waitComposerCleared(text)) {
          postDiagnostics('request-submit-success');
          return true;
        }
      } catch (_) {}
    }

    const keyOptions = {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true,
      cancelable: true
    };
    editor.dispatchEvent(new KeyboardEvent('keydown', keyOptions));
    editor.dispatchEvent(new KeyboardEvent('keypress', keyOptions));
    editor.dispatchEvent(new KeyboardEvent('keyup', keyOptions));
    const sent = await waitComposerCleared(text);
    postDiagnostics(sent ? 'enter-success' : 'submit-failed');
    return sent;
  }

  async function sendMessage(text) {
    for (let i = 0; i < 60; i++) {
      const editor = getEditor();
      if (!editor) {
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }

      const current = editorText(editor).trim();
      if (current && current !== text.trim()) {
        // Never overwrite a message the user is currently composing.
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }

      if (!current && !setEditorText(text)) {
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }

      await new Promise(r => setTimeout(r, 500));
      if (await trySubmit(text)) return true;

      console.debug('[MKE AUTO-WAKE] submit attempt failed; retrying');
      await new Promise(r => setTimeout(r, 1000));
    }
    return false;
  }

  function messageFor(t) {
    const commit = t.commit_sha ? ' Commit: ' + t.commit_sha + '.' : '';
    const branch = t.target_branch ? ' Branch: ' + t.target_branch + '.' : '';
    const err = t.error ? ' Error: ' + String(t.error).slice(0, 1200) : '';
    return 'MKE AUTO-WAKE: Anty task ' + t.task_id + ' reached ' + t.status + '.' +
           commit + branch + err +
           ' Independently inspect the Bridge/GitHub state, audit the result, then dispatch the next remediation or milestone without waiting for me.';
  }

  let initialized = false;
  let busy = false;
  const handled = loadHandled();

  async function tick() {
    if (busy) return;
    busy = true;
    try {
      const tasks = await requestTasks();
      if (!Array.isArray(tasks)) return;

      const terminal = tasks.filter(t => TERMINAL.has(t.status));
      terminal.sort((a, b) => String(a.finished_at || '').localeCompare(String(b.finished_at || '')));

      if (!initialized) {
        // Ignore historical terminal tasks that existed before this watcher started.
        for (const t of terminal) handled.add(taskKey(t));
        saveHandled(handled);
        initialized = true;
        console.log('[MKE AUTO-WAKE] armed; historical tasks seeded');
        return;
      }

      for (const t of terminal) {
        const key = taskKey(t);
        if (handled.has(key)) continue;
        const ok = await sendMessage(messageFor(t));
        if (ok) {
          handled.add(key);
          saveHandled(handled);
          console.log('[MKE AUTO-WAKE] sent', t.task_id, t.status);
          break;
        }
      }
    } catch (e) {
      console.debug('[MKE AUTO-WAKE] bridge check failed', e);
    } finally {
      busy = false;
    }
  }

  console.log('[MKE AUTO-WAKE] active');
  postDiagnostics('startup');
  setInterval(() => postDiagnostics('heartbeat'), 15000);
  setInterval(tick, POLL_MS);
  tick();
})();
