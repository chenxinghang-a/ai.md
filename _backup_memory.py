import os
import re
import subprocess

# 读取MEMORY.md
memory_path = r"c:\Users\cxx\WorkBuddy\Claw\.workbuddy\memory\MEMORY.md"
with open(memory_path, "r", encoding="utf-8") as f:
    content = f.read()

# 脱敏处理
# 1. 移除API key行
lines = content.split("\n")
filtered_lines = []
for line in lines:
    # 跳过包含key/token的行
    if any(kw in line.lower() for kw in ["api key", "apikey", "sk-", "tp-", "aisys", "aiza", "bearer"]):
        # 替换为占位符
        if "key" in line.lower() or "token" in line.lower():
            line = re.sub(r'(sk-|tp-|AIza)[^\s"]+', '[REDACTED]', line)
    filtered_lines.append(line)

content = "\n".join(filtered_lines)

# 2. 移除代理地址
content = content.replace("http://127.0.0.1:7890", "[PROXY_REDACTED]")

# 3. 移除个人信息
content = content.replace("C:\\Users\\cxx", "[USER_HOME]")
content = content.replace("佛山（常去中山/珠海）", "[CITY]")

# 写入脱敏版本
backup_path = r"c:\Users\cxx\WorkBuddy\Claw\MEMORY_backup.md"
with open(backup_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"脱敏完成，已保存到: {backup_path}")

# 检查git是否可用
git_path = r"c:\Users\cxx\WorkBuddy\Claw\tools\mingit\cmd\git.exe"
if not os.path.exists(git_path):
    git_path = "git"

# 尝试推送到GitHub
repo_url = "https://github.com/chenxinghang-a/ai.git"
work_dir = r"c:\Users\cxx\WorkBuddy\Claw"

try:
    # 检查是否已经clone过
    if not os.path.exists(os.path.join(work_dir, ".git")):
        print("需要先clone仓库...")
        # 这里需要主人手动操作，因为可能需要代理
        print(f"请主人手动执行:")
        print(f"  cd {work_dir}")
        print(f"  {git_path} clone {repo_url}")
    else:
        # 直接添加并推送
        print("尝试推送到GitHub...")
        # 这里也需要主人手动操作
        print(f"请主人手动执行:")
        print(f"  cd {work_dir}")
        print(f"  {git_path} add MEMORY_backup.md")
        print(f"  {git_path} commit -m \"backup memory (sanitized)\"")
        print(f"  {git_path} push origin main")
except Exception as e:
    print(f"操作失败: {e}")
    print("请主人手动操作")
