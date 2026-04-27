/**
 * finance.js - Logic for the Finance AI Dashboard
 */

class FinanceDashboard {
    constructor() {
        this.elements = {
            // Broker Connection
            connectBtn: document.getElementById('connect-broker-btn'),
            modal: document.getElementById('broker-connect-modal'),
            closeBtn: document.querySelector('.close-button'),
            sendOtpBtn: document.getElementById('send-otp-btn'),
            verifyOtpBtn: document.getElementById('verify-otp-btn'),
            step1: document.getElementById('step-1'),
            step2: document.getElementById('step-2'),
            step3: document.getElementById('step-3'),
            connectionStatusMsg: document.getElementById('connection-status-message'),
            // Market Data
            marketWatchlist: document.getElementById('market-watchlist'),
            liveMarketDataSection: document.getElementById('live-market-data'),
            chartTitle: document.getElementById('chart-title'),
            explainChartBtn: document.getElementById('explain-chart-btn'),
            marketChartContainer: document.getElementById('market-chart-container'),
            // Backtesting
            backtestBtn: document.getElementById('backtest-btn'),
            // Paper Trading
            paperBuyBtn: document.getElementById('paper-buy-btn'),
            paperSellBtn: document.getElementById('paper-sell-btn'),
            paperPositionsDiv: document.getElementById('paper-positions'),
            paperCashBalance: document.getElementById('paper-cash-balance'),
            paperSymbolInput: document.getElementById('paper-symbol'),
            paperQuantityInput: document.getElementById('paper-quantity'),
            paperStopLossInput: document.getElementById('paper-stop-loss'),
            paperTakeProfitInput: document.getElementById('paper-take-profit'),
            // Analytics
            analyticsTotalPnl: document.getElementById('analytics-total-pnl'),
            analyticsWinRate: document.getElementById('analytics-win-rate'),
            analyticsSharpeRatio: document.getElementById('analytics-sharpe-ratio'),
            analyticsMaxDrawdown: document.getElementById('analytics-max-drawdown'),
            // Strategy Studio
            newStrategyBtn: document.getElementById('new-strategy-btn'),
            saveStrategyBtn: document.getElementById('save-strategy-btn'),
            strategyEditor: document.querySelector('.strategy-editor textarea'),
            strategyLibrary: document.querySelector('.strategy-library ul'),
            // AI Assistant
            aiChatWindow: document.querySelector('.ai-chat-window'),
            aiChatInput: document.querySelector('.ai-chat-input'),
            // Tabs
            navTabs: document.querySelectorAll('.finance-nav-tab'),
        };
        this.state = {
            tempSessionId: null,
            currentStrategyId: null,
            chart: null,
            chartSymbol: 'AAPL', // Default symbol to track
            mainSeries: null,
        };
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupTabs();
        this.renderPortfolioAnalytics();
        this.initMarketChart();
        this.loadStrategies();
        this.connectMarketDataWebSocket();
        this.connectAIChatWebSocket();
        this.updatePaperPortfolio();
    }

