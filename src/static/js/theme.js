/**
 * 主题切换和持久化功能
 */
document.addEventListener('DOMContentLoaded', function() {
    // 从localStorage读取主题设置
    const savedTheme = localStorage.getItem('theme');
    
    // 检测系统主题
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // 应用主题
    let currentTheme = savedTheme;
    if (!currentTheme) {
        currentTheme = prefersDarkScheme.matches ? 'dark' : 'light';
    }
    
    // 设置主题
    document.body.setAttribute('data-bs-theme', currentTheme);
    
    // 更新主题切换按钮图标
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        if (icon) {
            if (currentTheme === 'dark') {
                icon.classList.remove('bi-moon-stars');
                icon.classList.add('bi-sun');
            } else {
                icon.classList.remove('bi-sun');
                icon.classList.add('bi-moon-stars');
            }
        }
    }
    
    // 监听系统主题变化
    prefersDarkScheme.addEventListener('change', function(e) {
        // 只有当用户没有明确设置主题时，才跟随系统主题
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            document.body.setAttribute('data-bs-theme', newTheme);
            
            // 更新图标
            if (themeToggle) {
                const icon = themeToggle.querySelector('i');
                if (icon) {
                    if (newTheme === 'dark') {
                        icon.classList.remove('bi-moon-stars');
                        icon.classList.add('bi-sun');
                    } else {
                        icon.classList.remove('bi-sun');
                        icon.classList.add('bi-moon-stars');
                    }
                }
            }
        }
    });
});