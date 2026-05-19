"""创建 GitHub 仓库并提交代码"""
import subprocess
import os
import json

# GitHub 配置 - 从 TOOLS.md 获取
GITHUB_USER = "guidao333"
GITHUB_EMAIL = "460552193@qq.com"
REPO_NAME = "agenthub"
REPO_DESC = "AgentHub - Agent Capability Marketplace Platform v2.0"

# 获取 GitHub Token
print("=" * 50)
print("  AgentHub GitHub 仓库初始化")
print("=" * 50)

# 检查已有的 Git 远程
git_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(git_dir)

# 检查是否已有远程
result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
if result.stdout.strip():
    print(f"\n已有远程仓库:")
    print(result.stdout)
    print("不需要重新创建。")
else:
    print(f"\n没有远程仓库，准备创建...")
    
    # 配置 Git 用户
    subprocess.run(["git", "config", "user.name", GITHUB_USER])
    subprocess.run(["git", "config", "user.email", GITHUB_EMAIL])
    
    # 提交所有更改
    subprocess.run(["git", "add", "-A"])
    status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    print(f"\n待提交文件: {len([l for l in status.stdout.strip().split(chr(10)) if l.strip()])}")
    
    # 创建提交
    result = subprocess.run(
        ["git", "commit", "-m", "AgentHub v2.0 架构升级 - 完整后端重构\n\n- 桥接协议 Bridge Protocol v1\n- 能力运行沙箱 (resource.setrlimit)\n- 计费引擎 (预检/冻结/扣款/结算)\n- 自动审核引擎 (安全检查+测试)\n- 健康监控\n- 统一错误码体系 (47个)\n- 多租户数据隔离\n- 客户配置管理\n- API Key 管理\n- 5 天分步开发计划"],
        capture_output=True, text=True
    )
    print(f"\n提交: {result.stdout[:100] if result.stdout else 'nothing to commit'}")
    
    if "nothing to commit" not in result.stdout and "everything up-to-date" not in result.stdout:
        # 尝试推送到 GitHub
        REMOTE_URL = f"https://github.com/{GITHUB_USER}/{REPO_NAME}.git"
        
        # 先用 API 检查仓库是否存在
        import http.client
        conn = http.client.HTTPSConnection("api.github.com")
        conn.request("GET", f"/repos/{GITHUB_USER}/{REPO_NAME}", headers={
            "User-Agent": "AgentHub-Setup",
            "Accept": "application/vnd.github+json",
        })
        resp = conn.getresponse()
        
        if resp.status == 404:
            print(f"\n仓库 {REPO_NAME} 不存在，需要手动创建。")
            print(f"请访问: https://github.com/new")
            print(f"仓库名: {REPO_NAME}")
            print(f"描述: {REPO_DESC}")
            print(f"公开仓库，不要勾选 Initialize this repository with a README")
        else:
            print(f"\n仓库存在，直接推送到 {REMOTE_URL}")
            # 需要 Token 才能推送
            print("需要 GitHub Personal Access Token 才能推送。")
            print(f"请在 https://github.com/settings/tokens 创建一个 token")
            print(f"然后执行: git remote add origin https://guidao333:TOKEN@github.com/guidao333/{REPO_NAME}.git")
    
    print(f"\n已完成:")
    print(f"  本地仓库: {git_dir}")
    print(f"  GitHub:   https://github.com/{GITHUB_USER}/{REPO_NAME}")
    print(f"")

# 生成部署命令
print("\n部署到服务器时需要执行的命令:")
print("=" * 50)
print(f"""
ssh -p 2222 root@183.11.239.100 "apt install -y git"
ssh -p 2222 root@183.11.239.100 "cd /opt/agenthub && git init"
ssh -p 2222 root@183.11.239.100 "cd /opt/agenthub && git remote add origin https://github.com/{GITHUB_USER}/{REPO_NAME}.git"
ssh -p 2222 root@183.11.239.100 "cd /opt/agenthub && git pull origin master"
# 或者直接 scp
scp -P 2222 -r {git_dir}/* root@183.11.239.100:/opt/agenthub/
""")
