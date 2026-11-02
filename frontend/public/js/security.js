/**
 * Security and Data Sanitization Utilities.
 * Protects the UI against Cross-Site Scripting (XSS) and malformed URL injection.
 */

export function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export function sanitizeUrl(url) {
    if (!url) return '#';
    const clean = String(url).trim();
    if (clean.startsWith('javascript:') || clean.startsWith('data:') || clean.startsWith('vbscript:')) {
        return '#';
    }
    return clean;
}

export function createSafeElement(tag, className = '', textContent = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (textContent) el.textContent = textContent;
    return el;
}
