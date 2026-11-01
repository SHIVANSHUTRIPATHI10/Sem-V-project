console.log("Dashboard.js loaded successfully.");

let riskChartInstance = null;
let shapChartInstance = null;

// Run initial loads
loadStats();
loadAlerts();
startLiveTicker();


// ============================================================
// UI UTILITIES (Toast, Modal, Loading)
// ============================================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '🚨';
    
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function closeModal() {
    document.getElementById('welcomeModal').style.display = 'none';
}

function filterTable(tableId, query) {
    const table = document.getElementById(tableId);
    const rows = table.getElementsByTagName('tr');
    const filter = query.toLowerCase();
    
    for (let i = 0; i < rows.length; i++) {
        const text = rows[i].textContent.toLowerCase();
        rows[i].style.display = text.includes(filter) ? '' : 'none';
    }
}


// ============================================================
// SIDEBAR NAVIGATION (SPA LOGIC)
// ============================================================
function switchView(targetId, element) {
    document.querySelectorAll('.menu').forEach(m => m.classList.remove('active'));
    if (element) element.classList.add('active');

    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    
    const targetView = document.getElementById(targetId);
    if (targetView) {
        targetView.classList.add('active');
    }

    const title = document.getElementById('pageTitle');
    const subtitle = document.getElementById('pageSubtitle');
    
    if (targetId === 'dashboard-view') {
        title.textContent = "Fraud Detection Dashboard";
        subtitle.textContent = "AI-Based Multi-Model Financial Risk Monitoring";
        loadStats();
    } else if (targetId === 'transactions-view') {
        title.textContent = "Transaction History";
        subtitle.textContent = "Complete log of analyzed transactions";
        loadTransactions();
    } else if (targetId === 'alerts-view') {
        title.textContent = "Fraud Alerts";
        subtitle.textContent = "High and Medium risk transactions requiring review";
        loadAlerts();
    } else if (targetId === 'analysis-view') {
        title.textContent = "Risk Analysis";
        subtitle.textContent = "Understanding the AI detection models";
    }
}


// ============================================================
// TRANSACTION SIMULATOR
// ============================================================
function simulateSafe() {
    document.getElementById("transaction_id").value = "TXN_SAFE_" + Date.now();
    document.getElementById("amount").value = 100; 
    document.getElementById("oldbalanceOrg").value = 1000000; 
    document.getElementById("oldbalanceDest").value = 500000;
    document.getElementById("type").value = "PAYMENT";
    document.getElementById("step").value = 360;
    document.getElementById("nameDest").value = "M12345678";
    showToast("Safe transaction template loaded.", "success");
}

function simulateFraud() {
    document.getElementById("transaction_id").value = "TXN_FRAUD_" + Date.now();
    document.getElementById("amount").value = 999999; 
    document.getElementById("oldbalanceOrg").value = 1000000; 
    document.getElementById("oldbalanceDest").value = 0; 
    document.getElementById("type").value = "TRANSFER";
    document.getElementById("step").value = 360;
    document.getElementById("nameDest").value = "C99999999";
    showToast("Fraud transaction template loaded.", "error");
}


// ============================================================
// CHART.JS RENDERING
// ============================================================
function renderRiskChart(high, medium, low) {
    const canvas = document.getElementById('riskChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (riskChartInstance) riskChartInstance.destroy();

    riskChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Risk', 'Medium Risk', 'Low Risk'],
            datasets: [{
                data: [high, medium, low],
                backgroundColor: ['#EF4444', '#F59E0B', '#10B981'],
                borderWidth: 0, hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom', labels: { color: '#F8FAFC', font: { family: 'Inter', size: 13 } } } },
            cutout: '70%'
        }
    });
}

function renderShapChart(labels, values) {
    const canvas = document.getElementById('shapChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (shapChartInstance) shapChartInstance.destroy();

    const backgroundColors = values.map(v => v > 0 ? '#EF4444' : '#10B981');

    shapChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Impact on Risk Score',
                data: values,
                backgroundColor: backgroundColors,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let value = context.raw;
                            return value > 0 ? `+${value} (Increases Risk)` : `${value} (Decreases Risk)`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { color: '#334155' }, ticks: { color: '#94A3B8' } },
                y: { grid: { display: false }, ticks: { color: '#F8FAFC' } }
            }
        }
    });
}


