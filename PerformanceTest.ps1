# Performance Analysis Program
# Created: January 30, 2025

# Initialize Requirements function
function Initialize-Requirements {
    Write-Host "Checking required modules..."
    
    # Check if ThreadJob module is available
    if (!(Get-Module -ListAvailable -Name ThreadJob)) {
        Write-Host "ThreadJob module not found. Attempting to install..."
        try {
            Install-Module -Name ThreadJob -Force -Scope CurrentUser
            Write-Host "ThreadJob module installed successfully" -ForegroundColor Green
        }
        catch {
            Write-Host "Unable to install ThreadJob module. Will proceed with single-threaded processing." -ForegroundColor Yellow
            Write-ToLog "ThreadJob module installation failed: $_"
            return $false
        }
    }
    
    try {
        Import-Module ThreadJob -ErrorAction Stop
        Write-Host "ThreadJob module loaded successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "Unable to load ThreadJob module. Will proceed with single-threaded processing." -ForegroundColor Yellow
        Write-ToLog "ThreadJob module import failed: $_"
        return $false
    }
}

# Function to write to log file
function Write-ToLog {
    param(
        [string]$Message
    )
    $LogPath = "C:\Scripts\log.txt"
    $LogMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $Message"
    
    $LogDir = Split-Path $LogPath -Parent
    if (!(Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir | Out-Null
    }
    
    Add-Content -Path $LogPath -Value $LogMessage
}

# Function to show progress bar
function Show-Progress {
    param(
        [int]$Current,
        [int]$Total,
        [string]$Activity
    )
    $PercentComplete = ($Current / $Total) * 100
    Write-Progress -Activity $Activity -PercentComplete $PercentComplete -Status "$PercentComplete% Complete"
}

# Performance metrics calculation function
function Calculate-Metrics {
    param(
        [double]$ClockSpeed,
        [double]$Instructions,
        [double]$Cycles
    )
    
    return [PSCustomObject]@{
        CPI = $Cycles / $Instructions
        TotalCycles = $Cycles
        ExecutionTime = $Cycles / $ClockSpeed
        MIPS = ($Instructions * 1e-6) / ($Cycles / $ClockSpeed)
        MFLOPS = ($Instructions * 1e-6) / ($Cycles / $ClockSpeed)
    }
}

# Calculate Amdahl's Law Speedup
function Calculate-AmdahlSpeedup {
    param(
        [double]$ParallelFraction,
        [int]$Processors
    )
    
    $Speedup = 1 / ((1 - $ParallelFraction) + ($ParallelFraction / $Processors))
    return $Speedup
}

# Performance Test Function
function Start-PerformanceTest {
    Write-ToLog "Starting Performance Test"
    
    # Validate CSV input
    do {
        $CSVPath = Read-Host "Enter the path to your CSV file"
        if (!(Test-Path $CSVPath)) {
            Write-Host "Error: File not found. The file should be a CSV with headers: ClockSpeed, Instructions, Cycles" -ForegroundColor Red
            Write-Host "Example format:"
            Write-Host "ClockSpeed,Instructions,Cycles"
            Write-Host "2400,1000000,2000000"
            continue
        }
        
        # Validate CSV headers
        $Headers = Get-Content $CSVPath -First 1
        if ($Headers -notmatch '(?i)ClockSpeed.*Instructions.*Cycles' -and 
            $Headers -notmatch '(?i)Instructions.*ClockSpeed.*Cycles') {
            Write-Host "Error: Invalid CSV format. Required headers: ClockSpeed, Instructions, Cycles" -ForegroundColor Red
            Write-Host "Current headers found: $Headers"
            continue
        }
        break
    } while ($true)
    
    $ExportPath = Read-Host "Enter the path for exported files"
    if (!(Test-Path $ExportPath)) {
        New-Item -ItemType Directory -Path $ExportPath | Out-Null
    }
    
    try {
        $Data = Import-Csv $CSVPath
        $Results = @()
        $Total = $Data.Count
        
        # Check if multithreading is available
        $UseThreading = Initialize-Requirements
        
        if ($UseThreading) {
            # Multithreaded processing
            $MaxJobs = [Environment]::ProcessorCount
            $ChunkSize = [Math]::Ceiling($Total / $MaxJobs)
            $Jobs = @()
            
            for ($i = 0; $i -lt $MaxJobs; $i++) {
                $Start = $i * $ChunkSize
                $End = [Math]::Min(($i + 1) * $ChunkSize, $Total)
                $ChunkData = $Data[$Start..($End-1)]
                
                $Jobs += Start-ThreadJob -ScriptBlock {
                    param($Data)
                    $ChunkResults = @()
                    foreach ($Item in $Data) {
                        $Metrics = [PSCustomObject]@{
                            CPI = [double]$Item.Cycles / [double]$Item.Instructions
                            TotalCycles = [double]$Item.Cycles
                            ExecutionTime = [double]$Item.Cycles / [double]$Item.ClockSpeed
                            MIPS = ([double]$Item.Instructions * 1e-6) / ([double]$Item.Cycles / [double]$Item.ClockSpeed)
                            MFLOPS = ([double]$Item.Instructions * 1e-6) / ([double]$Item.Cycles / [double]$Item.ClockSpeed)
                        }
                        $ChunkResults += $Metrics
                    }
                    return $ChunkResults
                } -ArgumentList $ChunkData
            }
            
            # Collect results
            $JobsCompleted = 0
            while ($JobsCompleted -lt $Jobs.Count) {
                $CompletedJobs = $Jobs | Where-Object { $_.State -eq 'Completed' }
                $JobsCompleted = $CompletedJobs.Count
                Show-Progress -Current $JobsCompleted -Total $Jobs.Count -Activity "Processing data chunks"
                Start-Sleep -Milliseconds 100
            }
            
            foreach ($Job in $Jobs) {
                $Results += Receive-Job -Job $Job
                Remove-Job -Job $Job
            }
        }
        else {
            # Single-threaded processing
            for ($i = 0; $i -lt $Total; $i++) {
                Show-Progress -Current $i -Total $Total -Activity "Processing performance metrics"
                
                try {
                    $Metrics = Calculate-Metrics `
                        -ClockSpeed ([double]$Data[$i].ClockSpeed) `
                        -Instructions ([double]$Data[$i].Instructions) `
                        -Cycles ([double]$Data[$i].Cycles)
                    
                    $Results += $Metrics
                }
                catch {
                    Write-Host "Error processing row $($i + 1): $_" -ForegroundColor Red
                    Write-ToLog "Error processing row $($i + 1): $_"
                    continue
                }
            }
        }
        
        # Export results
        $Results | Export-Csv -Path "$ExportPath\results.csv" -NoTypeInformation
        Write-Host "Results exported to $ExportPath\results.csv" -ForegroundColor Green
        
        # Calculate and display summary statistics
        $CPIAvg = ($Results | Measure-Object -Property CPI -Average).Average
        $MIPSAvg = ($Results | Measure-Object -Property MIPS -Average).Average
        
        Write-Host "`nProcessing complete. Found $($Results.Count) valid results."
        Write-Host "Summary:"
        Write-Host "Average CPI: $($CPIAvg.ToString('F2'))"
        Write-Host "Average MIPS: $($MIPSAvg.ToString('F2'))"
        
        # Display detailed statistics
        Write-Host "`nDetailed Statistics:"
        Write-Host "CPI Range: $(($Results | Measure-Object -Property CPI -Minimum).Minimum.ToString('F2')) - $(($Results | Measure-Object -Property CPI -Maximum).Maximum.ToString('F2'))"
        Write-Host "MIPS Range: $(($Results | Measure-Object -Property MIPS -Minimum).Minimum.ToString('F2')) - $(($Results | Measure-Object -Property MIPS -Maximum).Maximum.ToString('F2'))"
        Write-Host "Total Instructions Processed: $(($Results | Measure-Object -Property TotalCycles -Sum).Sum.ToString('N0'))"
        
    }
    catch {
        Write-Host "Error processing data: $_" -ForegroundColor Red
        Write-ToLog "Error in Performance Test: $_"
    }
}

# Speedup Comparison Function
function Start-SpeedupComparison {
    Write-ToLog "Starting Speedup Comparison"
    
    # Validate CSV input
    do {
        $CSVPath = Read-Host "Enter the path to your CSV file"
        if (!(Test-Path $CSVPath)) {
            Write-Host "Error: File not found. The file should be a CSV with headers: CPI, ClockSpeed" -ForegroundColor Red
            Write-Host "Example format:"
            Write-Host "CPI,ClockSpeed"
            Write-Host "2.5,2400"
            continue
        }
        
        # Validate CSV headers
        $Headers = Get-Content $CSVPath -First 1
        if ($Headers -notmatch '(?i)CPI.*ClockSpeed' -and 
            $Headers -notmatch '(?i)ClockSpeed.*CPI') {
            Write-Host "Error: Invalid CSV format. Required headers: CPI, ClockSpeed" -ForegroundColor Red
            Write-Host "Current headers found: $Headers"
            continue
        }
        break
    } while ($true)
    
    $ExportPath = Read-Host "Enter the path for exported files"
    if (!(Test-Path $ExportPath)) {
        New-Item -ItemType Directory -Path $ExportPath | Out-Null
    }
    
    try {
        $Data = Import-Csv $CSVPath
        $Results = @()
        $Total = $Data.Count
        
        # Calculate baseline performance (using first machine as reference)
        $BaselineCPI = [double]$Data[0].CPI
        $BaselineClockSpeed = [double]$Data[0].ClockSpeed
        $BaselinePerformance = 1 / ($BaselineCPI / $BaselineClockSpeed)
        
        for ($i = 0; $i -lt $Total; $i++) {
            Show-Progress -Current $i -Total $Total -Activity "Calculating speedup metrics"
            
            try {
                $CurrentCPI = [double]$Data[$i].CPI
                $CurrentClockSpeed = [double]$Data[$i].ClockSpeed
                $CurrentPerformance = 1 / ($CurrentCPI / $CurrentClockSpeed)
                
                $Metrics = [PSCustomObject]@{
                    MachineIndex = $i
                    CPI = $CurrentCPI
                    ClockSpeed = $CurrentClockSpeed
                    Speedup = $CurrentPerformance / $BaselinePerformance
                    Efficiency = ($CurrentPerformance / $BaselinePerformance) / ($CurrentClockSpeed / $BaselineClockSpeed)
                }
                
                $Results += $Metrics
            }
            catch {
                Write-Host "Error processing row $($i + 1): $_" -ForegroundColor Red
                Write-ToLog "Error processing row $($i + 1): $_"
                continue
            }
        }
        
        # Export results
        $Results | Export-Csv -Path "$ExportPath\speedup_results.csv" -NoTypeInformation
        Write-Host "Results exported to $ExportPath\speedup_results.csv" -ForegroundColor Green
        
        # Display summary statistics
        Write-Host "`nSpeedup Analysis Results:"
        Write-Host "Baseline Machine (Index 0):"
        Write-Host "  CPI: $BaselineCPI"
        Write-Host "  Clock Speed: $BaselineClockSpeed MHz"
        
        Write-Host "`nSpeedup Summary:"
        Write-Host "Maximum Speedup: $(($Results | Measure-Object -Property Speedup -Maximum).Maximum.ToString('F2'))x"
        Write-Host "Average Speedup: $(($Results | Measure-Object -Property Speedup -Average).Average.ToString('F2'))x"
        Write-Host "Maximum Efficiency: $(($Results | Measure-Object -Property Efficiency -Maximum).Maximum.ToString('P2'))"
        
    }
    catch {
        Write-Host "Error processing data: $_" -ForegroundColor Red
        Write-ToLog "Error in Speedup Comparison: $_"
    }
}

# Unit Test Functions
function Test-CPICalculation {
    Write-Host "`nTesting CPI Calculation..." -ForegroundColor Cyan
    $TestCases = @(
        @{Instructions=1000; Cycles=2000; Expected=2.0}
        @{Instructions=5000; Cycles=7500; Expected=1.5}
    )
    
    foreach ($Test in $TestCases) {
        $Result = $Test.Cycles / $Test.Instructions
        $Pass = [Math]::Abs($Result - $Test.Expected) -lt 0.0001
        
        Write-Host "Test Case: Instructions=$($Test.Instructions), Cycles=$($Test.Cycles)"
        Write-Host "Expected: $($Test.Expected), Got: $Result"
        Write-Host "Result: $(if ($Pass) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
        Write-Host ""
    }
}

function Test-ExecutionTime {
    Write-Host "`nTesting Execution Time Calculation..." -ForegroundColor Cyan
    $TestCases = @(
        @{Cycles=2000; ClockSpeed=1000; Expected=2.0}
        @{Cycles=5000; ClockSpeed=2500; Expected=2.0}
    )
    
    foreach ($Test in $TestCases) {
        $Result = $Test.Cycles / $Test.ClockSpeed
        $Pass = [Math]::Abs($Result - $Test.Expected) -lt 0.0001
        
        Write-Host "Test Case: Cycles=$($Test.Cycles), ClockSpeed=$($Test.ClockSpeed)"
        Write-Host "Expected: $($Test.Expected), Got: $Result"
        Write-Host "Result: $(if ($Pass) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
        Write-Host ""
    }
}

function Test-MIPSCalculation {
    Write-Host "`nTesting MIPS Calculation..." -ForegroundColor Cyan
    $TestCases = @(
        @{Instructions=1000000; Cycles=2000000; ClockSpeed=1000; Expected=1.0}
        @{Instructions=2000000; Cycles=2000000; ClockSpeed=1000; Expected=2.0}
    )
    
    foreach ($Test in $TestCases) {
        $Result = ($Test.Instructions * 1e-6) / ($Test.Cycles / $Test.ClockSpeed)
        $Pass = [Math]::Abs($Result - $Test.Expected) -lt 0.0001
        
        Write-Host "Test Case: Instructions=$($Test.Instructions), Cycles=$($Test.Cycles), ClockSpeed=$($Test.ClockSpeed)"
        Write-Host "Calculation: ($($Test.Instructions) * 1e-6) / ($($Test.Cycles) / $($Test.ClockSpeed))"
        Write-Host "Expected: $($Test.Expected), Got: $Result"
        Write-Host "Result: $(if ($Pass) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($Pass) { 'Green' } else { 'Red' })
        Write-Host ""
    }
}

function Start-UnitTest {
    Write-ToLog "Starting Unit Test"
    
    $UnitTestMenu = @"
Unit Test Menu
-------------
1. CPI Calculation
2. Execution Time Calculation
3. MIPS Calculation
4. Run All Tests
5. Return to Main Menu

Select an option:
"@
    
    do {
        Clear-Host
        Write-Host $UnitTestMenu
        $Choice = Read-Host
        
        switch ($Choice) {
            "1" { Test-CPICalculation }
            "2" { Test-ExecutionTime }
            "3" { Test-MIPSCalculation }
            "4" {
                Test-CPICalculation
                Test-ExecutionTime
                Test-MIPSCalculation
            }
            "5" { return }
            default { Write-Host "Invalid option" -ForegroundColor Yellow }
        }
        
        if ($Choice -ne "5") {
            Write-Host "`nPress any key to continue..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    } while ($Choice -ne "5")
}

# Function to show logs
function Show-Logs {
    Write-ToLog "Viewing Logs"
    
    $LogPath = "C:\Scripts\log.txt"
    if (Test-Path $LogPath) {
        Get-Content $LogPath -Tail 20
    }
    else {
        Write-Host "No logs found" -ForegroundColor Yellow
    }
}

# Function to show credits
function Show-Credits {
    Write-ToLog "Viewing Credits"
    
    $Credits = @"
Performance Analysis Program
---------------------------
Created by: Team Members
- Anthony Grissom, Arthur Smith, Carlos Sanchez, Rebeca Soto, Tristen Uschuk

AI Assistance: Claude 3.5 Sonnet by Anthropic
"@
    
    Write-Host $Credits
}

# Function to generate SVG performance charts
function Create-PerformanceChartSVG {
    param(
        [string]$InputPath,
        [string]$OutputPath,
        [string]$ChartType
    )
    
    # Start logging
    Write-ToLog "Starting chart generation for $ChartType"
    
    # Validate input file
    if (!(Test-Path $InputPath)) {
        Write-Host "Error: Input file not found." -ForegroundColor Red
        Write-ToLog "Chart generation failed: Input file not found"
        return
    }
    
    try {
        # Explicit timing and progress tracking
        $StartTime = Get-Date
        
        # Import CSV data with error handling
        Write-Host "Importing data..." -NoNewline
        $Data = Import-Csv $InputPath -ErrorAction Stop
        Write-Host "Done" -ForegroundColor Green
        
        # Validate data
        if ($Data.Count -eq 0) {
            Write-Host "Error: No data found in the CSV file." -ForegroundColor Red
            Write-ToLog "Chart generation failed: Empty CSV"
            return
        }
        
        # Determine chart properties based on chart type
        switch ($ChartType) {
            "CPI" {
                $MetricValues = $Data | ForEach-Object { 
                    try { [double]$_.CPI } 
                    catch { Write-Host "Warning: Invalid CPI value" -ForegroundColor Yellow; $null }
                } | Where-Object { $_ -ne $null }
                $Title = "Cycles Per Instruction (CPI) Comparison"
                $Color = "blue"
            }
            "MIPS" {
                $MetricValues = $Data | ForEach-Object { 
                    try { [double]$_.MIPS } 
                    catch { Write-Host "Warning: Invalid MIPS value" -ForegroundColor Yellow; $null }
                } | Where-Object { $_ -ne $null }
                $Title = "Million Instructions Per Second (MIPS) Comparison"
                $Color = "green"
            }
            "ExecutionTime" {
                $MetricValues = $Data | ForEach-Object { 
                    try { [double]$_.ExecutionTime } 
                    catch { Write-Host "Warning: Invalid Execution Time value" -ForegroundColor Yellow; $null }
                } | Where-Object { $_ -ne $null }
                $Title = "Execution Time Comparison"
                $Color = "red"
            }
            default {
                Write-Host "Invalid chart type selected." -ForegroundColor Red
                Write-ToLog "Chart generation failed: Invalid chart type"
                return
            }
        }
        
        # Validate metric values
        if ($MetricValues.Count -eq 0) {
            Write-Host "Error: No valid metric values found." -ForegroundColor Red
            Write-ToLog "Chart generation failed: No valid metric values"
            return
        }
        
        # Prepare output path with fallback
        $SafeOutputPath = if ([string]::IsNullOrWhiteSpace($OutputPath)) {
            Join-Path $env:USERPROFILE "Desktop\$ChartType-Chart.svg"
        } else { $OutputPath }
        
        # Ensure output directory exists
        $OutputDir = Split-Path $SafeOutputPath -Parent
        if (!(Test-Path $OutputDir)) {
            try {
                New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
            }
            catch {
                Write-Host "Error creating output directory: $_" -ForegroundColor Red
                Write-ToLog "Chart generation failed: Could not create output directory"
                return
            }
        }
        
        # Generate SVG
        Write-Host "Generating SVG chart..." -NoNewline
        
        $width = 600
        $height = 400
        $padding = 50
        $chartHeight = $height - (2 * $padding)
        $chartWidth = $width - (2 * $padding)
        
        # Calculate max value for scaling
        $maxValue = ($MetricValues | Measure-Object -Maximum).Maximum
        
        # Start SVG generation
        $svg = @"
<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height">
    <rect width="100%" height="100%" fill="white"/>
    <text x="$($width/2)" y="30" text-anchor="middle" font-size="16" font-weight="bold">$Title</text>
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">$ChartType Value</text>
"@
        
        # Generate bars
        $barWidth = $chartWidth / $MetricValues.Count
        for ($i = 0; $i -lt $MetricValues.Count; $i++) {
            $barHeight = ($MetricValues[$i] / $maxValue) * $chartHeight
            $x = $padding + ($i * $barWidth)
            $y = $height - $padding - $barHeight
            
            $svg += @"
    <rect x="$x" y="$y" width="$($barWidth * 0.8)" height="$barHeight" 
          fill="$Color" stroke="black" stroke-width="1" opacity="0.7">
        <title>Value: $($MetricValues[$i])</title>
    </rect>
    <text x="$($x + $barWidth/2)" y="$($height - 10)" text-anchor="middle" font-size="10">
        Run $($i + 1)
    </text>
"@
        }
        
        # Finalize SVG
        $svg += @"
    <text x="$($width/2)" y="$($height - 10)" text-anchor="middle">Test Runs</text>
</svg>
"@
        
        # Write SVG to file
        try {
            [System.IO.File]::WriteAllText($SafeOutputPath, $svg)
            Write-Host "Done" -ForegroundColor Green
            
            # Log and display success
            $EndTime = Get-Date
            $Duration = $EndTime - $StartTime
            Write-Host "Chart saved to $SafeOutputPath" -ForegroundColor Green
            Write-Host "Generation time: $($Duration.TotalSeconds) seconds" -ForegroundColor Cyan
            Write-ToLog "Chart generation successful: $ChartType chart created in $($Duration.TotalSeconds) seconds"
        }
        catch {
            Write-Host "Error saving chart: $_" -ForegroundColor Red
            Write-ToLog "Chart generation failed: Could not save SVG file"
        }
    }
    catch {
        Write-Host "Unexpected error during chart generation: $_" -ForegroundColor Red
        Write-ToLog "Chart generation failed with unexpected error: $_"
    }
}

# Function to show chart generation menu
function Show-ChartGenerationMenu {
    $ChartMenu = @"
Chart Generation Menu
--------------------
1. CPI Chart
2. MIPS Chart
3. Execution Time Chart
4. Return to Main Menu
"@
    
    while ($true) {
        Clear-Host
        Write-Host $ChartMenu
        $Choice = Read-Host "Select an option"
        
        switch ($Choice) {
            "1" { 
                $InputPath = Read-Host "Enter path to performance results CSV"
                $OutputPath = Read-Host "Enter path to save CPI chart SVG"
                Create-PerformanceChartSVG -InputPath $InputPath -OutputPath $OutputPath -ChartType "CPI"
            }
            "2" { 
                $InputPath = Read-Host "Enter path to performance results CSV"
                $OutputPath = Read-Host "Enter path to save MIPS chart SVG"
                Create-PerformanceChartSVG -InputPath $InputPath -OutputPath $OutputPath -ChartType "MIPS"
            }
            "3" { 
                $InputPath = Read-Host "Enter path to performance results CSV"
                $OutputPath = Read-Host "Enter path to save Execution Time chart SVG"
                Create-PerformanceChartSVG -InputPath $InputPath -OutputPath $OutputPath -ChartType "ExecutionTime"
            }
            "4" { return }
            default { 
                Write-Host "Invalid option" -ForegroundColor Yellow 
            }
        }
        
        if ($Choice -ne "4") {
            Write-Host "`nPress any key to continue..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    }
}

# Main Menu
function Show-MainMenu {
$MainMenu = @"
Performance Analysis Program
--------------------------
1. Performance Test
2. Speedup Comparison
3. Unit Test
4. Logs
5. Chart Generation
6. Credits
7. Exit
"@
    
    while ($true) {
        Clear-Host
        Write-Host $MainMenu
        $Choice = Read-Host "Select an option"
        
switch ($Choice) {
    "1" { Start-PerformanceTest }
    "2" { Start-SpeedupComparison }
    "3" { Start-UnitTest }
    "4" { Show-Logs }
    "5" { Show-ChartGenerationMenu }
    "6" { Show-Credits }  # Add this line
    "7" { 
        Write-ToLog "Program Exit"
        exit 
    }
    default {
        Write-Host "Invalid option. Please try again." -ForegroundColor Yellow
        Write-ToLog "Invalid menu selection: $Choice"
    }
}
        
        Write-Host "`nPress any key to continue..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

# Start the program
Write-ToLog "Program Start"
Show-MainMenu
