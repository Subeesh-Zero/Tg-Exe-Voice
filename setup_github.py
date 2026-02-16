import os

def create_github_workflow():
    # 1. .github/workflows ஃபோல்டர்களை உருவாக்குதல்
    folders = [".github", ".github/workflows"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # 2. build.yml ஃபைலை உருவாக்குதல் (ProjectAxis Admin பெயருடன்)
    workflow_content = """name: Build ProjectAxis EXE
on: [push]

jobs:
  build:
    runs-on: windows-2019
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install flask requests pillow pyinstaller==6.3.0 customtkinter psutil
      - name: Create EXE
        run: |
          pyinstaller --onefile --windowed --icon="app_icon.ico" --name "ProjectAxis_Admin" dashboard.py
      - name: Upload EXE
        uses: actions/upload-artifact@v4
        with:
          name: ProjectAxis_Admin_App
          path: dist/ProjectAxis_Admin.exe
"""
    with open(".github/workflows/build.yml", "w", encoding="utf-8") as f:
        f.write(workflow_content)
    
    # 3. requirements.txt ஃபைலை உருவாக்குதல்
    requirements_content = "flask\nrequests\npillow\ncustomtkinter\npsutil\npyinstaller==6.3.0"
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements_content)

    print("🎉 ProjectAxis Admin Setup தயார்! இப்போது GitHub-க்கு Push செய்யுங்கள்.")

if __name__ == "__main__":
    create_github_workflow()