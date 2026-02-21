import json
import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QAction,
    QActionGroup,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def _app_dir() -> Path:
    return Path(__file__).resolve().parent


def _lang_dir() -> Path:
    return _app_dir() / "lang"


def _load_json(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _has_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401

        return True
    except Exception:
        return False


def _default_upx_dir() -> Optional[str]:
    exe = _app_dir() / "UPX.EXE"
    if exe.exists():
        return str(exe.parent)
    exe2 = _app_dir() / "upx.exe"
    if exe2.exists():
        return str(exe2.parent)
    return None


def _try_enable_windows_blur(hwnd: int) -> None:
    try:
        import ctypes
        from ctypes import wintypes

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_int),
                ("AnimationId", ctypes.c_int),
            ]

        class WINCOMPATTRDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t),
            ]

        user32 = ctypes.windll.user32
        set_window_comp_attr = getattr(user32, "SetWindowCompositionAttribute", None)
        if not set_window_comp_attr:
            return

        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        WCA_ACCENT_POLICY = 19

        accent = ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = 0xCC202020
        accent.AnimationId = 0

        data = WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        set_window_comp_attr.argtypes = [wintypes.HWND, ctypes.POINTER(WINCOMPATTRDATA)]
        set_window_comp_attr.restype = wintypes.BOOL
        set_window_comp_attr(hwnd, ctypes.byref(data))
    except Exception:
        return


def _read_windows_apps_theme() -> Optional[str]:
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            value, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return "light" if int(value) == 1 else "dark"
    except Exception:
        return None


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, html: str, theme: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self.lbl_title = QLabel(title)
        f = self.lbl_title.font()
        f.setPointSize(max(12, f.pointSize() + 2))
        f.setBold(True)
        self.lbl_title.setFont(f)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(html)
        self.browser.setMinimumWidth(420)
        self.browser.setMinimumHeight(140)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_close = QPushButton("OK")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)

        root.addWidget(self.lbl_title)
        root.addWidget(self.browser)
        root.addLayout(btn_row)

        self.apply_theme(theme)

    def apply_theme(self, theme: str) -> None:
        if theme == "dark":
            self.setStyleSheet(
                "QDialog{background:#151924;color:#e6e6e6;}"
                "QTextBrowser{background:#0f1115;border:1px solid #2a2f3a;border-radius:10px;padding:10px;color:#e6e6e6;}"
                "QTextBrowser a{color:#60a5fa;}"
                "QPushButton{background:#2563eb;border:none;border-radius:8px;padding:8px 12px;color:white;}"
            )
        else:
            self.setStyleSheet(
                "QDialog{background:#ffffff;color:#111827;}"
                "QTextBrowser{background:#f8fafc;border:1px solid #d7dbe6;border-radius:10px;padding:10px;color:#111827;}"
                "QTextBrowser a{color:#2563eb;}"
                "QPushButton{background:#2563eb;border:none;border-radius:8px;padding:8px 12px;color:white;}"
            )


class TitleBar(QWidget):
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self._win = parent
        self._drag_active = False
        self._drag_pos = None

        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(6)

        self.lbl_title = QLabel()
        self.lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.btn_settings = QToolButton()
        self.btn_help = QToolButton()
        for b in (self.btn_settings, self.btn_help):
            b.setPopupMode(QToolButton.InstantPopup)
            b.setToolButtonStyle(Qt.ToolButtonTextOnly)
            b.setFixedHeight(28)
            b.setObjectName("titleMenuBtn")

        self.btn_min = QPushButton("–")
        self.btn_close = QPushButton("×")

        self.btn_min.setFixedSize(44, 28)
        self.btn_close.setFixedSize(44, 28)

        self.btn_min.setObjectName("titleMin")
        self.btn_close.setObjectName("titleClose")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.btn_settings)
        layout.addWidget(self.btn_help)
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_close)

        self.btn_min.clicked.connect(self._win.showMinimized)
        self.btn_close.clicked.connect(self._win.close)

    def set_menus(self, settings_menu: QMenu, help_menu: QMenu) -> None:
        self.btn_settings.setMenu(settings_menu)
        self.btn_help.setMenu(help_menu)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPos() - self._win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_active and self._drag_pos is not None:
            self._win.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_active = False
        self._drag_pos = None
        event.accept()


