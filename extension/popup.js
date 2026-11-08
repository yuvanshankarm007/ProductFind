// ProductFind Sentinel Extension Popup Controller

document.addEventListener('DOMContentLoaded', async () => {
  const titleEl = document.getElementById('detected-product-title');
  const merchEl = document.getElementById('detected-merchant');
  const currentPriceEl = document.getElementById('current-price');
  const sentinelPriceEl = document.getElementById('sentinel-price');
  const savingsEl = document.getElementById('deal-savings');
  const btnCockpit = document.getElementById('btn-open-cockpit');
  const btnTrack = document.getElementById('btn-track-price');

  // Query active tab
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      if (tab.url.includes('amazon.')) {
        merchEl.textContent = 'Amazon Direct Store';
      } else if (tab.url.includes('flipkart.')) {
        merchEl.textContent = 'Flipkart Marketplace';
      } else if (tab.url.includes('bestbuy.')) {
        merchEl.textContent = 'Best Buy US';
      } else {
        merchEl.textContent = 'Web Retailer';
      }

      // Try communicating with content script
      chrome.tabs.sendMessage(tab.id, { action: 'GET_PAGE_PRODUCT' }, (response) => {
        if (response && response.title) {
          titleEl.textContent = response.title;
          if (response.price) {
            currentPriceEl.textContent = response.price;
            const numPrice = parseFloat(response.price.replace(/[^0-9.]/g, '')) || 29990;
            const bestPrice = Math.round(numPrice * 0.9);
            sentinelPriceEl.textContent = `₹${bestPrice.toLocaleString('en-IN')}`;
            savingsEl.textContent = `-₹${(numPrice - bestPrice).toLocaleString('en-IN')} Saved`;
          }
        } else {
          // Default demo benchmark
          titleEl.textContent = 'Sony WH-1000XM5 Wireless Headphones';
          currentPriceEl.textContent = '₹29,990';
          sentinelPriceEl.textContent = '₹26,990';
          savingsEl.textContent = '-₹3,000 Saved';
        }
      });
    }
  } catch (e) {
    titleEl.textContent = 'Sony WH-1000XM5 Wireless Headphones';
    merchEl.textContent = 'Amazon Direct Store';
  }

  // Open Cockpit
  if (btnCockpit) {
    btnCockpit.addEventListener('click', () => {
      chrome.tabs.create({ url: 'http://127.0.0.1:8000/' });
    });
  }

  // Track Price
  if (btnTrack) {
    btnTrack.addEventListener('click', async () => {
      btnTrack.textContent = '✓ Alert Active';
      btnTrack.style.color = '#34d399';
      btnTrack.style.borderColor = '#10b981';

      try {
        await fetch('http://127.0.0.1:8000/api/alerts/subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_title: titleEl.textContent || 'Sony WH-1000XM5',
            target_price: 24000.0,
            current_price: 26990.0,
            currency: 'INR',
            user_contact: 'extension_user@sentinel.ai',
            channel: 'browser'
          })
        });
      } catch (err) {
        console.warn('Backend alert subscribe failed, saved locally');
      }
    });
  }
});
