from devices.gpib_device import GPIBDevice
from typing import Optional, List, Tuple
import math
import time

class BaseSpectrumAnalyzer(GPIBDevice):
    """基础频谱分析仪抽象类"""
    def __init__(self, address: Optional[str] = None):
        super().__init__(address)
        # 频率范围 (Hz)
        self.min_freq = 10  # 10 Hz
        self.max_freq = 26.5e9  # 26.5 GHz
        
        # 分辨率带宽范围 (Hz)
        self.min_rbw = 1  # 1 Hz
        self.max_rbw = 8e6  # 8 MHz
        
        # 扫描点数范围
        self.min_points = 1
        self.max_points = 40001  # 默认最大支持点数
        self.current_points = 1001  # 默认点数
        
        # 设置较长的超时时间，频谱仪扫描可能需要时间
        self.timeout = 30000  # 30秒
        
    def connect(self, address: Optional[str] = None) -> bool:
        """连接设备并设置长超时"""
        result = super().connect(address)
        if result:
            # 设置通信超时
            self.set_timeout(self.timeout)
            # 等待设备初始化
            time.sleep(0.5)
        return result
        
    @classmethod
    def find_analyzer(cls) -> Optional[str]:
        """自动寻找频谱仪设备"""
        # 具体实现由子类提供
        pass
        
    def calculate_sweep_points(self, start_freq: float, stop_freq: float, rbw: float) -> Tuple[int, str]:
        """
        计算建议的扫描点数
        :param start_freq: 起始频率 (Hz)
        :param stop_freq: 终止频率 (Hz)
        :param rbw: 分辨率带宽 (Hz)
        :return: (建议点数, 说明信息)
        """
        freq_span = stop_freq - start_freq
        
        # 根据奈奎斯特采样定理，采样间隔应不大于RBW/2
        min_points_by_rbw = math.ceil(freq_span / (rbw/2))
        
        # 考虑设备限制
        if min_points_by_rbw > self.max_points:
            message = (f"警告: 当前设置需要{min_points_by_rbw}个点以满足RBW要求，"
                      f"已自动调整为设备最大支持的{self.max_points}点")
            return self.max_points, message
        
        # 选择合适的点数
        if min_points_by_rbw <= 1001:
            points = 1001
        elif min_points_by_rbw <= 2001:
            points = 2001
        elif min_points_by_rbw <= 5001:
            points = 5001
        elif min_points_by_rbw <= 10001:
            points = 10001
        elif min_points_by_rbw <= 20001:
            points = 20001
        else:
            points = 40001
            
        message = f"已设置扫描点数为: {points}"
        return points, message
        
    def set_sweep_points(self, points: int):
        """设置扫描点数 - 由子类实现具体命令"""
        pass
        
    def get_sweep_points(self) -> int:
        """获取当前扫描点数 - 由子类实现具体命令"""
        pass
        
    def set_frequency_range(self, start: float, stop: float):
        """设置频率范围 (Hz) - 由子类实现具体命令"""
        pass
        
    def set_rbw(self, rbw: float):
        """设置分辨率带宽 (Hz) - 由子类实现具体命令"""
        pass
        
    def set_reference_level(self, level: float):
        """设置参考电平 (dBm) - 由子类实现具体命令"""
        pass
        
    def get_peak_power(self) -> float:
        """获取峰值功率 - 由子类实现具体命令"""
        pass
        
    def get_spectrum_data(self) -> List[float]:
        """获取频谱数据 - 由子类实现具体命令"""
        pass
        
    def set_sweep_mode(self, continuous: bool = True):
        """设置扫描模式 - 由子类实现具体命令"""
        pass
        
    def set_trigger_source(self, source: str = "IMM"):
        """设置触发源 - 由子类实现具体命令"""
        pass
        
    def auto_tune(self):
        """自动调谐 - 由子类实现具体命令"""
        pass
        
    def auto_scale(self):
        """自动调整幅度刻度 - 由子类实现具体命令"""
        pass
        
    def get_status(self) -> str:
        """获取设备状态 - 由子类实现具体命令"""
        pass
        
    def get_sweep_time(self) -> float:
        """获取当前扫描时间(秒) - 由子类实现具体命令"""
        pass
        
    def reset(self):
        """重置设备到默认状态 - 由子类实现具体命令"""
        pass

