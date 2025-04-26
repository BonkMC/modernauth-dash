document.addEventListener('DOMContentLoaded', () => {
  // ——— Chart on /analytics ——————————————
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
          options: {
            responsive: true,
            scales: {
              y: {
                beginAtZero: true,
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: {
                  color: getComputedStyle(document.documentElement)
                    .getPropertyValue('--text-color').trim()
                }
              },
              x: {
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: {
                  color: getComputedStyle(document.documentElement)
                    .getPropertyValue('--text-color').trim()
                }
              }
            },
            plugins: {
              legend: {
                labels: {
                  color: getComputedStyle(document.documentElement)
                    .getPropertyValue('--text-color').trim()
                }
              }
            }
          }
        });
      })
      .catch(console.error);
  }

  // ——— Settings: reset API key ——————————————
  const resetBtn = document.getElementById('resetBtn');
  const msg = document.getElementById('msg');
  const display = document.getElementById('apiKeyDisplay');

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      fetch('/api/reset_key', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success' && data.api_key) {
            display.textContent = data.api_key;
            msg.textContent = '✅ API key updated!';
          } else {
            msg.textContent = '❌ Error generating new key.';
          }
        })
        .catch(err => {
          console.error(err);
          msg.textContent = '❌ Error updating API key.';
        });
    });
  }
});
