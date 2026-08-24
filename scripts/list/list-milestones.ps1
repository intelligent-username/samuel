param([string]$Repo,[ValidateSet("open","closed","all")][string]$State="open")
function Get-Repo{param([string]$Explicit) if($Explicit){return $Explicit};$url=git remote get-url origin 2>$null;if($url -match 'github\.com[:/](.+?)(\.git)?$'){return $Matches[1]};throw "Could not detect repo. Pass -Repo owner/repo explicitly."}
$Repo=Get-Repo -Explicit $Repo
$ms=gh api "repos/$Repo/milestones?state=$State&per_page=100"|ConvertFrom-Json
$ms|ForEach-Object{[pscustomobject]@{Number="#$($_.number)";Title="$($_.title)  ";State="[$($_.state)]  ";Progress="$($_.open_issues) open / $($_.closed_issues) closed  ";Due=$(if($_.due_on){$_.due_on}else{"no due date"})}}|Format-Table -AutoSize|Out-String -Width 500|Write-Host
# also persist isolated copy for agent prep (already ignored via .cache/)
$outDir="./.cache/fetched/lists"; New-Item -ItemType Directory -Force -Path $outDir | Out-Null; Set-Content -Path "$outDir/.gitignore" -Value "*" -Force
$ms | ConvertTo-Json -Depth 10 | Out-File -Encoding utf8 "$outDir/milestones-$State.json"
Write-Host "Saved isolated list to $outDir/milestones-$State.json (ignored via .cache/)"
