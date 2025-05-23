# MyAIcheck - 多平台AI接口密钥验证工具

<div align="center">
  <img src="https://img.shields.io/badge/平台-Web-pink?style=for-the-badge" alt="平台"/>
  <img src="https://img.shields.io/badge/语言-Python%20%7C%20JavaScript-blue?style=for-the-badge" alt="语言"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="许可证"/>
  
  [![部署到Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fnariahlamb%2FMyAIcheck)
</div>

## 🌟 项目介绍

MyAIcheck是一款优雅高效的多平台AI接口密钥验证工具，支持批量检测各大AI平台的API密钥有效性。无论您是AI开发者、资源管理员还是API密钥收集爱好者，这款工具都能为您提供直观、快速的验证体验。

### ✨ 特性亮点

- **多平台支持**: 一键测活等多家AI平台的API密钥
- **自定义API**: 支持自定义API地址和模型，兼容众多OpenAI兼容平台
- **双端验证**: 提供浏览器端和服务器端两种验证模式，解决不同网络环境的连接问题
- **批量处理**: 支持文本批量输入和CSV/TXT文件导入，高效处理大量密钥
- **高级并发**: 提供可调节的批量大小和并发数量设置，平衡速度与稳定性
- **自动检测**: 智能检测并展示每个平台的所有可用模型
- **优雅界面**: 精心设计的用户界面，支持亮暗两种主题，关爱您的眼睛
- **全程安全**: 所有验证过程在本地完成，不会向第三方泄露您的API密钥

## 🚀 快速开始

### 在线使用

访问[MyAIcheck在线版本](https://myaicheck.vercel.app)立即开始使用。

### 本地部署

1. 克隆仓库
   ```bash
   git clone https://github.com/nariahlamb/MyAIcheck.git
   cd MyAIcheck
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 启动服务
   ```bash
   python api/index.py
   ```

4. 浏览器访问
   ```
   http://localhost:5000
   ```

### 纯静态使用

如果您只需要浏览器端验证功能，可以直接打开 `src/templates/index.html` 在浏览器中使用，无需安装Python或启动服务器。这种方式下，所有验证都在浏览器中完成，更加隐私安全。

### 部署到Vercel

只需点击下方按钮，轻松将MyAIcheck部署到Vercel：

[![部署到Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fnariahlamb%2FMyAIcheck)

## 📖 使用指南

1. 选择API类型（OpenAI、Claude、Gemini等）
2. 输入需要验证的API密钥（每行一个）或上传包含密钥的文件
3. 调整验证参数（批量大小、并发数量）
4. 点击"验证密钥"按钮开始检测
5. 实时查看验证进度和结果统计
6. 导出有效密钥或完整验证结果

## 🔧 高级选项

- **批量大小**: 控制每批处理的密钥数量，可通过滑块或直接输入设置
- **并发验证**: 同时处理多个批次，大幅提升验证速度
- **客户端验证**: 绕过网络限制，直接使用浏览器验证密钥
- **自动模型检测**: 使用有效密钥获取平台支持的所有模型列表
- **暗色模式**: 保护眼睛，提供舒适的夜间使用体验
- **节点信息**: 查看您的网络环境和IP信息，评估API访问质量

## 🔒 隐私说明

- 所有验证过程均在本地浏览器中执行，不经过第三方服务器
- 验证结果仅保存在浏览器内存中，不会持久化存储
- 未经您的许可，不会将任何数据发送至原始服务器之外的地方

## 📜 开源许可

本项目采用[MIT许可证](LICENSE)开源。

## 🤝 贡献指南

欢迎提交问题报告和功能请求！如果您想贡献代码：

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request
