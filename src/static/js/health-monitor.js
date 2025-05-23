/**
 * API服务健康监控页面的JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // 图表对象，用于后续更新
    let latencyChart = null;
    let successRateChart = null;
    let trendChart = null;
    
    // 缓存的健康数据
    let healthData = null;
    
    // 刷新按钮事件
    document.getElementById('refreshBtn').addEventListener('click', function() {
        fetchHealthData();
    });
    
    // 主题切换按钮
    document.getElementById('themeToggle').addEventListener('click', function() {
        const currentTheme = document.body.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-bs-theme', newTheme);
        
        // 更新按钮图标
        const icon = this.querySelector('i');
        icon.classList.toggle('bi-moon-stars');
        icon.classList.toggle('bi-sun');
        
        // 保存主题设置到本地存储
        localStorage.setItem('theme', newTheme);
        
        // 重新渲染图表以适应新主题
        if (healthData) {
            updateCharts(healthData);
        }
    });
    
    // 初始加载
    fetchHealthData();
    
    /**
     * 获取API健康状态数据
     */
    function fetchHealthData() {
        // 更新按钮状态
        const refreshBtn = document.getElementById('refreshBtn');
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 加载中...';
        
        // 发起API请求
        fetch('/api/advanced/health')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.health) {
                    healthData = data.health;
                    updateHealthDisplay(healthData);
                    updateCharts(healthData);
                    fetchGlobalData();  // 加载全球数据
                    
                    // 更新最后更新时间
                    const lastUpdated = document.getElementById('lastUpdated');
                    const updateTime = new Date().toLocaleTimeString();
                    lastUpdated.textContent = `最后更新: ${updateTime}`;
                } else {
                    showError('获取健康数据失败');
                }
            })
            .catch(error => {
                console.error('请求出错:', error);
                showError('网络请求失败');
            })
            .finally(() => {
                // 恢复按钮状态
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 刷新状态';
            });
    }
    
    /**
     * 获取全球各地区的健康状态数据
     */
    function fetchGlobalData() {
        fetch('/api/advanced/health/global')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.global_health) {
                    updateRegionalData(data.global_health);
                }
            })
            .catch(error => {
                console.error('获取全球数据失败:', error);
            });
    }
    
    /**
     * 更新健康状态显示
     */
    function updateHealthDisplay(data) {
        // 更新总体状态
        const overallStatus = document.getElementById('overallStatusText');
        const statusIndicator = document.getElementById('overallStatusIndicator');
        
        overallStatus.textContent = data.overall_status || '未知';
        
        // 根据状态设置颜色
        statusIndicator.className = 'status-circle mb-2';
        if (data.overall_status === '全部正常') {
            statusIndicator.classList.add('bg-success');
            statusIndicator.innerHTML = '<i class="bi bi-check-lg"></i>';
        } else if (data.overall_status === '全部故障') {
            statusIndicator.classList.add('bg-danger');
            statusIndicator.innerHTML = '<i class="bi bi-x-lg"></i>';
        } else {
            statusIndicator.classList.add('bg-warning');
            statusIndicator.innerHTML = '<i class="bi bi-exclamation-triangle"></i>';
        }
        
        // 更新各提供商状态
        if (data.providers) {
            for (const [provider, info] of Object.entries(data.providers)) {
                const statusElement = document.getElementById(`status${provider}`);
                if (statusElement) {
                    statusElement.className = 'status-badge badge';
                    
                    if (info.status === 'operational') {
                        statusElement.classList.add('bg-success');
                        statusElement.textContent = '正常';
                    } else if (info.status === 'degraded') {
                        statusElement.classList.add('bg-warning');
                        statusElement.textContent = '性能下降';
                    } else if (info.status === 'down') {
                        statusElement.classList.add('bg-danger');
                        statusElement.textContent = '故障';
                    } else {
                        statusElement.classList.add('bg-secondary');
                        statusElement.textContent = '未知';
                    }
                }
            }
        }
    }
    
    /**
     * 更新图表
     */
    function updateCharts(data) {
        if (!data.providers) return;
        
        const providers = Object.keys(data.providers);
        const providerColors = {
            'OpenAI': 'rgba(16, 163, 127, 0.8)', // OpenAI绿色
            'Claude': 'rgba(100, 116, 139, 0.8)', // Anthropic灰色
            'Gemini': 'rgba(66, 133, 244, 0.8)',  // Google蓝色
            'Cohere': 'rgba(103, 58, 183, 0.8)',  // 紫色
            'Mistral': 'rgba(255, 136, 0, 0.8)'   // 橙色
        };
        
        // 提取延迟数据
        const avgLatencies = [];
        const maxLatencies = [];
        const minLatencies = [];
        
        providers.forEach(provider => {
            const providerData = data.providers[provider];
            if (providerData.latency_ms) {
                avgLatencies.push(providerData.latency_ms.avg || 0);
                maxLatencies.push(providerData.latency_ms.max || 0);
                minLatencies.push(providerData.latency_ms.min || 0);
            } else {
                avgLatencies.push(0);
                maxLatencies.push(0);
                minLatencies.push(0);
            }
        });
        
        // 更新延迟图表
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        
        // 销毁旧图表
        if (latencyChart) {
            latencyChart.destroy();
        }
        
        // 创建新图表
        latencyChart = new Chart(latencyCtx, {
            type: 'bar',
            data: {
                labels: providers,
                datasets: [
                    {
                        label: '平均延迟 (ms)',
                        data: avgLatencies,
                        backgroundColor: providers.map(p => providerColors[p] || 'rgba(54, 162, 235, 0.8)'),
                        borderColor: providers.map(p => providerColors[p]?.replace('0.8', '1') || 'rgba(54, 162, 235, 1)'),
                        borderWidth: 1
                    }
                ]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '毫秒 (ms)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'API服务响应时间比较'
                    }
                }
            }
        });
        
        // 更新延迟表格
        const latencyTableBody = document.getElementById('latencyTableBody');
        latencyTableBody.innerHTML = '';
        
        providers.forEach((provider, index) => {
            const providerData = data.providers[provider];
            const row = document.createElement('tr');
            
            // 状态样式
            let statusClass = 'bg-secondary';
            let statusText = '未知';
            
            if (providerData.status === 'operational') {
                statusClass = 'bg-success';
                statusText = '正常';
            } else if (providerData.status === 'degraded') {
                statusClass = 'bg-warning';
                statusText = '性能下降';
            } else if (providerData.status === 'down') {
                statusClass = 'bg-danger';
                statusText = '故障';
            }
            
            row.innerHTML = `
                <td>${provider}</td>
                <td>${providerData.latency_ms ? providerData.latency_ms.avg.toFixed(2) : 'N/A'} ms</td>
                <td>${providerData.latency_ms ? providerData.latency_ms.min.toFixed(2) : 'N/A'} ms</td>
                <td>${providerData.latency_ms ? providerData.latency_ms.max.toFixed(2) : 'N/A'} ms</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            `;
            
            latencyTableBody.appendChild(row);
        });
        
        // 更新成功率图表
        const successRates = providers.map(provider => 
            data.providers[provider].success_rate || 0);
            
        const successRateCtx = document.getElementById('successRateChart').getContext('2d');
        
        // 销毁旧图表
        if (successRateChart) {
            successRateChart.destroy();
        }
        
        // 创建新图表
        successRateChart = new Chart(successRateCtx, {
            type: 'bar',
            data: {
                labels: providers,
                datasets: [
                    {
                        label: '成功率 (%)',
                        data: successRates,
                        backgroundColor: providers.map(p => providerColors[p] || 'rgba(75, 192, 192, 0.8)'),
                        borderColor: providers.map(p => providerColors[p]?.replace('0.8', '1') || 'rgba(75, 192, 192, 1)'),
                        borderWidth: 1
                    }
                ]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: '成功率 (%)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'API服务请求成功率'
                    }
                }
            }
        });
        
        // 更新成功率表格
        const successRateTableBody = document.getElementById('successRateTableBody');
        successRateTableBody.innerHTML = '';
        
        providers.forEach((provider, index) => {
            const providerData = data.providers[provider];
            const row = document.createElement('tr');
            
            // 状态样式
            let statusClass = 'bg-secondary';
            let statusText = '未知';
            
            if (providerData.status === 'operational') {
                statusClass = 'bg-success';
                statusText = '正常';
            } else if (providerData.status === 'degraded') {
                statusClass = 'bg-warning';
                statusText = '性能下降';
            } else if (providerData.status === 'down') {
                statusClass = 'bg-danger';
                statusText = '故障';
            }
            
            row.innerHTML = `
                <td>${provider}</td>
                <td>${providerData.success_rate ? providerData.success_rate.toFixed(2) : 'N/A'}%</td>
                <td>N/A</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            `;
            
            successRateTableBody.appendChild(row);
        });
        
        // 更新趋势图表（模拟数据）
        updateTrendChart(providers, providerColors);
    }
    
    /**
     * 更新趋势图表（使用模拟数据）
     */
    function updateTrendChart(providers, providerColors) {
        // 生成24小时的时间标签
        const hours = Array.from({length: 24}, (_, i) => `${i}:00`);
        
        // 为每个提供商生成模拟数据
        const datasets = providers.map(provider => {
            // 生成模拟的可用性数据（85%到100%之间的随机值）
            const generateRandomData = () => {
                return Array.from({length: 24}, () => Math.floor(Math.random() * 15) + 85);
            };
            
            return {
                label: provider,
                data: generateRandomData(),
                borderColor: providerColors[provider] || 'rgba(54, 162, 235, 1)',
                backgroundColor: 'transparent',
                tension: 0.4
            };
        });
        
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        
        // 销毁旧图表
        if (trendChart) {
            trendChart.destroy();
        }
        
        // 创建新图表
        trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: datasets
            },
            options: {
                scales: {
                    y: {
                        min: 80,
                        max: 100,
                        title: {
                            display: true,
                            text: '可用性 (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '时间 (小时)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: '24小时可用性趋势'
                    }
                }
            }
        });
    }
    
    /**
     * 更新区域数据显示
     */
    function updateRegionalData(globalData) {
        if (!globalData || !globalData.regions) return;
        
        const regionalCards = document.getElementById('regionalCards');
        regionalCards.innerHTML = '';
        
        // 为每个区域创建卡片
        for (const [region, data] of Object.entries(globalData.regions)) {
            const card = document.createElement('div');
            card.className = 'col';
            
            // 确定区域整体状态
            let statusClass = 'bg-success';
            let statusIcon = 'check-circle-fill';
            
            if (data.status === 'degraded') {
                statusClass = 'bg-warning';
                statusIcon = 'exclamation-triangle-fill';
            } else if (data.status === 'down') {
                statusClass = 'bg-danger';
                statusIcon = 'x-circle-fill';
            }
            
            // 构建提供商状态列表
            let providersHtml = '';
            for (const [provider, providerData] of Object.entries(data.providers)) {
                let providerStatusClass = 'success';
                
                if (providerData.status === 'degraded') {
                    providerStatusClass = 'warning';
                } else if (providerData.status === 'down') {
                    providerStatusClass = 'danger';
                }
                
                providersHtml += `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span>${provider}</span>
                        <div>
                            <span class="badge bg-${providerStatusClass} me-1">
                                ${providerData.status === 'operational' ? '正常' : 
                                  providerData.status === 'degraded' ? '性能下降' : '故障'}
                            </span>
                            <span class="small">${providerData.latency_ms ? providerData.latency_ms.toFixed(0) + 'ms' : 'N/A'}</span>
                        </div>
                    </div>
                `;
            }
            
            card.innerHTML = `
                <div class="card h-100">
                    <div class="card-header ${statusClass} text-white">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0"><i class="bi bi-globe"></i> ${region}</h5>
                            <i class="bi bi-${statusIcon}"></i>
                        </div>
                    </div>
                    <div class="card-body">
                        ${providersHtml}
                    </div>
                </div>
            `;
            
            regionalCards.appendChild(card);
        }
    }
    
    /**
     * 显示错误消息
     */
    function showError(message) {
        // 创建警告提示
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // 添加到页面顶部
        const container = document.querySelector('.container');
        container.insertBefore(alert, container.firstChild);
        
        // 5秒后自动关闭
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    }
});