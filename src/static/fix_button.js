// 修复按钮点击无响应问题
document.addEventListener('DOMContentLoaded', function() {
    console.log('按钮修复脚本已加载');
    
    // 添加一个修复按钮链接到页面顶部
    const fixBtnLink = document.createElement('div');
    fixBtnLink.style.position = 'fixed';
    fixBtnLink.style.top = '10px';
    fixBtnLink.style.right = '10px';
    fixBtnLink.style.zIndex = '9999';
    fixBtnLink.innerHTML = `<a href="/fix-buttons" style="
        display: inline-block;
        padding: 8px 15px;
        background-color: #D88CA0;
        color: white;
        text-decoration: none;
        border-radius: 50px;
        font-size: 14px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    ">修复按钮问题</a>`;
    document.body.appendChild(fixBtnLink);
    
    // 查找所有按钮
    const buttons = document.querySelectorAll('button');
    
    // 为每个按钮添加点击事件监听器
    buttons.forEach(button => {
        // 获取原始的onclick属性
        const originalOnClick = button.getAttribute('onclick');
        
        if (originalOnClick) {
            // 移除原始的onclick属性
            button.removeAttribute('onclick');
            
            // 添加事件监听器
            button.addEventListener('click', function(event) {
                // 尝试执行原始的onclick函数
                try {
                    // 使用eval执行原始的onclick代码
                    eval(originalOnClick);
                } catch (error) {
                    console.error('按钮点击处理错误:', error);
                }
            });
            
            console.log('已修复按钮:', button.textContent || button.innerText);
        }
    });
    
    // 修复乱码问题
    document.querySelectorAll('*').forEach(element => {
        if (element.childNodes && element.childNodes.length > 0) {
            element.childNodes.forEach(node => {
                if (node.nodeType === Node.TEXT_NODE && node.textContent) {
                    // 检测并修复常见的乱码模式
                    const text = node.textContent;
                    if (text.includes('\uFFFD') || /[\u4E00-\u9FFF]/.test(text)) {
                        try {
                            // 尝试使用UTF-8重新解码
                            const decoded = decodeURIComponent(escape(text));
                            if (decoded !== text) {
                                node.textContent = decoded;
                            }
                        } catch (e) {
                            // 解码失败，保持原样
                        }
                    }
                }
            });
        }
    });
    
    console.log('所有按钮已修复');
}); 