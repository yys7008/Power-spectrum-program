from devices.laser_controller import TSLController
from devices.spectrum_analyzer import BaseSpectrumAnalyzer, create_analyzer, find_any_analyzer
import time
import os
import io
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from typing import Optional, Tuple, Any, Dict, List
from datetime import datetime

# 导入必要的库
import pandas as pd
import numpy as np

class ScanThread(QThread):
    """扫描线程类"""
    # 定义信号
    progress_signal = pyqtSignal(int, float)  # 进度百分比, 当前波长
    data_signal = pyqtSignal(list, list)  # 频率列表, 功率列表
    alarm_signal = pyqtSignal(str)  # 报警信息
    complete_signal = pyqtSignal()  # 扫描完成信号
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.scanning = True
        self.paused = False
        
    def run(self):
        """线程运行函数"""
        # 初始化计数器
        self.current_point = 0
        self.total_points = 0
        
        try:
            if not self.controller.laser or not self.controller.analyzer:
                raise Exception("设备未连接")
                
            # 激光器 start_scan 实际上并不执行扫描，我们需要手动控制波长
            # 设置初始波长
            current_wl = self.controller.laser.start_wl
            self.controller.laser.set_wavelength(current_wl)
            
            # 计算总点数
            self.total_points = len(range(int((self.controller.laser.stop_wl - self.controller.laser.start_wl) / self.controller.laser.step) + 1))
            
            # 输出扫描信息
            self.alarm_signal.emit(f"开始扫描: {self.controller.laser.start_wl}nm 到 {self.controller.laser.stop_wl}nm, 步长 {self.controller.laser.step}nm")
            
            while self.scanning and current_wl <= self.controller.laser.stop_wl:
                # 检查是否暂停
                while self.controller.paused and self.scanning:
                    time.sleep(0.2)  # 暂停时短暂休眠，减少CPU使用
                    self.alarm_signal.emit("已暂停，等待继续...")
                # 记录当前波长
                displayed_wl = self.controller.laser.get_wavelength()
                # 打印波长信息用于调试
                self.alarm_signal.emit(f"波长: 设定={current_wl:.4f}nm, 读取={displayed_wl:.4f}nm")
                
                # 获取频谱数据并记录调试信息
                try:
                    spectrum_data = self.controller.analyzer.get_spectrum_data()
                    if not spectrum_data:
                        self.alarm_signal.emit("警告: 频谱仪返回空数据")
                        spectrum_data = []
                    
                    self.alarm_signal.emit(f"获取到频谱数据点: {len(spectrum_data)}个")
                    
                    # 调试日志: 记录前5个数据点
                    if len(spectrum_data) > 5:
                        debug_points = spectrum_data[:5]
                        self.alarm_signal.emit(f"前5个数据点: {debug_points}")
                    elif spectrum_data:
                        self.alarm_signal.emit(f"所有数据点: {spectrum_data}")
                        
                    # 检查数据有效性
                    if len(spectrum_data) < 10:
                        self.alarm_signal.emit("警告: 获取的数据点过少")
                        
                except Exception as e:
                    self.alarm_signal.emit(f"获取频谱数据错误: {str(e)}")
                    spectrum_data = []
                
                try:
                    # 获取当前频率范围用于显示
                    if self.controller.analyzer_model == "N9010B":
                        # Keysight使用中心频率和带宽
                        start_freq = float(self.controller.analyzer.query(":SENS:FREQ:STAR?"))
                        stop_freq = float(self.controller.analyzer.query(":SENS:FREQ:STOP?"))
                    else:
                        # 中科思仪直接使用起始和终止频率
                        start_freq = float(self.controller.analyzer.query(":SENSe:FREQuency:STARt?"))
                        stop_freq = float(self.controller.analyzer.query(":SENSe:FREQuency:STOP?"))
                except Exception as e:
                    self.alarm_signal.emit(f"获取频率范围失败: {str(e)}")
                    # 使用默认值或之前的值
                    start_freq = 0
                    stop_freq = 1
                
                try:
                    # 避免除以零的错误
                    if len(spectrum_data) > 1:
                        freq_step = (stop_freq - start_freq) / (len(spectrum_data) - 1)
                    else:
                        freq_step = 0
                    
                    # 生成频率列表用于显示
                    freqs = [start_freq + i * freq_step for i in range(len(spectrum_data))]
                    powers = spectrum_data
                except Exception as e:
                    self.alarm_signal.emit(f"生成频率列表失败: {str(e)}")
                    # 使用空列表或默认值
                    freqs = []
                    powers = []
                    
                # 确保有数据
                if not powers and spectrum_data:
                    powers = spectrum_data
                    freqs = list(range(len(powers)))
                
                # 记录调试信息
                self.alarm_signal.emit(f"采集到数据: {len(powers)}个点, 波长: {current_wl:.4f}nm")
                
                # 初始化数据矩阵(按列存储)
                if not hasattr(self.controller, 'power_matrix'):
                    self.controller.frequency_points = len(powers) if powers else 0
                    self.controller.power_matrix = np.zeros((len(powers), 0)) if powers else np.zeros((0, 0))
                    self.alarm_signal.emit(f"初始化数据矩阵 ({len(powers)}个频率点)")
                
                # 检查并存储数据(每个波长点的数据作为矩阵的一列)
                if powers and len(powers) > 0:
                    try:
                        # 确保频率点数一致
                        if len(powers) != self.controller.frequency_points:
                            self.alarm_signal.emit(f"警告: 频率点数不一致 ({len(powers)} != {self.controller.frequency_points})")
                            return
                        
                        # 将数据作为新列添加到矩阵([频率点×波长点])
                        if self.controller.power_matrix.size == 0:
                            self.controller.power_matrix = np.array([powers]).T  # 转置为列向量
                        else:
                            self.controller.power_matrix = np.column_stack((self.controller.power_matrix, powers))
                        
                        # 更新统计信息
                        wavelength_points = self.controller.power_matrix.shape[1]
                        frequency_points = self.controller.power_matrix.shape[0]
                        self.alarm_signal.emit(f"数据已存储: {wavelength_points}波长点 × {frequency_points}频率点")
                        
                        # 监控内存使用
                        mem_usage = self.controller.power_matrix.nbytes / (1024 * 1024)
                        if mem_usage > 500:  # 500MB警告阈值
                            self.alarm_signal.emit(f"内存使用警告: {mem_usage:.1f}MB")

                        # 调试信息
                        self.alarm_signal.emit(f"数据范围: {np.min(powers):.2f} 到 {np.max(powers):.2f} dBm")
                    except Exception as e:
                        self.alarm_signal.emit(f"数据存储错误: {str(e)}")
                else:
                    self.alarm_signal.emit("警告: 无有效数据可存储")
                
                # 获取当前频谱的峰值功率用于报警判断
                peak_power = max(powers) if powers else -100
                
                # 发射信号更新界面频谱图
                self.data_signal.emit(freqs, powers)
                
                # 更新进度
                self.current_point += 1
                progress = int(100 * self.current_point / self.total_points)
                # 发送实际读取到的波长值，而不是设定值
                self.progress_signal.emit(progress, displayed_wl)
                
                # 检查报警条件
                self._check_alarm_conditions(current_wl, peak_power)
                
                # 发送数据收集完成状态
                self.alarm_signal.emit(f"波长 {displayed_wl:.4f}nm 的数据收集完成，准备步进...")
                
                # 等待指定的停留时间 - 确保有足够时间处理数据
                if self.controller.laser.dwell > 0:
                    time.sleep(self.controller.laser.dwell)
                else:
                    time.sleep(0.2)  # 默认至少等待0.2秒确保数据处理完成
                
                # 步进到下一个波长
                current_wl += self.controller.laser.step
                
                # 设置新波长
                if current_wl <= self.controller.laser.stop_wl:
                    self.alarm_signal.emit(f"步进到新波长: {current_wl:.4f}nm")
                    # 设置新波长前先等待短暂时间确保上一步操作完成
                    time.sleep(0.2)
                    self.controller.laser.set_wavelength(current_wl)
                    # 设置后再等待短暂时间确保波长稳定
                    time.sleep(0.2)
                
        except Exception as e:
            self.alarm_signal.emit(f"扫描错误: {str(e)}")
        finally:
            self.scanning = False
            self.alarm_signal.emit(f"扫描结束，正在同步最终数据...")
            
            if self.controller.analyzer:
                self.controller.analyzer.auto_scale()
                self.alarm_signal.emit(f"频谱仪已自动调整刻度")
                
            # 调试: 检查最终数据状态
            if hasattr(self.controller, 'power_buffer'):
                self.alarm_signal.emit(f"最终缓冲区数据: {len(self.controller.power_buffer)}个波长点")
            if hasattr(self.controller, 'total_columns'):
                self.alarm_signal.emit(f"流式写入总列数: {self.controller.total_columns}")
                
            # 确保数据统计正确
            if hasattr(self, 'total_points') and self.controller.temp_file_handle:
                # 流式写入模式 - 确保 total_columns 更新正确
                if self.controller.total_columns == 0 and self.current_point > 0:
                    self.controller.total_columns = self.current_point
                    self.alarm_signal.emit(f"已同步总波长点数: {self.current_point}")
                else:
                    self.alarm_signal.emit(f"扫描完成: 共{self.controller.total_columns}个波长点")
            elif not self.controller.temp_file_handle and hasattr(self, 'current_point'):
                # 内存缓冲模式 - 确保 power_buffer 包含所有数据
                if len(self.controller.power_buffer) == 0 and self.current_point > 0:
                    self.alarm_signal.emit(f"警告: 没有捕获到任何数据点")
                else:
                    count = len(self.controller.power_buffer)
                    self.alarm_signal.emit(f"扫描完成: 内存中有{count}个波长点的数据")
                
            # 关闭文件
            if self.controller.temp_file_handle:
                try:
                    self.controller.temp_file_handle.close()
                    self.controller.temp_file_handle = None
                except:
                    pass
                    
            # 发送完成信号
            self.complete_signal.emit()
            
    def stop(self):
        """停止扫描"""
        self.scanning = False
    
    def _check_alarm_conditions(self, wavelength: float, power: float):
        """检查报警条件"""
        if power < -50:  # dBm
            self.alarm_signal.emit(f"功率过低: {power}dBm @ {wavelength}nm")
        elif power > 10:  # dBm
            self.alarm_signal.emit(f"功率过高: {power}dBm @ {wavelength}nm")
    


