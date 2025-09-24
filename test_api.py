#!/usr/bin/env python3
"""
FreePics API 测试脚本
用于测试图床服务的各个API接口
"""

import requests
import json
import os
import sys
from pathlib import Path
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置
# BASE_URL = "http://localhost:5000"  # 本地测试
BASE_URL = "http://noimnotahuman.top"  # 生产环境
API_KEY = "cbf2941a5d96356fe800ebd3bd57822657860b484a334ebf69e7563477c32101"  # 替换为实际的API密钥

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_session():
    """创建配置好的requests会话"""
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # 配置HTTP适配器
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置超时和SSL配置
    session.verify = False  # 跳过SSL证书验证
    session.timeout = 30
    
    # 设置User-Agent
    session.headers.update({
        'User-Agent': 'FreePics-API-Tester/1.0',
        'X-API-Key': API_KEY
    })
    
    return session

def test_health():
    """测试健康检查接口"""
    print("🔍 测试健康检查接口...")
    try:
        session = create_session()
        response = session.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_server_info():
    """测试服务器信息和镜像版本"""
    print("\n🔍 检查服务器信息...")
    try:
        session = create_session()
        
        # 检查健康状态中的时间戳，判断服务是否重启过
        response = session.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"服务器时间戳: {health_data.get('timestamp')}")
            print(f"服务版本: {health_data.get('version')}")
        
        # 尝试获取更多调试信息
        headers = session.headers.copy()
        headers['X-Debug'] = 'true'
        
        response = session.get(f"{BASE_URL}/health", headers=headers)
        print(f"响应头: {dict(response.headers)}")
        
        return True
    except Exception as e:
        print(f"❌ 服务器信息检查失败: {e}")
        return False

def test_config():
    """测试配置接口"""
    print("\n🔍 测试配置接口...")
    try:
        session = create_session()
        response = session.get(f"{BASE_URL}/config")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            config = response.json()
            print(f"配置信息: {json.dumps(config, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"配置获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_upload(image_path):
    """测试图片上传接口"""
    print(f"\n🔍 测试图片上传接口: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ 测试图片不存在: {image_path}")
        return None
    
    try:
        session = create_session()
        
        # 添加详细的上传调试信息
        file_size = os.path.getsize(image_path)
        print(f"📤 上传调试信息:")
        print(f"   - 文件路径: {image_path}")
        print(f"   - 文件大小: {file_size} bytes")
        
        files = {"file": open(image_path, "rb")}
        data = {"optimize": "true"}
        
        response = session.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data
        )
        
        files["file"].close()
        
        print(f"状态码: {response.status_code}")
        
        # 尝试解析响应
        try:
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应文本: {response.text}")
            return None
        
        if response.status_code == 200 and result.get("success"):
            return result.get("filename")
        return None
        
    except Exception as e:
        print(f"❌ 图片上传失败: {e}")
        return None

def test_image_access(filename):
    """测试图片访问接口"""
    print(f"\n🔍 测试图片访问接口: {filename}")
    try:
        response = requests.get(f"{BASE_URL}/image/{filename}")
        print(f"状态码: {response.status_code}")
        print(f"内容类型: {response.headers.get('content-type')}")
        print(f"内容大小: {len(response.content)} 字节")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 图片访问失败: {e}")
        return False

def test_list():
    """测试文件列表接口"""
    print("\n🔍 测试文件列表接口...")
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{BASE_URL}/list", headers=headers)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"文件总数: {result.get('total', 0)}")
        
        if result.get("files"):
            print("文件列表:")
            for file_info in result["files"][:3]:  # 只显示前3个
                print(f"  - {file_info['filename']} ({file_info['size']} 字节)")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 文件列表获取失败: {e}")
        return False

def test_delete(filename):
    """测试图片删除接口"""
    print(f"\n🔍 测试图片删除接口: {filename}")
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.delete(f"{BASE_URL}/delete/{filename}", headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 图片删除失败: {e}")
        return False

def create_test_image():
    """创建一个测试图片"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建一个简单的测试图片
        img = Image.new('RGB', (400, 200), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # 添加文字
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            # 如果没有找到字体，使用默认字体
            font = ImageFont.load_default()
        
        draw.text((50, 80), "FreePics Test Image", fill='black', font=font)
        draw.text((50, 120), f"Generated at: {os.getcwd()}", fill='darkblue', font=font)
        
        test_image_path = "test_image.jpg"
        img.save(test_image_path, "JPEG")
        print(f"✅ 创建测试图片: {test_image_path}")
        return test_image_path
        
    except ImportError:
        print("❌ 需要安装 Pillow 库来创建测试图片")
        print("运行: pip install Pillow")
        return None
    except Exception as e:
        print(f"❌ 创建测试图片失败: {e}")
        return None

def main():
    """主测试函数"""
    print("🚀 FreePics API 测试开始")
    print(f"测试服务器: {BASE_URL}")
    print(f"API密钥: {API_KEY[:10]}...")
    print("=" * 50)
    
    # 测试健康检查
    if not test_health():
        print("❌ 服务不可用，请检查服务是否正常运行")
        return
    
    # 检查服务器信息
    test_server_info()
    
    # 测试配置
    test_config()
    
    # 创建测试图片
    test_image_path = create_test_image()
    if not test_image_path:
        print("⚠️  无法创建测试图片，跳过上传测试")
        test_list()
        return
    
    try:
        # 测试上传
        uploaded_filename = test_upload(test_image_path)
        
        if uploaded_filename:
            # 测试图片访问
            test_image_access(uploaded_filename)
            
            # 测试文件列表
            test_list()
            
            # 询问是否删除测试图片
            try:
                delete_choice = input("\n🗑️  是否删除测试图片? (y/N): ").strip().lower()
                if delete_choice in ['y', 'yes']:
                    test_delete(uploaded_filename)
                else:
                    print(f"✅ 测试图片保留: {uploaded_filename}")
            except KeyboardInterrupt:
                print(f"\n✅ 测试图片保留: {uploaded_filename}")
        
        # 清理本地测试图片
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            print(f"🧹 清理本地测试图片: {test_image_path}")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
    
    print("\n🎉 API 测试完成")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--prod":
            BASE_URL = "http://noimnotahuman.top"
            print("🌐 使用生产环境进行测试")
        elif sys.argv[1] == "--help":
            print("用法:")
            print("  python test_api.py          # 测试本地环境")
            print("  python test_api.py --prod   # 测试生产环境")
            print("  python test_api.py --help   # 显示帮助")
            sys.exit(0)
    
    main()
