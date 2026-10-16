param([Parameter(Mandatory=$true)][int]$TargetProcessId,
      [Parameter(Mandatory=$true)][long]$MainWindow,
      [Parameter(Mandatory=$true)][string]$ObjectName)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [Windows.Automation.AutomationElement]::FromHandle([IntPtr]$MainWindow)
if ($root.Current.ProcessId -ne $TargetProcessId) { throw 'Refusing another process window' }
$scope = [Windows.Automation.TreeScope]::Descendants
$condition = New-Object Windows.Automation.PropertyCondition([Windows.Automation.AutomationElement]::NameProperty,$ObjectName)
$items = $root.FindAll($scope,$condition)
foreach ($item in $items) {
    $pattern = $null
    if ($item.TryGetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern,[ref]$pattern)) {
        $pattern.Select()
        Write-Output 'Selected test object through native UI Automation'
        exit 0
    }
}
throw 'Native object selection is not exposed through UI Automation on this build'
