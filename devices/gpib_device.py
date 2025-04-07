import pyvisa
import time
from typing import List, Optional

class GPIBDevice:
    def __init__(self, address: Optional[str] = None):
        self.address = address
        self.rm = pyvisa.ResourceManager()
        self.resource = None  # 改名为resource以避免与内建device冲突
        self.timeout = 5000  # 默认超时5秒
        
    @classmethod
    def list_available_devices(cls) -> List[str]:
        """列出所有可用的GPIB设备地址"""
        rm = pyvisa.ResourceManager()
        try:
            resources = rm.list_resources()
            print(f"找到 {len(resources)} 个设备: {resources}")
            return resources
        except Exception as e:
            print(f"列出设备失败: {str(e)}")
            return []
        
    def connect(self, address: Optional[str] = None) -> bool:
        """连接设备"""
        self.address = address or self.address
        
        if not self.address:
            print("错误: 未提供设备地址")
            return False
            
        try:
            print(f"尝试连接: {self.address}")
            self.resource = self.rm.open_resource(self.address)
            self.resource.timeout = self.timeout  # 设置超时时间
            print(f"成功连接并设置超时为{self.timeout}ms")
            
            # 发送清除和复位命令
            try:
                self.resource.clear()
                print("设备清除命令发送成功")
            except:
                print("设备不支持清除命令")
                
            return True
        except Exception as e:
            print(f"连接设备 {self.address} 失败: {str(e)}")
            return False
            
    def identify_device(self) -> Optional[str]:
        """识别设备类型"""
        if not self.resource:
            return None
        try:
            # 尝试多种标识命令
            for cmd in ["*IDN?", "ID?", "IDEN?"]:
                try:
                    response = self.query(cmd)
                    if response:
                        print(f"设备标识: {response}")
                        return response.strip()
                except:
                    continue
            return None
        except Exception as e:
            print(f"标识设备失败: {str(e)}")
            return None
            
    def disconnect(self):
        """断开设备连接"""
        if self.resource:
            try:
                self.resource.close()
                print(f"断开连接: {self.address}")
            except Exception as e:
                print(f"断开连接错误: {str(e)}")
            self.resource = None
            
    def is_connected(self) -> bool:
        """检查设备是否已连接"""
        return self.resource is not None
            
    def write(self, command: str):
        """发送命令"""
        if not self.resource:
            raise ConnectionError("设备未连接")
            
        try:
            # 命令发送前记录
            print(f"发送命令: {command}")
            self.resource.write(command)
            # 添加小延时，确保命令处理
            time.sleep(0.05)
        except Exception as e:
            print(f"命令发送错误: {str(e)}")
            raise
            
    def query(self, command: str) -> str:
        """查询设备"""
        if not self.resource:
            raise ConnectionError("设备未连接")
            
        try:
            # 查询前记录
            print(f"查询命令: {command}")
            response = self.resource.query(command)
            print(f"设备响应: {response}")
            return response
        except pyvisa.errors.VisaIOError as e:
            if e.error_code == pyvisa.constants.StatusCode.error_timeout:
                print(f"查询超时: {command}")
            else:
                print(f"VISA IO错误: {str(e)}")
            raise
        except Exception as e:
            print(f"查询错误: {str(e)}")
            raise
            
    def read(self) -> str:
        """读取设备数据"""
        if not self.resource:
            raise ConnectionError("设备未连接")
            
        try:
            response = self.resource.read()
            print(f"读取数据: {response}")
            return response
        except Exception as e:
            print(f"读取错误: {str(e)}")
            raise
            
    def set_timeout(self, timeout_ms: int):
        """设置通信超时时间(毫秒)"""
        self.timeout = timeout_ms
        if self.resource:
            self.resource.timeout = timeout_ms
            print(f"更新超时设置为 {timeout_ms}ms")
            
    def clear(self):
        """清除设备状态"""
        if not self.resource:
            return
            
        try:
            self.resource.clear()
            print("设备状态已清除")
        except:
            print("设备不支持清除命令")
            
    def __del__(self):
        self.disconnect()