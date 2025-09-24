#!/usr/bin/env python3
"""
FreePics API 测试脚本
完整测试图床服务的所有API接口
"""

import requests
import json
import os
import sys
import time
from io import BytesIO
from PIL import Image
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FreePicsAPITester:
    def __init__(self, base_url="http://localhost", api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.uploaded_files = []  # 记录上传的文件，用于清理
        
        # 设置API密钥
        if self.api_key:
            self.session.headers.update({'X-API-Key': self.api_key})
    
    def create_test_image(self, filename="test_image.png", size=(200, 200), color="blue"):
        """创建测试图片"""
        try:
            img = Image.new('RGB', size, color=color)
            # 添加一些文字
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), f"Test Image\n{filename}", fill="white")
            except:
                pass
            
            # 保存到内存
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            logger.info(f"创建测试图片: {filename} ({size[0]}x{size[1]})")
            return img_bytes
        except Exception as e:
            logger.error(f"创建测试图片失败: {e}")
            return None
    
    def test_health_check(self):
        """测试健康检查接口"""
        logger.info("🔍 测试健康检查接口...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 健康检查成功: {data}")
                return True
            else:
                logger.error(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 健康检查异常: {e}")
            return False
    
    def test_get_config(self):
        """测试获取配置接口"""
        logger.info("🔍 测试获取配置接口...")
        try:
            response = self.session.get(f"{self.base_url}/config")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 配置获取成功:")
                logger.info(f"   - 支持格式: {data.get('allowed_extensions', [])}")
                logger.info(f"   - 最大文件大小: {data.get('max_file_size_mb', 0)}MB")
                logger.info(f"   - 是否需要API密钥: {data.get('has_api_keys', False)}")
                return True
            elif response.status_code == 401:
                logger.warning("⚠️  配置接口需要API密钥")
                return False
            else:
                logger.error(f"❌ 配置获取失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 配置获取异常: {e}")
            return False
    
    def test_upload_image(self, filename="test_upload.png", optimize=True):
        """测试图片上传接口"""
        logger.info(f"🔍 测试图片上传接口: {filename}")
        
        # 创建测试图片
        img_data = self.create_test_image(filename)
        if not img_data:
            return None
        
        try:
            files = {'file': (filename, img_data, 'image/png')}
            data = {'optimize': 'true' if optimize else 'false'}
            
            response = self.session.post(
                f"{self.base_url}/upload",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    uploaded_filename = result.get('filename')
                    file_url = result.get('url')
                    file_size = result.get('size')
                    
                    logger.info(f"✅ 图片上传成功:")
                    logger.info(f"   - 文件名: {uploaded_filename}")
                    logger.info(f"   - 访问URL: {file_url}")
                    logger.info(f"   - 文件大小: {file_size} bytes")
                    
                    # 记录上传的文件
                    self.uploaded_files.append(uploaded_filename)
                    return uploaded_filename
                else:
                    logger.error(f"❌ 上传失败: {result}")
                    return None
            elif response.status_code == 401:
                logger.error("❌ 上传失败: 需要API密钥")
                return None
            else:
                logger.error(f"❌ 上传失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 上传异常: {e}")
            return None
    
    def test_access_image(self, filename):
        """测试图片访问接口"""
        logger.info(f"🔍 测试图片访问: {filename}")
        try:
            response = self.session.get(f"{self.base_url}/image/{filename}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                
                logger.info(f"✅ 图片访问成功:")
                logger.info(f"   - 内容类型: {content_type}")
                logger.info(f"   - 文件大小: {content_length} bytes")
                return True
            else:
                logger.error(f"❌ 图片访问失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 图片访问异常: {e}")
            return False
    
    def test_list_files(self):
        """测试文件列表接口"""
        logger.info("🔍 测试文件列表接口...")
        try:
            response = self.session.get(f"{self.base_url}/list")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    files = data.get('files', [])
                    total = data.get('total', 0)
                    
                    logger.info(f"✅ 文件列表获取成功:")
                    logger.info(f"   - 文件总数: {total}")
                    
                    if files:
                        logger.info("   - 最近文件:")
                        for file_info in files[:3]:  # 只显示前3个
                            logger.info(f"     * {file_info['filename']} ({file_info['size']} bytes)")
                    
                    return True
                else:
                    logger.error(f"❌ 文件列表获取失败: {data}")
                    return False
            elif response.status_code == 401:
                logger.error("❌ 文件列表获取失败: 需要API密钥")
                return False
            else:
                logger.error(f"❌ 文件列表获取失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 文件列表获取异常: {e}")
            return False
    
    def test_delete_image(self, filename):
        """测试图片删除接口"""
        logger.info(f"🔍 测试图片删除: {filename}")
        try:
            response = self.session.delete(f"{self.base_url}/delete/{filename}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"✅ 图片删除成功: {data.get('message', '')}")
                    # 从记录中移除
                    if filename in self.uploaded_files:
                        self.uploaded_files.remove(filename)
                    return True
                else:
                    logger.error(f"❌ 图片删除失败: {data}")
                    return False
            elif response.status_code == 401:
                logger.error("❌ 图片删除失败: 需要API密钥")
                return False
            elif response.status_code == 404:
                logger.error("❌ 图片删除失败: 文件不存在")
                return False
            else:
                logger.error(f"❌ 图片删除失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 图片删除异常: {e}")
            return False
    
    def test_upload_different_formats(self):
        """测试不同格式的图片上传"""
        logger.info("🔍 测试不同格式图片上传...")
        
        formats = [
            ('test.jpg', 'JPEG'),
            ('test.png', 'PNG'),
            ('test.gif', 'GIF'),
            ('test.webp', 'WEBP')
        ]
        
        results = []
        for filename, format_type in formats:
            try:
                # 创建不同格式的测试图片
                img = Image.new('RGB', (100, 100), color='red')
                img_bytes = BytesIO()
                
                if format_type == 'GIF':
                    img = img.convert('P')
                
                img.save(img_bytes, format=format_type)
                img_bytes.seek(0)
                
                files = {'file': (filename, img_bytes, f'image/{format_type.lower()}')}
                response = self.session.post(f"{self.base_url}/upload", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        uploaded_filename = result.get('filename')
                        logger.info(f"✅ {format_type}格式上传成功: {uploaded_filename}")
                        self.uploaded_files.append(uploaded_filename)
                        results.append((format_type, True, uploaded_filename))
                    else:
                        logger.error(f"❌ {format_type}格式上传失败: {result}")
                        results.append((format_type, False, None))
                else:
                    logger.error(f"❌ {format_type}格式上传失败: {response.status_code}")
                    results.append((format_type, False, None))
                    
            except Exception as e:
                logger.error(f"❌ {format_type}格式测试异常: {e}")
                results.append((format_type, False, None))
        
        return results
    
    def test_large_file_upload(self):
        """测试大文件上传"""
        logger.info("🔍 测试大文件上传...")
        
        try:
            # 创建一个较大的测试图片 (约2MB)
            img = Image.new('RGB', (2000, 2000), color='green')
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            file_size = len(img_bytes.getvalue())
            logger.info(f"创建大文件测试图片: {file_size / 1024 / 1024:.2f}MB")
            
            files = {'file': ('large_test.png', img_bytes, 'image/png')}
            response = self.session.post(f"{self.base_url}/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    uploaded_filename = result.get('filename')
                    logger.info(f"✅ 大文件上传成功: {uploaded_filename}")
                    self.uploaded_files.append(uploaded_filename)
                    return uploaded_filename
                else:
                    logger.error(f"❌ 大文件上传失败: {result}")
                    return None
            else:
                logger.error(f"❌ 大文件上传失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 大文件上传异常: {e}")
            return None
    
    def cleanup_uploaded_files(self):
        """清理上传的测试文件"""
        if not self.uploaded_files:
            return
        
        logger.info("🧹 清理测试文件...")
        for filename in self.uploaded_files.copy():
            if self.test_delete_image(filename):
                logger.info(f"✅ 清理文件: {filename}")
            else:
                logger.warning(f"⚠️  清理失败: {filename}")
    
    def run_all_tests(self, cleanup=True):
        """运行所有测试"""
        logger.info("🚀 开始FreePics API完整测试")
        logger.info(f"测试服务器: {self.base_url}")
        logger.info(f"API密钥: {'已设置' if self.api_key else '未设置'}")
        logger.info("=" * 60)
        
        test_results = {}
        
        # 1. 健康检查
        test_results['health'] = self.test_health_check()
        
        # 2. 获取配置
        test_results['config'] = self.test_get_config()
        
        # 3. 基础图片上传
        uploaded_file = self.test_upload_image()
        test_results['upload'] = uploaded_file is not None
        
        # 4. 图片访问
        if uploaded_file:
            test_results['access'] = self.test_access_image(uploaded_file)
        
        # 5. 文件列表
        test_results['list'] = self.test_list_files()
        
        # 6. 不同格式上传
        format_results = self.test_upload_different_formats()
        test_results['formats'] = all(result[1] for result in format_results)
        
        # 7. 大文件上传
        large_file = self.test_large_file_upload()
        test_results['large_file'] = large_file is not None
        
        # 8. 删除测试
        if uploaded_file:
            test_results['delete'] = self.test_delete_image(uploaded_file)
        
        # 清理测试文件
        if cleanup:
            self.cleanup_uploaded_files()
        
        # 输出测试结果
        logger.info("=" * 60)
        logger.info("📊 测试结果汇总:")
        
        passed = 0
        total = 0
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"   {test_name}: {status}")
            if result:
                passed += 1
            total += 1
        
        logger.info(f"\n🎯 测试完成: {passed}/{total} 通过")
        
        if passed == total:
            logger.info("🎉 所有测试通过！FreePics API工作正常")
        else:
            logger.warning("⚠️  部分测试失败，请检查服务配置")
        
        return test_results

def main():
    parser = argparse.ArgumentParser(description='FreePics API 测试工具')
    parser.add_argument('--url', default='http://localhost', 
                       help='API服务器地址 (默认: http://localhost)')
    parser.add_argument('--api-key', 
                       help='API密钥')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='不清理测试文件')
    parser.add_argument('--test', choices=['health', 'upload', 'delete', 'list', 'all'],
                       default='all', help='运行特定测试')
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = FreePicsAPITester(args.url, args.api_key)
    
    # 运行测试
    if args.test == 'all':
        tester.run_all_tests(cleanup=not args.no_cleanup)
    elif args.test == 'health':
        tester.test_health_check()
    elif args.test == 'upload':
        filename = tester.test_upload_image()
        if filename and not args.no_cleanup:
            tester.test_delete_image(filename)
    elif args.test == 'list':
        tester.test_list_files()

if __name__ == '__main__':
    main()
