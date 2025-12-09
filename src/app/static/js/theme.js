const root = document.documentElement;
const storageKey = 'theme';

const prefersDark = () => window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

const getStoredTheme = () => {
    try {
        return localStorage.getItem(storageKey);
    } catch (error) {
        return null;
    }
};

const storeTheme = (theme) => {
    try {
        localStorage.setItem(storageKey, theme);
    } catch (error) {
        // ignore storage issues
    }
};

const applyTheme = (theme) => {
    const isDark = theme === 'dark';
    root.classList[isDark ? 'add' : 'remove']('dark');
    return isDark;
};

const initToggle = () => {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) {
        return;
    }

    const syncState = () => {
        const isDark = root.classList.contains('dark');
        toggle.setAttribute('aria-pressed', String(isDark));
    };

    toggle.addEventListener('click', () => {
        const nextTheme = root.classList.contains('dark') ? 'light' : 'dark';
        applyTheme(nextTheme);
        storeTheme(nextTheme);
        syncState();
    });

    syncState();
};

const initialTheme = getStoredTheme() || (prefersDark() ? 'dark' : 'light');
applyTheme(initialTheme);

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initToggle);
} else {
    initToggle();
}
