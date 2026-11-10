/**
 * ProductFind Sentinel — Search Autocomplete & Quick Suggestion Engine.
 * Provides a modern, responsive, keyboard-navigable autocomplete dropdown with
 * trending hardware, budget brackets, head-to-head showdowns, and multi-item bundles.
 */

import { escapeHtml } from './security.js';

const AUTOCOMPLETE_DATA = [
    // Trending Hardware & Deal Arbitrations
    {
        query: "Apple iPhone 16 (128GB)",
        title: "Apple iPhone 16 (128GB)",
        subtitle: "A18 Chip • Camera Control • Apple Intelligence Ready",
        category: "Smartphones",
        icon: "📱",
        badge: "Trending"
    },
    {
        query: "ASUS Vivobook 15 under 50k",
        title: "ASUS Vivobook 15 Laptop",
        subtitle: "Intel Core i5 12th Gen • 16GB RAM • 512GB SSD • Under ₹50k",
        category: "Laptops",
        icon: "💻",
        badge: "Under ₹50,000"
    },
    {
        query: "Sony WH-1000XM5",
        title: "Sony WH-1000XM5 Wireless ANC",
        subtitle: "Auto NC Optimizer • 30-Hr Battery • Hi-Res LDAC",
        category: "Audio",
        icon: "🎧",
        badge: "Flagship ANC"
    },
    {
        query: "Apple MacBook Air M2",
        title: "Apple MacBook Air M2 (13.6-inch)",
        subtitle: "16GB Unified Memory • 256GB SSD • 18-Hour Battery",
        category: "Laptops",
        icon: "💻",
        badge: "Best Ultrabook"
    },
    {
        query: "Samsung 32\" M7 4K Smart Monitor",
        title: "Samsung 32\" M7 4K Smart Monitor",
        subtitle: "3840x2160 UHD • Smart TV Apps • 65W USB-C PD Charging",
        category: "Monitors",
        icon: "🖥️",
        badge: "4K Productivity"
    },

    // Head-to-Head Versus Showdowns
    {
        query: "iPhone 16 vs Galaxy S24",
        title: "Apple iPhone 16 vs Samsung Galaxy S24",
        subtitle: "Head-to-head camera, battery, and value arbitration",
        category: "Showdowns",
        icon: "⚡",
        badge: "Versus"
    },
    {
        query: "Sony XM5 vs Bose QC45",
        title: "Sony WH-1000XM5 vs Bose QuietComfort 45",
        subtitle: "Comfort, active noise cancellation, and microphone shootout",
        category: "Showdowns",
        icon: "⚡",
        badge: "Versus"
    },
    {
        query: "MacBook Air M2 vs Lenovo Legion Slim 5",
        title: "MacBook Air M2 vs Lenovo Legion Slim 5",
        subtitle: "Ultraportable battery vs Dedicated RTX 4050 gaming power",
        category: "Showdowns",
        icon: "⚡",
        badge: "Versus"
    },

    // Budget Tech Brackets
    {
        query: "laptop under 50k",
        title: "Laptops under ₹50,000",
        subtitle: "Top verified 16GB RAM models with 1-Year Brand Warranty",
        category: "Budget",
        icon: "💻",
        badge: "Under ₹50k"
    },
    {
        query: "iphone under 1 lakh",
        title: "iPhones under ₹1,00,000",
        subtitle: "iPhone 16, 15 Plus, and 15 with Open-Box OTP delivery",
        category: "Budget",
        icon: "📱",
        badge: "Under 1 Lakh"
    },
    {
        query: "5G smartphone under 20k",
        title: "5G Smartphones under ₹20,000",
        subtitle: "CMF Phone 1, Redmi Note 13 5G, Moto G85 with AMOLED",
        category: "Budget",
        icon: "📱",
        badge: "Under ₹20k"
    },
    {
        query: "4k monitor under 30k",
        title: "4K Monitors under ₹30,000",
        subtitle: "Samsung M7, LG 27UL500, BenQ 4K HDR displays",
        category: "Budget",
        icon: "🖥️",
        badge: "Under ₹30k"
    },

    // Multi-Item Knapsack Bundles
    {
        query: "WFH Setup under ₹50,000",
        title: "WFH Home Office Setup",
        subtitle: "Monitor + Ergonomic Chair + Mechanical Keyboard + Webcam",
        category: "Bundles",
        icon: "📦",
        badge: "Knapsack Cart Split"
    },
    {
        query: "Gaming Rig Peripherals",
        title: "Gaming Rig Peripherals Bundle",
        subtitle: "240Hz Gaming Display + Mechanical Keyboard + Wireless Mouse",
        category: "Bundles",
        icon: "🎮",
        badge: "Knapsack Cart Split"
    }
];