class LaserSystemController(QObject):
    # 定义信号
    scan_progress = pyqtSignal(int, float)  # 进度百分比, 当前波长
    scan_complete = pyqtSignal()
    data_updated = pyqtSignal(list, list)  # 频率列表, 功率列表
    alarm_triggered = pyqtSignal(str)  # 报警信息
    device_found = pyqtSignal(str, str)  # 设备类型, 地址
    analyzer_model_detected = pyqtSignal(str)  # 频谱仪型号
    points_calculated = pyqtSignal(int, str)  # 采样点数, 说明信息
    memory_warning = pyqtSignal(float, str)  # 内存使用警告 (MB, 消息)
    sweep_time_updated = pyqtSignal(float)  # 单次扫描时间 (ms)

    def __init__(self):
        super().__init__()
        self.laser = None
        self.analyzer = None
        self.analyzer_model = None
        self.paused = False
        self.scanning = False
        # 使用列表存储最近的几个波长点数据，避免全部存在内存中
        self.power_buffer = []
        # 如果启用了流式写入，存储临时文件句柄
        self.temp_file_handle = None
        self.buffer_max_size = 10  # 最多缓存10个波长点数据
        self.total_columns = 0  # 记录总列数
        self.alarm_status = "Normal"
        self.memory_usage_threshold_mb = 500  # 500MB内存使用警告阈值
        self.laser_power = 0.0  # 当前设置的激光器功率
        
    def auto_connect_devices(self) -> bool:
        """自动连接设备"""
        # 发送开始搜索信号
        self.device_found.emit("SearchStart", "")
        self.alarm_triggered.emit("开始自动搜索设备...")
        
        laser_found = False
        analyzer_found = False
        
        try:
            # 尝试获取可用设备列表
            try:
                # 自动寻找激光器
                self.alarm_triggered.emit("正在搜索激光器...")
                laser_addr = TSLController.find_laser()
                if laser_addr:
                    self.device_found.emit("Laser", laser_addr)
                    self.laser = TSLController(laser_addr)
                    if not self.laser.connect():
                        self.alarm_triggered.emit("激光器设备找到但连接失败")
                    else:
                        self.alarm_triggered.emit(f"成功连接激光器: {laser_addr}")
                        laser_found = True
                else:
                    self.alarm_triggered.emit("未找到激光器设备")
            except Exception as e:
                self.alarm_triggered.emit(f"搜索激光器时出错: {str(e)}")
                
            # 自动寻找频谱仪
            try:
                self.alarm_triggered.emit("正在搜索频谱仪...")
                model, analyzer_addr = find_any_analyzer()
                if model and analyzer_addr:
                    self.device_found.emit("Analyzer", analyzer_addr)
                    self.analyzer_model = model
                    self.analyzer_model_detected.emit(model)
                    self.analyzer = create_analyzer(model, analyzer_addr)
                    
                    if not self.analyzer.connect():
                        self.alarm_triggered.emit("频谱仪设备找到但连接失败")
                    else:
                        self.alarm_triggered.emit(f"成功连接频谱仪: {analyzer_addr}, 型号: {model}")
                        # 初始化频谱仪设置
                        self._init_analyzer_settings()
                        analyzer_found = True
                else:
                    self.alarm_triggered.emit("未找到频谱仪设备")
            except Exception as e:
                self.alarm_triggered.emit(f"搜索频谱仪时出错: {str(e)}")
            
            # 搜索完成总结
            if laser_found or analyzer_found:
                self.alarm_triggered.emit("自动搜索完成，部分或全部设备已连接")
                self.device_found.emit("SearchComplete", "success")
                return True
            else:
                self.alarm_triggered.emit("自动搜索完成，未找到任何可用设备")
                self.device_found.emit("SearchComplete", "failed")
                return False
            
        except Exception as e:
            self.alarm_triggered.emit(f"自动连接失败: {str(e)}")
            self.device_found.emit("SearchComplete", "error")
            return False

    def connect_devices(self, laser_address: Optional[str] = None, 
                       analyzer_address: Optional[str] = None,
                       analyzer_model: str = "N9010B") -> bool:
        """连接设备"""
        if not laser_address and not analyzer_address:
            return self.auto_connect_devices()
            
        try:
            if laser_address:
                try:
                    print(f"[DEBUG] 尝试连接激光器，地址: {laser_address}")
                    self.laser = TSLController(laser_address)
                    if not self.laser.connect():
                        error_msg = f"激光器连接失败，请检查: 1) GPIB地址{laser_address} 2) 设备电源 3) GPIB线缆"
                        self.alarm_triggered.emit(error_msg)
                        print(f"[ERROR] {error_msg}")
                        return False
                    print("[DEBUG] 激光器连接成功")
                except Exception as e:
                    error_msg = f"激光器连接异常: {str(e)}. 请检查GPIB连接和设备状态"
                    self.alarm_triggered.emit(error_msg)
                    print(f"[ERROR] {error_msg}")
                    return False
                    
            if analyzer_address:
                self.analyzer_model = analyzer_model
                self.analyzer = create_analyzer(analyzer_model, analyzer_address)
                if not self.analyzer.connect():
                    self.alarm_triggered.emit("频谱仪连接失败")
                    return False
                
                self._init_analyzer_settings()
            
            # 如果激光器连接成功，获取功率范围并更新UI
            if self.laser and self.laser.is_connected():
                try:
                    # 获取激光器当前功率和功率范围
                    self.laser_power = self.laser.get_power()
                    power_range = self.laser.get_power_range()
                    
                    # 发送信号更新UI
                    self.data_updated.emit([], [])  # 清空图表
                    # 这里我们需要创建新的信号来传递功率信息
                    # 暂时使用data_updated以避免修改太多代码
                    
                    # 发送激光器状态信息
                    self.device_found.emit("LaserPower", f"{self.laser_power}")
                    self.device_found.emit("LaserPowerRange", f"{power_range[0]},{power_range[1]}")
                    self.device_found.emit("LaserOutputStatus", "1" if self.laser.is_output_enabled() else "0")
                    self.device_found.emit("LaserAPCMode", "1" if self.laser.is_apc_mode() else "0")
                except Exception as e:
                    # 激光器功率参数获取失败，不影响正常流程
                    self.alarm_triggered.emit(f"激光器功率参数获取失败: {str(e)}")
                    
            return True
                
        except Exception as e:
            self.alarm_triggered.emit(f"连接错误: {str(e)}")
            return False
    
    def set_laser_power(self, power: float):
        """设置激光器输出功率(简化版本，不检查APC模式)"""
        if not self.laser:
            self.alarm_triggered.emit("未连接激光器，无法设置功率")
            return False
            
        try:
            # 只在功率变化超过阈值时才发送命令，减少频繁通信
            if not hasattr(self, 'last_power') or abs(self.last_power - power) >= 0.05:
                # 直接设置功率，不检查APC模式
                result = self.laser.set_power(power)
                self.last_power = power
                self.laser_power = power
            return True
        except Exception as e:
            self.alarm_triggered.emit(f"设置功率失败: {str(e)}")
            return False
                    
            
    def set_laser_apc_mode(self, enabled: bool):
        """设置激光器自动功率控制模式"""
        if not self.laser:
            self.alarm_triggered.emit("未连接激光器，无法设置自动功率控制")
            print("[DEBUG] 激光器未连接")
            return False
            
        try:
            print(f"[DEBUG] 尝试设置APC模式: {'开启' if enabled else '关闭'}")
            result = self.laser.auto_power_control(enabled)
            print(f"[DEBUG] APC设置结果: {result}")
            
            # 验证APC模式是否设置成功
            actual_apc = self.laser.is_apc_mode()
            if actual_apc != enabled:
                error_msg = f"APC模式设置不一致: 设定={enabled}, 实际={actual_apc}"
                self.alarm_triggered.emit(error_msg)
                print(f"[ERROR] {error_msg}")
                return False
                
            self.alarm_triggered.emit(f"APC模式已{'开启' if enabled else '关闭'}")
            return True
        except Exception as e:
            error_msg = f"设置自动功率控制失败: {str(e)}"
            self.alarm_triggered.emit(error_msg)
            print(f"[ERROR] {error_msg}")
            return False
            
    def set_laser_output(self, enabled: bool):
        """设置激光器输出使能"""
        if not self.laser:
            self.alarm_triggered.emit("未连接激光器，无法控制输出")
            return False
            
        try:
            self.laser.enable_output(enabled)
            return True
        except Exception as e:
            self.alarm_triggered.emit(f"设置激光输出失败: {str(e)}")
            return False

    def _init_analyzer_settings(self):
        """初始化频谱仪设置"""
        if self.analyzer:
            self.analyzer.set_reference_level(0)  # 0 dBm
            self.analyzer.set_sweep_mode(True)
            self.analyzer.set_trigger_source("IMM")
            self.analyzer.auto_scale()

    def calculate_sweep_points(self, start_freq: float, stop_freq: float, rbw: float) -> Tuple[int, str]:
        """计算扫描点数"""
        if self.analyzer:
            return self.analyzer.calculate_sweep_points(start_freq, stop_freq, rbw)
        return 1001, "未连接频谱仪，使用默认点数：1001"
        
    def estimate_memory_usage(self, wl_points: int, freq_points: int) -> float:
        """估计内存使用量 (MB)"""
        # 假设每个浮点数8字节
        bytes_per_point = 8
        total_bytes = wl_points * freq_points * bytes_per_point
        return total_bytes / (1024 * 1024)  # 转换为MB
    def set_scan_parameters(self, start_wl, stop_wl, step, dwell, start_freq, stop_freq, rbw, manual_points: int = -1):
        """设置扫描参数
        
        Args:
            start_wl: 起始波长
            stop_wl: 终止波长
            step: 波长步长
            dwell: 停留时间
            start_freq: 起始频率
            stop_freq: 终止频率
            rbw: 分辨率带宽
            manual_points: 手动设置的采样点数，-1表示自动计算
        """
        if self.laser:
            self.laser.set_scan_parameters(start_wl, stop_wl, step, dwell)
            
        if self.analyzer:
            self.analyzer.set_frequency_range(start_freq, stop_freq)
            self.analyzer.set_rbw(rbw)
            
            # 设置采样点数
            if manual_points > 0:
                # 使用手动设置的采样点数
                points = manual_points
                message = f"采用手动设置的采样点数: {points}"
                self.analyzer.set_sweep_points(points)
            else:
                # 自动计算采样点数
                points, message = self.calculate_sweep_points(start_freq, stop_freq, rbw)
                self.analyzer.set_sweep_points(points)
            
            # 发送采样点数更新信号
            self.points_calculated.emit(points, message)
            
            # 估计内存使用量
            wl_points = int((stop_wl - start_wl) / step) + 1
            mem_usage = self.estimate_memory_usage(wl_points, points)
            
            # 计算单次扫描时间（ms）
            # 先计算频谱仪单次扫描时间
            analyzer_sweep_time = self.analyzer.get_sweep_time() * 1000  # 转换为ms
            
            # 计算激光器扫描时间
            # dwell是每个波长点的停留时间（秒），需要转换为ms
            laser_sweep_time = dwell * 1000  # 转换为ms
            
            # 发射扫描时间更新信号
            self.sweep_time_updated.emit(analyzer_sweep_time + laser_sweep_time)
            
            # 优化内存使用提示和流式写入逻辑
            if mem_usage > 100:  # 降低警告阈值为100MB
                warning_msg = (f"预计内存使用: {mem_usage:.1f}MB，"
                              f"已自动启用流式写入模式优化内存使用。")
                self.memory_warning.emit(mem_usage, warning_msg)
                
                # 确保启用流式写入
                if not self.temp_file_handle:
                    try:
                        self.temp_file_handle = open("temp_scan_data.dat", "w")
                        self.total_columns = 0
                    except Exception as e:
                        self.alarm_triggered.emit(f"创建临时文件失败: {str(e)}")

    def start_scan(self):
        """开始扫描"""
        if not self.scanning:
            self.scanning = True
            # 重置数据缓冲区
            self.power_buffer = []
            # 重置数据矩阵，防止新数据与旧数据混合
            if hasattr(self, 'power_matrix'):
                self.power_matrix = np.zeros((0, 0))
            self.alarm_triggered.emit("初始化内存数据缓冲区和数据矩阵")
            
            # 检查设备连接状态
            if not hasattr(self, 'laser') or not hasattr(self, 'analyzer'):
                self.alarm_triggered.emit("扫描失败: 设备未连接")
                self.scanning = False
                return
            
            # 创建并启动扫描线程
            self.scan_thread = ScanThread(self)
            
            # 连接线程信号
            self.scan_thread.progress_signal.connect(self.scan_progress.emit)
            self.scan_thread.data_signal.connect(self.data_updated.emit)
            self.scan_thread.alarm_signal.connect(self.alarm_triggered.emit)
            self.scan_thread.complete_signal.connect(self.scan_complete.emit)
            
            # 启动线程
            self.scan_thread.start()

    def stop_scan(self):
        """停止扫描"""
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.scan_thread.stop()
            self.scan_thread.wait()  # 等待线程结束
            
        self.scanning = False
        if self.laser:
            self.laser.stop_scan()
            
        # 关闭流式写入的文件
        if self.temp_file_handle:
            try:
                self.temp_file_handle.close()
                self.temp_file_handle = None
            except:
                pass
                
    def pause_scan(self):
        """暂停扫描"""
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.paused = True
            self.alarm_triggered.emit("扫描已暂停")
            return True
        return False
        
    def resume_scan(self):
        """恢复扫描"""
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.paused = False
            self.alarm_triggered.emit("扫描已恢复")
            return True
        return False

    def simple_save_data(self, filename: str):
        """统一的数据保存方法(支持CSV/XLSX/TXT/H5DF)"""
        try:
            # 详细检查数据状态
            if not hasattr(self, 'power_matrix'):
                self.alarm_triggered.emit("保存失败: 数据矩阵未初始化")
                return False
                
            if self.power_matrix.size == 0:
                self.alarm_triggered.emit("保存失败: 数据矩阵为空")
                return False
                
            if self.power_matrix.shape[0] == 0 or self.power_matrix.shape[1] == 0:
                self.alarm_triggered.emit(f"保存失败: 矩阵维度异常 {self.power_matrix.shape}")
                return False
                
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # 保存前再次检查数据有效性
            if not isinstance(self.power_matrix, np.ndarray):
                self.alarm_triggered.emit("保存失败: 数据格式错误")
                return False
                
            # 确保矩阵非空
            if self.power_matrix.size == 0:
                self.alarm_triggered.emit("保存失败: 无数据可保存")
                return False
                
            # 保存矩阵(每行一个频率点，每列一个波长点)
            try:
                if filename.endswith('.h5') or filename.endswith('.hdf5'):
                    # 导入h5py模块
                    try:
                        import h5py
                    except ImportError:
                        self.alarm_triggered.emit("保存H5DF失败: 未安装h5py库，请安装后重试")
                        return False
                    
                    # 保存为H5DF格式
                    with h5py.File(filename, 'w') as f:
                        # 创建主数据集
                        dset = f.create_dataset("power_data", data=self.power_matrix)
                        
                        # 添加元数据
                        dset.attrs['description'] = '激光扫描数据: 频率(行) x 波长(列)'
                        dset.attrs['frequency_count'] = self.power_matrix.shape[0]
                        dset.attrs['wavelength_count'] = self.power_matrix.shape[1]
                        dset.attrs['timestamp'] = str(datetime.now())
                        
                        # 创建波长和频率索引数据集
                        f.create_dataset("wavelength_index", data=np.arange(1, self.power_matrix.shape[1]+1))
                        f.create_dataset("frequency_index", data=np.arange(1, self.power_matrix.shape[0]+1))
                    
                    self.alarm_triggered.emit(f"成功保存H5DF文件: {os.path.basename(filename)}")
                    
                elif filename.endswith('.xlsx'):
                    df = pd.DataFrame(self.power_matrix)
                    df.columns = [f"WL_{i+1}" for i in range(df.shape[1])]  # 添加波长点列名
                    df.index = [f"Freq_{i+1}" for i in range(df.shape[0])]   # 添加频率点行名
                    df.to_excel(filename)
                    
                elif filename.endswith('.csv'):
                    np.savetxt(filename, self.power_matrix, delimiter=',', fmt='%.6f',
                              header=",".join([f"WL_{i+1}" for i in range(self.power_matrix.shape[1])]))
                
                else:  # .txt或其他格式
                    np.savetxt(filename, self.power_matrix, delimiter='\t', fmt='%.6f',
                              header="\t".join([f"WL_{i+1}" for i in range(self.power_matrix.shape[1])]))
                    
                self.alarm_triggered.emit(f"成功保存数据: {self.power_matrix.shape[1]}个波长点, {self.power_matrix.shape[0]}个频率点")
                return True
                
            except Exception as e:
                self.alarm_triggered.emit(f"保存过程出错: {str(e)}")
                print(f"保存错误详情: {str(e)}")
                return False
                
        except Exception as e:
            self.alarm_triggered.emit(f"保存失败: {str(e)}")
            print(f"保存错误详情: {str(e)}")
            return False

    def _write_column_to_file(self, powers):
        """将一列数据写入文件"""
        if not self.temp_file_handle:
            return
            
        try:
            # 如果是第一列，直接写入
            if self.total_columns == 0:
                for p in powers:
                    self.temp_file_handle.write(f"{p}\n")
            else:
                # 如果不是第一列，需要修改文件
                # 这种方法对大文件很低效，但简单起见先这样实现
                # 实际产品应该使用更高效的方法如追加列等
                self.temp_file_handle.seek(0)  # 回到文件开头
                lines = self.temp_file_handle.readlines()
                self.temp_file_handle.seek(0)  # 准备重写
                self.temp_file_handle.truncate()  # 清空文件
                
                # 写入每行，添加新的列
                for i, line in enumerate(lines):
                    if i < len(powers):
                        # 移除末尾的换行符，添加分隔符和新的值
                        new_line = line.rstrip('\n') + ',' + str(powers[i]) + '\n'
                        self.temp_file_handle.write(new_line)
                    else:
                        # 如果新数据列比旧数据短，保持旧数据不变
                        self.temp_file_handle.write(line)
                        
                # 如果新数据比旧数据长，添加额外的行
                if len(powers) > len(lines):
                    for i in range(len(lines), len(powers)):
                        # 为前面的列添加空值
                        prefix = ',' * self.total_columns
                        self.temp_file_handle.write(f"{prefix}{powers[i]}\n")
                        
            # 刷新文件，确保写入磁盘
            self.temp_file_handle.flush()
            
        except Exception as e:
            self.alarm_triggered.emit(f"写入文件错误: {str(e)}")

    def _scan_thread(self):
        """扫描线程"""
        try:
            if not self.laser or not self.analyzer:
                raise Exception("设备未连接")
                
            self.laser.start_scan()
            total_points = len(range(int((self.laser.stop_wl - self.laser.start_wl) / self.laser.step)))
            current_point = 0
            
            while self.scanning:
                current_wl = self.laser.get_wavelength()
                
                # 获取频谱数据
                spectrum_data = self.analyzer.get_spectrum_data()
                
                # 获取当前频率范围用于显示
                if self.analyzer_model == "N9010B":
                    # Keysight使用中心频率和带宽
                    start_freq = float(self.analyzer.query(":SENS:FREQ:STAR?"))
                    stop_freq = float(self.analyzer.query(":SENS:FREQ:STOP?"))
                else:
                    # 中科思仪直接使用起始和终止频率
                    start_freq = float(self.analyzer.query(":SENSe:FREQuency:STARt?"))
                    stop_freq = float(self.analyzer.query(":SENSe:FREQuency:STOP?"))
                
                freq_step = (stop_freq - start_freq) / (len(spectrum_data) - 1)
                
                # 生成频率列表用于显示
                freqs = [start_freq + i * freq_step for i in range(len(spectrum_data))]
                powers = spectrum_data
                
                # 如果使用流式写入，直接写入文件
                if self.temp_file_handle:
                    self._write_column_to_file(powers)
                    self.total_columns += 1
                else:
                    # 调试日志：记录接收到的数据
                    print(f"[DEBUG] 接收到波长点数据，长度: {len(powers)}")
                    
                    # 检查数据有效性
                    if len(powers) == 0:
                        print("[WARNING] 接收到空数据点")
                        return
                        
                    # 添加到内存缓冲区
                    self.power_buffer.append(powers)
                    print(f"[DEBUG] 当前缓冲区数据点数量: {len(self.power_buffer)}")

                    # 如果缓冲区过大，清除最早的数据以节省内存
                    if len(self.power_buffer) > self.buffer_max_size:
                        self.power_buffer = self.power_buffer[-self.buffer_max_size:]
                        print("[DEBUG] 清理缓冲区以节省内存")
                
                # 获取当前频谱的峰值功率用于报警判断
                peak_power = max(powers) if powers else -100
                
                # 发射信号更新界面频谱图
                self.data_updated.emit(freqs, powers)
                
                # 更新进度
                current_point += 1
                progress = int(100 * current_point / total_points)
                self.scan_progress.emit(progress, current_wl)
                
                # 检查报警条件
                self._check_alarm_conditions(current_wl, peak_power)
                
                time.sleep(0.1)  # 避免过快采样
                
        except Exception as e:
            self.alarm_triggered.emit(f"扫描错误: {str(e)}")
        finally:
            self.scanning = False
            if self.analyzer:
                self.analyzer.auto_scale()
            # 关闭文件
            if self.temp_file_handle:
                try:
                    self.temp_file_handle.close()
                    self.temp_file_handle = None
                except:
                    pass
            self.scan_complete.emit()

    def _check_alarm_conditions(self, wavelength: float, power: float):
        """检查报警条件"""
        if power < -50:  # dBm
            self.alarm_status = "Low Power"
            self.alarm_triggered.emit(f"功率过低: {power}dBm @ {wavelength}nm")
        elif power > 10:  # dBm
            self.alarm_status = "High Power"
            self.alarm_triggered.emit(f"功率过高: {power}dBm @ {wavelength}nm")
        else:
            self.alarm_status = "Normal"
            
    def get_analyzer_info(self) -> dict:
        """获取频谱仪信息"""
        if not self.analyzer:
            return {"connected": False}
        
        return {
            "connected": True,
            "model": self.analyzer_model,
            "max_points": self.analyzer.max_points,
            "max_freq": self.analyzer.max_freq,
            "status": self.analyzer.get_status()
        }
        
    def get_data_info(self) -> dict:
        """获取数据信息"""
        columns = len(self.power_buffer)
        rows = len(self.power_buffer[0]) if columns > 0 else 0
        
        if self.temp_file_handle:
            # 如果使用流式写入，返回文件信息
            return {
                "wave_length_points": self.total_columns,
                "frequency_points": rows,
                "total_points": self.total_columns * rows,
                "streaming_mode": True,
                "buffer_points": 0
            }
        else:
            # 否则返回缓冲区信息
            return {
                "wave_length_points": columns,
                "frequency_points": rows,
                "total_points": columns * rows,
                "streaming_mode": False,
                "buffer_points": columns * rows,
                "buffer_size_mb": self.estimate_memory_usage(columns, rows)
            }
