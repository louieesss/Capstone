@echo off
SET GIT="C:\Program Files\Git\bin\git.exe"

cd /d "C:\Users\Admin\Desktop\CAPS"

%GIT% config user.email "louieesss@github.com"
%GIT% config user.name "louieesss"

%GIT% add .
echo Files staged.

%GIT% commit -m "Initial commit - Pollination Monitoring System"
echo Committed.

%GIT% remote remove origin 2>nul
%GIT% remote add origin https://github.com/louieesss/Capstone.git
echo Remote added.

%GIT% branch -M main
%GIT% push -u origin main
echo Done!
pause
