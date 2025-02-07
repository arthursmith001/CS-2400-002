# Performance Analysis Program
# Created: January 30, 2025
# Updated: February 04, 2025 - Added enhanced charting capabilities

#Requires -Version 5.1

Add-Type -AssemblyName System.Web

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
        [string]$Message,
        [string]$LogPath = "C:\Scripts\log.txt"
    )
    try {
        $LogDir = Split-Path $LogPath -Parent
        if (!(Test-Path $LogDir)) {
            New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
        }
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $Message" | 
            Out-File -FilePath $LogPath -Append -Encoding UTF8 -Force
    }
    catch {
        Write-Warning "Failed to write to log: $_"
    }
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
        [Parameter(Mandatory=$true)]
        [ValidateRange(0.1, [double]::MaxValue)]
        [double]$ClockSpeed,
        
        [Parameter(Mandatory=$true)]
        [ValidateRange(1, [double]::MaxValue)]
        [double]$Instructions,
        
        [Parameter(Mandatory=$true)]
        [ValidateRange(1, [double]::MaxValue)]
        [double]$Cycles
    )
    
    try {
        $CPI = $Cycles / $Instructions
        $MIPS = ($ClockSpeed / $CPI) / 1000
        $ExecutionTime = ($Cycles / $ClockSpeed) / 1000000
        
        return [PSCustomObject]@{
            CPI = $CPI
            MIPS = $MIPS
            ExecutionTime = $ExecutionTime
        }
    }
    catch {
        Write-Error "Error calculating metrics: $_"
        return $null
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

function Start-SpeedupComparison {
    Write-ToLog "Starting Speedup Comparison"

    Write-Host "Speedup Comparison Tool" -ForegroundColor Cyan
    Write-Host "------------------------"
    Write-Host "`nThis tool compares performance between baseline and optimized implementations."

    $inputMethod = Read-Host "`nSelect input method:`n1. Manual entry`n2. CSV file`nChoice"

    if ($inputMethod -eq "1") {
        # Manual entry
        try {
            do {
                [double]$clockSpeed = Read-Host "`nEnter clock speed (MHz)"
                if ($clockSpeed -le 0) { Write-Host "Clock speed must be greater than zero." -ForegroundColor Red }
            } until ($clockSpeed -gt 0)

            do {
                [double]$cycles = Read-Host "Enter number of cycles"
                if ($cycles -lt 0) { Write-Host "Cycles cannot be negative." -ForegroundColor Red }
            } until ($cycles -ge 0)

            do {
                [int]$processors = Read-Host "Enter number of processors/cores used"
                if ($processors -le 0) { Write-Host "Number of processors must be greater than zero." -ForegroundColor Red }
            } until ($processors -gt 0)

            $executionTime = $cycles / $clockSpeed

            $baselineTime = $executionTime
            $optimizedTime = $baselineTime / $processors

            if ($baselineTime -eq 0) {
                Write-Host "Error: Baseline time is zero. Cannot calculate speedup." -ForegroundColor Red
                Write-ToLog "Error: Baseline time is zero in manual speedup comparison."
                return
            }

            $actualSpeedup = $baselineTime / $optimizedTime
            $parallelFraction = 1 - ($optimizedTime * $processors / $baselineTime)
            $theoreticalSpeedup = Calculate-AmdahlSpeedup -ParallelFraction $parallelFraction -Processors $processors
            $efficiency = ($actualSpeedup / $processors) * 100

            Write-Host "`nResults:" -ForegroundColor Green
            Write-Host "Actual Speedup: $($actualSpeedup.ToString('F2'))x"
            Write-Host "Theoretical Maximum Speedup: $($theoreticalSpeedup.ToString('F2'))x"
            Write-Host "Parallel Fraction: $($parallelFraction.ToString('P2'))"
            Write-Host "Parallel Efficiency: $($efficiency.ToString('F2'))%"

            $results = [PSCustomObject]@{
                ClockSpeed = $clockSpeed
                Cycles = $cycles
                Processors = $processors
                BaselineTime = $baselineTime
                OptimizedTime = $optimizedTime
                ActualSpeedup = $actualSpeedup
                TheoreticalSpeedup = $theoreticalSpeedup
                ParallelFraction = $parallelFraction
                Efficiency = $efficiency
            }

            $exportPath = Join-Path $env:USERPROFILE "Desktop\SpeedupResults.csv"
            $results | Export-Csv -Path $exportPath -NoTypeInformation
            Write-Host "`nResults exported to: $exportPath" -ForegroundColor Green
        }
        catch {
            Write-Host "Error processing input: $_" -ForegroundColor Red
            Write-ToLog "Error in manual speedup comparison: $_"
            return
        }
    }
    elseif ($inputMethod -eq "2") {
        # CSV file input
        do {
            $csvPath = Read-Host "`nEnter path to CSV file"
            if (!(Test-Path $csvPath)) {
                Write-Host "Error: File not found." -ForegroundColor Red
                continue
            }

            $headers = Get-Content $csvPath -First 1
            if ($headers -notmatch '(?i)Machine.*ClockSpeed.*Cycles') {
                Write-Host "Error: Invalid CSV format. Required headers: Machine, ClockSpeed, Cycles" -ForegroundColor Red
                continue
            }
            break
        } while ($true)

        try {
            $data = Import-Csv $csvPath
            $results = @()
            $machines = $data | Group-Object Machine

            foreach ($machine in $machines) {
                $executionTimes = @()

                foreach ($item in $machine.Group) {
                    $cycles = [double]$item.Cycles
                    $clockSpeed = [double]$item.ClockSpeed

                    if ($clockSpeed -eq 0) {
                        Write-Warning "ClockSpeed is zero for $($item.Machine). Skipping this entry."
                        continue
                    }

                    $executionTimes += $cycles / $clockSpeed
                }

                if ($executionTimes.Count -eq 0) {
                    Write-Warning "No valid execution times found for $($machine.Name). Skipping this machine."
                    continue
                }

                $baselineTime = ($executionTimes | Measure-Object -Maximum).Maximum
                $optimizedTime = ($executionTimes | Measure-Object -Minimum).Minimum

                $processors = 1
                if ($machine.Group | Select-Object -First 1 | Get-Member -Name Processors -MemberType NoteProperty) {
                    $processors = [int]($machine.Group | Select-Object -First 1).Processors
                    if ($processors -eq 0) {
                        Write-Warning "Processors is zero for $($machine.Name). Defaulting to 1."
                        $processors = 1
                    }
                } else {
                    Write-Host "Processors column not found. Defaulting to 1 processor." -ForegroundColor Yellow
                }

                $actualSpeedup = $baselineTime / $optimizedTime
                $parallelFraction = 1 - ($optimizedTime * $processors / $baselineTime)
                $theoreticalSpeedup = Calculate-AmdahlSpeedup -ParallelFraction $parallelFraction -Processors $processors
                $efficiency = ($actualSpeedup / $processors) * 100

                $results += [PSCustomObject]@{
                    Machine = $machine.Name
                    BaselineTime = $baselineTime
                    OptimizedTime = $optimizedTime
                    Processors = $processors
                    ActualSpeedup = $actualSpeedup
                    TheoreticalSpeedup = $theoreticalSpeedup
                    ParallelFraction = $parallelFraction
                    Efficiency = $efficiency
                }
            }

            Write-Host "`nResults by Machine:" -ForegroundColor Green
            foreach ($result in $results) {
                Write-Host "`nMachine: $($result.Machine)"
                Write-Host "Actual Speedup: $($result.ActualSpeedup.ToString('F2'))x"
                Write-Host "Theoretical Maximum Speedup: $($result.TheoreticalSpeedup.ToString('F2'))x"
                Write-Host "Parallel Fraction: $($result.ParallelFraction.ToString('P2'))"
                Write-Host "Parallel Efficiency: $($result.Efficiency.ToString('F2'))%"
            }

            $exportPath = Join-Path $env:USERPROFILE "Desktop\SpeedupResults_Detailed.csv"
            $results | Export-Csv -Path $exportPath -NoTypeInformation
            Write-Host "`nDetailed results exported to: $exportPath" -ForegroundColor Green

        }
        catch {
            Write-Host "Error processing CSV: $_" -ForegroundColor Red
            Write-ToLog "Error in CSV speedup comparison: $_"
            return
        }
    }
    else {
        Write-Host "Invalid input method selected" -ForegroundColor Red
        return
    }

    Write-ToLog "Speedup Comparison completed successfully"
}

# Implementation of Calculate-AmdahlSpeedup
function Calculate-AmdahlSpeedup {
    param(
        [decimal]$ParallelFraction,
        [int]$Processors
    )
    $Speedup = 1 / (1 - $ParallelFraction + ($ParallelFraction / $Processors))
    return $Speedup
}

# Implementation of Write-ToLog
function Write-ToLog {
    param(
        [string]$Message,
        [string]$LogPath = "C:\Scripts\log.txt"
    )
    try {
        "$([datetime]::Now) - $Message" | Out-File -FilePath $LogPath -Append -Encoding UTF8 -Force
    } catch {
        Write-Warning "Failed to write to log: $_"
    }
}

function Calculate-CPI {
    param (
        [double]$TotalCycles,
        [double]$TotalInstructions
    )
    return $TotalCycles / $TotalInstructions
}

function Calculate-MIPS {
    param (
        [double]$TotalInstructions,
        [double]$ExecutionTimeInSeconds
    )
    return ($TotalInstructions / $ExecutionTimeInSeconds) / 1e6
}

function Calculate-MFLOPS {
    param (
        [double]$TotalFloatingPointOperations,
        [double]$ExecutionTimeInSeconds
    )
    return ($TotalFloatingPointOperations / $ExecutionTimeInSeconds) / 1e6
}

function Calculate-Speedup {
    param (
        [double]$TimeWithoutEnhancement,
        [double]$TimeWithEnhancement
    )
    return $TimeWithoutEnhancement / $TimeWithEnhancement
}

function Calculate-Efficiency {
    param (
        [double]$Speedup,
        [int]$NumberOfProcessors
    )
    return $Speedup / $NumberOfProcessors
}

function Calculate-AmdahlLaw {
    param (
        [double]$FractionEnhanced,
        [double]$SpeedupEnhanced
    )
    return 1 / ((1 - $FractionEnhanced) + ($FractionEnhanced / $SpeedupEnhanced))
}

# Function to run unit tests for the performance analysis functions
function Start-UnitTest {
	Write-ToLog "Unit Testing in progress"
    # Initialize counters for passed and failed tests
    $passedTests = 0
    $failedTests = 0

    # Function to display test results with color coding
    function Write-TestResult {
        param (
            [string]$TestName,
            [bool]$Passed,
            [string]$ActualValue
        )
        if ($Passed) {
            Write-Host "[PASS] $TestName - Actual Value: $ActualValue" -ForegroundColor Green
            $script:passedTests++
        } else {
            Write-Host "[FAIL] $TestName - Actual Value: $ActualValue" -ForegroundColor Red
            $script:failedTests++
        }
    }

    # Prompt user for input values
    Write-Host "`n=== Enter Input Values for Unit Tests ===" -ForegroundColor Cyan

    # CPI Calculation Input
    $totalCycles = Read-Host "Enter Total Cycles for CPI Calculation"
    $totalInstructions = Read-Host "Enter Total Instructions for CPI Calculation"
    $cpi = Calculate-CPI -TotalCycles $totalCycles -TotalInstructions $totalInstructions
    Write-TestResult -TestName "CPI Calculation" -Passed ($cpi -eq 2) -ActualValue $cpi

    # MIPS Calculation Input
    $totalInstructionsMIPS = Read-Host "Enter Total Instructions for MIPS Calculation"
    $executionTimeMIPS = Read-Host "Enter Execution Time (in seconds) for MIPS Calculation"
    $mips = Calculate-MIPS -TotalInstructions $totalInstructionsMIPS -ExecutionTimeInSeconds $executionTimeMIPS
    Write-TestResult -TestName "MIPS Calculation" -Passed ($mips -eq 1) -ActualValue $mips

    # MFLOPS Calculation Input
    $totalFloatingPointOps = Read-Host "Enter Total Floating-Point Operations for MFLOPS Calculation"
    $executionTimeMFLOPS = Read-Host "Enter Execution Time (in seconds) for MFLOPS Calculation"
    $mflops = Calculate-MFLOPS -TotalFloatingPointOperations $totalFloatingPointOps -ExecutionTimeInSeconds $executionTimeMFLOPS
    Write-TestResult -TestName "MFLOPS Calculation" -Passed ($mflops -eq 1) -ActualValue $mflops

    # Speedup Calculation Input
    $timeWithoutEnhancement = Read-Host "Enter Time Without Enhancement for Speedup Calculation"
    $timeWithEnhancement = Read-Host "Enter Time With Enhancement for Speedup Calculation"
    $speedup = Calculate-Speedup -TimeWithoutEnhancement $timeWithoutEnhancement -TimeWithEnhancement $timeWithEnhancement
    Write-TestResult -TestName "Speedup Calculation" -Passed ($speedup -eq 2) -ActualValue $speedup

    # Efficiency Calculation Input
    $speedupEfficiency = Read-Host "Enter Speedup for Efficiency Calculation"
    $numberOfProcessors = Read-Host "Enter Number of Processors for Efficiency Calculation"
    $efficiency = Calculate-Efficiency -Speedup $speedupEfficiency -NumberOfProcessors $numberOfProcessors
    Write-TestResult -TestName "Efficiency Calculation" -Passed ($efficiency -eq 1) -ActualValue $efficiency

    # Amdahl's Law Calculation Input
    $fractionEnhanced = Read-Host "Enter Fraction Enhanced for Amdahl's Law Calculation"
    $speedupEnhanced = Read-Host "Enter Speedup Enhanced for Amdahl's Law Calculation"
    $amdahl = Calculate-AmdahlLaw -FractionEnhanced $fractionEnhanced -SpeedupEnhanced $speedupEnhanced
    Write-TestResult -TestName "Amdahl's Law Calculation" -Passed ($amdahl -eq 1.3333333333333333) -ActualValue $amdahl

    # Display summary
	Write-ToLog "Unit Testing complete"
    Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan

    # Return overall result
    if ($failedTests -eq 0) {
        Write-Host "`nAll tests passed successfully!" -ForegroundColor Green
    } else {
        Write-Host "`nSome tests failed. Please review the failed tests." -ForegroundColor Red
    }
}

# Example implementation of Calculate-Metrics
    function Calculate-Metrics {
        param(
            [double]$ClockSpeed,
            [double]$Instructions,
            [double]$Cycles
        )

        $CPI = $Cycles / $Instructions
        $MIPS = ($ClockSpeed / $CPI) / 1000 # Corrected MIPS: Divide by 1000
        $ExecutionTime = ($Cycles / $ClockSpeed) / 1000000 # Corrected: Divide by 1,000,000 for seconds

        return [PSCustomObject]@{
            CPI = $CPI
            MIPS = $MIPS
            ExecutionTime = $ExecutionTime
        }
    }

# Example implementation of Calculate-AmdahlSpeedup
    function Calculate-AmdahlSpeedup {
        param(
            [decimal]$ParallelFraction, # Use decimal
            [int]$Processors
        )

        $Speedup = 1 / (1 - $ParallelFraction + ($ParallelFraction / $Processors))
        return $Speedup # No rounding needed here
    }

# Function to create SVG performance charts
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
            "LineTrend" {
                $MetricNames = @("CPI", "MIPS", "ExecutionTime")
                $Title = "Performance Metrics Trend"
                
                # Dynamically collect metrics
                $MetricData = $MetricNames | ForEach-Object {
                    $metric = $_
                    $values = $Data | ForEach-Object { 
                        try { [double]$_.$metric } 
                        catch { Write-Host "Warning: Invalid $metric value" -ForegroundColor Yellow; $null }
                    } | Where-Object { $_ -ne $null }
                    @{Name = $metric; Values = $values}
                }
                
                # Line chart generation logic
                $width = 800
                $height = 500
                $padding = 60
                $chartHeight = $height - (2 * $padding)
                $chartWidth = $width - (2 * $padding)
                
                # Find max values for scaling
                $maxValue = ($MetricData | ForEach-Object { 
                    ($_.Values | Measure-Object -Maximum).Maximum 
                } | Measure-Object -Maximum).Maximum
                
                $svg += @"
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">Metric Value</text>
    <text x="$($width/2)" y="$($height - 10)" text-anchor="middle">Test Runs</text>
"@
                
                # Color palette for different metrics
                $colors = @{
                    "CPI" = "blue"
                    "MIPS" = "green"
                    "ExecutionTime" = "red"
                }
                
                # Generate lines for each metric
                $MetricData | ForEach-Object {
                    $metric = $_.Name
                    $values = $_.Values
                    $color = $colors[$metric]
                    
                    $points = for ($i = 0; $i -lt $values.Count; $i++) {
                        $x = $padding + (($i / ($values.Count - 1)) * $chartWidth)
                        $y = $height - $padding - (($values[$i] / $maxValue) * $chartHeight)
                        "$x,$y"
                    }
                    
                    $svg += @"
    <polyline 
        points="$($points -join ' ')" 
        fill="none" 
        stroke="$color" 
        stroke-width="2">
        <title>$metric Trend</title>
    </polyline>
    <text x="$($width - $padding + 10)" y="$($padding + ($MetricData.IndexOf($_) * 20))" 
        fill="$color" font-size="12">$metric</text>
"@
                }
                
                # Finalize SVG
                $svg += @"
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">Metric Value</text>
    <text x="$($width/2)" y="$($height - 10)" text-anchor="middle">Test Runs</text>
</svg>
"@
                return
            }
            "ScatterCorrelation" {
                $Title = "Performance Metrics Correlation"
                
                # Collect two metrics for scatter plot
                $MetricX = "ClockSpeed"
                $MetricY = "MIPS"
                
                $xValues = $Data | ForEach-Object { 
                    try { [double]$_.$MetricX } 
                    catch { Write-Host "Warning: Invalid $MetricX value" -ForegroundColor Yellow; $null }
                } | Where-Object { $_ -ne $null }
                
                $yValues = $Data | ForEach-Object { 
                    try { [double]$_.$MetricY } 
                    catch { Write-Host "Warning: Invalid $MetricY value" -ForegroundColor Yellow; $null }
                } | Where-Object { $_ -ne $null }
                
                $width = 800
                $height = 500
                $padding = 60
                $chartHeight = $height - (2 * $padding)
                $chartWidth = $width - (2 * $padding)
                
                # Calculate min and max for scaling
                $xMin = ($xValues | Measure-Object -Minimum).Minimum
                $xMax = ($xValues | Measure-Object -Maximum).Maximum
                $yMin = ($yValues | Measure-Object -Minimum).Minimum
                $yMax = ($yValues | Measure-Object -Maximum).Maximum
                
                $svg += @"
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">$MetricY</text>
    <text x="$($width/2)" y="$($height - 10)" text-anchor="middle">$MetricX</text>
"@
                
                # Generate scatter points
                for ($i = 0; $i -lt $xValues.Count; $i++) {
                    $x = $padding + ((($xValues[$i] - $xMin) / ($xMax - $xMin)) * $chartWidth)
                    $y = $height - $padding - ((($yValues[$i] - $yMin) / ($yMax - $yMin)) * $chartHeight)
                    
                    # Fixed string formatting using single quotes to avoid variable interpretation
                    $titleText = "$($MetricX): $($xValues[$i]), $($MetricY): $($yValues[$i])"
                    $svg += @"
    <circle 
        cx="$x" 
        cy="$y" 
        r="5" 
        fill="purple" 
        opacity="0.7">
        <title>$([System.Web.HttpUtility]::HtmlEncode($titleText))</title>
    </circle>
"@
                }
                
                # Axes and labels
                $svg += @"
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">$MetricY</text>
    <text x="$($width/2)" y="$($height - 10)" text-anchor="middle">$MetricX</text>
</svg>
"@
                return
            }
            "BoxPlot" {
                $MetricNames = @("CPI", "MIPS", "ExecutionTime")
                $Title = "Performance Metrics Distribution"
                
                # Collect metrics for box plot
                $MetricData = $MetricNames | ForEach-Object {
                    $metric = $_
                    $values = $Data | ForEach-Object { 
                        try { [double]$_.$metric } 
                        catch { Write-Host "Warning: Invalid $metric value" -ForegroundColor Yellow; $null }
                    } | Where-Object { $_ -ne $null }
                    
                    # Calculate box plot statistics
                    $sorted = $values | Sort-Object
                    $q1 = $sorted[[int]($sorted.Count * 0.25)]
                    $median = $sorted[[int]($sorted.Count * 0.5)]
                    $q3 = $sorted[[int]($sorted.Count * 0.75)]
                    $iqr = $q3 - $q1
                    $whiskerLow = $sorted | Where-Object { $_ -ge ($q1 - 1.5 * $iqr) } | Select-Object -First 1
                    $whiskerHigh = $sorted | Where-Object { $_ -le ($q3 + 1.5 * $iqr) } | Select-Object -Last 1
                    
                    @{
                        Name = $metric
                        Q1 = $q1
                        Median = $median
                        Q3 = $q3
                        WhiskerLow = $whiskerLow
                        WhiskerHigh = $whiskerHigh
                    }
                }
                
                $width = 800
                $height = 500
                $padding = 60
                $chartHeight = $height - (2 * $padding)
                $chartWidth = $width - (2 * $padding)
                
                # Find max value for scaling
                $maxValue = ($MetricData | ForEach-Object { $_.WhiskerHigh } | Measure-Object -Maximum).Maximum
                
                $svg += @"
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">Metric Value</text>
"@
                
                # Color palette
                $colors = @{
                    "CPI" = "blue"
                    "MIPS" = "green"
                    "ExecutionTime" = "red"
                }
                
                # Generate box plots
                for ($i = 0; $i -lt $MetricData.Count; $i++) {
                    $metric = $MetricData[$i]
                    $x = $padding + (($i + 0.5) * ($chartWidth / $MetricData.Count))
                    $color = $colors[$metric.Name]
                    
                    # Box dimensions
                    $boxWidth = $chartWidth / ($MetricData.Count * 2)
                    $boxBottom = $height - $padding - (($metric.Q1 / $maxValue) * $chartHeight)
                    $boxTop = $height - $padding - (($metric.Q3 / $maxValue) * $chartHeight)
                    $medianY = $height - $padding - (($metric.Median / $maxValue) * $chartHeight)
                    $whiskerLowY = $height - $padding - (($metric.WhiskerLow / $maxValue) * $chartHeight)
                    $whiskerHighY = $height - $padding - (($metric.WhiskerHigh / $maxValue) * $chartHeight)
                    
                    $svg += @"
    <!-- Whiskers -->
    <line x1="$x" y1="$whiskerLowY" x2="
$svg += @"
    <!-- Whiskers -->
    <line x1="$x" y1="$whiskerLowY" x2="$x" y2="$whiskerHighY" stroke="$color" stroke-width="2"/>
    
    <!-- Box -->
    <rect x="$($x - $boxWidth/2)" y="$boxTop" width="$boxWidth" height="$($boxBottom - $boxTop)" 
          fill="$color" fill-opacity="0.3" stroke="$color" stroke-width="2"/>
    
    <!-- Median Line -->
    <line x1="$($x - $boxWidth/2)" y1="$medianY" x2="$($x + $boxWidth/2)" y2="$medianY" 
          stroke="$color" stroke-width="3"/>
    
    <!-- Metric Label -->
    <text x="$x" y="$($height - 20)" text-anchor="middle" fill="$color">$($metric.Name)</text>
"@
                }
                
                # Y-axis label
                $svg += @"
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">Metric Value</text>
</svg>
"@
                return
            }
            default {
                Write-Host "Invalid chart type selected." -ForegroundColor Red
                Write-ToLog "Chart generation failed: Invalid chart type"
                return
            }
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
        
        # Generate SVG for standard charts (bar charts)
        if ($ChartType -in @("CPI", "MIPS", "ExecutionTime")) {
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
            
            # Add axes labels
            $svg += @"
    <text x="$($width/2)" y="$($height - 10)" text-anchor="middle">Test Runs</text>
    <text x="20" y="$($height/2)" transform="rotate(-90 20,$($height/2))" text-anchor="middle">$ChartType Value</text>
</svg>
"@
        }
        
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
1. CPI Bar Chart
2. MIPS Bar Chart
3. Execution Time Bar Chart
4. Line Trend Chart
5. Scatter Correlation Chart
6. Box Plot Distribution
7. Return to Main Menu
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
            "4" { 
                $InputPath = Read-Host "Enter path to performance results CSV"
                $OutputPath = Read-Host "Enter path to save Line Trend chart SVG"
                Create-PerformanceChartSVG -InputPath $InputPath -OutputPath $OutputPath -ChartType "LineTrend"
            }
            "5" { 
                $InputPath = Read-Host "Enter path to performance results CSV"
                $OutputPath = Read-Host "Enter path to save Scatter Correlation chart SVG"
                Create-PerformanceChartSVG -InputPath $InputPath -OutputPath $OutputPath -ChartType "ScatterCorrelation"
            }
            "6" { 
                $InputPath = Read-Host "Enter path to performance results CSV"
                $OutputPath = Read-Host "Enter path to save Box Plot Distribution chart SVG"
                Create-PerformanceChartSVG -InputPath $InputPath -OutputPath $OutputPath -ChartType "BoxPlot"
            }
            "7" { return }
            default { 
                Write-Host "Invalid option" -ForegroundColor Yellow 
            }
        }
        
        if ($Choice -ne "7") {
            Write-Host "`nPress any key to continue..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    }
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

# Show credits function
function Show-Credits {
    Write-Host "`nCredits"
    Write-Host "======="
    Write-Host "Performance Analysis Program v1.0"
    Write-Host "Created by: Team 7"
    Write-Host "Team Members:"
    Write-Host "- Anthony Grissom"
    Write-Host "- Arthur Smith"
    Write-Host "- Carlos Sanchez"
	Write-Host "- Rebeca Soto"
    Write-Host "- Tristen Uschuk"
    Write-Host "`nAssisted by ClaudeAI (Anthropic)"
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Show-MainMenu
}

# Main Menu
function Show-MainMenu {
    $MainMenu = @"
Performance Analysis Program
--------------------------
1. Performance Test
2. Speedup Comparison
3. Unit Test
4. Chart Generation
5. View Logs
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
            "4" { Show-ChartGenerationMenu }
            "5" { Show-Logs }
            "6" { Show-Credits }
            "7" { 
                Write-ToLog "Program Exit"
                exit 
            }
            default {
                Write-Host "Invalid option. Please try again." -ForegroundColor Yellow
                Write-ToLog "Invalid menu selection: $Choice"
            }
        }
        
        if ($Choice -ne "7") {
            Write-Host "`nPress any key to continue..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    }
}

# Start the program
Write-ToLog "Program Start"
Show-MainMenu