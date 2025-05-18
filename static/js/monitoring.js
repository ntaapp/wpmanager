document.addEventListener('DOMContentLoaded', function() {
    // Server status checks
    const checkServerStatus = async function() {
        try {
            const response = await fetch('/monitoring/api/stats');
            const data = await response.json();
            
            // Update CPU usage
            const cpuGauge = document.getElementById('cpu-gauge');
            if (cpuGauge) {
                const cpuUsage = data.cpu_usage || 0;
                updateGauge(cpuGauge, cpuUsage);
                document.getElementById('cpu-usage-text').textContent = `${cpuUsage.toFixed(1)}%`;
            }
            
            // Update memory usage
            const memoryGauge = document.getElementById('memory-gauge');
            if (memoryGauge) {
                const memoryUsage = data.memory_usage || 0;
                updateGauge(memoryGauge, memoryUsage);
                document.getElementById('memory-usage-text').textContent = `${memoryUsage.toFixed(1)}%`;
                
                if (data.memory_total) {
                    const memoryTotal = formatBytes(data.memory_total);
                    const memoryUsedBytes = formatBytes(data.memory_used || 0);
                    document.getElementById('memory-details').textContent = `${memoryUsedBytes} / ${memoryTotal}`;
                }
            }
            
            // Update disk usage
            const diskGauge = document.getElementById('disk-gauge');
            if (diskGauge) {
                const diskUsage = data.disk_usage || 0;
                updateGauge(diskGauge, diskUsage);
                document.getElementById('disk-usage-text').textContent = `${diskUsage.toFixed(1)}%`;
                
                if (data.disk_total) {
                    const diskTotal = formatBytes(data.disk_total);
                    const diskUsedBytes = formatBytes(data.disk_used || 0);
                    document.getElementById('disk-details').textContent = `${diskUsedBytes} / ${diskTotal}`;
                }
            }
            
            // Update load average
            const loadAvgElement = document.getElementById('load-average');
            if (loadAvgElement && data.load_average) {
                loadAvgElement.textContent = data.load_average.join(' | ');
            }
            
            // Update uptime
            const uptimeElement = document.getElementById('uptime');
            if (uptimeElement && data.uptime) {
                uptimeElement.textContent = formatUptime(data.uptime);
            }
            
            // Update service status
            updateServiceStatus('web-server-status', data.web_server);
            updateServiceStatus('database-status', data.database);
            updateServiceStatus('netdata-status', data.netdata);
            updateServiceStatus('glances-status', data.glances);
            
        } catch (error) {
            console.error('Error fetching server status:', error);
        }
    };
    
    // Update gauge visualization
    function updateGauge(element, value) {
        const percentage = Math.min(100, Math.max(0, value));
        const angle = (percentage / 100) * 180;
        const needle = element.querySelector('.gauge-needle');
        
        if (needle) {
            needle.style.transform = `rotate(${angle}deg)`;
        }
        
        // Update color based on value
        let color;
        if (percentage < 60) {
            color = '#4caf50'; // Green
        } else if (percentage < 80) {
            color = '#ff9800'; // Orange
        } else {
            color = '#f44336'; // Red
        }
        
        if (needle) {
            needle.style.backgroundColor = color;
        }
        
        // Update value text
        const valueText = element.querySelector('.gauge-value');
        if (valueText) {
            valueText.textContent = `${percentage.toFixed(1)}%`;
            valueText.style.color = color;
        }
    }
    
    // Update service status indicator
    function updateServiceStatus(elementId, isRunning) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        if (isRunning) {
            element.classList.remove('bg-danger');
            element.classList.add('bg-success');
            element.textContent = 'Running';
        } else {
            element.classList.remove('bg-success');
            element.classList.add('bg-danger');
            element.textContent = 'Stopped';
        }
    }
    
    // Format uptime from seconds
    function formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        let result = '';
        if (days > 0) {
            result += `${days}d `;
        }
        if (hours > 0 || days > 0) {
            result += `${hours}h `;
        }
        result += `${minutes}m`;
        
        return result;
    }
    
    // Refresh monitoring data every 30 seconds
    const monitoringPage = document.getElementById('monitoring-page');
    if (monitoringPage) {
        checkServerStatus();
        setInterval(checkServerStatus, 30000);
    }
    
    // Handle restart service buttons
    document.querySelectorAll('.restart-service-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const serviceName = this.getAttribute('data-service');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to restart the ${serviceName} service?`)) {
                form.submit();
            }
        });
    });
    
    // Create CPU usage chart if Chart.js is available
    const cpuChartCanvas = document.getElementById('cpu-chart');
    if (typeof Chart !== 'undefined' && cpuChartCanvas) {
        const ctx = cpuChartCanvas.getContext('2d');
        
        // Initialize with empty data
        const cpuChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(10).fill('').map((_, i) => `-${9-i}m`),
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: Array(10).fill(null),
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // Update chart with new data point every 30 seconds
        setInterval(async function() {
            try {
                const response = await fetch('/monitoring/api/stats');
                const data = await response.json();
                
                const cpuUsage = data.cpu_usage || 0;
                
                // Add new data point
                cpuChart.data.datasets[0].data.push(cpuUsage);
                cpuChart.data.datasets[0].data.shift();
                
                // Update time labels
                const now = new Date();
                const timeLabel = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
                cpuChart.data.labels.push(timeLabel);
                cpuChart.data.labels.shift();
                
                cpuChart.update();
            } catch (error) {
                console.error('Error updating CPU chart:', error);
            }
        }, 30000);
    }
});
