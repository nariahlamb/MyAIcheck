import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app

# 为Vercel serverless函数指定WSGI应用
app.debug = False

# 导出WSGI应用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000) 