export function initSearchAutocomplete(inputEl, onSelectCallback) {
    if (!inputEl) return;

    // Check or create dropdown container
    let dropdown = document.getElementById('search-autocomplete-dropdown');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'search-autocomplete-dropdown';
        dropdown.className = 'search-autocomplete-dropdown';
        
        // Append right inside the search-pill-container parent
        const container = inputEl.closest('.search-pill-container') || inputEl.parentElement;
        container.style.position = 'relative';
        container.appendChild(dropdown);
    }

    let selectedIndex = -1;
    let visibleItems = [];

    function renderDropdown(filterText = '') {
        const q = filterText.toLowerCase().trim();
        
        let filtered = [];
        if (!q) {
            // Show top curated suggestions when input is empty
            filtered = AUTOCOMPLETE_DATA.slice(0, 7);
        } else {
            // Search across title, subtitle, query, and category
            filtered = AUTOCOMPLETE_DATA.filter(item => {
                return item.query.toLowerCase().includes(q) ||
                       item.title.toLowerCase().includes(q) ||
                       item.subtitle.toLowerCase().includes(q) ||
                       item.category.toLowerCase().includes(q);
            });

            // If user typed something custom, put their exact query as the first option
            if (!filtered.some(f => f.query.toLowerCase() === q)) {
                filtered.unshift({
                    query: filterText,
                    title: `Search for "${filterText}"`,
                    subtitle: "Arbitrate deals across 23 global merchants with multi-agent swarm",
                    category: "Search",
                    icon: "🔍",
                    badge: "Execute"
                });
            }
        }

        visibleItems = filtered;
        selectedIndex = -1;

        if (filtered.length === 0) {
            dropdown.style.display = 'none';
            return;
        }

        dropdown.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 12px 8px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 6px;">
                <span style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.06em;">
                    ${q ? '⚡ Smart Search Suggestions' : '🔥 Trending Arbitrations & Popular Deals'}
                </span>
                <span style="font-size: 10px; color: #64748b; font-family: monospace;">Use ↑↓ to navigate • ↵ Enter</span>
            </div>
            <div class="autocomplete-list" style="display: flex; flex-direction: column; gap: 3px;">
                ${filtered.map((item, idx) => {
                    const highlightedTitle = highlightMatch(item.title, q);
                    const badgeColor = item.badge === 'Versus' ? 'rgba(239, 68, 68, 0.2); color: #f87171;' : 
                                      (item.badge.includes('Knapsack') ? 'rgba(168, 85, 247, 0.2); color: #c084fc;' : 'rgba(56, 189, 248, 0.15); color: #38bdf8;');
                    return `
                        <div class="autocomplete-item" data-index="${idx}" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-radius: 8px; cursor: pointer; transition: all 0.15s ease;">
                            <div style="display: flex; align-items: center; gap: 10px; flex: 1; overflow: hidden;">
                                <span style="font-size: 16px;">${item.icon}</span>
                                <div style="line-height: 1.25; overflow: hidden;">
                                    <div style="font-size: 13px; font-weight: 600; color: #f1f5f9; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">
                                        ${highlightedTitle}
                                    </div>
                                    <div style="font-size: 11px; color: #94a3b8; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">
                                        ${escapeHtml(item.subtitle)}
                                    </div>
                                </div>
                            </div>
                            <span style="font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 9999px; background: ${badgeColor}; white-space: nowrap; margin-left: 8px;">
                                ${escapeHtml(item.badge)}
                            </span>
                        </div>
                    `;
                }).join('')}
            </div>
        `;

        dropdown.style.display = 'block';

        // Add click events to items
        dropdown.querySelectorAll('.autocomplete-item').forEach(el => {
            el.addEventListener('mouseenter', () => {
                const idx = parseInt(el.getAttribute('data-index'), 10);
                setSelectedItem(idx);
            });

            el.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const idx = parseInt(el.getAttribute('data-index'), 10);
                selectItem(idx);
            });
        });
    }

    function highlightMatch(text, query) {
        if (!query) return escapeHtml(text);
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        return escapeHtml(text).replace(regex, '<span style="color: #38bdf8; font-weight: 800; text-decoration: underline;">$1</span>');
    }

    function setSelectedItem(index) {
        selectedIndex = index;
        const items = dropdown.querySelectorAll('.autocomplete-item');
        items.forEach((item, i) => {
            if (i === selectedIndex) {
                item.style.background = 'rgba(56, 189, 248, 0.15)';
                item.style.transform = 'translateX(4px)';
            } else {
                item.style.background = 'transparent';
                item.style.transform = 'none';
            }
        });
    }

    function selectItem(index) {
        if (index >= 0 && index < visibleItems.length) {
            const item = visibleItems[index];
            inputEl.value = item.query;
            dropdown.style.display = 'none';
            if (typeof onSelectCallback === 'function') {
                onSelectCallback(item.query);
            }
        }
    }

    // Input listeners
    inputEl.addEventListener('focus', () => {
        renderDropdown(inputEl.value);
    });

    inputEl.addEventListener('input', () => {
        renderDropdown(inputEl.value);
    });

    inputEl.addEventListener('keydown', (e) => {
        if (dropdown.style.display === 'none') {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                renderDropdown(inputEl.value);
                e.preventDefault();
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const next = selectedIndex + 1 >= visibleItems.length ? 0 : selectedIndex + 1;
            setSelectedItem(next);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prev = selectedIndex - 1 < 0 ? visibleItems.length - 1 : selectedIndex - 1;
            setSelectedItem(prev);
        } else if (e.key === 'Enter') {
            if (selectedIndex >= 0) {
                e.preventDefault();
                selectItem(selectedIndex);
            } else {
                dropdown.style.display = 'none';
            }
        } else if (e.key === 'Escape') {
            dropdown.style.display = 'none';
        }
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
        if (!inputEl.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}
