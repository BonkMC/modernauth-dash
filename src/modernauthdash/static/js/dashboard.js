document.addEventListener('DOMContentLoaded', () => {
  //
  // Modal helpers
  //
  const overlay = document.getElementById('modal-overlay');
  const titleEl = document.getElementById('modal-title');
  const bodyEl  = document.getElementById('modal-body');
  const actions = document.querySelector('.modal-actions');
  const closeBtn = document.getElementById('modal-close');

  function showModal({ title, bodyHTML, buttons }) {
    titleEl.textContent = title;
    bodyEl.innerHTML = bodyHTML;
    actions.innerHTML = '';
    buttons.forEach(b => {
      const btn = document.createElement('button');
      btn.className = b.className || 'btn';
      btn.textContent = b.text;
      btn.addEventListener('click', () => {
        b.onClick();
      });
      actions.appendChild(btn);
    });
    overlay.classList.remove('hidden');
  }
  function hideModal() {
    overlay.classList.add('hidden');
  }

  // ensure it starts hidden
  hideModal();

  closeBtn.addEventListener('click', hideModal);
  overlay.addEventListener('click', e => {
    if (e.target === overlay) hideModal();
  });

  //
  // Create Server
  //
  const createForm = document.getElementById('createForm');
  if (createForm) {
    createForm.addEventListener('submit', async e => {
      e.preventDefault();
      const inp = createForm.querySelector('input[name="server_id"]');
      let serverId = inp.value.trim().toLowerCase().replace(/\s+/g, '-');

      try {
        const res = await fetch(CREATE_SERVER_URL, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ server_id: serverId })
        });
        const data = await res.json();
        if (!res.ok || data.status !== 'success') {
          throw new Error(data.message || `HTTP ${res.status}`);
        }

        showModal({
          title: 'Server Created',
          bodyHTML: `
            <p><strong>${data.owned_server}</strong> has been created.</p>
            <p>Secret key (save this – you won’t see it again):</p>
            <input type="text" readonly id="newKey" value="${data.secret_key}" />
          `,
          buttons: [
            {
              text: 'Copy Key',
              className: 'btn btn--primary',
              onClick: () => {
                document.getElementById('newKey').select();
                document.execCommand('copy');
              }
            },
            {
              text: 'Close',
              onClick: () => {
                hideModal();
                window.location.reload();
              }
            }
          ]
        });

      } catch (err) {
        console.error('Create Server error:', err);
        showModal({
          title: 'Error Creating Server',
          bodyHTML: `<p>${err.message}</p>`,
          buttons: [{ text: 'Close', onClick: hideModal }]
        });
      }
    });
  }

  //
  // Remove Server (Dashboard)
  //
  const removeBtn = document.getElementById('removeServerBtn');
  if (removeBtn) {
    removeBtn.addEventListener('click', () => {
      showModal({
        title: 'Confirm Removal',
        bodyHTML: `<p>Are you sure you want to remove your server?</p>`,
        buttons: [
          {
            text: 'Yes, Remove',
            className: 'btn btn--primary',
            onClick: async () => {
              try {
                const r = await fetch('/api/delete_server', { method: 'POST' });
                const j = await r.json();
                if (r.ok && j.status === 'success') {
                  window.location.href = '/';
                } else {
                  throw new Error(j.message || 'Unknown error');
                }
              } catch (err) {
                console.error(err);
                showModal({
                  title: 'Error',
                  bodyHTML: `<p>${err.message}</p>`,
                  buttons: [{ text: 'Close', onClick: hideModal }]
                });
              }
            }
          },
          { text: 'Cancel', onClick: hideModal }
        ]
      });
    });
  }

  //
  // Reset Server Access Code (Settings)
  //
  const resetSrvBtn = document.getElementById('resetServerCodeBtn');
  if (resetSrvBtn) {
    resetSrvBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/reset_server_code', { method: 'POST' });
        const j = await res.json();
        if (res.ok && j.status === 'success') {
          showModal({
            title: 'New Server Key',
            bodyHTML: `
              <p>Here is your new server access code:</p>
              <input type="text" readonly id="resetKey" value="${j.new_code}" />
            `,
            buttons: [
              {
                text: 'Copy Code',
                className: 'btn btn--primary',
                onClick: () => {
                  document.getElementById('resetKey').select();
                  document.execCommand('copy');
                }
              },
              { text: 'Close', onClick: hideModal }
            ]
          });
        } else {
          throw new Error(j.message || 'Failed to reset');
        }
      } catch (err) {
        console.error(err);
        showModal({
          title: 'Error',
          bodyHTML: `<p>${err.message}</p>`,
          buttons: [{ text: 'Close', onClick: hideModal }]
        });
      }
    });
  }

  //
  // Reset Dashboard Access Code (Settings page)
  //
  const resetACBtn = document.getElementById('resetAccessCodeBtn');
  const acMsg     = document.getElementById('accessCodeMsg');
  if (resetACBtn) {
    resetACBtn.addEventListener('click', () => {
      fetch('/api/reset_key', { method: 'POST' })
        .then(r => r.json())
        .then(j => {
          if (j.status === 'success') {
            acMsg.innerHTML =
              '✅ Your new access code (will only be shown once): ' +
              '<strong>' + j.api_key + '</strong>';
            resetACBtn.disabled = true;
          } else {
            acMsg.textContent = '❌ Error resetting code.';
          }
        })
        .catch(() => acMsg.textContent = '❌ Error resetting code.');
    });
  }

  //
  // Analytics Chart
  //
  const chartEl = document.getElementById('myChart');
  if (chartEl) {
    fetch('/api/data')
      .then(res => res.json())
      .then(({ labels, values }) => {
        const accentColor = getComputedStyle(document.documentElement)
          .getPropertyValue('--accent-color').trim();
        new Chart(chartEl, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: 'Players',
              data: values,
              fill: true,
              tension: 0.4,
              borderWidth: 2,
              borderColor: accentColor,
              backgroundColor: accentColor + '33'
            }]
          },
          options: { /*…*/ }
        });
      })
      .catch(console.error);
  }
});
