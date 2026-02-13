/**
 * 高级API密钥分析页面的JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const analyzeForm = document.getElementById('analyzeForm');
    const apiKeyInput = document.getElementById('apiKey');
    const togglePasswordButton = document.getElementById('togglePassword');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsCard = document.getElementById('resultsCard');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const performanceSection = document.getElementById('performanceSection');
    
    // 密码可见性切换
    togglePasswordButton.addEventListener('click', function() {
        const type = apiKeyInput.getAttribute('type') === 'password' ? 'text' : 'password';
        apiKeyInput.setAttribute('type', type);
        
        // 切换图标
        const icon = togglePasswordButton.querySelector('i');
        icon.classList.toggle('bi-eye');
        icon.classList.toggle('bi-eye-slash');
    });
    
    // 表单提交处理
    analyzeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 获取表单数据
        const apiKey = apiKeyInput.value.trim();
        const checkModels = document.getElementById('checkModels').checked;
        const checkQuota = document.getElementById('checkQuota').checked;
        const checkPerformance = document.getElementById('checkPerformance').checked;
        const preferredModelInput = document.getElementById('preferredModel');
        const preferredModel = preferredModelInput ? preferredModelInput.value.trim() : '';
        
        if (!apiKey) {
            showError('请输入API密钥');
            return;
        }
        
        // 显示加载状态
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 分析中...';
        
        // 隐藏之前的结果和错误
        resultsCard.classList.add('d-none');
        errorAlert.classList.add('d-none');
        
        // 调用API进行分析
        fetch('/api/advanced/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: apiKey,
                check_models: checkModels,
                check_quota: checkQuota,
                check_performance: checkPerformance,
                model: preferredModel || null
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.result) {
                displayResults(data.result, checkPerformance);
            } else {
                showError(data.error || '分析过程中出现错误');
            }
        })
        .catch(error => {
            showError('请求失败: ' + error.message);
        })
        .finally(() => {
            // 恢复按钮状态
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="bi bi-search"></i> 开始分析';
        });
    });
    
    // 复制结果按钮
    document.getElementById('copyResultsBtn').addEventListener('click', function() {
        // 获取当前显示的结果信息
        const apiType = document.getElementById('result-api-type').textContent;
        const status = document.getElementById('result-status').textContent;
        const capabilities = document.getElementById('result-capabilities').textContent;
        const selectedModel = document.getElementById('result-selected-model').textContent;
        const effectiveModel = document.getElementById('result-effective-model').textContent;
        const quota = document.getElementById('result-quota').textContent;
        const expiry = document.getElementById('result-expiry').textContent;
        
        // 构建文本内容
        let text = `API密钥分析结果:\n`;
        text += `API类型: ${apiType}\n`;
        text += `状态: ${status}\n`;
        text += `支持的能力: ${capabilities}\n`;
        text += `请求模型: ${selectedModel}\n`;
        text += `实际检测模型: ${effectiveModel}\n`;
        text += `配额信息: ${quota}\n`;
        text += `到期时间: ${expiry}\n\n`;
        
        // 获取模型列表
        const modelsList = document.getElementById('result-models-list');
        if (modelsList && !modelsList.querySelector('.alert')) {
            text += `支持的模型:\n`;
            const models = modelsList.querySelectorAll('.badge');
            models.forEach(model => {
                text += `- ${model.textContent.trim()}\n`;
            });
        }
        
        // 复制到剪贴板
        navigator.clipboard.writeText(text)
            .then(() => {
                alert('分析结果已复制到剪贴板');
            })
            .catch(err => {
                console.error('复制失败:', err);
                alert('复制失败，请手动选择并复制');
            });
    });
    
    // 导出JSON按钮
    document.getElementById('exportJsonBtn').addEventListener('click', function() {
        // 导出当前结果为JSON文件
        if (window.analysisResult) {
            const dataStr = JSON.stringify(window.analysisResult, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const exportFileDefaultName = `api-analysis-${timestamp}.json`;
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
        } else {
            alert('没有可导出的分析结果');
        }
    });
    
    // 显示错误消息
    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
    }
    
    // 显示分析结果
    function displayResults(result, showPerformance) {
        // 存储完整结果供导出使用
        window.analysisResult = result;
        
        // 填充基本信息
        document.getElementById('result-api-type').textContent = result.api_type || '未知';
        
        // 显示API密钥状态
        const statusElement = document.getElementById('result-status');
        if (result.valid) {
            statusElement.textContent = '有效';
            statusElement.classList.add('text-success');
            statusElement.classList.remove('text-danger');
        } else {
            statusElement.textContent = '无效 - ' + (result.error || '未知错误');
            statusElement.classList.add('text-danger');
            statusElement.classList.remove('text-success');
        }
        
        // 显示功能和能力
        const capabilitiesElement = document.getElementById('result-capabilities');
        if (result.capabilities && result.capabilities.length > 0) {
            capabilitiesElement.textContent = result.capabilities.join(', ');
        } else {
            capabilitiesElement.textContent = '未检测到';
        }

        // 显示模型对齐信息
        document.getElementById('result-selected-model').textContent = result.selected_model || '未指定';
        document.getElementById('result-effective-model').textContent = result.effective_model || '未提供';
        
        // 显示配额信息
        document.getElementById('result-quota').textContent = result.quota || '未检测到';
        document.getElementById('result-expiry').textContent = result.expiration || '未检测到';
        
        // 显示模型列表
        const modelsListElement = document.getElementById('result-models-list');
        modelsListElement.innerHTML = '';
        
        if (result.models && result.models.length > 0) {
            const modelsContainer = document.createElement('div');
            modelsContainer.className = 'd-flex flex-wrap gap-2';
            
            result.models.forEach(model => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-primary';
                badge.textContent = model;
                modelsContainer.appendChild(badge);
            });
            
            modelsListElement.appendChild(modelsContainer);
        } else {
            modelsListElement.innerHTML = '<div class="alert alert-secondary">未获取模型信息</div>';
        }
        
        // 显示性能分析（如果启用）
        if (showPerformance && result.performance) {
            performanceSection.classList.remove('d-none');
            
            // 更新成功率
            const successRateElement = document.getElementById('result-success-rate');
            successRateElement.querySelector('.display-4').textContent = 
                result.performance.success_rate ? `${result.performance.success_rate}%` : 'N/A';
            
            // 绘制延迟图表
            if (result.performance.latency) {
                const latencyData = result.performance.latency;
                const ctx = document.getElementById('latencyChart').getContext('2d');
                
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['最小延迟', '平均延迟', '最大延迟'],
                        datasets: [{
                            label: '延迟 (毫秒)',
                            data: [
                                latencyData.min || 0,
                                latencyData.avg || 0,
                                latencyData.max || 0
                            ],
                            backgroundColor: [
                                'rgba(75, 192, 192, 0.2)',
                                'rgba(54, 162, 235, 0.2)',
                                'rgba(255, 99, 132, 0.2)'
                            ],
                            borderColor: [
                                'rgba(75, 192, 192, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 99, 132, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: '毫秒'
                                }
                            }
                        }
                    }
                });
            }
        } else {
            performanceSection.classList.add('d-none');
        }
        
        // 显示错误信息（如果有）
        if (result.error && !result.valid) {
            errorMessage.textContent = result.error;
            errorAlert.classList.remove('d-none');
        } else {
            errorAlert.classList.add('d-none');
        }
        
        // 显示结果卡片
        resultsCard.classList.remove('d-none');
    }
});
