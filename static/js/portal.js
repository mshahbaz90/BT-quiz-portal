// BreakThru Portal Core Client JS

document.addEventListener('DOMContentLoaded', () => {
  // Theme Switcher Logic (supports #theme-toggle-btn, #themeToggle, .theme-toggle)
  const metaUser = document.querySelector('meta[name="portal-user-id"]');
  const userId = metaUser ? metaUser.getAttribute('content') : (document.body?.dataset?.userId || '');
  const userKey = userId ? `breakthru-theme-${userId}` : 'breakthru-theme';

  let storedTheme = userId ? localStorage.getItem(userKey) : null;
  if (!storedTheme) {
    storedTheme = localStorage.getItem('breakthru-theme') || 
                  (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }
  
  document.documentElement.setAttribute('data-theme', storedTheme);

  function applyTheme(target) {
    document.documentElement.setAttribute('data-theme', target);
    if (userId) {
      localStorage.setItem(`breakthru-theme-${userId}`, target);
    }
    localStorage.setItem('breakthru-theme', target);
    updateThemeDisplays(target);
    window.dispatchEvent(new CustomEvent('breakthru:themechange', { detail: { theme: target } }));
  }

  function updateThemeDisplays(theme) {
    document.querySelectorAll('#theme-icon, .theme-icon').forEach(icon => {
      icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    });
    document.querySelectorAll('.theme-label').forEach(label => {
      label.textContent = theme === 'dark' ? 'Light' : 'Dark';
    });
    document.querySelectorAll('#themeToggle').forEach(btToggle => {
      btToggle.innerHTML = theme === 'dark' ? '☀️ Light mode' : '🌙 Dark mode';
    });
    document.querySelectorAll('#theme-toggle-btn, #themeToggle, .theme-toggle').forEach(btn => {
      const nextTheme = theme === 'dark' ? 'Light' : 'Dark';
      btn.setAttribute('title', `Switch to ${nextTheme} Mode`);
      btn.setAttribute('aria-label', `Switch to ${nextTheme} Mode`);
    });
  }

  const themeToggleBtns = document.querySelectorAll('#theme-toggle-btn, #themeToggle, .theme-toggle');
  themeToggleBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const target = current === 'dark' ? 'light' : 'dark';
      applyTheme(target);
    });
  });

  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      const hasSavedTheme = userId ? localStorage.getItem(`breakthru-theme-${userId}`) : localStorage.getItem('breakthru-theme');
      if (!hasSavedTheme) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  updateThemeDisplays(storedTheme);

  // Mobile Navigation Drawer Toggle & Backdrop
  const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
  const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
  const sidebarBackdrop = document.getElementById('sidebar-backdrop');
  const sidebar = document.querySelector('.sidebar');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('open');
    if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
  }

  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', () => {
      if (sidebar && sidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }
  if (sidebarCloseBtn) {
    sidebarCloseBtn.addEventListener('click', closeSidebar);
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', closeSidebar);
  }

  // Password Visibility Toggle
  document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.getAttribute('data-target'));
      if (input) {
        const isPassword = input.getAttribute('type') === 'password';
        input.setAttribute('type', isPassword ? 'text' : 'password');
        btn.textContent = isPassword ? '👁️‍🗨️' : '👁️';
      }
    });
  });

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.alert-auto-dismiss').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });
});
