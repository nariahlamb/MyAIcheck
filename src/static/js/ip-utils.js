/**
 * IP查询工具库
 * 提供可靠的多源IP信息查询功能
 */

// IP查询服务列表，按优先级排序
const IP_SERVICES = [
  {
    name: 'ipify',
    url: 'https://api.ipify.org?format=json',
    parseResult: (data) => data.ip
  },
  {
    name: 'ipapi.co',
    url: 'https://ipapi.co/json/',
    parseResult: (data) => data.ip
  },
  {
    name: 'ipinfo.io',
    url: 'https://ipinfo.io/json',
    parseResult: (data) => data.ip
  }
];

// IP信息查询服务列表
const IP_INFO_SERVICES = [
  {
    name: 'ipapi.co',
    getUrl: (ip) => `https://ipapi.co/${ip}/json/`,
    parseResult: (data) => {
      if (data.error) return null;
      return {
        ip: data.ip,
        country_code: data.country_code,
        country_name: data.country_name,
        region: data.region,
        city: data.city,
        org: data.org,
        asn: data.asn,
        timezone: data.timezone,
        latitude: data.latitude,
        longitude: data.longitude
      };
    }
  },
  {
    name: 'ip-api.com',
    getUrl: (ip) => `https://ip-api.com/json/${ip}?fields=status,message,country,countryCode,region,regionName,city,timezone,isp,org,as,query,lat,lon`,
    parseResult: (data) => {
      if (data.status !== 'success') return null;
      return {
        ip: data.query,
        country_code: data.countryCode,
        country_name: data.country,
        region: data.regionName,
        city: data.city,
        org: data.isp,
        asn: data.as,
        timezone: data.timezone,
        latitude: data.lat,
        longitude: data.lon
      };
    }
  },
  {
    name: 'ipwhois.app',
    getUrl: (ip) => `https://ipwhois.app/json/${ip}`,
    parseResult: (data) => {
      if (data.success === false) return null;
      return {
        ip: data.ip,
        country_code: data.country_code,
        country_name: data.country,
        region: data.region,
        city: data.city,
        org: data.isp,
        asn: data.asn,
        timezone: data.timezone,
        latitude: data.latitude,
        longitude: data.longitude
      };
    }
  }
];

// IP信息缓存
const ipInfoCache = new Map();

/**
 * 确定用户IP地址
 * 使用多种服务尝试获取用户IP，具有重试和超时机制
 */
async function determineIP() {
  for (const service of IP_SERVICES) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000); // 5秒超时
      
      const response = await fetch(service.url, {
        signal: controller.signal,
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache'
        }
      });
      
      clearTimeout(timeout);
      
      if (!response.ok) continue;
      
      const data = await response.json();
      const ip = service.parseResult(data);
      
      if (ip) {
        console.log(`[IP-Utils] 使用 ${service.name} 获取IP成功: ${ip}`);
        return ip;
      }
    } catch (error) {
      console.warn(`[IP-Utils] 使用 ${service.name} 获取IP失败:`, error);
      // 继续尝试下一个服务
    }
  }
  
  console.error('[IP-Utils] 无法确定IP地址，所有服务均失败');
  return null;
}

/**
 * 获取IP详细信息
 * @param {string} ip - IP地址
 * @returns {Promise<Object>} - IP详细信息
 */
async function getIPInfo(ip) {
  // 检查缓存
  if (ipInfoCache.has(ip)) {
    console.log(`[IP-Utils] 从缓存获取IP信息: ${ip}`);
    return ipInfoCache.get(ip);
  }
  
  for (const service of IP_INFO_SERVICES) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 6000); // 6秒超时
      
      const response = await fetch(service.getUrl(ip), {
        signal: controller.signal,
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache'
        }
      });
      
      clearTimeout(timeout);
      
      if (!response.ok) {
        console.warn(`[IP-Utils] ${service.name} 返回错误状态码: ${response.status}`);
        continue;
      }
      
      const data = await response.json();
      const ipInfo = service.parseResult(data);
      
      if (ipInfo) {
        console.log(`[IP-Utils] 使用 ${service.name} 获取IP信息成功`);
        // 缓存结果
        ipInfoCache.set(ip, ipInfo);
        return ipInfo;
      }
    } catch (error) {
      console.warn(`[IP-Utils] 使用 ${service.name} 获取IP信息失败:`, error);
      // 继续尝试下一个服务
    }
  }
  
  // 所有服务均失败，返回基本信息
  const fallbackInfo = {
    ip: ip,
    country_code: 'UN',
    country_name: '未知',
    region: '未知',
    city: '未知',
    org: '未知',
    asn: '未知',
    timezone: '未知'
  };
  
  // 缓存基本信息
  ipInfoCache.set(ip, fallbackInfo);
  return fallbackInfo;
}

