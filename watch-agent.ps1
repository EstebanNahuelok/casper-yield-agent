###############################################################################
#  watch-agent.ps1  –  Monitor en tiempo real del Casper Yield Agent
#  Uso:  .\watch-agent.ps1          (refresca cada 5 s por defecto)
#        .\watch-agent.ps1 -Interval 10 -Url http://localhost:8000
###############################################################################
param(
    [int]    $Interval = 5,
    [string] $Url      = "http://localhost:8000"
)

$ESC   = [char]27
$RESET = "$ESC[0m"
$BOLD  = "$ESC[1m"
$DIM   = "$ESC[2m"

$CYAN    = "$ESC[96m"
$GREEN   = "$ESC[92m"
$YELLOW  = "$ESC[93m"
$RED     = "$ESC[91m"
$MAGENTA = "$ESC[95m"
$BLUE    = "$ESC[94m"
$WHITE   = "$ESC[97m"
$GRAY    = "$ESC[90m"

function Color-Status([string]$s) {
    switch -Wildcard ($s) {
        "running"      { return "$GREEN$s$RESET" }
        "deciding"     { return "$YELLOW$s$RESET" }
        "executing"    { return "$MAGENTA$s$RESET" }
        "observing"    { return "$CYAN$s$RESET" }
        "connecting*"  { return "$YELLOW$s$RESET" }
        "waiting*"     { return "$YELLOW$s$RESET" }
        "reconnecting" { return "$YELLOW$s$RESET" }
        "stopped"      { return "$RED$s$RESET" }
        default        { return "$GRAY$s$RESET" }
    }
}

function Color-Action([string]$a) {
    switch ($a) {
        "SWAP"  { return "${GREEN}${BOLD}▲ SWAP$RESET" }
        "HOLD"  { return "${BLUE}${BOLD}◆ HOLD$RESET" }
        default { return "$GRAY$a$RESET" }
    }
}

function Draw-Header {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host ""
    Write-Host "  ${CYAN}${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
    Write-Host "  ${CYAN}${BOLD}║        🌀  CASPER YIELD AGENT  —  MONITOR               ║${RESET}"
    Write-Host "  ${CYAN}${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
    Write-Host "  ${GRAY}Endpoint : $Url   |   Refresh : ${Interval}s   |   $now${RESET}"
    Write-Host ""
}

function Draw-Section([string]$title) {
    $line = "─" * [Math]::Max(0, 52 - $title.Length)
    Write-Host "  ${YELLOW}── $title ${DIM}$line${RESET}"
}

function Fmt([object]$n, [int]$d = 4) {
    if ($null -eq $n -or $n -eq "") { return "${GRAY}—${RESET}" }
    try { return "$WHITE$([math]::Round([double]$n, $d))$RESET" }
    catch { return "$WHITE$n$RESET" }
}

function Draw-AgentState($data) {
    $status   = Color-Status ($data.status ?? "—")
    $actions  = if ($null -ne $data.actions_taken) { "$WHITE$($data.actions_taken)$RESET" } else { "${GRAY}—${RESET}" }
    $balance  = Fmt $data.balance_cspr 2
    $updated  = if ($data.last_updated) {
        try { "$GRAY$(([datetime]$data.last_updated).ToString('HH:mm:ss'))$RESET" }
        catch { "$GRAY$($data.last_updated)$RESET" }
    } else { "${GRAY}—${RESET}" }
    $hash     = if ($data.last_tx_hash) { "$CYAN$($data.last_tx_hash.Substring(0, [Math]::Min(20,$data.last_tx_hash.Length)))...$RESET" } else { "${GRAY}—${RESET}" }

    Draw-Section "AGENT STATE"
    Write-Host "    Status         : $status"
    Write-Host "    Acciones       : $actions"
    Write-Host "    Balance vault  : $balance CSPR"
    Write-Host "    Último update  : $updated"
    Write-Host "    Último tx hash : $hash"
    Write-Host ""
}

function Draw-Market($market) {
    if (-not $market) {
        Draw-Section "MARKET DATA"
        Write-Host "    ${GRAY}Sin datos de mercado todavía...${RESET}"
        Write-Host ""
        return
    }
    $ts = ""
    if ($market.timestamp) {
        try { $ts = "$GRAY$(([datetime]$market.timestamp).ToString('HH:mm:ss'))$RESET" }
        catch { $ts = "$GRAY$($market.timestamp)$RESET" }
    }

    Draw-Section "MARKET DATA"
    Write-Host "    Balance vault  : $(Fmt $market.balance_cspr 2) CSPR"
    Write-Host "    Pool APY       : $(Fmt $market.pool_apy 2) %"
    Write-Host "    Current APY    : $(Fmt $market.current_apy 2) %"
    Write-Host "    Slippage est.  : $(Fmt $market.estimated_slippage 4) %"
    Write-Host "    CSPR/USD       : `$$(Fmt $market.cspr_price_usd 4)"
    Write-Host "    Timestamp      : $ts"
    Write-Host ""
}

function Wrap-Text([string]$text, [int]$width = 55, [string]$indent = "              ") {
    if (-not $text) { return @("—") }
    $words  = $text -split "\s+"
    $lines  = @()
    $line   = "    "
    foreach ($w in $words) {
        if (($line + $w).Length -gt $width) {
            $lines += $line.TrimEnd()
            $line = "$indent$w "
        } else {
            $line += "$w "
        }
    }
    if ($line.Trim()) { $lines += $line.TrimEnd() }
    return $lines
}