class N9010BAnalyzer(BaseSpectrumAnalyzer):
    """Keysight N9010B 频谱分析仪"""
    def __init__(self, address: Optional[str] = None):
        super().__init__(address)
        self.model = "N9010B"
        self.max_points = 40001  # N9010B最大支持40001点
        
    @classmethod
    def find_analyzer(cls) -> Optional[str]:
        """自动寻找N9010B频谱仪设备"""
        devices = cls.list_available_devices()
        for addr in devices:
            dev = cls(addr)
            if dev.connect():
                idn = dev.identify_device()
                dev.disconnect()
                if idn and "N9010B" in idn:
                    return addr
        return None
        
    def set_sweep_points(self, points: int):
        """设置扫描点数"""
        if not (self.min_points <= points <= self.max_points):
            raise ValueError(f"扫描点数必须在{self.min_points}-{self.max_points}之间")
        self.write(":SWE:POIN {}".format(points))
        self.current_points = points
        
    def get_sweep_points(self) -> int:
        """获取当前扫描点数"""
        try:
            return int(self.query(":SWE:POIN?"))
        except:
            return self.current_points
        
    def set_frequency_range(self, start: float, stop: float):
        """设置频率范围 (Hz)"""
        if not (self.min_freq <= start <= self.max_freq):
            raise ValueError(f"起始频率必须在{self.min_freq/1e3:.3f}kHz - {self.max_freq/1e3:.0f}kHz之间")
        if not (self.min_freq <= stop <= self.max_freq):
            raise ValueError(f"终止频率必须在{self.min_freq/1e3:.3f}kHz - {self.max_freq/1e3:.0f}kHz之间")
        if stop <= start:
            raise ValueError("终止频率必须大于起始频率")
            
        center = (start + stop) / 2
        span = stop - start
        
        self.write(":SENS:FREQ:CENT {:.1f}".format(center))
        time.sleep(0.1)
        self.write(":SENS:FREQ:SPAN {:.1f}".format(span))
        time.sleep(0.1)
        
    def set_rbw(self, rbw: float):
        """设置分辨率带宽 (Hz)"""
        if not (self.min_rbw <= rbw <= self.max_rbw):
            raise ValueError(f"分辨率带宽必须在{self.min_rbw/1e3:.3f}kHz - {self.max_rbw/1e3:.0f}kHz之间")
            
        self.write(":SENS:BAND:RES {:.1f}".format(rbw))
        time.sleep(0.1)
        self.write(":SENS:BAND:VID:AUTO ON")  # 自动设置视频带宽
        time.sleep(0.1)
        
    def set_reference_level(self, level: float):
        """设置参考电平 (dBm)"""
        if not (-170 <= level <= 30):
            raise ValueError("参考电平必须在-170dBm到30dBm之间")
        self.write(":DISP:WIND:TRAC:Y:RLEV {:.1f}".format(level))
        time.sleep(0.1)
        
    def get_peak_power(self) -> float:
        """获取峰值功率"""
        try:
            self.write(":CALC:MARK1:MAX")  # 将标记移动到峰值
            time.sleep(0.1)
            return float(self.query(":CALC:MARK1:Y?"))
        except Exception as e:
            print(f"获取峰值功率失败: {str(e)}")
            return -100  # 返回一个默认的低功率值
        
    def get_spectrum_data(self) -> List[float]:
        """获取频谱数据"""
        try:
            self.write(":INIT:CONT OFF")  # 关闭连续扫描
            time.sleep(0.1)
            self.write(":INIT:IMM;*WAI")  # 开始单次扫描并等待完成
            # 增加超时时间，确保大扫描能完成
            old_timeout = self.timeout
            self.set_timeout(60000)  # 设置为60秒
            
            data_str = self.query(":TRAC? TRACE1")
            # 恢复原超时
            self.set_timeout(old_timeout)
            
            data = data_str.split(',')
            self.write(":INIT:CONT ON")  # 恢复连续扫描
            time.sleep(0.1)
            
            # 转换数据
            return [float(x) for x in data]
        except Exception as e:
            print(f"获取频谱数据失败: {str(e)}")
            return []  # 返回空列表
        
    def set_sweep_mode(self, continuous: bool = True):
        """设置扫描模式"""
        self.write(":INIT:CONT {}".format("ON" if continuous else "OFF"))
        time.sleep(0.1)
        
    def set_trigger_source(self, source: str = "IMM"):
        """设置触发源
        source: 'IMM' - 立即触发
                'EXT' - 外部触发
                'VID' - 视频触发
        """
        if source.upper() not in ["IMM", "EXT", "VID"]:
            raise ValueError("无效的触发源")
        self.write(":TRIG:SOUR {}".format(source))
        time.sleep(0.1)
        
    def auto_tune(self):
        """自动调谐"""
        try:
            self.write(":SENS:FREQ:TUNE:IMM")
            time.sleep(2.0)  # 自动调谐需要较长时间
        except Exception as e:
            print(f"自动调谐失败: {str(e)}")
        
    def auto_scale(self):
        """
        自动调整幅度刻度 - 使用参考电平设置方式
        """
        try:
            # 获取当前最大功率
            self.write(":CALC:MARK1:MAX")
            time.sleep(0.1)
            peak_power = float(self.query(":CALC:MARK1:Y?"))
            
            # 设置参考电平为峰值功率+10dB
            ref_level = peak_power + 10
            if ref_level < -50:  # 信号太弱
                ref_level = 0  # 默认参考电平
            elif ref_level > 30:  # 超出上限
                ref_level = 30
                
            self.write(f":DISP:WIND:TRAC:Y:RLEV {ref_level:.1f}")
            time.sleep(0.1)
        except Exception as e:
            print(f"自动调整幅度刻度失败: {str(e)}")
            # 异常时设置一个默认参考电平
            try:
                self.write(":DISP:WIND:TRAC:Y:RLEV 0")
            except:
                pass
        
    def get_status(self) -> str:
        """获取设备状态"""
        try:
            return self.query("*IDN?")
        except:
            return "Unknown"
        
    def get_sweep_time(self) -> float:
        """获取当前扫描时间(秒)"""
        try:
            return float(self.query(":SENS:SWE:TIME?"))
        except Exception as e:
            print(f"获取扫描时间失败: {str(e)}")
            return 1.0  # 默认返回1秒
            
    def reset(self):
        """重置设备到默认状态"""
        try:
            self.write("*RST")
            time.sleep(1.0)  # 复位后等待
        except Exception as e:
            print(f"重置设备失败: {str(e)}")