@dataclass
class BuildOptions:
    py_file: str
    output_dir: str
    mode_onefile: bool
    windowed: bool
    name: str
    icon: str
    uac_admin: bool
    clean: bool
    noconfirm: bool
    use_upx: bool
    upx_dir: str
    specpath: str
    workpath: str
    distpath: str


class PyInstallerWorker(QThread):
    line = pyqtSignal(str)
    finished_with_code = pyqtSignal(int)

    def __init__(self, args: List[str], cwd: str):
        super().__init__()
        self._args = args
        self._cwd = cwd
        self._proc = None

    def run(self) -> None:
        try:
            import subprocess

            self._proc = subprocess.Popen(
                self._args,
                cwd=self._cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            assert self._proc.stdout is not None
            for raw in self._proc.stdout:
                if raw is None:
                    continue
                self.line.emit(raw.rstrip("\n"))

            code = self._proc.wait()
            self.finished_with_code.emit(code)
        except Exception:
            self.line.emit(traceback.format_exc())
            self.finished_with_code.emit(-1)

    def cancel(self) -> None:
        try:
            if self._proc is None:
                return
            if self._proc.poll() is not None:
                return
            self._proc.terminate()
        except Exception:
            pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._lang: Dict[str, str] = {}
        self._lang_code = "zh_CN"
        self._theme = "light"  # applied theme: 'light' | 'dark'
        self._theme_mode = "system"  # 'system' | 'light' | 'dark'
        self._worker: Optional[PyInstallerWorker] = None
        self._fade_anim: Optional[QPropertyAnimation] = None

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self._build_ui()
        self._load_language(self._lang_code)
        self._apply_theme(self._get_effective_theme())
        self._sync_enabled_state(running=False)
        self._on_use_upx_toggled(self.ck_use_upx.isChecked())

        try:
            hwnd = int(self.winId())
            _try_enable_windows_blur(hwnd)
        except Exception:
            pass

        self._theme_timer = QTimer(self)
        self._theme_timer.setInterval(1200)
        self._theme_timer.timeout.connect(self._poll_system_theme)
        self._theme_timer.start()

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("root")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)

        self._build_menu()

        self._root_layout = root

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(10)
        top_grid.setVerticalSpacing(10)
        root.addLayout(top_grid)

        self.grp_files = QGroupBox()
        files_layout = QFormLayout(self.grp_files)
        files_layout.setLabelAlignment(Qt.AlignLeft)
        files_layout.setFormAlignment(Qt.AlignTop)
        files_layout.setHorizontalSpacing(10)
        files_layout.setVerticalSpacing(8)

        self.ed_py = QLineEdit()
        self.btn_py = QPushButton()
        py_row = QHBoxLayout()
        py_row.addWidget(self.ed_py)
        py_row.addWidget(self.btn_py)
        self.lbl_py_file = QLabel()
        files_layout.addRow(self.lbl_py_file, py_row)

        self.ed_out = QLineEdit()
        self.btn_out = QPushButton()
        out_row = QHBoxLayout()
        out_row.addWidget(self.ed_out)
        out_row.addWidget(self.btn_out)
        self.lbl_output_dir = QLabel()
        files_layout.addRow(self.lbl_output_dir, out_row)

        top_grid.addWidget(self.grp_files, 0, 0)

        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)

        self.grp_basic = QGroupBox()
        basic_layout = QGridLayout(self.grp_basic)
        basic_layout.setHorizontalSpacing(10)
        basic_layout.setVerticalSpacing(8)

        self.rb_onefile = QCheckBox()
        self.rb_onedir = QCheckBox()
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_group.addButton(self.rb_onefile)
        self._mode_group.addButton(self.rb_onedir)
        self.rb_onefile.setChecked(True)

        self.rb_console = QCheckBox()
        self.rb_windowed = QCheckBox()
        self._console_group = QButtonGroup(self)
        self._console_group.setExclusive(True)
        self._console_group.addButton(self.rb_console)
        self._console_group.addButton(self.rb_windowed)
        self.rb_windowed.setChecked(True)

        basic_layout.addWidget(self.rb_onefile, 0, 0)
        basic_layout.addWidget(self.rb_onedir, 0, 1)
        basic_layout.addWidget(self.rb_console, 1, 0)
        basic_layout.addWidget(self.rb_windowed, 1, 1)

        self.ed_name = QLineEdit()
        self.ed_icon = QLineEdit()
        self.btn_icon = QPushButton()
        icon_row = QHBoxLayout()
        icon_row.addWidget(self.ed_icon)
        icon_row.addWidget(self.btn_icon)

        self.lbl_name = QLabel()
        basic_layout.addWidget(self.lbl_name, 2, 0)
        basic_layout.addWidget(self.ed_name, 2, 1)
        self.lbl_icon = QLabel()
        basic_layout.addWidget(self.lbl_icon, 3, 0)
        basic_layout.addLayout(icon_row, 3, 1)

        top_grid.addWidget(self.grp_basic, 1, 0)

        self.grp_opt = QGroupBox()
        opt_layout = QGridLayout(self.grp_opt)
        opt_layout.setHorizontalSpacing(10)
        opt_layout.setVerticalSpacing(8)

        self.ck_uac = QCheckBox()
        self.ck_clean = QCheckBox()
        self.ck_noconfirm = QCheckBox()
        self.ck_use_upx = QCheckBox()
        self.ed_upx_dir = QLineEdit()
        self.btn_upx_dir = QPushButton()
        upx_row = QHBoxLayout()
        upx_row.addWidget(self.ed_upx_dir)
        upx_row.addWidget(self.btn_upx_dir)

        opt_layout.addWidget(self.ck_uac, 0, 0)
        opt_layout.addWidget(self.ck_clean, 0, 1)
        opt_layout.addWidget(self.ck_noconfirm, 1, 0)
        opt_layout.addWidget(self.ck_use_upx, 1, 1)
        self.lbl_upx_dir = QLabel()
        opt_layout.addWidget(self.lbl_upx_dir, 2, 0)
        opt_layout.addLayout(upx_row, 2, 1)

        top_grid.addWidget(self.grp_opt, 1, 1)

        self.grp_paths = QGroupBox()
        paths_layout = QFormLayout(self.grp_paths)
        paths_layout.setHorizontalSpacing(10)
        paths_layout.setVerticalSpacing(8)

        self.ed_specpath = QLineEdit()
        self.btn_specpath = QPushButton()
        spec_row = QHBoxLayout()
        spec_row.addWidget(self.ed_specpath)
        spec_row.addWidget(self.btn_specpath)

        self.ed_workpath = QLineEdit()
        self.btn_workpath = QPushButton()
        work_row = QHBoxLayout()
        work_row.addWidget(self.ed_workpath)
        work_row.addWidget(self.btn_workpath)

        self.ed_distpath = QLineEdit()
        self.btn_distpath = QPushButton()
        dist_row = QHBoxLayout()
        dist_row.addWidget(self.ed_distpath)
        dist_row.addWidget(self.btn_distpath)

        self.lbl_specpath = QLabel()
        self.lbl_workpath = QLabel()
        self.lbl_distpath = QLabel()
        paths_layout.addRow(self.lbl_specpath, spec_row)
        paths_layout.addRow(self.lbl_workpath, work_row)
        paths_layout.addRow(self.lbl_distpath, dist_row)
        root.addWidget(self.grp_paths)

        actions = QHBoxLayout()
        self.btn_start = QPushButton()
        self.btn_cancel = QPushButton()
        self.btn_clear = QPushButton()
        self.lbl_status = QLabel()
        self.lbl_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_clear)
        actions.addWidget(self.lbl_status)
        root.addLayout(actions)

        self.grp_log = QGroupBox()
        log_layout = QVBoxLayout(self.grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.txt_log)
        root.addWidget(self.grp_log)

        self.btn_py.clicked.connect(self._pick_py)
        self.btn_out.clicked.connect(self._pick_out)
        self.btn_icon.clicked.connect(self._pick_icon)
        self.btn_specpath.clicked.connect(lambda: self._pick_dir(self.ed_specpath))
        self.btn_workpath.clicked.connect(lambda: self._pick_dir(self.ed_workpath))
        self.btn_distpath.clicked.connect(lambda: self._pick_dir(self.ed_distpath))
        self.btn_upx_dir.clicked.connect(lambda: self._pick_dir(self.ed_upx_dir))
        self.btn_start.clicked.connect(self._start)
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_clear.clicked.connect(self.txt_log.clear)
        self.ck_use_upx.toggled.connect(self._on_use_upx_toggled)

    def _build_menu(self) -> None:
        self.menu_settings = QMenu(self)
        self.menu_language = QMenu(self.menu_settings)
        self.menu_theme = QMenu(self.menu_settings)
        self.menu_help = QMenu(self)

        self.menu_settings.addMenu(self.menu_language)
        self.menu_settings.addMenu(self.menu_theme)

        self.act_lang_group = QActionGroup(self)
        self.act_lang_group.setExclusive(True)
        self.act_lang_zh = QAction(self)
        self.act_lang_zh.setCheckable(True)
        self.act_lang_zh.setData("zh_CN")
        self.act_lang_en = QAction(self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setData("en_US")
        self.act_lang_group.addAction(self.act_lang_zh)
        self.act_lang_group.addAction(self.act_lang_en)
        self.menu_language.addAction(self.act_lang_zh)
        self.menu_language.addAction(self.act_lang_en)
        self.act_lang_zh.triggered.connect(lambda: self._set_language("zh_CN"))
        self.act_lang_en.triggered.connect(lambda: self._set_language("en_US"))

        self.act_theme_group = QActionGroup(self)
        self.act_theme_group.setExclusive(True)

        self.act_theme_system = QAction(self)
        self.act_theme_system.setCheckable(True)
        self.act_theme_system.setData("system")
        self.act_theme_light = QAction(self)
        self.act_theme_light.setCheckable(True)
        self.act_theme_light.setData("light")
        self.act_theme_dark = QAction(self)
        self.act_theme_dark.setCheckable(True)
        self.act_theme_dark.setData("dark")
        self.act_theme_group.addAction(self.act_theme_system)
        self.act_theme_group.addAction(self.act_theme_light)
        self.act_theme_group.addAction(self.act_theme_dark)
        self.menu_theme.addAction(self.act_theme_system)
        self.menu_theme.addAction(self.act_theme_light)
        self.menu_theme.addAction(self.act_theme_dark)
        self.act_theme_system.triggered.connect(lambda: self._set_theme_mode("system"))
        self.act_theme_light.triggered.connect(lambda: self._set_theme_mode("light"))
        self.act_theme_dark.triggered.connect(lambda: self._set_theme_mode("dark"))

        self.act_about = QAction(self)
        self.menu_help.addAction(self.act_about)
        self.act_about.triggered.connect(self._show_about)

        self.title_bar.set_menus(self.menu_settings, self.menu_help)

        self._set_language(self._lang_code)
        self._set_theme_mode(self._theme_mode)

    def _t(self, key: str) -> str:
        return self._lang.get(key, key)

    def _load_language(self, code: str) -> None:
        path = _lang_dir() / f"{code}.json"
        self._lang = _load_json(path)
        self._lang_code = code
        self._apply_texts()

    def _apply_texts(self) -> None:
        self.setWindowTitle(self._t("app_title"))
        self.grp_files.setTitle(self._t("group_files"))
        self.grp_basic.setTitle(self._t("group_basic"))
        self.grp_opt.setTitle(self._t("group_opt"))
        self.grp_paths.setTitle(self._t("group_paths"))
        self.grp_log.setTitle(self._t("group_log"))

        self.title_bar.lbl_title.setText(self._t("app_title"))

        self.lbl_py_file.setText(self._t("lbl_py_file"))
        self.lbl_output_dir.setText(self._t("lbl_output_dir"))

        self.btn_py.setText(self._t("btn_browse"))
        self.btn_out.setText(self._t("btn_browse"))

        self.menu_settings.setTitle(self._t("menu_settings"))
        self.menu_language.setTitle(self._t("menu_language"))
        self.menu_theme.setTitle(self._t("menu_theme"))
        self.menu_help.setTitle(self._t("menu_help"))

        self.title_bar.btn_settings.setText(self._t("menu_settings"))
        self.title_bar.btn_help.setText(self._t("menu_help"))

        self.act_lang_zh.setText(self._t("lang_zh"))
        self.act_lang_en.setText(self._t("lang_en"))
        self.act_theme_system.setText(self._t("theme_system"))
        self.act_theme_light.setText(self._t("theme_light"))
        self.act_theme_dark.setText(self._t("theme_dark"))
        self.act_about.setText(self._t("menu_about"))

        self.rb_onefile.setText(self._t("opt_onefile"))
        self.rb_onedir.setText(self._t("opt_onedir"))
        self.rb_console.setText(self._t("opt_console"))
        self.rb_windowed.setText(self._t("opt_windowed"))

        self.lbl_name.setText(self._t("lbl_name"))
        self.lbl_icon.setText(self._t("lbl_icon"))
        self.btn_icon.setText(self._t("btn_browse"))

        self.ck_uac.setText(self._t("opt_uac_admin"))
        self.ck_clean.setText(self._t("opt_clean"))
        self.ck_noconfirm.setText(self._t("opt_noconfirm"))
        self.ck_use_upx.setText(self._t("opt_use_upx"))

        self.lbl_upx_dir.setText(self._t("lbl_upx_dir"))
        self.btn_upx_dir.setText(self._t("btn_browse"))

        self.lbl_specpath.setText(self._t("lbl_specpath"))
        self.lbl_workpath.setText(self._t("lbl_workpath"))
        self.lbl_distpath.setText(self._t("lbl_distpath"))
        self.btn_specpath.setText(self._t("btn_browse"))
        self.btn_workpath.setText(self._t("btn_browse"))
        self.btn_distpath.setText(self._t("btn_browse"))

        self.btn_start.setText(self._t("btn_start"))
        self.btn_cancel.setText(self._t("btn_cancel"))
        self.btn_clear.setText(self._t("btn_clear"))

        if not self._worker:
            self.lbl_status.setText(self._t("status_ready"))

    def _apply_theme(self, theme: str) -> None:
        self._theme = theme
        if theme == "dark":
            self.setStyleSheet(
                "QWidget{color:#e6e6e6;}"
                "QMainWindow{background:transparent;}"
                "#root{background:rgba(15,17,21,190);border-radius:14px;}"
                "QGroupBox{border:1px solid #2a2f3a;border-radius:8px;margin-top:12px;padding:8px;}"
                "QGroupBox::title{subcontrol-origin: margin;subcontrol-position: top left;left:10px;top:0px;padding:0 6px;}"
                "QLineEdit,QTextEdit,QComboBox{background:#151924;border:1px solid #2a2f3a;border-radius:6px;padding:6px;}"
                "QPushButton{background:#1f6feb;border:none;border-radius:8px;padding:8px 12px;color:white;}"
                "QPushButton:disabled{background:#2a2f3a;color:#8892a6;}"
                "QCheckBox{spacing:8px;}"
                "QMenuBar{background:transparent;border:none;padding:2px;}"
                "QMenuBar::item{background:transparent;padding:6px 10px;border-radius:8px;}"
                "QMenuBar::item:selected{background:#151924;}"
                "QMenu{background:#151924;border:1px solid #2a2f3a;border-radius:10px;padding:6px;}"
                "QMenu::item{padding:6px 14px;border-radius:8px;}"
                "QMenu::item:selected{background:#2a2f3a;}"
                "TitleBar{background:transparent;}"
                "#titleMenuBtn{background:#151924;border:1px solid #2a2f3a;border-radius:8px;padding:0 10px;color:#e6e6e6;}"
                "#titleMenuBtn:hover{background:#2a2f3a;}"
                "#titleMenuBtn:disabled{background:#11161f;border:1px solid #222836;color:#6b7385;}"
                "#titleMin{background:rgba(255,255,255,0.06);color:white;border-radius:8px;}"
                "#titleMin:hover{background:rgba(255,255,255,0.10);}"
                "#titleClose{background:#ef4444;color:white;border-radius:8px;}"
                "#titleClose:hover{background:#dc2626;}"
            )
        else:
            self.setStyleSheet(
                "QWidget{color:#1f2328;}"
                "QMainWindow{background:transparent;}"
                "#root{background:rgba(246,247,251,210);border-radius:14px;}"
                "QGroupBox{border:1px solid #d7dbe6;border-radius:8px;margin-top:12px;padding:8px;background:white;}"
                "QGroupBox::title{subcontrol-origin: margin;subcontrol-position: top left;left:10px;top:0px;padding:0 6px;}"
                "QLineEdit,QTextEdit,QComboBox{background:white;border:1px solid #d7dbe6;border-radius:6px;padding:6px;}"
                "QPushButton{background:#2563eb;border:none;border-radius:8px;padding:8px 12px;color:white;}"
                "QPushButton:disabled{background:#d7dbe6;color:#6b7280;}"
                "QCheckBox{spacing:8px;}"
                "QMenuBar{background:transparent;border:none;padding:2px;}"
                "QMenuBar::item{background:transparent;padding:6px 10px;border-radius:8px;}"
                "QMenuBar::item:selected{background:#ffffff;}"
                "QMenu{background:#ffffff;border:1px solid #d7dbe6;border-radius:10px;padding:6px;}"
                "QMenu::item{padding:6px 14px;border-radius:8px;}"
                "QMenu::item:selected{background:#eef2ff;}"
                "TitleBar{background:transparent;}"
                "#titleMenuBtn{background:#ffffff;border:1px solid #d7dbe6;border-radius:8px;padding:0 10px;color:#111827;}"
                "#titleMenuBtn:hover{background:#f3f4f6;}"
                "#titleMenuBtn:disabled{background:#f3f4f6;border:1px solid #e5e7eb;color:#9ca3af;}"
                "#titleMin{background:rgba(0,0,0,0.05);color:#111827;border-radius:8px;}"
                "#titleMin:hover{background:rgba(0,0,0,0.08);}"
                "#titleClose{background:#ef4444;color:white;border-radius:8px;}"
                "#titleClose:hover{background:#dc2626;}"
            )
        self._apply_popup_menu_theme()

    def _apply_popup_menu_theme(self) -> None:
        if self._theme == "dark":
            menu_style = (
                "QMenu{background:#151924;color:#e6e6e6;border:1px solid #2a2f3a;border-radius:10px;padding:6px;}"
                "QMenu::item{padding:6px 14px;border-radius:8px;}"
                "QMenu::item:selected{background:#2a2f3a;}"
                "QMenu::separator{height:1px;background:#2a2f3a;margin:4px 10px;}"
            )
        else:
            menu_style = (
                "QMenu{background:#ffffff;color:#111827;border:1px solid #d7dbe6;border-radius:10px;padding:6px;}"
                "QMenu::item{padding:6px 14px;border-radius:8px;}"
                "QMenu::item:selected{background:#eef2ff;}"
                "QMenu::separator{height:1px;background:#e5e7eb;margin:4px 10px;}"
            )

        for menu in (self.menu_settings, self.menu_language, self.menu_theme, self.menu_help):
            menu.setStyleSheet(menu_style)

    def _show_message(self, icon: QMessageBox.Icon, text: str) -> None:
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(self._t("app_title"))
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        box.setWindowModality(Qt.WindowModal)
        box.setStyleSheet(self._message_box_style())
        box.exec_()

    def _message_box_style(self) -> str:
        if self._theme == "dark":
            return (
                "QMessageBox{background:#151924;color:#e6e6e6;}"
                "QLabel{color:#e6e6e6;}"
                "QPushButton{background:#1f6feb;border:none;border-radius:8px;padding:8px 12px;color:white;min-width:88px;}"
            )
        return (
            "QMessageBox{background:#ffffff;color:#111827;}"
            "QLabel{color:#111827;}"
            "QPushButton{background:#2563eb;border:none;border-radius:8px;padding:8px 12px;color:white;min-width:88px;}"
        )

    def _set_language(self, code: str) -> None:
        if code != self._lang_code:
            self._load_language(code)
        if code == "zh_CN":
            self.act_lang_zh.setChecked(True)
        else:
            self.act_lang_en.setChecked(True)

    def _get_effective_theme(self) -> str:
        if self._theme_mode == "system":
            sys_theme = _read_windows_apps_theme()
            return sys_theme or "light"
        return self._theme_mode

    def _set_theme_mode(self, mode: str) -> None:
        if mode not in ("system", "light", "dark"):
            return

        self._theme_mode = mode
        target = self._get_effective_theme()
        if target == self._theme:
            self._update_theme_checks()
            return

        self.setWindowOpacity(0.0)
        self._apply_theme(target)
        self._animate_fade(0.0, 1.0, duration_ms=220)
        self._update_theme_checks()

    def _update_theme_checks(self) -> None:
        if self._theme_mode == "system":
            self.act_theme_system.setChecked(True)
        elif self._theme_mode == "dark":
            self.act_theme_dark.setChecked(True)
        else:
            self.act_theme_light.setChecked(True)

    def _poll_system_theme(self) -> None:
        if self._theme_mode != "system":
            return
        target = self._get_effective_theme()
        if target != self._theme:
            self._apply_theme(target)

    def _show_about(self) -> None:
        title = self._t("about_title")
        text = self._t("about_text")
        dlg = AboutDialog(self, title=title, html=text, theme=self._theme)
        dlg.exec_()

    def _pick_py(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "", "", "Python (*.py)")
        if path:
            self.ed_py.setText(path)

    def _pick_out(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "")
        if path:
            self.ed_out.setText(path)
            if not self.ed_distpath.text().strip():
                self.ed_distpath.setText(path)

    def _pick_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "", "", "Icon (*.ico)")
        if path:
            self.ed_icon.setText(path)

    def _pick_dir(self, target: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "")
        if path:
            target.setText(path)

    def _sync_enabled_state(self, running: bool) -> None:
        widgets = [
            self.ed_py,
            self.btn_py,
            self.ed_out,
            self.btn_out,
            self.rb_onefile,
            self.rb_onedir,
            self.rb_console,
            self.rb_windowed,
            self.ed_name,
            self.ed_icon,
            self.btn_icon,
            self.ck_uac,
            self.ck_clean,
            self.ck_noconfirm,
            self.ck_use_upx,
            self.ed_upx_dir,
            self.btn_upx_dir,
            self.ed_specpath,
            self.btn_specpath,
            self.ed_workpath,
            self.btn_workpath,
            self.ed_distpath,
            self.btn_distpath,
        ]
        for w in widgets:
            w.setEnabled(not running)

        self.btn_start.setEnabled(not running)
        self.btn_cancel.setEnabled(running)

        self.lbl_status.setText(self._t("status_running") if running else self._t("status_ready"))
        self._on_use_upx_toggled(self.ck_use_upx.isChecked())

        self.title_bar.btn_settings.setEnabled(not running)
        self.title_bar.btn_help.setEnabled(not running)

    def _validate(self) -> Optional[BuildOptions]:
        py_file = self.ed_py.text().strip()
        out_dir = self.ed_out.text().strip()

        if not py_file.lower().endswith(".py") or not Path(py_file).exists():
            self._show_message(QMessageBox.Warning, self._t("msg_select_py"))
            return None
        if not out_dir or not Path(out_dir).exists():
            self._show_message(QMessageBox.Warning, self._t("msg_select_output"))
            return None

        distpath = self.ed_distpath.text().strip() or out_dir
        specpath = self.ed_specpath.text().strip()
        workpath = self.ed_workpath.text().strip()

        use_upx = self.ck_use_upx.isChecked()
        upx_dir = self.ed_upx_dir.text().strip()
        if use_upx and not upx_dir:
            default_dir = _default_upx_dir()
            if default_dir:
                upx_dir = default_dir
            else:
                self._show_message(QMessageBox.Warning, self._t("msg_upx_missing"))
                return None

        return BuildOptions(
            py_file=py_file,
            output_dir=out_dir,
            mode_onefile=self.rb_onefile.isChecked(),
            windowed=self.rb_windowed.isChecked(),
            name=self.ed_name.text().strip(),
            icon=self.ed_icon.text().strip(),
            uac_admin=self.ck_uac.isChecked(),
            clean=self.ck_clean.isChecked(),
            noconfirm=self.ck_noconfirm.isChecked(),
            use_upx=use_upx,
            upx_dir=upx_dir,
            specpath=specpath,
            workpath=workpath,
            distpath=distpath,
        )

    def _build_args(self, opt: BuildOptions) -> List[str]:
        args: List[str] = [sys.executable, "-m", "PyInstaller"]

        args.append("--onefile" if opt.mode_onefile else "--onedir")
        args.append("--windowed" if opt.windowed else "--console")

        if opt.name:
            args += ["--name", opt.name]
        if opt.icon:
            args += ["--icon", opt.icon]
        if opt.uac_admin:
            args.append("--uac-admin")
        if opt.clean:
            args.append("--clean")
        if opt.noconfirm:
            args.append("-y")

        if opt.specpath:
            args += ["--specpath", opt.specpath]
        if opt.workpath:
            args += ["--workpath", opt.workpath]
        if opt.distpath:
            args += ["--distpath", opt.distpath]

        if opt.use_upx:
            args += ["--upx-dir", opt.upx_dir]
        else:
            args.append("--noupx")

        args.append(opt.py_file)
        return args

    def _append_line(self, line: str) -> None:
        is_error, friendly = self._analyze_error_line(line)
        if is_error and friendly:
            self._append_html(f"<span style='color:#ef4444;'><b>{self._escape(line)}</b></span>")
            self._append_html(f"<span style='color:#ef4444;'>{self._escape(friendly)}</span>")
            return
        if is_error:
            self._append_html(f"<span style='color:#ef4444;'>{self._escape(line)}</span>")
        else:
            self._append_html(self._escape(line))

    def _append_html(self, html: str) -> None:
        self.txt_log.append(html)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _analyze_error_line(self, line: str) -> Tuple[bool, str]:
        lower = line.lower()
        if "modulenotfounderror" in lower or "no module named" in lower:
            m = re.search(r"No module named ['\"]([^'\"]+)['\"]", line)
            module = m.group(1) if m else ""
            detail = line.strip()
            msg = self._t("err_module_not_found").format(detail=detail, module=module or "<module>")
            return True, msg

        if "permissionerror" in lower or "access is denied" in lower:
            detail = line.strip()
            msg = self._t("err_permission").format(detail=detail)
            return True, msg

        if "syntaxerror" in lower:
            detail = line.strip()
            msg = self._t("err_syntax").format(detail=detail)
            return True, msg

        if "error:" in lower or "traceback" in lower:
            return True, ""

        return False, ""

    def _start(self) -> None:
        if self._worker:
            return
        if not _has_pyinstaller():
            self._show_message(QMessageBox.Critical, self._t("msg_pyinstaller_missing"))
            return

        opt = self._validate()
        if not opt:
            return

        args = self._build_args(opt)
        self.txt_log.clear()
        self._append_html(self._escape(" ".join(args)))
        self._append_html(self._escape(""))

        cwd = str(Path(opt.py_file).resolve().parent)
        self._worker = PyInstallerWorker(args=args, cwd=cwd)
        self._worker.line.connect(self._append_line)
        self._worker.finished_with_code.connect(self._on_finished)
        self._sync_enabled_state(running=True)
        self._worker.start()

        if opt.use_upx:
            default_dir = _default_upx_dir()
            if default_dir and (not self.ed_upx_dir.text().strip() or self.ed_upx_dir.text().strip() == default_dir):
                self._append_html(
                    f"<span style='color:#64748b;'>{self._escape(self._t('msg_note_upx_default').format(detail=default_dir))}</span>"
                )

    def _cancel(self) -> None:
        if self._worker:
            self._worker.cancel()

    def _on_finished(self, code: int) -> None:
        self._sync_enabled_state(running=False)

        if code == 0:
            self.lbl_status.setText(self._t("status_done"))
        else:
            self.lbl_status.setText(self._t("status_failed"))
            self._append_html(
                f"<span style='color:#ef4444;'><b>{self._escape(self._t('err_generic').format(detail=str(code)))}</b></span>"
            )

        if self._worker:
            self._worker.deleteLater()
        self._worker = None

    def _on_use_upx_toggled(self, checked: bool) -> None:
        enabled = checked and not self._worker
        self.ed_upx_dir.setEnabled(enabled)
        self.btn_upx_dir.setEnabled(enabled)
        if checked and not self.ed_upx_dir.text().strip():
            default_dir = _default_upx_dir()
            if default_dir:
                self.ed_upx_dir.setText(default_dir)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(".py"):
                event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path.lower().endswith(".py"):
                self.ed_py.setText(path)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._fade_anim is None:
            self.setWindowOpacity(0.0)
            self._animate_fade(0.0, 1.0, duration_ms=260)

    def _animate_fade(self, start: float, end: float, duration_ms: int) -> None:
        try:
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setDuration(duration_ms)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            self._fade_anim = anim
        except Exception:
            self.setWindowOpacity(end)


def main() -> int:
    app = QApplication(sys.argv)
    f = app.font()
    f.setPointSize(max(11, f.pointSize() + 2))
    app.setFont(f)
    win = MainWindow()
    win.resize(980, 720)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