/**
 * 获取IP类型
 */
function getIpType(data) {
  if (!data) return 'Unknown';
  
  const countryCode = data.country_code;
  const countryName = data.country_name;
  
  if (countryCode === 'US') return 'United States IP';
  if (countryCode === 'CN') return '中国 IP';
  
  return `${countryName || 'Unknown'} IP`;
}

/**
 * 获取节点类型
 */
function getNodeType(data) {
  if (!data) return 'Unknown';
  
  const org = (data.org || '').toLowerCase();
  
  // 检查是否为数据中心或云服务提供商
  if (org.includes('amazon') || 
      org.includes('aws') || 
      org.includes('microsoft') || 
      org.includes('azure') || 
      org.includes('google') || 
      org.includes('cloudflare') ||
      org.includes('digital ocean') ||
      org.includes('linode')) {
    return '数据中心节点 <span class="badge badge-info">高速</span>';
  }
  
  // 检查是否为移动网络
  if (org.includes('mobile') || 
      org.includes('wireless') || 
      org.includes('cellular')) {
    return '移动网络节点';
  }
  
  return '普通网络节点';
}

/**
 * 计算IP可信度分数
 * @param {Object} data - IP信息数据
 * @returns {number} 可信度分数 (0-100)
 */
function calculateTrustScore(data) {
  if (!data) return 30;
  
  let ipTrustScore = 70; // 基础分数
  
  // 基于地理位置调整分数
  if (data.country_code) {
    // 高可信区域
    if (['US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'JP', 'KR', 'SG'].includes(data.country_code)) {
      ipTrustScore += 15;
    }
    // 中等可信区域
    else if (['BR', 'IN', 'ZA', 'MX', 'AR'].includes(data.country_code)) {
      ipTrustScore += 0;
    }
    // 低可信区域
    else if (['CN', 'RU', 'IR', 'KP', 'SY', 'CU'].includes(data.country_code)) {
      ipTrustScore -= 15;
    }
  }
  
  // 确保分数在0-100范围内
  return Math.max(0, Math.min(100, ipTrustScore));
}

/**
 * 获取浏览器名称
 */
function getBrowserName(userAgent) {
  if (userAgent.indexOf("Firefox") > -1) return "Firefox";
  if (userAgent.indexOf("Opera") > -1 || userAgent.indexOf("OPR") > -1) return "Opera";
  if (userAgent.indexOf("Trident") > -1) return "Internet Explorer";
  if (userAgent.indexOf("Edge") > -1) return "Edge";
  if (userAgent.indexOf("Chrome") > -1) return "Chrome";
  if (userAgent.indexOf("Safari") > -1) return "Safari";
  return "Unknown";
}

/**
 * 获取操作系统名称
 */
function getOSName(userAgent) {
  if (userAgent.indexOf("Win") > -1) return "Windows";
  if (userAgent.indexOf("Mac") > -1) return "MacOS";
  if (userAgent.indexOf("Linux") > -1) return "Linux";
  if (userAgent.indexOf("Android") > -1) return "Android";
  if (userAgent.indexOf("iOS") > -1 || userAgent.indexOf("iPhone") > -1 || userAgent.indexOf("iPad") > -1) return "iOS";
  return "Unknown";
}

/**
 * 完整获取节点信息
 * 这是一个综合函数，用于获取完整的节点信息
 * @returns {Promise<Object>} 包含所有节点信息的对象
 */
async function fetchCompleteNodeInfo() {
  try {
    // 显示加载状态
    const nodeInfoContent = document.getElementById('node-info-content');
    if (nodeInfoContent) {
      nodeInfoContent.innerHTML = '<div class="node-info-loading">正在获取节点信息...</div>';
    }
    
    // 获取IP
    const ip = await determineIP();
    if (!ip) {
      throw new Error('无法获取IP地址');
    }
    
    // 获取IP详细信息
    const ipInfo = await getIPInfo(ip);
    
    // 计算IP信任度分数
    const ipTrustScore = calculateTrustScore(ipInfo);
    
    // 获取浏览器信息
    const browserInfo = {
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      vendor: navigator.vendor || 'Unknown'
    };
    
    // 设置分数颜色
    const ipScoreColor = ipTrustScore < 30 ? '#EF5350' : (ipTrustScore < 60 ? '#FFA726' : '#66BB6A');
    
    // 构建完整节点信息
    const nodeInfo = {
      ip: ip,
      ipInfo: ipInfo,
      browser: {
        name: getBrowserName(browserInfo.userAgent),
        os: getOSName(browserInfo.userAgent),
        language: browserInfo.language,
        userAgent: browserInfo.userAgent
      },
      ipType: getIpType(ipInfo),
      nodeType: getNodeType(ipInfo),
      trustScore: ipTrustScore,
      trustScoreColor: ipScoreColor,
      updateTime: new Date().toLocaleString()
    };
    
    // 构建HTML
    let infoHTML = `
      <div class="node-info-item">
        <span class="node-info-label">IP:</span>
        <span class="node-info-value">${ip}</span>
      </div>
    `;
    
    if (ipInfo) {
      infoHTML += `
        <div class="node-info-item">
          <span class="node-info-label">地区:</span>
          <span class="node-info-value">${ipInfo.country_name || '未知'} (${ipInfo.country_code || 'N/A'})</span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">城市:</span>
          <span class="node-info-value">${ipInfo.city || '未知'}, ${ipInfo.region || '未知'}</span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">ISP:</span>
          <span class="node-info-value">${ipInfo.org || '未知'}</span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">时区:</span>
          <span class="node-info-value">${ipInfo.timezone || '未知'}</span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">ASN:</span>
          <span class="node-info-value">${ipInfo.asn || '未知'}</span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">IP类型:</span>
          <span class="node-info-value">${nodeInfo.ipType}</span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">可信度分数:</span>
          <span class="node-info-value" style="color: ${ipScoreColor}; font-weight: bold;">
            ${ipTrustScore}/100 ${ipTrustScore < 30 ? '<span class="badge badge-warning">危险</span>' : ''}
          </span>
        </div>
        <div class="node-info-item">
          <span class="node-info-label">节点类型:</span>
          <span class="node-info-value">${nodeInfo.nodeType}</span>
        </div>
      `;
    } else {
      infoHTML += `
        <div class="node-info-item">
          <span class="node-info-label">地理信息:</span>
          <span class="node-info-value">无法获取地理位置数据</span>
        </div>
      `;
    }
    
    // 添加浏览器信息
    infoHTML += `
      <div class="node-info-item">
        <span class="node-info-label">浏览器:</span>
        <span class="node-info-value">${nodeInfo.browser.name}</span>
      </div>
      <div class="node-info-item">
        <span class="node-info-label">操作系统:</span>
        <span class="node-info-value">${nodeInfo.browser.os}</span>
      </div>
      <div class="node-info-item">
        <span class="node-info-label">语言:</span>
        <span class="node-info-value">${nodeInfo.browser.language}</span>
      </div>
      <div class="node-info-item">
        <span class="node-info-label">更新时间:</span>
        <span class="node-info-value">${nodeInfo.updateTime}</span>
      </div>
    `;
    
    // 更新节点信息内容
    if (nodeInfoContent) {
      nodeInfoContent.innerHTML = infoHTML;
    }
    
    return {
      nodeInfo: nodeInfo,
      html: infoHTML
    };
  } catch (error) {
    console.error('[IP-Utils] 获取节点信息失败:', error);
    
    // 构建错误HTML
    const errorHTML = `
      <div class="node-info-item">
        <span class="node-info-label">错误:</span>
        <span class="node-info-value">获取节点信息失败: ${error.message}</span>
      </div>
      <button class="btn btn-secondary" style="width: 100%; margin-top: 10px;" onclick="fetchNodeInfo()">重试</button>
    `;
    
    // 更新节点信息内容
    const nodeInfoContent = document.getElementById('node-info-content');
    if (nodeInfoContent) {
      nodeInfoContent.innerHTML = errorHTML;
    }
    
    return {
      error: true,
      message: error.message,
      html: errorHTML
    };
  }
}