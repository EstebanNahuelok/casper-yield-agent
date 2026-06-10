@echo off
start cmd /k "C:\PROYECTOS\casper-mcp\src\CasperMcp\bin\Debug\net10.0\CasperMcp.exe --transport http --network testnet --port 3001"
timeout /t 3
start cmd /k "cd C:\PROYECTOS\casper-yield-agent\agent && C:\PROYECTOS\casper-yield-agent\venv\Scripts\python.exe main.py"
start cmd /k "ngrok http 8000"