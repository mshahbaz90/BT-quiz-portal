// BreakThru Portal Core Client JS

document.addEventListener('DOMContentLoaded', () => {
  // Theme Switcher Logic (supports both #theme-toggle-btn and #themeToggle)
  const themeToggleBtns = document.querySelectorAll('#theme-toggle-btn, #themeToggle, .theme-toggle');
  const storedTheme = localStorage.getItem('breakthru-theme') || 
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  
  document.documentElement.setAttribute('data-theme', storedTheme);

  function applyTheme(target) {
    document.documentElement.setAttribute('data-theme', target);
    localStorage.setItem('breakthru-theme', target);
    updateThemeDisplays(target);
  }

  function updateThemeDisplays(theme) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
      icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    const btToggle = document.getElementById('themeToggle');
    if (btToggle) {
      btToggle.innerHTML = theme === 'dark' ? '☀️ Light mode' : '🌙 Dark mode';
    }
  }

  themeToggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const target = current === 'dark' ? 'light' : 'dark';
      applyTheme(target);
    });
  });

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