class CEYEAR4037Analyzer(BaseSpectrumAnalyzer):
    """中科思仪4037频谱分析仪"""
    def __init__(self, address: Optional[str] = None):
        super().__init__(address)
        self.model = "CEYEAR4037"
        self.max_freq = 7.5e9  # 4037频率上限为7.5GHz
        self.max_points = 10001  # 最大支持10001点
        
    @classmethod
    def find_analyzer(cls) -> Optional[str]:
        """自动寻找中科思仪4037频谱仪设备"""
        devices = cls.list_available_devices()
        for addr in devices:
            dev = cls(addr)
            if dev.connect():
                idn = dev.identify_device()
                dev.disconnect()
                # 中科思仪设备标识包含"4037"
                if idn and "4037" in idn:
                    return addr
        return None
        
    def set_sweep_points(self, points: int):
        """设置扫描点数"""
        if not (self.min_points <= points <= self.max_points):
            raise ValueError(f"扫描点数必须在{self.min_points}-{self.max_points}之间")
        # 中科思仪使用不同的SCPI命令
        self.write(":SENSe:SWEep:POINts {}".format(points))
        time.sleep(0.1)
        self.current_points = points
        
    def get_sweep_points(self) -> int:
        """获取当前扫描点数"""
        try:
            return int(self.query(":SENSe:SWEep:POINts?"))
        except:
            return self.current_points
        
    def set_frequency_range(self, start: float, stop: float):
        """设置频率范围 (Hz)"""
        if not (self.min_freq <= start <= self.max_freq):
            raise ValueError(f"起始频率必须在{self.min_freq/1e3:.3f}kHz - {self.max_freq/1e3:.0f}kHz之间")
        if not (self.min_freq <= stop <= self.max_freq):
            raise ValueError(f"终止频率必须在{self.min_freq/1e3:.3f}kHz - {self.max_freq/1e3:.0f}kHz之间")
        if stop <= start:
            raise ValueError("终止频率必须大于起始频率")
            
        # 中科思仪使用起始/终止频率命令
        self.write(":SENSe:FREQuency:STARt {:.1f}".format(start))
        time.sleep(0.1)
        self.write(":SENSe:FREQuency:STOP {:.1f}".format(stop))
        time.sleep(0.1)
        
    def set_rbw(self, rbw: float):
        """设置分辨率带宽 (Hz)"""
        if not (self.min_rbw <= rbw <= self.max_rbw):
            raise ValueError(f"分辨率带宽必须在{self.min_rbw/1e3:.3f}kHz - {self.max_rbw/1e3:.0f}kHz之间")
            
        self.write(":SENSe:BANDwidth:RESolution {:.1f}".format(rbw))
        time.sleep(0.1)
        self.write(":SENSe:BANDwidth:VIDeo:AUTO ON")
        time.sleep(0.1)
        
    def set_reference_level(self, level: float):
        """设置参考电平 (dBm)"""
        if not (-170 <= level <= 30):
            raise ValueError("参考电平必须在-170dBm到30dBm之间")
        self.write(":DISPlay:WINDow:TRACe:Y:RLEVel {:.1f}".format(level))
        time.sleep(0.1)
        
    def get_peak_power(self) -> float:
        """获取峰值功率"""
        try:
            self.write(":CALCulate:MARKer1:MAXimum")
            time.sleep(0.1)
            return float(self.query(":CALCulate:MARKer1:Y?"))
        except Exception as e:
            print(f"获取峰值功率失败: {str(e)}")
            return -100  # 返回一个默认的低功率值
        
    def get_spectrum_data(self) -> List[float]:
        """获取频谱数据"""
        try:
            self.write(":INITiate:CONTinuous OFF")
            time.sleep(0.1)
            self.write(":INITiate:IMMediate;*WAI")
            
            # 增加超时时间，确保大扫描能完成
            old_timeout = self.timeout
            self.set_timeout(60000)  # 设置为60秒
            
            data_str = self.query(":TRACe:DATA? TRACE1")
            
            # 恢复原超时
            self.set_timeout(old_timeout)
            
            data = data_str.split(',')
            self.write(":INITiate:CONTinuous ON")
            time.sleep(0.1)
            
            return [float(x) for x in data]
        except Exception as e:
            print(f"获取频谱数据失败: {str(e)}")
            return []  # 返回空列表
        
    def set_sweep_mode(self, continuous: bool = True):
        """设置扫描模式"""
        self.write(":INITiate:CONTinuous {}".format("ON" if continuous else "OFF"))
        time.sleep(0.1)
        
    def set_trigger_source(self, source: str = "IMM"):
        """设置触发源"""
        if source.upper() not in ["IMM", "EXT", "VID"]:
            raise ValueError("无效的触发源")
        self.write(":TRIGger:SOURce {}".format(source))
        time.sleep(0.1)
        
    def auto_tune(self):
        """自动调谐"""
        try:
            # 中科思仪可能使用不同命令，这里使用通用方法
            self.write(":SENSe:FREQuency:CENTer:STEP:AUTO ON")
            time.sleep(2.0)  # 自动调谐需要较长时间
        except Exception as e:
            print(f"自动调谐失败: {str(e)}")
        
    def auto_scale(self):
        """
        自动调整幅度刻度 - 使用参考电平设置方式
        """
        try:
            # 获取当前最大功率
            self.write(":CALCulate:MARKer1:MAXimum")
            time.sleep(0.1)
            peak_power = float(self.query(":CALCulate:MARKer1:Y?"))
            
            # 设置参考电平为峰值功率+10dB
            ref_level = peak_power + 10
            if ref_level < -50:  # 信号太弱
                ref_level = 0  # 默认参考电平
            elif ref_level > 30:  # 超出上限
                ref_level = 30
                
            self.write(f":DISPlay:WINDow:TRACe:Y:RLEVel {ref_level:.1f}")
            time.sleep(0.1)
        except Exception as e:
            print(f"自动调整幅度刻度失败: {str(e)}")
            # 异常时设置一个默认参考电平
            try:
                self.write(":DISPlay:WINDow:TRACe:Y:RLEVel 0")
            except:
                pass
        
    def get_status(self) -> str:
        """获取设备状态"""
        try:
            return self.query("*IDN?")
        except:
            return "Unknown"
        
    def get_sweep_time(self) -> float:
        """获取当前扫描时间(秒)"""
        try:
            return float(self.query(":SENSe:SWEep:TIME?"))
        except Exception as e:
            print(f"获取扫描时间失败: {str(e)}")
            return 1.0  # 默认返回1秒
            
    def reset(self):
        """重置设备到默认状态"""
        try:
            self.write("*RST")
            time.sleep(1.0)  # 复位后等待
        except Exception as e:
            print(f"重置设备失败: {str(e)}")

def create_analyzer(model: str, address: Optional[str] = None) -> BaseSpectrumAnalyzer:
    """创建适合的频谱仪对象"""
    if model.upper() == "N9010B":
        return N9010BAnalyzer(address)
    elif model.upper() in ["CEYEAR4037", "4037"]:
        return CEYEAR4037Analyzer(address)
    else:
        raise ValueError(f"不支持的频谱仪型号: {model}")

def find_any_analyzer() -> Tuple[Optional[str], Optional[str]]:
    """寻找任何可用的频谱仪
    返回: (型号, 地址) 或 (None, None)
    """
    # 先尝试找N9010B
    addr = N9010BAnalyzer.find_analyzer()
    if addr:
        return "N9010B", addr
    
    # 再尝试找中科思仪4037
    addr = CEYEAR4037Analyzer.find_analyzer()
    if addr:
        return "CEYEAR4037", addr
    
    return None, None