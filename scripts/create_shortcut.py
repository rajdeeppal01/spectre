import os
import subprocess

desktop_onedrive = os.path.expanduser(r"~\OneDrive\Desktop")
desktop_normal = os.path.expanduser(r"~\Desktop")

desktop = desktop_onedrive if os.path.exists(desktop_onedrive) else desktop_normal
bat = r"C:\Users\rajde\.gemini\antigravity-ide\scratch\spectre\start_spectre.bat"
lnk = os.path.join(desktop, "SPECTRE Command Center.lnk")
work_dir = r"C:\Users\rajde\.gemini\antigravity-ide\scratch\spectre"

vbs_content = f"""Set ws = CreateObject("WScript.Shell")
Set sc = ws.CreateShortcut("{lnk}")
sc.TargetPath = "{bat}"
sc.WorkingDirectory = "{work_dir}"
sc.Description = "Launch SPECTRE Command Center & Local Uncensored AI Sandbox"
sc.IconLocation = "shell32.dll,47"
sc.Save
"""

vbs_path = os.path.join(work_dir, "temp_create_shortcut.vbs")
with open(vbs_path, "w", encoding="utf-8") as f:
    f.write(vbs_content)

res = subprocess.run(["cscript", "//nologo", vbs_path], capture_output=True, text=True)
if os.path.exists(vbs_path):
    os.remove(vbs_path)

print("Status:", "SUCCESS" if os.path.exists(lnk) else "FAILED")
print("Path:", lnk)
