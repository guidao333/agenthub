"""
AgentHub Edge - PyInstaller 打包入口
"""
import sys
import os

def setup_paths():
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，_MEIXXXXX 是临时解压目录
        base = os.path.dirname(sys.executable)
        # 模型在 exe 同级 models/ 目录
        model_dir = os.path.join(base, 'models')
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(base, 'models')
    
    os.makedirs(model_dir, exist_ok=True)
    os.environ['AGENTHUB_EDGE_MODELS'] = model_dir
    os.environ['AGENTHUB_EDGE_BASE'] = base
    return base, model_dir

if __name__ == '__main__':
    base, model_dir = setup_paths()
    # 切换工作目录到 edge 源码目录（开发时）或 exe 目录（打包后）
    if not getattr(sys, 'frozen', False):
        os.chdir(base)
    
    from main import main
    main()
