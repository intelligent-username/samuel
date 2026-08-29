# create-milestone.ps1 [-Repo owner/repo] -Title "<title>" [-Description "<desc>"] [-DueOn yyyy-MM-dd] [-State open|closed]
param(
    [string]$Repo,
    [Parameter(Mandatory=$true)][string]$Title,
    [string]$Description,
    [string]$DueOn,
    [ValidateSet("open","closed")][string]$State
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
$ghArgs = @("api", "repos/$Repo/milestones", "-f", "title=$Title")
if ($Description) { $ghArgs += @("-f", "description=$Description") }
if ($DueOn)        { $ghArgs += @("-f", "due_on=$($DueOn)T00:00:00Z") }
if ($State)        { $ghArgs += @("-f", "state=$State") }
$result = gh @ghArgs | ConvertFrom-Json
Write-Host "Created milestone #$($result.number): $Title"
return $result
