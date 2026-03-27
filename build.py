#!/usr/bin/env python3
"""
打包脚本 - 使用 PyInstaller 打包 JOKER POKER 为可执行程序
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

def clean_build():
    """清理之前的构建文件"""
    dirs_to_remove = ['build', 'dist', '__pycache__', '.pytest_cache']
    files_to_remove = ['*.spec']
    
    print("Cleaning previous builds...")
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}/")
    
    # 确保必要的目录存在（即使它们被误删）
    prepare_dirs()
    
    for pattern in files_to_remove:
        for f in Path('.').glob(pattern):
            f.unlink()
            print(f"  Removed {f}")

def get_platform_options():
    """获取平台特定选项"""
    system = sys.platform
    
    if system == 'win32':
        return {
            'icon': '--icon=NONE',
            'extension': '.exe',
            'name': 'JokerPoker.exe'
        }
    elif system == 'darwin':
        return {
            'icon': '--icon=NONE',
            'extension': '',
            'name': 'JokerPoker'
        }
    else:  # Linux
        return {
            'icon': '--icon=NONE',
            'extension': '',
            'name': 'joker-poker'
        }

def prepare_dirs():
    """创建必要的目录"""
    dirs = ['configs', 'core', 'games', 'lib']
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            print(f"  Created {d}/")

def build_app():
    """使用 PyInstaller 打包"""
    print("=" * 50)
    print("Building JOKER POKER Application")
    print("=" * 50)
    
    # 创建必要的目录
    print("Preparing directories...")
    prepare_dirs()
    
    # 确保 PyInstaller 已安装
    try:
        import PyInstaller
        print("✓ PyInstaller found")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    platform_opts = get_platform_options()
    
    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=JokerPoker',           # 应用名称
        '--onefile',                    # 单文件模式
        '--console',                    # 需要控制台（终端游戏）
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不确认覆盖
        # 数据文件
        '--add-data=configs:configs',
        '--add-data=core:core',
        '--add-data=games:games',
        '--add-data=lib:lib',
        # 隐藏的导入
        '--hidden-import=simple_term_menu',
        '--hidden-import=lib.cardclass',
        '--hidden-import=lib.cardset_class',
        '--hidden-import=lib.playerclass',
        '--hidden-import=lib.gameclass',
        '--hidden-import=lib.serverclass',
        '--hidden-import=lib.getip',
        '--hidden-import=games.fight_the_landlord',
        '--hidden-import=games.ftl_online_server',
        '--hidden-import=games.ftl_online_client',
        '--hidden-import=games.settings',
        '--hidden-import=core.FTLCore',
        # 入口文件
        'app.py'
    ]
    
    print("\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("Build Successful!")
        print("=" * 50)
        output_path = f"dist/{platform_opts['name']}"
        print(f"Output: {output_path}")
        print(f"Size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
        return True
    else:
        print("\n✗ Build failed!")
        return False

def build_directory_mode():
    """使用目录模式打包（启动更快）"""
    print("=" * 50)
    print("Building JOKER POKER (Directory Mode)")
    print("=" * 50)
    
    # 创建必要的目录
    print("Preparing directories...")
    prepare_dirs()
    
    try:
        import PyInstaller
    except ImportError:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    platform_opts = get_platform_options()
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=JokerPoker',
        '--onedir',                     # 目录模式（启动更快）
        '--console',
        '--clean',
        '--noconfirm',
        '--add-data=configs:configs',
        '--add-data=core:core',
        '--add-data=games:games',
        '--add-data=lib:lib',
        '--hidden-import=simple_term_menu',
        '--hidden-import=core.FTLCore',
        '--hidden-import=lib.cardclass',
        '--hidden-import=lib.cardset_class',
        '--hidden-import=lib.playerclass',
        '--hidden-import=lib.gameclass',
        '--hidden-import=lib.serverclass',
        '--hidden-import=lib.getip',
        '--hidden-import=games.fight_the_landlord',
        '--hidden-import=games.ftl_online_server',
        '--hidden-import=games.ftl_online_client',
        '--hidden-import=games.settings',
        'app.py'
    ]
    
    print("\nRunning PyInstaller (directory mode)...")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n✓ Build successful!")
        print(f"Output: dist/JokerPoker/{platform_opts['name']}")
        return True
    return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Build JOKER POKER Application')
    parser.add_argument('--clean', action='store_true', help='Clean build files only')
    parser.add_argument('--dir', action='store_true', help='Use directory mode (faster startup)')
    parser.add_argument('--keep', action='store_true', help='Keep previous build files')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_build()
        return
    
    if not args.keep:
        clean_build()
    
    if args.dir:
        success = build_directory_mode()
    else:
        success = build_app()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
