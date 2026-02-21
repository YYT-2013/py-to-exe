const translations = {
  zh: {
    navFeatures: "功能",
    navWorkflow: "流程",
    navFaq: "常见问题",
    navDownload: "下载",
    heroEyebrow: "PYTHON TO EXE, VISUAL & FAST",
    heroTitle: "让 Python 打包成 EXE，像点一个按钮一样简单",
    heroText:
      "PyExe Studio 是一个面向 Windows 的可视化打包工具。你只需要选择 `.py` 文件和输出目录，就能调用 PyInstaller 完成构建，并实时查看日志与错误建议。",
    heroBtnMain: "立即下载",
    heroBtnAlt: "查看使用流程",
    featuresTitle: "核心功能",
    f1Title: "一键打包",
    f1Text: "支持 `--onefile` 和 `--onedir`，覆盖常见发布方式。",
    f2Title: "运行模式切换",
    f2Text: "可切换 `--windowed` / `--console`，适配 GUI 与命令行项目。",
    f3Title: "UPX 压缩",
    f3Text: "支持手动设置 UPX 路径，也可自动使用内置 `UPX.EXE`。",
    f4Title: "实时日志",
    f4Text: "构建过程逐行输出，常见错误会给出可读的修复提示。",
    f5Title: "双语界面",
    f5Text: "中文 / English 切换，团队沟通和交付更直观。",
    f6Title: "浅色/深色主题",
    f6Text: "支持跟随系统主题，也可手动指定视觉风格。",
    workflowTitle: "3 步完成打包",
    step1: "选择 Python 源文件（`.py`）和输出目录",
    step2: "设置参数（名称、图标、模式、UPX、管理员权限）",
    step3: "点击开始并在日志区域观察构建结果",
    argTitle: "支持的常用参数",
    faqTitle: "常见问题",
    q1: "提示找不到 PyInstaller 怎么办？",
    a1: "先执行 `pip install pyinstaller`，然后重启软件再试。",
    q2: "出现 ModuleNotFoundError 怎么处理？",
    a2: "根据报错安装缺失依赖，例如 `pip install <module>`。",
    q3: "权限不足或 Access is denied？",
    a3: "可尝试启用管理员权限选项，或以管理员方式运行软件。",
    downloadTitle: "立即体验 PyExe Studio",
    downloadText: "适用于 Windows 10 / 11，推荐 Python 3.8-3.12。本项目开源于 GitHub。",
    downloadBtn: "下载 EXE",
    docBtn: "GitHub 仓库",
  },
  en: {
    navFeatures: "Features",
    navWorkflow: "Workflow",
    navFaq: "FAQ",
    navDownload: "Download",
    heroEyebrow: "PYTHON TO EXE, VISUAL & FAST",
    heroTitle: "Package Python to EXE with one clean click",
    heroText:
      "PyExe Studio is a visual build tool for Windows. Select a `.py` file and output folder, then it runs PyInstaller and streams logs with readable error tips.",
    heroBtnMain: "Download Now",
    heroBtnAlt: "See Workflow",
    featuresTitle: "Core Features",
    f1Title: "One-click build",
    f1Text: "Supports `--onefile` and `--onedir` for common release strategies.",
    f2Title: "Runtime switch",
    f2Text: "Toggle `--windowed` / `--console` for GUI apps and CLI tools.",
    f3Title: "UPX compression",
    f3Text: "Set UPX path manually or auto-use bundled `UPX.EXE`.",
    f4Title: "Live logs",
    f4Text: "Build output streams line-by-line with friendly guidance for common errors.",
    f5Title: "Bilingual UI",
    f5Text: "Switch between Chinese and English for smoother team delivery.",
    f6Title: "Light/Dark mode",
    f6Text: "Follow system theme or choose your preferred style manually.",
    workflowTitle: "Build in 3 Steps",
    step1: "Select your Python source file (`.py`) and output directory",
    step2: "Set options (name, icon, mode, UPX, admin privilege)",
    step3: "Start build and track results in the log panel",
    argTitle: "Supported Options",
    faqTitle: "FAQ",
    q1: "What if PyInstaller is not found?",
    a1: "Run `pip install pyinstaller`, then restart the app.",
    q2: "How to fix ModuleNotFoundError?",
    a2: "Install the missing dependency from the error, e.g. `pip install <module>`.",
    q3: "Permission error or Access is denied?",
    a3: "Enable admin privilege in options, or run the app as Administrator.",
    downloadTitle: "Start with PyExe Studio",
    downloadText: "For Windows 10/11, recommended Python 3.8-3.12. This project is open source on GitHub.",
    downloadBtn: "Download EXE",
    docBtn: "GitHub Repo",
  },
};

const langToggle = document.getElementById("langToggle");
const yearEl = document.getElementById("year");
yearEl.textContent = String(new Date().getFullYear());

let currentLang = "zh";

function renderI18n() {
  document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
  langToggle.textContent = currentLang === "zh" ? "EN" : "中";
  document.title = currentLang === "zh" ? "PyExe Studio | Python 打包 EXE" : "PyExe Studio | Python to EXE";

  const dict = translations[currentLang];
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key || !(key in dict)) return;
    el.textContent = dict[key];
  });
}

langToggle.addEventListener("click", () => {
  currentLang = currentLang === "zh" ? "en" : "zh";
  renderI18n();
});

const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    });
  },
  { threshold: 0.14 }
);

document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

renderI18n();
