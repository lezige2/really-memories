param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

# Convenience entry: run the chat UI from the project root with UTF-8.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
Push-Location $root
try {
    python -m biomem @Rest
} finally {
    Pop-Location
}