param(
    [string]$InputPath,
    [string]$OutputPath
)

$htmlContent = Get-Content -Path $InputPath -Raw
$plainText = $htmlContent -replace '(?s)<script.*?</script>',''
$plainText = $plainText -replace '(?s)<style.*?</style>',''
$plainText = $plainText -replace '<[^>]+>', ''
$plainText = [System.Net.WebUtility]::HtmlDecode($plainText)
$plainText = $plainText -replace '\s+', ' ' | Out-File -FilePath $OutputPath -Encoding utf8

