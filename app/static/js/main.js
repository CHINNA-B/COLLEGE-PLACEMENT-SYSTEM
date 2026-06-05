/**
 * PlaceHub — College Placement System
 * Client-side JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {

    // ===== Dark / Light Theme Toggle =====
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    const savedTheme = localStorage.getItem('placehub-theme') || 'dark';
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('placehub-theme', next);
            updateThemeIcon(next);
        });
    }

    function updateThemeIcon(theme) {
        if (themeToggle) {
            themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
            themeToggle.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
        }
    }

    // ===== Mobile Sidebar Toggle =====
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('active');
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    }

    // ===== Auto-dismiss Flash Messages =====
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // ===== Notification Badge Polling =====
    const notifBadge = document.getElementById('notifBadge');
    function pollNotifications() {
        fetch('/notifications/api/unread-count')
            .then(r => r.json())
            .then(data => {
                if (notifBadge) {
                    if (data.count > 0) {
                        notifBadge.textContent = data.count > 99 ? '99+' : data.count;
                        notifBadge.style.display = 'flex';
                    } else {
                        notifBadge.style.display = 'none';
                    }
                }
            })
            .catch(() => {}); // Silently fail
    }

    // Poll every 30 seconds
    if (notifBadge || document.querySelector('.notification-bell')) {
        setInterval(pollNotifications, 30000);
    }

    // ===== Search with Debounce =====
    const searchInputs = document.querySelectorAll('.search-bar input[type="text"]');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const form = input.closest('form');
                if (form) form.submit();
            }, 600);
        });
    });

    // ===== Confirm Delete =====
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            if (!confirm(el.dataset.confirm || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // ===== Animate Stat Numbers =====
    const statNumbers = document.querySelectorAll('.stat-number[data-count]');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCount(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    statNumbers.forEach(el => observer.observe(el));

    function animateCount(el) {
        const target = parseFloat(el.dataset.count);
        const isFloat = target % 1 !== 0;
        const duration = 1000;
        const start = performance.now();

        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            const current = target * eased;

            el.textContent = isFloat ? current.toFixed(1) : Math.floor(current);

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = isFloat ? target.toFixed(1) : target;
            }
        }

        requestAnimationFrame(update);
    }

    // ===== Progress Bar Animation =====
    document.querySelectorAll('.progress-fill[data-width]').forEach(bar => {
        const targetWidth = bar.dataset.width;
        setTimeout(() => {
            bar.style.width = targetWidth + '%';
        }, 300);
    });

});
