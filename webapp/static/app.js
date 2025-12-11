// app.js - Enhanced UI behaviors for Broadcast Studio
(() => {
  'use strict';

  /* ---------- UTILITIES ---------- */
  const $ = (sel) => document.querySelector(sel);
  const $all = (sel) => Array.from(document.querySelectorAll(sel));
  
  // Enhanced toast with icons and better animations
  function toast(message, type = 'success', duration = 3500) {
    const container = document.querySelector('.toast-container') || createToastContainer();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    
    const icons = {
      success: '✓',
      error: '✕',
      info: 'ℹ',
      warning: '⚠'
    };
    
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px">
        <span style="font-size:18px;opacity:0.9">${icons[type] || icons.info}</span>
        <span>${message}</span>
      </div>
    `;
    
    container.appendChild(el);
    
    // Auto-remove with fade out
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(100px) scale(0.9)';
      setTimeout(() => el.remove(), 300);
    }, duration);
    
    // Click to dismiss
    el.addEventListener('click', () => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(100px) scale(0.9)';
      setTimeout(() => el.remove(), 300);
    });
  }

  function createToastContainer() {
    const c = document.createElement('div');
    c.className = 'toast-container';
    document.body.appendChild(c);
    return c;
  }

  function setProgress(el, pct) {
    if (el) el.style.width = Math.min(100, Math.max(0, pct)) + '%';
  }

  // Debounce utility for performance
  function debounce(fn, delay) {
    let timer;
    return function(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // Animate number counting
  function animateNumber(el, start, end, duration = 800) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
        current = end;
        clearInterval(timer);
      }
      el.textContent = Math.round(current).toLocaleString();
    }, 16);
  }

  /* ---------- ENHANCED QUILL EDITOR ---------- */
  const quillEl = $('#editor');
  let quill = null;
  
  if (quillEl) {
    quill = new Quill('#editor', {
      theme: 'snow',
      placeholder: 'Compose your message...',
      modules: {
        toolbar: [
          [{ header: [1, 2, 3, false] }],
          ['bold', 'italic', 'underline', 'strike'],
          [{ color: [] }, { background: [] }],
          ['link', 'image', 'code-block'],
          [{ list: 'ordered' }, { list: 'bullet' }],
          [{ align: [] }],
          ['clean']
        ]
      }
    });

    // Restore draft with error handling
    try {
      const savedHTML = localStorage.getItem('draft_body_html');
      if (savedHTML) {
        quill.root.innerHTML = savedHTML;
        toast('Draft restored', 'info', 2000);
      }
    } catch (e) {
      console.warn('Failed to restore draft:', e);
    }

    // Debounced auto-save
    const autoSave = debounce(() => {
      try {
        localStorage.setItem('draft_body_html', quill.root.innerHTML);
        // Visual feedback for auto-save
        const toolbar = document.querySelector('.ql-toolbar');
        if (toolbar) {
          toolbar.style.borderColor = 'rgba(16,185,129,0.3)';
          setTimeout(() => {
            toolbar.style.borderColor = '';
          }, 300);
        }
      } catch (e) {
        console.error('Auto-save failed:', e);
      }
      updateCharCount();
    }, 500);

    quill.on('text-change', autoSave);

    // Enhanced keyboard shortcuts
    quill.keyboard.addBinding({
      key: 'S',
      ctrlKey: true,
      handler: () => {
        localStorage.setItem('draft_body_html', quill.root.innerHTML);
        toast('Draft saved manually', 'success', 1500);
        return false;
      }
    });
  }

  /* ---------- CHARACTER COUNT ---------- */
  const charCountEl = $('#charCount');
  
  function updateCharCount() {
    let len = 0;
    if (quill) {
      len = quill.getText().trim().length;
    } else {
      const ta = $('#body');
      if (ta) len = ta.value.trim().length;
    }
    
    if (charCountEl) {
      charCountEl.textContent = `${len.toLocaleString()} characters`;
      
      // Color coding for length
      if (len > 5000) {
        charCountEl.style.color = '#ef4444';
      } else if (len > 3000) {
        charCountEl.style.color = '#f59e0b';
      } else {
        charCountEl.style.color = '';
      }
    }
  }

  /* ---------- FORM STATE MANAGEMENT ---------- */
  const subjectEl = $('#subject');
  const concurrencyEl = $('#concurrency');

  // Restore saved values with validation
  if (subjectEl) {
    const savedSubject = localStorage.getItem('draft_subject');
    if (savedSubject) subjectEl.value = savedSubject;
    
    subjectEl.addEventListener('input', debounce(() => {
      localStorage.setItem('draft_subject', subjectEl.value);
    }, 300));
  }

  if (concurrencyEl) {
    const savedConcurrency = localStorage.getItem('draft_concurrency');
    concurrencyEl.value = savedConcurrency || concurrencyEl.value || 10;
    
    concurrencyEl.addEventListener('input', () => {
      let val = parseInt(concurrencyEl.value, 10);
      if (val < 1) val = 1;
      if (val > 100) val = 100;
      concurrencyEl.value = val;
      localStorage.setItem('draft_concurrency', val);
    });
  }

  updateCharCount();

  /* ---------- ENHANCED PREVIEW ---------- */
  const previewBtn = $('#previewBtn');
  
  if (previewBtn) {
    previewBtn.addEventListener('click', () => {
      const subject = subjectEl ? subjectEl.value.trim() : '';
      const bodyHTML = quill ? quill.root.innerHTML : ($('#body') ? $('#body').value : '');
      
      if (!subject) {
        toast('Please enter a subject line', 'warning');
        subjectEl?.focus();
        return;
      }
      
      if (!bodyHTML.trim() || bodyHTML === '<p><br></p>') {
        toast('Please compose a message body', 'warning');
        quill?.focus();
        return;
      }

      showPreviewModal(subject, bodyHTML);
    });
  }

  function showPreviewModal(subject, bodyHTML) {
    const modal = document.createElement('div');
    modal.className = 'preview-modal';
    modal.innerHTML = `
      <div class="preview-backdrop"></div>
      <div class="preview-card card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px">
          <div>
            <h3 style="margin:0;font-size:18px">Email Preview</h3>
            <p style="margin:4px 0 0 0;color:var(--muted);font-size:13px">How your email will appear to recipients</p>
          </div>
          <button id="closePreview" class="btn btn-outline" style="padding:8px 16px">
            <span style="font-size:18px">×</span>
          </button>
        </div>
        
        <div style="padding:20px;border-radius:12px;background:linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));border:1px solid rgba(255,255,255,0.06);box-shadow:0 4px 20px rgba(0,0,0,0.3)">
          <div style="border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:14px;margin-bottom:14px">
            <div style="font-size:13px;color:var(--muted);margin-bottom:8px">
              <strong>To:</strong> ${(window.totalRecipients || 0).toLocaleString()} recipients
            </div>
            <h2 style="margin:0;font-size:22px;color:#fff">${escapeHtml(subject)}</h2>
          </div>
          <div class="preview-body" style="line-height:1.7;color:#e6eef8">${bodyHTML}</div>
        </div>
        
        <div style="margin-top:16px;padding:12px;border-radius:8px;background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.1)">
          <small style="color:var(--muted);display:flex;align-items:center;gap:8px">
            <span style="font-size:16px">ℹ</span>
            <span>This is a preview. Actual emails may render slightly differently based on email clients.</span>
          </small>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Animate modal entrance
    requestAnimationFrame(() => {
      modal.style.opacity = '1';
    });
    
    // Close handlers
    const closeBtn = $('#closePreview');
    const backdrop = modal.querySelector('.preview-backdrop');
    
    const closeModal = () => {
      modal.style.opacity = '0';
      setTimeout(() => modal.remove(), 300);
    };
    
    closeBtn.addEventListener('click', closeModal);
    backdrop.addEventListener('click', closeModal);
    
    // ESC key to close
    const escHandler = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', escHandler);
      }
    };
    document.addEventListener('keydown', escHandler);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- ENHANCED BROADCAST SENDING ---------- */
  const composeForm = $('#composeForm');
  
  if (composeForm) {
    composeForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const subject = subjectEl ? subjectEl.value.trim() : '';
      const bodyHTML = quill ? quill.root.innerHTML : ($('#body') ? $('#body').value : '');
      const concurrency = concurrencyEl ? parseInt(concurrencyEl.value, 10) : 10;

      // Enhanced validation
      if (!subject) {
        toast('Subject line is required', 'error');
        subjectEl?.focus();
        return;
      }
      
      if (!bodyHTML.trim() || bodyHTML === '<p><br></p>') {
        toast('Message body cannot be empty', 'error');
        quill?.focus();
        return;
      }
      
      if (!window.totalRecipients || window.totalRecipients === 0) {
        toast('No recipients configured. Please add recipients first.', 'error');
        return;
      }

      // Confirmation dialog
      const confirmed = await showConfirmDialog(
        'Send Broadcast',
        `You are about to send this email to <strong>${window.totalRecipients.toLocaleString()}</strong> recipients. This action cannot be undone.`,
        'Send Now',
        'Cancel'
      );
      
      if (!confirmed) return;

      // Disable form
      const submitBtn = composeForm.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';
      }

      // Show progress panel
      const progressPanel = createProgressPanel(window.totalRecipients);
      document.body.appendChild(progressPanel);

      const progressBar = progressPanel.querySelector('#broadcastProgress');
      const sentCountEl = progressPanel.querySelector('#sentCount');
      const statusTextEl = progressPanel.querySelector('#statusText');

      try {
        const payload = { subject, body: bodyHTML, concurrency };

        const resp = await fetch('/compose', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || 'Server error occurred');
        }

        const data = await resp.json();

        if (data.job_id) {
          // Poll for progress
          await pollJobProgress(data.job_id, data.total || window.totalRecipients, 
            progressBar, sentCountEl, statusTextEl);
          
          // Clear draft on success
          localStorage.removeItem('draft_body_html');
          localStorage.removeItem('draft_subject');
          if (quill) quill.setText('');
          if (subjectEl) subjectEl.value = '';
          
          toast('Broadcast completed successfully! 🎉', 'success', 4000);
        } else {
          // Immediate completion
          const total = data.total || window.totalRecipients;
          setProgress(progressBar, 100);
          animateNumber(sentCountEl, 0, total);
          if (statusTextEl) statusTextEl.textContent = 'Complete';
          toast(`Broadcast sent to ${total.toLocaleString()} recipients`, 'success');
        }

        setTimeout(() => progressPanel.remove(), 2000);

      } catch (err) {
        console.error('Broadcast error:', err);
        toast(`Failed to send: ${err.message}`, 'error', 6000);
        progressPanel.remove();
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Send Broadcast';
        }
      }
    });
  }

  function createProgressPanel(total) {
    const panel = document.createElement('div');
    panel.className = 'card';
    panel.style.cssText = 'position:fixed;bottom:24px;right:24px;width:380px;z-index:1000;animation:modal-slide-up 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
    panel.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div>
          <strong style="font-size:16px">Sending Broadcast</strong>
          <div style="color:var(--muted);font-size:12px;margin-top:4px" id="statusText">In progress...</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:24px;font-weight:800;color:#fff">
            <span id="sentCount">0</span>
          </div>
          <div style="font-size:12px;color:var(--muted)">of ${total.toLocaleString()}</div>
        </div>
      </div>
      <div class="progress-wrap">
        <div class="progress-bar" id="broadcastProgress" style="width:0"></div>
      </div>
    `;
    return panel;
  }

  async function pollJobProgress(jobId, total, progressBar, sentCountEl, statusTextEl) {
    const pollUrl = `/compose/status/${jobId}`;
    let lastDone = 0;
    
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const resp = await fetch(pollUrl);
          if (!resp.ok) throw new Error('Status check failed');
          
          const status = await resp.json();
          const done = status.done || 0;
          const pct = Math.round((done / total) * 100);
          
          setProgress(progressBar, pct);
          animateNumber(sentCountEl, lastDone, done, 400);
          lastDone = done;
          
          if (status.complete) {
            clearInterval(interval);
            if (statusTextEl) statusTextEl.textContent = 'Complete ✓';
            resolve();
          }
        } catch (err) {
          clearInterval(interval);
          reject(err);
        }
      }, 1000);
      
      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(interval);
        reject(new Error('Progress polling timeout'));
      }, 300000);
    });
  }

  /* ---------- CONFIRMATION DIALOG ---------- */
  function showConfirmDialog(title, message, confirmText = 'Confirm', cancelText = 'Cancel') {
    return new Promise((resolve) => {
      const modal = document.createElement('div');
      modal.className = 'preview-modal';
      modal.innerHTML = `
        <div class="preview-backdrop"></div>
        <div class="preview-card card" style="max-width:480px">
          <h3 style="margin:0 0 12px 0;font-size:20px">${title}</h3>
          <p style="margin:0 0 20px 0;color:var(--muted);line-height:1.6">${message}</p>
          <div style="display:flex;gap:12px;justify-content:flex-end">
            <button id="cancelBtn" class="btn btn-outline">${cancelText}</button>
            <button id="confirmBtn" class="btn btn-primary">${confirmText}</button>
          </div>
        </div>
      `;
      
      document.body.appendChild(modal);
      
      const close = (result) => {
        modal.style.opacity = '0';
        setTimeout(() => modal.remove(), 200);
        resolve(result);
      };
      
      $('#cancelBtn').addEventListener('click', () => close(false));
      $('#confirmBtn').addEventListener('click', () => close(true));
      modal.querySelector('.preview-backdrop').addEventListener('click', () => close(false));
    });
  }

  /* ---------- ENHANCED CSV HANDLING ---------- */
  const dropArea = $('#csvDropArea');
  
  if (dropArea) {
    // Drag and drop styling
    ['dragenter', 'dragover'].forEach(evt => {
      dropArea.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropArea.style.borderColor = 'rgba(99,102,241,0.6)';
        dropArea.style.background = 'linear-gradient(180deg, rgba(99,102,241,0.1), rgba(6,182,212,0.05))';
      });
    });

    ['dragleave', 'drop'].forEach(evt => {
      dropArea.addEventListener(evt, () => {
        dropArea.style.borderColor = '';
        dropArea.style.background = '';
      });
    });

    dropArea.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const file = e.dataTransfer.files[0];
      handleCSV(file);
    });

    const csvInput = $('#csvFileInput');
    if (csvInput) {
      csvInput.addEventListener('change', (e) => {
        handleCSV(e.target.files[0]);
      });
    }
  }

  function handleCSV(file) {
    if (!file) {
      toast('No file selected', 'error');
      return;
    }
    
    if (!file.name.match(/\.(csv|txt)$/i)) {
      toast('Please upload a CSV or TXT file', 'error');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast('File too large. Maximum 10MB allowed.', 'error');
      return;
    }

    // Show loading indicator
    const loadingToast = toast('Processing CSV file...', 'info', 30000);

    Papa.parse(file, {
      header: false,
      skipEmptyLines: true,
      complete: (results) => {
        const emails = results.data
          .flat()
          .map(r => String(r).trim())
          .filter(email => {
            // Basic email validation
            return email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
          });
        
        const unique = Array.from(new Set(emails));
        
        if (unique.length === 0) {
          toast('No valid email addresses found in file', 'error');
          return;
        }
        
        const duplicates = emails.length - unique.length;
        if (duplicates > 0) {
          toast(`Removed ${duplicates} duplicate email(s)`, 'info', 3000);
        }
        
        showCSVPreview(unique);
      },
      error: (err) => {
        console.error('CSV parse error:', err);
        toast('Failed to parse CSV: ' + err.message, 'error', 5000);
      }
    });
  }

  function showCSVPreview(emails) {
    const modal = document.createElement('div');
    modal.className = 'preview-modal';
    
    const previewCount = Math.min(emails.length, 100);
    
    modal.innerHTML = `
      <div class="preview-backdrop"></div>
      <div class="preview-card card" style="max-width:680px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <div>
            <h3 style="margin:0;font-size:18px">Import Recipients</h3>
            <p style="margin:4px 0 0 0;color:var(--muted);font-size:13px">
              Found ${emails.length.toLocaleString()} valid email${emails.length !== 1 ? 's' : ''}
            </p>
          </div>
          <button id="closeModal" class="btn btn-outline" style="padding:8px 16px">
            <span style="font-size:18px">×</span>
          </button>
        </div>
        
        <div style="margin:16px 0;padding:16px;border-radius:10px;background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.1)">
          <div style="font-size:32px;font-weight:800;color:#fff;text-align:center">
            ${emails.length.toLocaleString()}
          </div>
          <div style="text-align:center;color:var(--muted);font-size:13px;margin-top:4px">
            Recipients ready to import
          </div>
        </div>
        
        <div style="margin-top:16px;max-height:320px;overflow:auto;padding:12px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04)">
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px">
            Preview (showing first ${previewCount}):
          </div>
          <div style="display:grid;gap:4px;font-size:13px;font-family:monospace">
            ${emails.slice(0, previewCount).map(e => 
              `<div style="padding:6px 8px;background:rgba(255,255,255,0.02);border-radius:4px">${escapeHtml(e)}</div>`
            ).join('')}
            ${emails.length > previewCount ? 
              `<div style="padding:8px;text-align:center;color:var(--muted);font-style:italic">
                ... and ${(emails.length - previewCount).toLocaleString()} more
              </div>` : ''}
          </div>
        </div>
        
        <div style="margin-top:20px;display:flex;gap:12px;justify-content:flex-end">
          <button id="cancelImport" class="btn btn-secondary">Cancel</button>
          <button id="confirmImport" class="btn btn-primary">
            Import ${emails.length.toLocaleString()} Recipient${emails.length !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    const closeModal = () => {
      modal.style.opacity = '0';
      setTimeout(() => modal.remove(), 200);
    };
    
    $('#closeModal').addEventListener('click', closeModal);
    $('#cancelImport').addEventListener('click', closeModal);
    modal.querySelector('.preview-backdrop').addEventListener('click', closeModal);
    
    $('#confirmImport').addEventListener('click', async () => {
      const btn = $('#confirmImport');
      btn.disabled = true;
      btn.textContent = 'Importing...';
      
      try {
        const resp = await fetch('/upload-csv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ emails })
        });
        
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || 'Import failed');
        }
        
        const result = await resp.json();
        toast(`Successfully imported ${emails.length.toLocaleString()} recipients`, 'success', 3000);
        closeModal();
        
        // Update recipient count if element exists
        setTimeout(() => {
          window.location.reload();
        }, 1000);
        
      } catch (err) {
        console.error('Import error:', err);
        toast('Import failed: ' + err.message, 'error', 5000);
        btn.disabled = false;
        btn.textContent = `Import ${emails.length.toLocaleString()} Recipients`;
      }
    });
  }

  /* ---------- GLOBAL STATE ---------- */
  window.totalRecipients = (() => {
    try {
      const statEl = document.querySelector('.stat-value');
      if (!statEl) return 0;
      
      const text = statEl.textContent.replace(/[^0-9]/g, '');
      return parseInt(text, 10) || 0;
    } catch (e) {
      console.warn('Failed to parse recipient count:', e);
      return 0;
    }
  })();

  /* ---------- KEYBOARD SHORTCUTS ---------- */
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + P for preview
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
      e.preventDefault();
      previewBtn?.click();
    }
    
    // Ctrl/Cmd + Enter to submit form
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      composeForm?.dispatchEvent(new Event('submit'));
    }
  });

  /* ---------- ENHANCED VISUAL FEEDBACK ---------- */
  // Add ripple effect to buttons
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
        left: ${x}px;
        top: ${y}px;
        pointer-events: none;
        transform: scale(0);
        animation: ripple 0.6s ease-out;
      `;
      
      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(ripple);
      
      setTimeout(() => ripple.remove(), 600);
    });
  });

  // Add ripple animation
  if (!document.querySelector('#ripple-style')) {
    const style = document.createElement('style');
    style.id = 'ripple-style';
    style.textContent = `
      @keyframes ripple {
        to {
          transform: scale(2);
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  }

  console.log('✓ Broadcast Studio initialized');
  console.log(`✓ ${window.totalRecipients.toLocaleString()} recipients loaded`);
  
})();