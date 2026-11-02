/**
 * Reactive State Store & Race-Condition Safe Search Controller.
 * Implements schema-versioned localStorage, AbortController request deduplication,
 * and sequence-token tracking.
 */

class AppStore {
    constructor() {
        this.preferences = this.loadPreferences();
        this.riskPreferences = {
            warrantyPriority: 0.5,
            speedPriority: 0.5,
            trustTolerance: 0.7
        };
        this.activeSearchToken = 0;
        this.searchAbortController = null;
        this.lastState = null;
        this.listeners = new Set();
        this.sessionId = 'sess-' + Math.random().toString(36).substring(2, 10);
    }

    subscribe(fn) {
        this.listeners.add(fn);
        return () => this.listeners.delete(fn);
    }

    notify(eventType, payload) {
        for (const fn of this.listeners) {
            try {
                fn(eventType, payload);
            } catch (e) {
                console.error("Listener error:", e);
            }
        }
    }

    loadPreferences() {
        const DEFAULT_PREFS = {
            version: 2,
            language: 'en',
            country: 'US',
            currency: 'USD',
            preferredPayment: 'all'
        };
        try {
            const raw = localStorage.getItem('ProductFind_Preferences_v2');
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed.version === 2) {
                    return { ...DEFAULT_PREFS, ...parsed };
                }
            }
        } catch (e) {
            console.warn("Failed reading localStorage preferences:", e);
        }
        return DEFAULT_PREFS;
    }

    savePreferences(prefs) {
        this.preferences = { ...this.preferences, ...prefs, version: 2 };
        try {
            localStorage.setItem('ProductFind_Preferences_v2', JSON.stringify(this.preferences));
        } catch (e) {
            console.warn("Failed writing localStorage preferences:", e);
        }
        this.notify('PREFERENCES_UPDATED', this.preferences);
    }

    setRiskPreferences(risk) {
        this.riskPreferences = { ...this.riskPreferences, ...risk };
        this.notify('RISK_PREFERENCES_UPDATED', this.riskPreferences);
    }

    setLastState(state) {
        this.lastState = state;
        this.notify('STATE_UPDATED', state);
    }
}

export const store = new AppStore();

export function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✓' : (type === 'error' ? '⚠️' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
