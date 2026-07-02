# PreToolUse guard: refuse edits to files that hold secrets (.env with the
# DASHSCOPE_API_KEY / RDS DATABASE_URL). .env.example is fine to edit.
# Blocks by exiting 2 with a message on stderr (surfaced to Claude).
$raw = [Console]::In.ReadToEnd()
try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$fp = $null
if ($data.tool_input -and $data.tool_input.file_path) { $fp = [string]$data.tool_input.file_path }
if (-not $fp) { exit 0 }

if (($fp -match '\.env$') -and ($fp -notmatch '\.env\.example$')) {
    [Console]::Error.WriteLine("BLOCKED: '$fp' holds secrets (DASHSCOPE_API_KEY / DATABASE_URL). Edit it by hand, not via Claude.")
    exit 2
}
exit 0
