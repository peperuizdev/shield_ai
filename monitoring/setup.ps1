# Shield AI Monitoring Setup Script (Windows PowerShell)
# Configura e inicia el stack completo de monitoreo

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "clean", "help")]
    [string]$Action = "start"
)

# Functions
function Write-Header {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host "        Shield AI Monitoring Setup" -ForegroundColor Blue
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Test-Requirements {
    Write-Step "Checking requirements..."
    
    # Check Docker
    try {
        $null = docker --version
    }
    catch {
        Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop first."
        exit 1
    }
    
    # Check Docker Compose
    try {
        $null = docker-compose --version
    }
    catch {
        Write-Error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    }
    
    # Check if Docker is running
    try {
        $null = docker info 2>$null
    }
    catch {
        Write-Error "Docker is not running. Please start Docker Desktop first."
        exit 1
    }
    
    Write-Success "All requirements met!"
}

function Setup-Directories {
    Write-Step "Setting up directories..."
    
    # Create directories if they don't exist
    $dirs = @("config\grafana", "dashboards")
    foreach ($dir in $dirs) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Success "Directories created!"
}

function Test-Backend {
    Write-Step "Checking Shield AI Backend..."
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Success "Shield AI Backend is running!"
    }
    catch {
        Write-Warning "Shield AI Backend not detected on port 8000"
        Write-Warning "Make sure to start the backend before monitoring can collect metrics"
    }
}

function Start-Monitoring {
    Write-Step "Starting monitoring stack..."
    
    # Pull latest images
    Write-Step "Pulling Docker images..."
    docker-compose pull
    
    # Start services
    Write-Step "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    Write-Step "Waiting for services to start..."
    Start-Sleep -Seconds 10
    
    Write-Success "Monitoring stack started!"
}

function Test-Services {
    Write-Step "Verifying services..."
    
    $services = @(
        @{Name="prometheus"; Port=9090; Path="/api/v1/status/config"},
        @{Name="grafana"; Port=3000; Path="/api/health"},
        @{Name="alertmanager"; Port=9093; Path="/-/healthy"},
        @{Name="node-exporter"; Port=9100; Path="/metrics"}
    )
    
    foreach ($service in $services) {
        Write-Host "  Checking $($service.Name)... " -NoNewline
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:$($service.Port)$($service.Path)" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "✓" -ForegroundColor Green
        }
        catch {
            Write-Host "✗" -ForegroundColor Red
            Write-Warning "$($service.Name) is not responding on port $($service.Port)"
        }
    }
}

function Show-AccessInfo {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host "      Monitoring Services Access Info" -ForegroundColor Blue
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""
    
    Write-Host "Grafana Dashboard: " -NoNewline -ForegroundColor Green
    Write-Host "http://localhost:3000"
    Write-Host "  Username: admin"
    Write-Host "  Password: admin123"
    Write-Host ""
    
    Write-Host "Prometheus: " -NoNewline -ForegroundColor Green
    Write-Host "http://localhost:9090"
    Write-Host "AlertManager: " -NoNewline -ForegroundColor Green
    Write-Host "http://localhost:9093"
    Write-Host "Node Exporter: " -NoNewline -ForegroundColor Green
    Write-Host "http://localhost:9100"
    Write-Host ""
    
    Write-Host "Backend Metrics: " -NoNewline -ForegroundColor Green
    Write-Host "http://localhost:8000/metrics"
    Write-Host "Backend Health: " -NoNewline -ForegroundColor Green
    Write-Host "http://localhost:8000/metrics/health"
    Write-Host ""
    
    Write-Host "=============================================" -ForegroundColor Blue
}

function Show-Help {
    Write-Host "Shield AI Monitoring Setup Script (PowerShell)"
    Write-Host ""
    Write-Host "Usage: .\setup.ps1 [ACTION]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  start    Start the monitoring stack (default)"
    Write-Host "  stop     Stop the monitoring stack"
    Write-Host "  restart  Restart the monitoring stack"
    Write-Host "  status   Show status of services"
    Write-Host "  logs     Show logs from all services"
    Write-Host "  clean    Stop and remove all containers and volumes"
    Write-Host "  help     Show this help message"
    Write-Host ""
}

function Stop-Monitoring {
    Write-Step "Stopping monitoring stack..."
    docker-compose down
    Write-Success "Monitoring stack stopped!"
}

function Restart-Monitoring {
    Write-Step "Restarting monitoring stack..."
    docker-compose down
    docker-compose up -d
    Start-Sleep -Seconds 10
    Write-Success "Monitoring stack restarted!"
}

function Show-Status {
    Write-Step "Checking service status..."
    docker-compose ps
}

function Show-Logs {
    Write-Step "Showing logs from all services..."
    docker-compose logs -f
}

function Clean-Monitoring {
    Write-Warning "This will remove all monitoring containers and data!"
    $confirmation = Read-Host "Are you sure? (y/N)"
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        Write-Step "Cleaning monitoring stack..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        Write-Success "Monitoring stack cleaned!"
    }
    else {
        Write-Host "Operation cancelled."
    }
}

# Main script execution
switch ($Action) {
    "start" {
        Write-Header
        Test-Requirements
        Setup-Directories
        Test-Backend
        Start-Monitoring
        Test-Services
        Show-AccessInfo
    }
    "stop" {
        Stop-Monitoring
    }
    "restart" {
        Restart-Monitoring
        Test-Services
    }
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs
    }
    "clean" {
        Clean-Monitoring
    }
    "help" {
        Show-Help
    }
    default {
        Write-Error "Invalid action: $Action"
        Show-Help
        exit 1
    }
}