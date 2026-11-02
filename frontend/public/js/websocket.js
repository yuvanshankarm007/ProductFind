/**
 * Full-Duplex Resilient WebSocket Client for ProductFind Swarm.
 * Supports auto-reconnection, event forwarding, and session isolation.
 */

import { store, showToast } from './state.js';

class SwarmWebSocketClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1500;
        this.isConnected = false;
        this.messageHandlers = new Set();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/negotiate?session_id=${encodeURIComponent(store.sessionId)}`;

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                this.isConnected = true;
                this.reconnectAttempts = 0;
                console.log("[WebSocket] Connected to agent negotiation stream.");
                this.updateConnectionBadge(true);
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (err) {
                    console.error("[WebSocket] Parse error:", err);
                }
            };

            this.socket.onclose = () => {
                this.isConnected = false;
                this.updateConnectionBadge(false);
                this.scheduleReconnect();
            };

            this.socket.onerror = (err) => {
                console.warn("[WebSocket] Error occurred:", err);
            };
        } catch (e) {
            console.error("[WebSocket] Connection failure:", e);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
            console.log(`[WebSocket] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts})...`);
            setTimeout(() => this.connect(), delay);
        }
    }

    updateConnectionBadge(connected) {
        const badge = document.getElementById('ws-connection-indicator');
        if (badge) {
            badge.className = `tag-pill ${connected ? 'tag-version' : 'status-degraded'}`;
            badge.textContent = connected ? '● Swarm Live' : '○ Offline Reconnecting';
        }
    }

    onMessage(fn) {
        this.messageHandlers.add(fn);
        return () => this.messageHandlers.delete(fn);
    }

    handleMessage(data) {
        for (const handler of this.messageHandlers) {
            try {
                handler(data);
            } catch (e) {
                console.error("Handler error:", e);
            }
        }
    }

    send(action, payload = {}) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ action, ...payload }));
            return true;
        }
        return false;
    }
}

export const wsClient = new SwarmWebSocketClient();
