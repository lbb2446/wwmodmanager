# PyInstaller hook: 确保 pywebview（import webview）及其依赖被打包
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('pywebview')
