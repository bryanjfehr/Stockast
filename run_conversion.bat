@echo off
setlocal

set "PYTHON_SCRIPT=converter.py"
set "INPUT_DIR=shared"
set "OUTPUT_DIR=shared"

REM Process each HTML file
python %PYTHON_SCRIPT% "%INPUT_DIR%\Accessing the API _ Santiment Academy.html" "%OUTPUT_DIR%\Accessing the API _ Santiment Academy.txt"
python %PYTHON_SCRIPT% "%INPUT_DIR%\Common Santiment API GraphQL Queries _ Santiment Academy.html" "%OUTPUT_DIR%\Common Santiment API GraphQL Queries _ Santiment Academy.txt"
python %PYTHON_SCRIPT% "%INPUT_DIR%\Fetching Metrics _ Santiment Academy.html" "%OUTPUT_DIR%\Fetching Metrics _ Santiment Academy.txt"
python %PYTHON_SCRIPT% "%INPUT_DIR%\API Historical and Realtime data restrictions _ Santiment Academy.html" "%OUTPUT_DIR%\API Historical and Realtime data restrictions _ Santiment Academy.txt"
python %PYTHON_SCRIPT% "%INPUT_DIR%\API Rate Limits _ Santiment Academy.html" "%OUTPUT_DIR%\API Rate Limits _ Santiment Academy.txt"
python %PYTHON_SCRIPT% "%INPUT_DIR%\API Complexity _ Santiment Academy.html" "%OUTPUT_DIR%\API Complexity _ Santiment Academy.txt"

endlocal
echo "HTML processing complete."

