@echo off
setlocal enabledelayedexpansion

:: Configuration
set "REPO_URL=https://github.com/Mastersuek/Vera.git"
set "COMMIT_MSG=Initial commit: Setup project structure and core functionality"

:: Colors
set "RED=<NUL set /p="">NUL&findstr /a:4f /R "[^\n]\+\n" NUL"
set "GREEN=<NUL set /p="">NUL&findstr /a:2f /R "[^\n]\+\n" NUL"
set "YELLOW=<NUL set /p="">NUL&findstr /a:6f /R "[^\n]\+\n" NUL"
set "RESET=<NUL set /p="">NUL&findstr /a:7f /R "[^\n]\+\n" NUL"

echo %YELLOW%🚀 Подготовка к загрузке проекта Vera на GitHub...%RESET%
echo.

:: Проверка установки Git
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %RED%❌ Git не установлен или не добавлен в PATH. Установите Git и попробуйте снова.%RESET%
    echo Скачайте с: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Инициализация репозитория, если еще не инициализирован
if not exist .git (
    echo %YELLOW%Инициализация нового Git репозитория...%RESET%
    git init
) else (
    echo %GREEN%✓ Git репозиторий уже инициализирован%RESET%
)

:: Добавление удаленного репозитория, если его еще нет
git remote show origin >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%Добавление удаленного репозитория: %REPO_URL%%RESET%
    git remote add origin %REPO_URL%
) else (
    echo %YELLOW%Удаленный репозиторий 'origin' уже существует. Обновление URL...%RESET%
    git remote set-url origin %REPO_URL%
)

:: Добавление файлов
echo.
echo %YELLOW%📦 Добавление изменений в индекс...%RESET%
git add .

:: Создание коммита
echo.
echo %YELLOW%💾 Создание коммита...%RESET%
git commit -m "%COMMIT_MSG%"

:: Проверка существования ветки main, создание если нужно
git show-ref --verify --quiet refs/heads/main
if %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%Создание ветки 'main'...%RESET%
    git checkout -b main
)

:: Отправка изменений
echo.
echo %YELLOW%🚀 Отправка изменений в удаленный репозиторий...%RESET%
git push -u origin main --force

if %ERRORLEVEL% EQU 0 (
    echo.
    echo %GREEN%✅ Успешно загружено в %REPO_URL%%RESET%
    echo %GREEN%🎉 Репозиторий успешно настроен!%RESET%
) else (
    echo.
    echo %RED%❌ Не удалось отправить изменения. Проверьте настройки Git и попробуйте снова.%RESET%
)

echo.
pause