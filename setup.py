from setuptools import setup, find_packages
import platform
import sys

# 确定特定版本和安装选项的依赖列表
install_requires = [
    'pyvisa',
    'pyqt5',
    'pyqtgraph',
    'openpyxl'
]

# 根据系统和Python版本确定pandas的安装方式
python_version = sys.version_info
system = platform.system()

# 添加pandas依赖，使用最稳定的版本
if system == 'Windows':
    # Windows系统通常可以直接安装
    install_requires.append('pandas<2.0.0')
elif system == 'Linux':
    # Linux系统可能需要特定版本
    install_requires.append('pandas<2.0.0')
elif system == 'Darwin':  # macOS
    install_requires.append('pandas<2.0.0')
else:
    # 其他系统尝试安装最基础版本
    install_requires.append('pandas==1.3.5')  # 选择一个稳定的老版本

setup(
    name="laser_controller",
    version="0.1",
    packages=find_packages(),
    install_requires=install_requires,
    python_requires='>=3.6',  # 明确支持的Python版本
)