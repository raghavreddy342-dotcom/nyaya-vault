/* NYAYA VAULT – Frontend JS */

// ── Modal helpers ──
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        e.target.classList.remove('active');
    }
});

// ── Verify document integrity ──
function verifyDocument(docId, btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Verifying…';

    fetch(`/documents/${docId}/verify`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById(`verify-result-${docId}`);
            if (!container) {
                alert(`${data.status}: ${data.message}`);
                btnEl.disabled = false;
                btnEl.textContent = '🔍 Verify';
                return;
            }
            container.className = 'verify-result show ' +
                (data.status === 'VERIFIED' ? 'verified' : 'mismatch');
            container.innerHTML = `
                <strong>${data.status}</strong><br>
                ${data.message}<br>
                <span class="text-mono mt-1" style="display:block;">
                    Original: ${data.original_hash}<br>
                    Current:  ${data.current_hash}
                </span>`;
            btnEl.disabled = false;
            btnEl.textContent = '🔍 Verify';
        })
        .catch(() => {
            alert('Verification failed.');
            btnEl.disabled = false;
            btnEl.textContent = '🔍 Verify';
        });
}

// ── Verify audit chain ──
function verifyAuditChain(btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Verifying chain…';

    fetch('/audit/verify-chain')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('chain-result');
            el.className = 'verify-result show ' +
                (data.status === 'VERIFIED' ? 'verified' : 'mismatch');
            el.innerHTML = `<strong>${data.status}</strong> – ${data.message} (${data.checked} records checked)`;
            btnEl.disabled = false;
            btnEl.textContent = '🔗 Verify Audit Chain';
        })
        .catch(() => {
            alert('Chain verification failed.');
            btnEl.disabled = false;
            btnEl.textContent = '🔗 Verify Audit Chain';
        });
}

// ── Auto-dismiss flash messages ──
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 4000);
    });
});
