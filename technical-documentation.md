# Performance Analysis Program
## Technical Documentation

### Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Core Components](#core-components)
4. [Usage Guide](#usage-guide)
5. [Component Details](#component-details)
6. [Data Formats](#data-formats)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

## Overview
The Performance Analysis Program is a PowerShell-based tool designed for analyzing and visualizing computer performance metrics. It provides capabilities for performance testing, speedup analysis, metric visualization, and unit testing.

## System Requirements
- PowerShell 5.1 or higher
- ThreadJob module (optional, will be automatically installed if possible)
- Write permissions to C:\Scripts\ for logging
- Sufficient permissions to create and write to files on the desktop

## Core Components

### 1. Performance Testing Module
**Key Functions:**
- `Start-PerformanceTest`: Main entry point for performance analysis
- `Calculate-Metrics`: Processes raw performance data
- `Initialize-Requirements`: Sets up required dependencies

**Metrics Calculated:**
- Cycles Per Instruction (CPI)
- Million Instructions Per Second (MIPS)
- Execution Time
- Total Cycles
- MFLOPS (Million Floating Point Operations Per Second)

### 2. Speedup Analysis Module
**Key Functions:**
- `Start-SpeedupComparison`: Analyzes performance improvements
- `Calculate-AmdahlSpeedup`: Implements Amdahl's Law calculations

**Features:**
- Supports both manual data entry and CSV input
- Calculates actual vs theoretical speedup
- Determines parallel efficiency
- Exports results to CSV

### 3. Visualization Module
**Key Functions:**
- `Create-PerformanceChartSVG`: Generates performance visualizations
- `Show-ChartGenerationMenu`: Manages chart creation workflow

**Chart Types:**
- CPI Bar Chart
- MIPS Bar Chart
- Execution Time Bar Chart
- Line Trend Chart
- Scatter Correlation Chart
- Box Plot Distribution

### 4. Testing Framework
**Key Functions:**
- `Start-UnitTest`: Executes test suite
- `Add-TestResult`: Records test outcomes
- `Compare-FloatingPoint`: Handles floating-point comparisons
- `Compare-Decimal`: Manages decimal comparisons

## Usage Guide

### 1. Starting the Program
```powershell
# Navigate to script directory
cd C:\Path\To\Script
# Execute the script
.\PerformanceTesting.ps1
```

### 2. Performance Testing
1. Select option 1 from the main menu
2. Provide path to CSV file with performance data
3. Specify export location for results
4. Review generated statistics and charts

Required CSV Format:
```csv
ClockSpeed,Instructions,Cycles
2400,1000000,2000000
3000,1500000,3000000
```

### 3. Speedup Comparison
1. Select option 2 from the main menu
2. Choose input method:
   - Manual entry: Input values directly
   - CSV file: Provide path to data file
3. Review speedup analysis results

### 4. Chart Generation
1. Select option 4 from the main menu
2. Choose chart type
3. Provide input data location
4. Specify output location for SVG file

## Data Formats

### Input CSV Requirements

#### Performance Test Data
```csv
ClockSpeed,Instructions,Cycles
2400,1000000,2000000
3000,1500000,3000000
1600,800000,1200000
```

#### Speedup Comparison Data
```csv
Machine,ClockSpeed,Cycles
Machine1,2400,2000000
Machine2,3000,3000000
```

### Output Formats

#### Results CSV
```csv
CPI,MIPS,ExecutionTime,TotalCycles,MFLOPS
2.0,1200,0.000833,2000000,1200
```

## Error Handling

The program implements comprehensive error handling:

1. **Input Validation**
   - Checks for file existence
   - Validates CSV headers
   - Verifies data types
   - Ensures positive values for critical metrics

2. **Runtime Protection**
   - Graceful handling of missing modules
   - Recovery from calculation errors
   - Protection against division by zero
   - Handling of missing or corrupt data

3. **Logging**
   - All operations are logged to C:\Scripts\log.txt
   - Includes timestamps and error details
   - Maintains operation history

## Best Practices

1. **Data Preparation**
   - Ensure CSV files use correct headers
   - Clean data before processing
   - Remove any non-numeric values
   - Use consistent units across datasets

2. **Performance Optimization**
   - Use CSV input for large datasets
   - Enable threading when possible
   - Regular log file maintenance
   - Export results to dedicated folders

3. **Chart Generation**
   - Choose appropriate chart types for data
   - Use consistent naming conventions
   - Maintain organized output directories
   - Review SVG files for accuracy

4. **Testing**
   - Run unit tests after modifications
   - Verify results against known data
   - Test with various input sizes
   - Validate output formats

## Common Issues and Solutions

1. **ThreadJob Module Installation Fails**
   - Ensure PowerShell is running as administrator
   - Check internet connectivity
   - Verify PowerShell version compatibility
   - Use single-threaded mode if necessary

2. **Chart Generation Errors**
   - Verify input data format
   - Check file permissions
   - Ensure sufficient disk space
   - Review log files for specific errors

3. **Performance Issues**
   - Reduce dataset size
   - Enable threading if available
   - Close unnecessary applications
   - Monitor system resources

## Support and Maintenance

### Logging
The program maintains detailed logs at C:\Scripts\log.txt, including:
- Operation timestamps
- Error messages
- Performance metrics
- System status

### Updates and Modifications
- Version control through comments
- Modular design for easy updates
- Extensible chart types
- Configurable parameters

## Contributing
When modifying the code:
1. Follow existing naming conventions
2. Add appropriate error handling
3. Update documentation
4. Run unit tests
5. Test with various data sets
