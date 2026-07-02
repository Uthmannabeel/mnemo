# PostToolUse guard: when core memory/agent/eval code changes, run the fast
# offline regression test that encodes Mnemo's thesis (memory improves accuracy).
# Non-fatal: reports failure to Claude via exit 2 so it can fix, but never blocks
# edits to unrelated files.
$raw = [Console]::In.ReadToEnd()
try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$fp = $null
if ($data.tool_input -and $data.tool_input.file_path) { $fp = [string]$data.tool_input.file_path }
if (-not $fp) { exit 0 }

# Only trigger for the code paths the invariant depends on.
if ($fp -notmatch 'app[\\/](memory|agent|eval)') { exit 0 }

$backend = "C:\Users\Nabeel Uthman\mnemo\backend"
$env:MNEMO_OFFLINE = "1"
$env:MNEMO_STORE = "memory"
Push-Location $backend
$out1 = & python -m tests.test_learning 2>&1
$c1 = $LASTEXITCODE
$out2 = & python -m tests.test_org_learning 2>&1
$c2 = $LASTEXITCODE
Pop-Location

if ($c1 -ne 0 -or $c2 -ne 0) {
    [Console]::Error.WriteLine("test-guardian: an eval invariant FAILED after editing $fp`nExp1: $out1`nExp2: $out2")
    exit 2
}
Write-Output "test-guardian: both invariants green (Exp1 ablation + Exp2 org conventions)."
exit 0
