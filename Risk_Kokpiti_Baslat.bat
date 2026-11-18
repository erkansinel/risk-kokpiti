@echo off
setlocal
title Risk Kokpiti

rem ------------------------------------------------------------
rem  Risk Kokpiti baslatici
rem  Ilk calistirmada Python sanal ortamini (.venv) kurar ve
rem  paketleri yukler. Sonraki calistirmalarda dogrudan acar.
rem ------------------------------------------------------------

rem Bu dosyanin bulundugu klasore gec; app.py yoksa varsayilan klasore
cd /d "%~dp0"
if not exist "app.py" cd /d "C:\Programlarim\likidite_kokpiti\kokpit"
if not exist "app.py" (
    echo [HATA] app.py bulunamadi. Bu dosyayi kokpit klasorune koyun.
    goto :hata
)

rem Python'u bul (once py baslaticisi, sonra python)
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [HATA] Python bulunamadi.
    echo Python 3.10 veya ustunu https://www.python.org/downloads/ adresinden kurun
    echo ve kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
    goto :hata
)

rem Sanal ortam yoksa olustur
if not exist ".venv\Scripts\python.exe" (
    echo Ilk kurulum yapiliyor, bu islem birkac dakika surebilir...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [HATA] Sanal ortam olusturulamadi.
        goto :hata
    )
)
set "VPY=.venv\Scripts\python.exe"

rem requirements.txt degistiyse (veya ilk kurulumsa) paketleri yukle
fc /b "requirements.txt" ".venv\requirements.kurulu.txt" >nul 2>nul
if errorlevel 1 (
    echo Paketler yukleniyor...
    "%VPY%" -m pip install --upgrade pip --disable-pip-version-check -q
    "%VPY%" -m pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 (
        echo [HATA] Paketler yuklenemedi. Internet baglantinizi kontrol edin.
        goto :hata
    )
    copy /y "requirements.txt" ".venv\requirements.kurulu.txt" >nul
)

rem Streamlit ilk acilista e-posta sormasin
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    mkdir "%USERPROFILE%\.streamlit" 2>nul
    >"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

echo.
echo Risk Kokpiti baslatiliyor... Tarayici otomatik acilacak.
echo Kapatmak icin bu pencereyi kapatin veya Ctrl+C basin.
echo.
"%VPY%" -m streamlit run app.py --browser.gatherUsageStats false
if errorlevel 1 goto :hata
goto :eof

:hata
echo.
pause
exit /b 1
