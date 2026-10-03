// ==UserScript==
// @name         MKE ChatGPT Auto-Wake
// @namespace    mke-datn
// @version      1.0.0
// @description  Wake the current ChatGPT conversation when a new MKE Bridge task reaches a terminal state.
// @match        https://chatgpt.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const ENDPOINT = 'http://127.0.0.1:8765/api/tasks/list';
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
    const el = document.querySelector('#prompt-textarea, textarea, div[contenteditable="true"]');
    if (!el) return false;
    el.focus();

    if (el.tagName === 'TEXTAREA') {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      if (setter) setter.call(el, text);
      else el.value = text;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return true;
    }

    try {
      document.execCommand('selectAll', false, null);
      document.execCommand('insertText', false, text);
    } catch {
      el.textContent = text;
    }
    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
    return true;
  }

  async function sendMessage(text) {
    for (let i = 0; i < 60; i++) {
      if (setEditorText(text)) {
        await new Promise(r => setTimeout(r, 400));
        const btn = document.querySelector(
          'button[data-testid="send-button"], button[aria-label="Send prompt"], button[aria-label="Gửi lời nhắc"]'
        );
        if (btn && !btn.disabled) {
          btn.click();
          return true;
        }
      }
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
  setInterval(tick, POLL_MS);
  tick();
})();
