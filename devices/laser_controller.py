from devices.gpib_device import GPIBDevice
from typing import Optional, Tuple
import time

class TSLController(GPIBDevice):
    def __init__(self, address: Optional[str] = None):
        super().__init__(address)
        self.min_wavelength = 1500  # nm
        self.max_wavelength = 1600  # nm
        self.min_power = -20.0  # dBm
        self.max_power = 13.0   # dBm
        # 添加属性存储扫描参数
        self.start_wl = None
        self.stop_wl = None
        self.step = None
        self.dwell = None
        
        # 增加通信超时时间
        self.timeout = 10000  # 10秒
        
    def connect(self) -> bool:
        """连接设备并设置超时时间"""
        result = super().connect()
        if result and self.resource:
            # 设置更长的超时时间
            self.resource.timeout = self.timeout
            print(f"已设置通信超时为 {self.timeout}ms")
        return result
        
    @classmethod
    def find_laser(cls) -> Optional[str]:
        """自动寻找激光器设备"""
        devices = cls.list_available_devices()
        for addr in devices:
            dev = cls(addr)
            if dev.connect():
                idn = dev.identify_device()
                dev.disconnect()
                if idn and "TSL" in idn:  # 根据实际设备ID调整
                    return addr
        return None
        
    def set_wavelength(self, wavelength: float) -> float:
        """
        设置激光器波长
        :param wavelength: 波长值(nm)
        :return: 返回设置后的实际波长
        """
        try:
            # 发送简单的SCPI命令，不使用多重尝试
            print(f"设置波长: {wavelength} nm")
            
            # 基于用户的反馈，尝试使用最简单的命令格式
            self.write(f':WAV {wavelength}')
            
            # 查询当前波长并返回
            result = self.query(':WAV?')
            print(f"波长设置响应: {result}")
            
            # 尝试解析返回的波长
            try:
                return float(result)
            except:
                return wavelength  # 如果解析失败，返回设定值
                
        except Exception as e:
            print(f"设置波长出错: {str(e)}")
            return wavelength  # 出错时返回设定值
        
    def get_wavelength(self) -> float:
        """获取当前波长"""
        try:
            # 使用简单的波长查询命令
            response = self.query(':WAV?')
            print(f"波长查询响应: {response}")
            
            try:
                # 尝试直接转换为浮点数
                return float(response)
            except ValueError:
                # 如果无法转换，可能有单位或格式问题
                response = response.strip()
                # 移除单位(如果有)
                if 'nm' in response.lower():
                    response = response.lower().replace('nm', '').strip()
                try:
                    return float(response)
                except:
                    print(f"无法解析波长返回值: {response}")
                    return self.start_wl or self.min_wavelength
        except Exception as e:
            print(f"获取波长错误: {str(e)}")
            # 如果出错，返回一个默认值或上次设置的值
            return self.start_wl or self.min_wavelength
        
    def set_scan_parameters(self, start: float, stop: float, step: float, dwell: float):
        """设置扫描参数 - 只存储参数，不实际发送到设备"""
        # 验证参数有效性
        if start < self.min_wavelength or start > self.max_wavelength:
            raise ValueError(f"起始波长必须在{self.min_wavelength}-{self.max_wavelength}nm之间")
        if stop < self.min_wavelength or stop > self.max_wavelength:
            raise ValueError(f"终止波长必须在{self.min_wavelength}-{self.max_wavelength}nm之间")
        if step <= 0:
            raise ValueError("步长必须大于0")
        if dwell <= 0:
            raise ValueError("停留时间必须大于0")
        if stop <= start:
            raise ValueError("终止波长必须大于起始波长")
        
        # 存储参数到实例变量
        self.start_wl = start
        self.stop_wl = stop
        self.step = step
        self.dwell = dwell
        
        print(f"已存储扫描参数: 起始={start}nm, 终止={stop}nm, 步长={step}nm, 停留时间={dwell}s")
        return True
        
    def start_scan(self):
        """启动扫描 - 保留接口但实际不使用，现在使用手动波长控制"""
        print("激光器扫描逻辑已改为手动控制波长")
        return True
        
    def stop_scan(self):
        """停止扫描 - 保留接口但实际不使用"""
        return True
        
    def get_status(self) -> str:
        """获取设备状态"""
        try:
            return self.query("SU?")
        except:
            return "Unknown"
        
    def enable_output(self, enable: bool = True):
        """启用/禁用激光输出"""
        try:
            if enable:
                print("启用激光器输出")
                self.write("LO")
            else:
                print("禁用激光器输出")
                self.write("LF")
                
            time.sleep(0.2)  # 添加延时确保执行完成
            return True
        except Exception as e:
            print(f"设置激光输出错误: {str(e)}")
            return False
        
    def is_output_enabled(self) -> bool:
        """检查激光输出是否启用"""
        try:
            response = self.query("LO?")
            # 尝试处理可能的不同响应格式
            if response in ["1", "ON", "TRUE", "ENABLED"]:
                return True
            return False
        except:
            return False
        
    def set_power(self, power: float):
        """设置激光器输出功率 (dBm) - 优化响应速度和0值处理"""
        # 明确处理0值情况
        if abs(power) < 0.001:  # 视为0值
            power = 0.0
            
        if power < self.min_power or power > self.max_power:
            raise ValueError(f"功率必须在{self.min_power}-{self.max_power}dBm之间")
            
        try:
            # 确保输出已启用（仅当功率非0时）
            if abs(power) > 0.001 and not self.is_output_enabled():
                self.enable_output(True)
                time.sleep(0.1)  # 缩短等待时间
            
            # 使用官方命令格式
            cmd = f":POWer:LEVel {power:.2f}"
            print(f"设置功率: {cmd}")
            self.write(cmd)
            
            # 适当等待确保执行完成（根据经验调整为较短时间）
            time.sleep(0.3)
            
            # 仅简单日志记录，不进行严格验证以提高响应速度
            print(f"功率设置命令已发送: {power:.2f} dBm")
            
            return True
        except Exception as e:
            print(f"设置功率错误: {str(e)}")
            return False
        
    def get_power(self) -> float:
        """获取当前输出功率 (dBm)"""
        try:
            response = self.query("OP?")
            # 尝试处理可能的不同响应格式
            response = response.strip()
            for unit in ["dBm", "DBM", "db"]:
                if response.endswith(unit):
                    response = response.replace(unit, "").strip()
            return float(response)
        except:
            return self.min_power
        
    def get_power_range(self) -> Tuple[float, float]:
        """获取功率设置范围"""
        return (self.min_power, self.max_power)
        
    def auto_power_control(self, enable: bool = True):
        """启用/禁用自动功率控制模式"""
        try:
            cmd = "APC" if enable else "ACC"
            self.write(cmd)
            time.sleep(0.1)  # 添加延时确保执行完成
            return True
        except Exception as e:
            print(f"设置功率控制模式错误: {str(e)}")
            return False
        
    def is_apc_mode(self) -> bool:
        """检查是否处于自动功率控制模式"""
        try:
            response = self.query("APC?")
            if response in ["1", "ON", "TRUE", "ENABLED"]:
                return True
            return False
        except:
            return False
            
    def get_scan_points(self) -> int:
        """计算并返回扫描点数"""
        if self.start_wl is None or self.stop_wl is None or self.step is None:
            return 0
            
        if self.step <= 0:
            return 0
            
        # 计算扫描点数并确保至少为1
        import math
        scan_points = math.ceil((self.stop_wl - self.start_wl) / self.step) + 1
        return max(1, scan_points)
        
    def reset(self):
        """复位设备到默认状态"""
        try:
            self.write("*RST")
            time.sleep(1.0)  # 复位后等待1秒
            return True
        except:
            return False