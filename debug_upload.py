#!/usr/bin/env python3
"""
上传接口调试脚本
用于详细分析上传失败的原因
"""

import requests
import json
import os
from io import BytesIO
from PIL import Image

BASE_URL = "http://noimnotahuman.top"
API_KEY = "cbf2941a5d96356fe800ebd3bd57822657860b484a334ebf69e7563477c32101"

def create_minimal_test_image():
    """创建最小的测试图片"""
    # 创建一个1x1像素的PNG图片
    img = Image.new('RGB', (1, 1), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

def test_upload_step_by_step():
    """逐步测试上传过程"""
    print("DEBUG: 逐步调试上传接口...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'FreePics-Debug/1.0',
        'X-API-Key': API_KEY
    })
    session.verify = False
    
    # 1. 测试最小图片上传
    print("\n1. 测试最小PNG图片上传...")
    try:
        img_data = create_minimal_test_image()
        print(f"   图片大小: {len(img_data)} bytes")
        
        files = {'file': ('test.png', img_data, 'image/png')}
        data = {'optimize': 'false'}  # 关闭优化避免PIL问题
        
        response = session.post(f"{BASE_URL}/upload", files=files, data=data)
        
        print(f"   状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        
        try:
            result = response.json()
            print(f"   响应JSON: {json.dumps(result, indent=2, ensure_ascii=False)}")
        except:
            print(f"   响应文本: {response.text}")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. 测试不同的请求格式
    print("\n2. 测试不同请求格式...")
    try:
        # 尝试不同的Content-Type
        img_data = create_minimal_test_image()
        
        files = {'file': ('test.png', BytesIO(img_data), 'image/png')}
        
        response = session.post(f"{BASE_URL}/upload", files=files)
        print(f"   无data参数 - 状态码: {response.status_code}")
        
        if response.status_code != 200:
            try:
                print(f"   响应: {response.json()}")
            except:
                print(f"   响应文本: {response.text}")
                
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 3. 测试API密钥验证
    print("\n3. 测试API密钥验证...")
    try:
        # 不带API密钥的请求
        session_no_key = requests.Session()
        session_no_key.verify = False
        
        img_data = create_minimal_test_image()
        files = {'file': ('test.png', BytesIO(img_data), 'image/png')}
        
        response = session_no_key.post(f"{BASE_URL}/upload", files=files)
        print(f"   无API密钥 - 状态码: {response.status_code}")
        
        if response.status_code == 401:
            print("   OK: API密钥验证正常工作")
        else:
            print(f"   WARNING: 预期401，实际{response.status_code}")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 4. 检查服务器错误日志（如果可能）
    print("\n4. 尝试获取更多服务器信息...")
    try:
        # 尝试访问一些可能的调试端点
        debug_endpoints = ['/debug', '/status', '/info']
        
        for endpoint in debug_endpoints:
            try:
                response = session.get(f"{BASE_URL}{endpoint}")
                if response.status_code == 200:
                    print(f"   {endpoint}: {response.json()}")
            except:
                pass
                
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == '__main__':
    test_upload_step_by_step()
