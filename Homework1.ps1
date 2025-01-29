# CPU Performance Calculator
# This script calculates CPI metrics and performs speedup comparisons

# Input validation function
function Test-InputValue {
    param (
        [Parameter(Mandatory=$true)]
        [double]$Value,
        [Parameter(Mandatory=$true)]
        [string]$ParameterName,
        [double]$MinValue = 0,
        [double]$MaxValue = [double]::MaxValue
    )
    
    if ($Value -lt $MinValue -or $Value -gt $MaxValue) {
        throw "Invalid $ParameterName. Value must be between $MinValue and $MaxValue"
    }
    return $true
}

# Function to get validated numeric input
function Get-ValidatedInput {
    param (
        [string]$prompt,
        [double]$minValue = 0,
        [double]$maxValue = [double]::MaxValue
    )
    
    while ($true) {
        try {
            $input = Read-Host -Prompt $prompt
            $value = [double]$input
            if ($value -ge $minValue -and $value -le $maxValue) {
                return $value
            }
            Write-Host "Value must be between $minValue and $maxValue" -ForegroundColor Yellow
        }
        catch {
            Write-Host "Please enter a valid number" -ForegroundColor Yellow
        }
    }
}

# CPI Calculator
function Start-CPICalculator {
    Clear-Host
    Write-Host "CPI Calculator" -ForegroundColor Cyan
    Write-Host "===============" -ForegroundColor Cyan
    
    try {
        # Get user input with validation
        Write-Host "`nEnter instruction mix (percentages must sum to 100):" -ForegroundColor Green
        
        $ALUPercentage = Get-ValidatedInput "Enter percentage of ALU instructions (0-100)" 0 100
        $ALUCycles = Get-ValidatedInput "Enter number of ALU instruction cycles" 1
        
        $LoadStorePercentage = Get-ValidatedInput "Enter percentage of Load/Store instructions (0-100)" 0 100
        $LoadStoreCycles = Get-ValidatedInput "Enter number of Load/Store cycles" 1
        
        $remainingPercentage = 100 - ($ALUPercentage + $LoadStorePercentage)
        Write-Host "`nRemaining percentage for Branch instructions: $remainingPercentage%" -ForegroundColor Yellow
        
        if ($remainingPercentage -lt 0) {
            throw "Total percentage exceeds 100%"
        }
        
        $BranchCycles = Get-ValidatedInput "Enter number of Branch cycles" 1
        
        # Calculate metrics
        $ALUFraction = $ALUPercentage / 100
        $LoadStoreFraction = $LoadStorePercentage / 100
        $BranchFraction = $remainingPercentage / 100
        
        # Calculate average CPI
        $averageCPI = ($ALUCycles / $ALUFraction + 
                      $LoadStoreCycles / $LoadStoreFraction + 
                      $BranchCycles / $BranchFraction)
		$averageCPI = $averageCPI / 3
        
        # Calculate metrics for 1 million instructions
        $totalInstructions = 1000000
        $totalCycles = $totalInstructions * $averageCPI
        $clockSpeed = 2 # GHz
        $executionTime = $totalCycles / ($clockSpeed * 1E9) # seconds
        $MFLOPS = $totalInstructions / ($executionTime * 1E6)
        
        # Display results
        Write-Host "`nResults:" -ForegroundColor Green
        Write-Host "========" -ForegroundColor Green
        Write-Host "Average CPI: $($averageCPI.ToString('F2'))"
        Write-Host "Total Cycles: $($totalCycles.ToString('N0'))"
        Write-Host "Execution Time: $($executionTime.ToString('E3')) seconds"
        Write-Host "MFLOPS: $($MFLOPS.ToString('N2'))"
    }
    catch {
        Write-Host "`nError: $_" -ForegroundColor Red
    }
}

# Speedup Comparison Calculator
function Start-SpeedupCalculator {
    Clear-Host
    Write-Host "Speedup Comparison Calculator" -ForegroundColor Cyan
    Write-Host "===========================" -ForegroundColor Cyan
    
    try {
        Write-Host "`nMachine 1 Configuration:" -ForegroundColor Green
        $clockSpeed1 = Get-ValidatedInput "Enter Clock Speed (GHz)" 0.1
        $CPI1 = Get-ValidatedInput "Enter CPI" 0.1
        
        Write-Host "`nMachine 2 Configuration:" -ForegroundColor Green
        $clockSpeed2 = Get-ValidatedInput "Enter Clock Speed (GHz)" 0.1
        $CPI2 = Get-ValidatedInput "Enter CPI" 0.1
        
        # Calculate execution time for each machine (normalized to 1 instruction)
        $executionTime1 = $CPI1 / $clockSpeed1
        $executionTime2 = $CPI2 / $clockSpeed2
        
        # Calculate speedup
        $speedup = $executionTime1 / $executionTime2
        
        # Display results
        Write-Host "`nResults:" -ForegroundColor Green
        Write-Host "========" -ForegroundColor Green
        Write-Host "Machine 1 Execution Time: $($executionTime1.ToString('E3')) seconds per instruction"
        Write-Host "Machine 2 Execution Time: $($executionTime2.ToString('E3')) seconds per instruction"
        Write-Host "Speedup (Machine 2 vs Machine 1): $($speedup.ToString('F2'))x"
        
        if ($speedup -gt 1) {
            Write-Host "Machine 2 is faster by $([Math]::Round(($speedup - 1) * 100, 2))%" -ForegroundColor Green
        }
        elseif ($speedup -lt 1) {
            Write-Host "Machine 2 is slower by $([Math]::Round((1 - $speedup) * 100, 2))%" -ForegroundColor Yellow
        }
        else {
            Write-Host "Both machines have the same performance" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "`nError: $_" -ForegroundColor Red
    }
}

# Main menu function
function Show-MainMenu {
    while ($true) {
        Clear-Host
        Write-Host "CPU Performance Calculator" -ForegroundColor Cyan
        Write-Host "=======================" -ForegroundColor Cyan
        Write-Host "1. CPI Calculator"
        Write-Host "2. Speedup Comparison"
        Write-Host "3. Exit"
        
        $choice = Read-Host "`nEnter your choice (1-3)"
        
        switch ($choice) {
            "1" { 
                Start-CPICalculator
                Read-Host "`nPress Enter to continue"
            }
            "2" { 
                Start-SpeedupCalculator
                Read-Host "`nPress Enter to continue"
            }
            "3" { 
                Write-Host "Goodbye!" -ForegroundColor Green
                return 
            }
            default { 
                Write-Host "Invalid choice. Please try again." -ForegroundColor Yellow
                Start-Sleep -Seconds 1
            }
        }
    }
}

# Start the program
Show-MainMenu