// ============================================================
// ANALYZE TRANSACTION
// ============================================================
async function analyzeTransaction(event) {
    event.preventDefault();

    // Set Loading State
    const btn = document.getElementById("analyzeBtn");
    const btnText = btn.querySelector(".btn-text");
    const btnLoader = btn.querySelector(".btn-loader");
    btnText.style.display = "none";
    btnLoader.style.display = "inline-block";
    btn.disabled = true;

    const transaction = {
        transaction_id: document.getElementById("transaction_id").value,
        amount: Number(document.getElementById("amount").value),
        oldbalanceOrg: Number(document.getElementById("oldbalanceOrg").value),
        oldbalanceDest: Number(document.getElementById("oldbalanceDest").value),
        type: document.getElementById("type").value,
        step: Number(document.getElementById("step").value),
        nameDest: document.getElementById("nameDest").value
    };

    try {
        const response = await fetch("/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(transaction)
        });

        const data = await response.json();

        if (!response.ok) { 
            showToast(data.detail || "Prediction failed", "error"); 
            return; 
        }

        document.getElementById("predictionResult").style.display = "block";
        document.getElementById("resultXgb").textContent = data.xgb_score;
        document.getElementById("resultLstm").textContent = data.lstm_score === null ? "Not enough history" : data.lstm_score;
        document.getElementById("resultAe").textContent = data.ae_score;
        document.getElementById("resultRisk").textContent = data.risk_score;
        
        const riskLevelEl = document.getElementById("resultRiskLevel");
        riskLevelEl.textContent = data.risk_level;
        riskLevelEl.style.color = data.risk_level === "HIGH" ? "#EF4444" : data.risk_level === "MEDIUM" ? "#F59E0B" : "#10B981";

        document.getElementById("resultDecision").textContent = data.decision;

        // Show toast based on result
        if (data.risk_level === "HIGH") showToast(`HIGH RISK: Transaction ${transaction.transaction_id} flagged!`, "error");
        else if (data.risk_level === "MEDIUM") showToast(`MEDIUM RISK: Verification required for ${transaction.transaction_id}`, "info");
        else showToast(`Transaction ${transaction.transaction_id} approved.`, "success");

        const list = document.getElementById("explanationsList");
        list.innerHTML = "";
        const labels = [];
        const values = [];

        data.explanations.forEach(exp => {
            const li = document.createElement("li");
            li.textContent = exp.text;
            list.appendChild(li);
            labels.push(exp.feature);
            values.push(exp.value);
        });

        if (labels.length > 0) {
            renderShapChart(labels, values);
        }

        await loadStats();
        await loadAlerts();

    } catch (error) {
        console.error("Prediction error:", error);
        showToast("Could not connect to the server.", "error");
    } finally {
        // Reset Loading State
        btnText.style.display = "inline-block";
        btnLoader.style.display = "none";
        btn.disabled = false;
    }
}


// ============================================================
// LOAD STATS
// ============================================================
async function loadStats() {
    try {
        const response = await fetch("/dashboard/stats");
        const data = await response.json();

        document.getElementById("totalTransactions").textContent = data.total_transactions;
        document.getElementById("totalAlerts").textContent = data.total_alerts;
        document.getElementById("highRisk").textContent = data.high_risk;
        document.getElementById("mediumRisk").textContent = data.medium_risk;
        document.getElementById("lowRisk").textContent = data.low_risk;

        renderRiskChart(data.high_risk, data.medium_risk, data.low_risk);
    } catch (error) {
        console.error("Error loading dashboard stats:", error);
    }
}


