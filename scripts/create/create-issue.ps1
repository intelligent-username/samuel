# create-issue.ps1 [-Repo owner/repo] -Title "<title>" -BodyFile <path> [-Labels a,b] [-Assignees user1] [-Milestone <number>] [-Parent <issue-number>]
param(
    [string]$Repo,
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$BodyFile,
    [string[]]$Labels,
    [string[]]$Assignees,
    [int]$Milestone,
    [int]$Parent
)
$ErrorActionPreference = "Stop"
function Get-Repo {
    param([string]$Explicit)
    if ($Explicit) { return $Explicit }
    $url = git remote get-url origin 2>$null
    if ($url -match 'github\.com[:/](.+?)(\.git)?$') { return $Matches[1] }
    throw "Could not detect repo. Pass -Repo owner/repo explicitly."
}
$Repo = Get-Repo -Explicit $Repo
$ghArgs = @("api", "repos/$Repo/issues", "-f", "title=$Title", "-F", "body=@$BodyFile")
foreach ($l in $Labels)    { $ghArgs += @("-f", "labels[]=$l") }
foreach ($a in $Assignees) { $ghArgs += @("-f", "assignees[]=$a") }
if ($Milestone) { $ghArgs += @("-F", "milestone=$Milestone") }
$result = gh @ghArgs | ConvertFrom-Json
Write-Host "Created issue #$($result.number) in $Repo"
if ($Parent) {
    $issueId = gh api "repos/$Repo/issues/$($result.number)" --jq '.id'
    gh api "repos/$Repo/issues/$Parent/sub_issues" -X POST -F "sub_issue_id=$issueId" | Out-Null
    Write-Host "Linked #$($result.number) as sub-issue of #$Parent"
}
return $result