function Draw-LastDecision($dec) {
    if (-not $dec) {
        Draw-Section "LAST DECISION"
        Write-Host "    ${GRAY}Sin decisiones todavía...${RESET}"
        Write-Host ""
        return
    }
    $action  = Color-Action ($dec.action ?? "—")
    $amount  = Fmt $dec.amount 2
    $amtOut  = Fmt $dec.amount_out 2
    $tIn     = if ($dec.token_in)  { "$WHITE$($dec.token_in)$RESET"  } else { "${GRAY}—${RESET}" }
    $tOut    = if ($dec.token_out) { "$WHITE$($dec.token_out)$RESET" } else { "${GRAY}—${RESET}" }

    Draw-Section "LAST DECISION"
    Write-Host "    Acción     : $action"
    Write-Host "    Token In   : $tIn"
    Write-Host "    Token Out  : $tOut"
    Write-Host "    Amount In  : $amount CSPR"
    Write-Host "    Amount Out : $amtOut sCSPR"
    Write-Host "    Reasoning  :"
    foreach ($l in (Wrap-Text $dec.reasoning)) {
        Write-Host "  ${GRAY}$l${RESET}"
    }
    Write-Host ""
}

function Draw-SwarmVotes($swarm) {
    if (-not $swarm -or -not $swarm.votes -or $swarm.votes.Count -eq 0) { return }

    $tally = $swarm.vote_tally
    $final = Color-Action ($swarm.final_action ?? "—")

    Draw-Section "SWARM VOTES"
    Write-Host "    Decisión final : $final"
    if ($tally) {
        $swap = if ($tally.SWAP) { $tally.SWAP } else { 0 }
        $hold = if ($tally.HOLD) { $tally.HOLD } else { 0 }
        Write-Host "    Tally          : ${GREEN}SWAP=$swap${RESET}  ${BLUE}HOLD=$hold${RESET}"
    }
    Write-Host ""
    foreach ($v in $swarm.votes) {
        $icon   = Color-Action ($v.action ?? "—")
        $name   = "$CYAN$($v.agent_name)$RESET"
        $reason = $v.reasoning
        if ($reason -and $reason.Length -gt 60) { $reason = $reason.Substring(0,57) + "..." }
        Write-Host "    $icon  $name"
        Write-Host "       ${GRAY}$reason${RESET}"
    }
    Write-Host ""
}

function Draw-History($history) {
    if (-not $history -or $history.Count -eq 0) { return }
    $recent = $history | Select-Object -Last 5

    Draw-Section "HISTORY (últimas 5)"
    foreach ($h in $recent) {
        $ts = ""
        if ($h.timestamp) {
            try { $ts = ([datetime]$h.timestamp).ToString("HH:mm:ss") }
            catch { $ts = $h.timestamp }
        }
        $act  = Color-Action ($h.action ?? "—")
        $hash = if ($h.deploy_hash) { "$CYAN$($h.deploy_hash.Substring(0,[Math]::Min(16,$h.deploy_hash.Length)))...$RESET" } else { "${GRAY}(no hash)${RESET}" }
        Write-Host "    $GRAY$ts$RESET  $act  $hash"
    }
    Write-Host ""
}

function Draw-Errors($errs) {
    if (-not $errs -or $errs.Count -eq 0) { return }
    Draw-Section "RECENT ERRORS"
    foreach ($e in ($errs | Select-Object -Last 3)) {
        $msg = $e
        if ($msg.Length -gt 75) { $msg = $msg.Substring(0,72) + "..." }
        Write-Host "    ${RED}✖ $msg${RESET}"
    }
    Write-Host ""
}

function Draw-Footer {
    Write-Host "  ${GRAY}Ctrl+C para salir  |  Próximo refresh en ${Interval}s${RESET}"
    Write-Host ""
}

###############################################################################
#  MAIN LOOP
###############################################################################

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { $host.UI.RawUI.WindowTitle = "Casper Yield Agent – Monitor" } catch {}

Write-Host ""
Write-Host "  ${CYAN}Conectando a $Url ...${RESET}"

while ($true) {
    $ok = $false
    $errMsg = ""
    $resp = $null
    try {
        $resp   = Invoke-RestMethod -Uri "$Url/status" -TimeoutSec 4 -ErrorAction Stop
        $ok     = $true
    } catch {
        $errMsg = $_.Exception.Message
    }

    Clear-Host
    Draw-Header

    if (-not $ok) {
        Write-Host "  ${RED}${BOLD}  SIN CONEXIÓN CON EL AGENTE  ${RESET}"
        Write-Host ""
        Write-Host "  ${GRAY}Error: $errMsg${RESET}"
        Write-Host ""
        Write-Host "  ${YELLOW}Para iniciar el agente:${RESET}"
        Write-Host "  ${GRAY}  cd agent${RESET}"
        Write-Host "  ${GRAY}  ..\venv\Scripts\python.exe main.py${RESET}"
        Write-Host ""
        Write-Host "  ${YELLOW}O usa el launcher:${RESET}"
        Write-Host "  ${GRAY}  .\start-agent-dev.ps1${RESET}"
        Write-Host ""
    } else {
        Draw-AgentState   $resp
        Draw-Market       $resp.last_market_data
        Draw-LastDecision $resp.last_decision
        Draw-SwarmVotes   $resp.last_swarm_result
        Draw-History      $resp.decision_history
        Draw-Errors       $resp.errors
    }

    Draw-Footer
    Start-Sleep -Seconds $Interval
}