// ============================================================
// LIVE ACTIVITY TICKER
// ============================================================
async function startLiveTicker() {
    setInterval(async () => {
        try {
            const response = await fetch("/alerts");
            const data = await response.json();
            const feed = document.getElementById("liveFeed");

            if (data.alerts && data.alerts.length > 0) {
                if (feed.children.length === 1 && feed.children[0].tagName === 'P') {
                    feed.innerHTML = "";
                }

                const latest = data.alerts[0];
                const item = document.createElement("div");
                item.className = `live-feed-item ${latest.risk_level.toLowerCase()}`;
                
                item.innerHTML = `
                    <div>
                        <strong style="font-size: 13px;">${latest.transaction_id}</strong><br>
                        <span style="font-size: 12px; color: #94A3B8;">${latest.type} - $${latest.amount.toLocaleString()}</span>
                    </div>
                    <span class="badge ${latest.risk_level.toLowerCase()}">${latest.risk_level}</span>
                `;

                feed.insertBefore(item, feed.firstChild);

                if (feed.children.length > 5) {
                    feed.removeChild(feed.lastChild);
                }
            }
        } catch (error) {
            console.error("Ticker error:", error);
        }
    }, 5000);
}


// ============================================================
// LOAD TABLES & FEEDBACK
// ============================================================
function formatCurrency(amount) {
    return '$' + amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getBadgeClass(level) {
    if (level === "HIGH") return "high";
    if (level === "MEDIUM") return "medium";
    return "low";
}

async function submitFeedback(transactionId, feedbackType) {
    try {
        await fetch(`/alerts/${transactionId}/feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ feedback: feedbackType })
        });
        showToast(`Feedback saved: ${feedbackType.replace('_', ' ')}`, "success");
        loadAlerts(); 
    } catch (error) {
        console.error("Error submitting feedback:", error);
        showToast("Failed to save feedback.", "error");
    }
}

async function loadAlerts() {
    try {
        const response = await fetch("/alerts");
        const data = await response.json();
        const tableBody = document.getElementById("alertsTable");
        tableBody.innerHTML = "";

        if (!data.alerts || data.alerts.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94A3B8; padding: 30px;">No fraud alerts found.</td></tr>`;
            return;
        }

        data.alerts.forEach(alert => {
            const row = document.createElement("tr");
            
            let actionHtml = `
                <button class="btn-sm btn-fraud" onclick="submitFeedback('${alert.transaction_id}', 'CONFIRMED_FRAUD')">Confirm Fraud</button>
                <button class="btn-sm btn-safe" onclick="submitFeedback('${alert.transaction_id}', 'FALSE_POSITIVE')">Mark Safe</button>
            `;
            
            if (alert.analyst_feedback === 'CONFIRMED_FRAUD') {
                actionHtml = `<span class="badge high">Confirmed Fraud</span>`;
            } else if (alert.analyst_feedback === 'FALSE_POSITIVE') {
                actionHtml = `<span class="badge low">Marked Safe</span>`;
            }

            row.innerHTML = `
                <td><strong>${alert.transaction_id}</strong></td>
                <td>${alert.type}</td>
                <td>${formatCurrency(alert.amount)}</td>
                <td><strong>${alert.risk_score}</strong></td>
                <td><span class="badge ${getBadgeClass(alert.risk_level)}">${alert.risk_level}</span></td>
                <td>${actionHtml}</td>
            `;
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error("Error loading alerts:", error);
    }
}

async function loadTransactions() {
    try {
        const response = await fetch("/transactions");
        const data = await response.json();
        const tableBody = document.getElementById("transactionsTable");
        tableBody.innerHTML = "";

        if (!data.transactions || data.transactions.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #94A3B8; padding: 30px;">No transactions found.</td></tr>`;
            return;
        }

        data.transactions.forEach(tx => {
            const row = document.createElement("tr");
            
            let feedbackText = "-";
            if (tx.analyst_feedback === 'CONFIRMED_FRAUD') feedbackText = `<span class="badge high">Fraud</span>`;
            if (tx.analyst_feedback === 'FALSE_POSITIVE') feedbackText = `<span class="badge low">Safe</span>`;

            row.innerHTML = `
                <td><strong>${tx.transaction_id}</strong></td>
                <td>${tx.step}</td>
                <td>${tx.type}</td>
                <td>${formatCurrency(tx.amount)}</td>
                <td><span class="badge ${getBadgeClass(tx.risk_level)}">${tx.risk_level}</span></td>
                <td>${tx.decision}</td>
                <td>${feedbackText}</td>
            `;
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error("Error loading transactions:", error);
    }
}

document.getElementById("predictionForm").addEventListener("submit", analyzeTransaction);