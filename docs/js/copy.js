// Copy to Clipboard
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const code = btn.previousElementSibling.innerText;
    
    navigator.clipboard.writeText(code).then(() => {
      const originalText = btn.innerText;
      btn.innerText = 'Copied!';
      btn.style.background = 'var(--accent)';
      btn.style.color = 'var(--bg)';
      
      setTimeout(() => {
        btn.innerText = originalText;
        btn.style.background = '';
        btn.style.color = '';
      }, 2000);
    });
  });
});