    setupEventListeners() {
        // Broker Connection
        this.elements.connectBtn.addEventListener('click', () => this.openBrokerModal());
        this.elements.closeBtn.addEventListener('click', () => this.closeBrokerModal());
        window.addEventListener('click', (e) => { if (e.target == this.elements.modal) this.closeBrokerModal(); });
        this.elements.sendOtpBtn.addEventListener('click', () => this.sendOtp());
        this.elements.verifyOtpBtn.addEventListener('click', () => this.verifyOtp());

        // Backtesting
        this.elements.backtestBtn.addEventListener('click', () => this.runBacktest());

        // Paper Trading
        this.elements.paperBuyBtn.addEventListener('click', () => this.executePaperTrade('BUY'));
        this.elements.paperSellBtn.addEventListener('click', () => this.executePaperTrade('SELL'));

        // Strategy Studio
        this.elements.newStrategyBtn.addEventListener('click', () => this.clearStrategyEditor());
        this.elements.saveStrategyBtn.addEventListener('click', () => this.saveStrategy());

        // Charting
        this.elements.explainChartBtn.addEventListener('click', () => this.explainChart());

        // AI Assistant
        this.elements.aiChatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendAIChatMessage();
            }
        });
    }

    setupTabs() {
        this.elements.navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                
                this.elements.navTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                document.querySelectorAll('.finance-tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`tab-${tabName}`).classList.add('active');
            });
        });
    }

    // --- Broker Connection Methods ---
    openBrokerModal() {
        this.elements.modal.style.display = 'flex';
        this.elements.step1.classList.add('active');
        this.elements.step2.classList.remove('active');
        this.elements.step3.classList.remove('active');
        document.getElementById('pan-number').value = '';
        document.getElementById('mobile-number').value = '';
        document.getElementById('otp-code').value = '';
    }

    closeBrokerModal() {
        this.elements.modal.style.display = 'none';
    }

    async sendOtp() {
        const broker = document.getElementById('broker-selector').value;
        const panNumber = document.getElementById('pan-number').value;
        const mobileNumber = document.getElementById('mobile-number').value;

        if (!panNumber || !mobileNumber) {
            alert('Please enter both PAN and Mobile Number.');
            return;
        }

        this.elements.sendOtpBtn.disabled = true;
        this.elements.sendOtpBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

        try {
            const response = await fetch('/api/v1/finance/connect/initiate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ broker, pan_number: panNumber, mobile_number: mobileNumber }),
            });
            const data = await response.json();

            if (response.ok && data.success) {
                this.state.tempSessionId = data.session_id;
                this.elements.step1.classList.remove('active');
                this.elements.step2.classList.add('active');
            } else {
                throw new Error(data.detail || 'Failed to send OTP.');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            this.elements.sendOtpBtn.disabled = false;
            this.elements.sendOtpBtn.innerHTML = 'Send OTP';
        }
    }

    async verifyOtp() {
        const broker = document.getElementById('broker-selector').value;
        const otp = document.getElementById('otp-code').value;

        if (!otp) {
            alert('Please enter the OTP.');
            return;
        }

        this.elements.verifyOtpBtn.disabled = true;
        this.elements.verifyOtpBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
        this.elements.step2.classList.remove('active');
        this.elements.step3.classList.add('active');
        this.elements.connectionStatusMsg.textContent = 'Verifying OTP and connecting to broker...';

        try {
            const response = await fetch('/api/v1/finance/connect/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ broker, session_id: this.state.tempSessionId, otp }),
            });
            const data = await response.json();

            if (response.ok && data.success) {
                this.elements.connectionStatusMsg.textContent = `✅ Success! Connected to ${broker}.`;
                document.getElementById('connection-status-indicator').classList.replace('disconnected', 'connected');
                document.getElementById('connection-status-text').textContent = `Connected (${broker})`;
                this.elements.connectBtn.textContent = 'Disconnect';
                setTimeout(() => this.closeBrokerModal(), 2000);
            } else {
                throw new Error(data.detail || 'OTP verification failed.');
            }
        } catch (error) {
            this.elements.connectionStatusMsg.textContent = `❌ Error: ${error.message}`;
            setTimeout(() => { this.elements.step3.classList.remove('active'); this.elements.step2.classList.add('active'); }, 3000);
        } finally {
            this.elements.verifyOtpBtn.disabled = false;
            this.elements.verifyOtpBtn.innerHTML = 'Verify & Connect';
        }
    }

    // --- Charting Methods ---
    initMarketChart() {
        if (!this.elements.marketChartContainer || typeof LightweightCharts === 'undefined') return;

        this.state.chart = LightweightCharts.createChart(this.elements.marketChartContainer, {
            width: this.elements.marketChartContainer.clientWidth,
            height: this.elements.marketChartContainer.clientHeight,
            layout: {
                backgroundColor: 'var(--primary-bg)',
                textColor: 'var(--text-primary)',
            },
            grid: {
                vertLines: { color: 'var(--border-color)' },
                horzLines: { color: 'var(--border-color)' },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: true,
            },
        });

        this.state.mainSeries = this.state.chart.addLineSeries({
            color: 'var(--primary-color)',
            lineWidth: 2,
        });

        // Handle chart resizing
        new ResizeObserver(entries => {
            if (entries.length > 0 && entries[0].contentRect) {
                this.state.chart.resize(entries[0].contentRect.width, entries[0].contentRect.height);
            }
        }).observe(this.elements.marketChartContainer);
    }

    async changeChartSymbol(symbol) {
        if (this.state.chartSymbol === symbol) return; // No change

        this.state.chartSymbol = symbol;
        this.elements.chartTitle.textContent = `Real-Time Chart: ${symbol}`;

        // Show loading state on chart
        this.state.mainSeries.setData([]); // Clear previous data

        try {
            const response = await fetch(`/api/v1/finance/historical-data/${symbol}`);
            if (!response.ok) {
                throw new Error('Failed to load historical data.');
            }
            const result = await response.json();
            if (result.success && result.data) {
                this.state.mainSeries.setData(result.data);
                showToast(`Loaded historical data for ${symbol}.`, 'success');
            }
        } catch (error) {
            console.error(error);
            showToast(error.message, 'error');
        }
    }

    explainChart() {
        const prompt = `Explain chart for ${this.state.chartSymbol}`;
        this.addMessageToAIChat('user', prompt);
        this.sendAIChatMessage(prompt, true); // Send pre-formatted message
    }

    // --- Market Data Methods ---
    connectMarketDataWebSocket() {
        const ws = new WebSocket(`ws://${window.location.host}/api/v1/ws/market-data`);

        ws.onopen = () => {
            console.log('Connected to market data WebSocket');
            this.elements.liveMarketDataSection.innerHTML = '<h3>Live Market Data</h3><ul id="market-watchlist"></ul>';
            this.elements.marketWatchlist = document.getElementById('market-watchlist'); // Re-assign after innerHTML change
        };

        ws.onmessage = (event) => {
            const stockData = JSON.parse(event.data);

            // Update the real-time chart (tracking AAPL for this example)
            if (this.state.mainSeries && stockData.symbol === this.state.chartSymbol) {
                const timestamp = new Date(stockData.timestamp).getTime() / 1000;
                this.state.mainSeries.update({ time: timestamp, value: stockData.price });
            }

            let listItem = document.getElementById(`watchlist-${stockData.symbol}`);
            
            if (!listItem) {
                // Create a new list item if it doesn't exist
                listItem = document.createElement('li');
                listItem.id = `watchlist-${stockData.symbol}`;
                listItem.className = 'watchlist-item';
                listItem.style.cursor = 'pointer';
                listItem.onclick = () => this.changeChartSymbol(stockData.symbol);
                this.elements.marketWatchlist.appendChild(listItem);
            }

            const oldPrice = parseFloat(listItem.dataset.price || stockData.price);
            const priceChange = stockData.price - oldPrice;

            listItem.dataset.price = stockData.price;
            listItem.innerHTML = `
                <span class="symbol">${stockData.symbol}</span>
                <span class="price">$${stockData.price.toFixed(2)}</span>
            `;
            
            // Add a temporary class for visual feedback on price change
            if (priceChange > 0) {
                listItem.classList.add('price-up');
            } else if (priceChange < 0) {
                listItem.classList.add('price-down');
            }
            setTimeout(() => {
                listItem.classList.remove('price-up', 'price-down');
            }, 500);
        };

        ws.onclose = () => {
            console.log('Market data WebSocket disconnected. Reconnecting in 5s...');
            setTimeout(() => this.connectMarketDataWebSocket(), 5000);
        };
    }

    // --- AI Assistant Chat Methods ---
    connectAIChatWebSocket() {
        this.aiChatSocket = new WebSocket(`ws://${window.location.host}/api/v1/ws/chat`);

        this.aiChatSocket.onopen = () => {
            console.log('Connected to AI Assistant chat WebSocket');
        };

        this.aiChatSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.addMessageToAIChat('agent', data.content);
        };

        this.aiChatSocket.onclose = () => {
            console.log('AI Assistant chat WebSocket disconnected. Reconnecting in 5s...');
            setTimeout(() => this.connectAIChatWebSocket(), 5000);
        };
    }

    sendAIChatMessage(messageOverride = null, isInternal = false) {
        const message = messageOverride || this.elements.aiChatInput.value.trim();
        if (!message || !this.aiChatSocket || this.aiChatSocket.readyState !== WebSocket.OPEN) {
            return;
        }

        if (!isInternal) {
            this.addMessageToAIChat('user', message);
        }

        this.aiChatSocket.send(JSON.stringify({
            message: message,
            context: { page: 'finance' } // Provide context for agent routing
        }));

        this.elements.aiChatInput.value = '';
    }

    addMessageToAIChat(sender, content) {
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${sender}`;
        
        // Simple text for now, can be enhanced with markdown parsing
        const contentEl = document.createElement('p');
        contentEl.textContent = content;
        messageEl.appendChild(contentEl);

        this.elements.aiChatWindow.appendChild(messageEl);
        this.elements.aiChatWindow.scrollTop = this.elements.aiChatWindow.scrollHeight;
    }

    // --- Backtesting Methods ---
    async runBacktest() {
        const strategyEditor = document.querySelector('.strategy-editor textarea');
        const strategy = strategyEditor.value.trim();

        if (!strategy) {
            alert('Please define a strategy in the editor before backtesting.');
            return;
        }

        this.elements.backtestBtn.disabled = true;
        this.elements.backtestBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Backtesting...';

        const resultsContainer = document.getElementById('backtest-results-container');
        const resultsGrid = document.getElementById('backtest-results-grid');
        resultsContainer.style.display = 'block';
        resultsGrid.innerHTML = '<p>Running simulation...</p>';

        try {
            const response = await fetch('/api/v1/finance/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ strategy }),
            });
            const data = await response.json();

            if (response.ok && data.success) {
                const results = data.results;
                resultsGrid.innerHTML = `
                    <div class="metric-card"><strong>Strategy</strong><br>${results.strategy}</div>
                    <div class="metric-card"><strong>P&L</strong><br>${results.pnl} (${results.pnl_percent})</div>
                    <div class="metric-card"><strong>Sharpe Ratio</strong><br>${results.sharpe_ratio}</div>
                    <div class="metric-card"><strong>Win Rate</strong><br>${results.win_rate}</div>
                    <div class="metric-card"><strong>Max Drawdown</strong><br>${results.max_drawdown}</div>
                    <div class="metric-card"><strong>Total Trades</strong><br>${results.total_trades}</div>
                    <div class="metric-card"><strong>Final Capital</strong><br>${results.final_capital}</div>
                `;
            } else {
                throw new Error(data.detail || 'Backtest failed.');
            }
        } catch (error) {
            resultsGrid.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
        } finally {
            this.elements.backtestBtn.disabled = false;
            this.elements.backtestBtn.innerHTML = '<i class="fas fa-history"></i> Backtest';
        }
    }

    // --- Paper Trading Methods ---
    async executePaperTrade(action) {
        const symbol = this.elements.paperSymbolInput.value.trim();
        const quantity = parseFloat(this.elements.paperQuantityInput.value);
        const stopLoss = parseFloat(this.elements.paperStopLossInput.value);
        const takeProfit = parseFloat(this.elements.paperTakeProfitInput.value);

        if (!symbol || !quantity || quantity <= 0) {
            alert('Please enter a valid symbol and quantity.');
            return;
        }

        const btn = action === 'BUY' ? this.elements.paperBuyBtn : this.elements.paperSellBtn;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch('/api/v1/finance/paper-trade/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, quantity, action }),
            });
            const data = await response.json();

            if (response.ok && data.success) {
                showToast(data.message, 'success');
                if (stopLoss) showToast(`Stop-loss order set at $${stopLoss.toFixed(2)}`, 'info');
                if (takeProfit) showToast(`Take-profit order set at $${takeProfit.toFixed(2)}`, 'info');
                await this.updatePaperPortfolio();
            } else {
                throw new Error(data.detail || 'Paper trade failed.');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = action;
        }
    }

    async updatePaperPortfolio() {
        try {
            const response = await fetch('/api/v1/finance/paper-trade/portfolio');
            const data = await response.json();
            if (data.success) {
                const portfolio = data.portfolio;
                document.getElementById('paper-cash-balance').textContent = `$${portfolio.cash.toFixed(2)}`;
                document.getElementById('paper-total-value').textContent = `$${portfolio.total_value.toFixed(2)}`;

                if (Object.keys(portfolio.positions).length === 0) {
                    this.elements.paperPositionsDiv.innerHTML = '<p>No open positions.</p>';
                    return;
                }

                let tableHTML = '<table class="paper-positions-table"><thead><tr><th>Symbol</th><th>Qty</th><th>Avg. Price</th><th>Current Price</th><th>Market Value</th><th>P&L</th><th>Actions</th></tr></thead><tbody>';
                for (const symbol in portfolio.positions) {
                    const pos = portfolio.positions[symbol];
                    const pnlClass = pos.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
                    const positionDetails = `(${pos.quantity} shares @ $${pos.avg_price.toFixed(2)})`;
                    tableHTML += `
                        <tr>
                            <td>${symbol}</td>
                            <td>${pos.quantity}</td>
                            <td>$${pos.avg_price.toFixed(2)}</td>
                            <td>$${pos.current_price.toFixed(2)}</td>
                            <td>$${pos.market_value.toFixed(2)}</td>
                            <td class="${pnlClass}">${pos.pnl >= 0 ? '+' : ''}$${pos.pnl.toFixed(2)}</td>
                            <td><button class="btn btn-xs btn-outline-info explain-position-btn" data-symbol="${symbol}" data-details="${positionDetails}"><i class="fas fa-info-circle"></i></button></td>
                        </tr>
                    `;
                }
                tableHTML += '</tbody></table>';
                this.elements.paperPositionsDiv.innerHTML = tableHTML;
            }
        } catch (error) {
            this.elements.paperPositionsDiv.innerHTML = `<p class="text-danger">Could not load portfolio: ${error.message}</p>`;
        }

        // Add event listeners for the new explain buttons
        this.elements.paperPositionsDiv.querySelectorAll('.explain-position-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const symbol = e.currentTarget.dataset.symbol;
                const details = e.currentTarget.dataset.details;
                const prompt = `Explain my position in ${symbol} ${details}`;
                this.addMessageToAIChat('user', prompt);
                this.sendAIChatMessage(prompt, true);
            });
        });
    }

    // --- Analytics Methods ---
    updatePerformanceAnalytics(pnl, winRate, sharpeRatio, maxDrawdown) {
        this.elements.analyticsTotalPnl.textContent = `$${pnl.toFixed(2)}`;
        this.elements.analyticsTotalPnl.className = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        this.elements.analyticsWinRate.textContent = `${winRate.toFixed(2)}%`;
        this.elements.analyticsSharpeRatio.textContent = `${sharpeRatio.toFixed(2)}`;
        this.elements.analyticsMaxDrawdown.textContent = `${maxDrawdown.toFixed(2)}%`;
    }

    async renderPortfolioAnalytics() {
        const container = document.getElementById('portfolio-analytics-container');
        if (!container) return;

        container.innerHTML = '<div class="text-center py-4"><div class="spinner"></div><p>Loading analytics...</p></div>';

        try {
            const response = await fetch('/api/v1/finance/portfolio/analytics');
            if (!response.ok) throw new Error('Failed to load portfolio analytics.');

            const result = await response.json();
            if (result.success && result.analytics) {
                const analytics = result.analytics;
                // For now, we will just display the raw data. Charting can be added next.
                container.innerHTML = `
                    <h4>Asset Allocation</h4>
                    <pre>${JSON.stringify(analytics.allocation, null, 2)}</pre>
                    <h4 class="mt-4">Historical Performance (Simulated)</h4>
                    <pre>${JSON.stringify(analytics.historical_performance.slice(-5), null, 2)}...</pre>
                `;
            }
        } catch (error) {
            container.innerHTML = `<p class="text-danger">${error.message}</p>`;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FinanceDashboard();
});

// Helper function, assuming showToast is globally available from app.js
function showToast(message, type) {
    // This is a placeholder. A real implementation would create a toast element.
    console.log(`[Toast - ${type}]: ${message}`);
}