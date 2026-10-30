# EC2 Linux Health Monitoring API

A Python Flask-based REST API for monitoring Linux system health, packaged with Docker and served using Gunicorn.

## Project Overview

This project monitors Linux system health and provides two HTTP endpoints:

- GET /health — Returns overall health status, hostname, UTC timestamp, and a summary reason.
- GET /health/details — Returns detailed system metrics, thresholds, and individual check results.

## Health Checks

The application monitors:

1. CPU utilization
2. Memory utilization
3. System load averages (1, 5, and 15 minutes)
4. Disk usage by filesystem
5. System uptime
6. Listening TCP ports and owning processes
7. DNS resolution
8. Outbound TCP connectivity
9. Network interfaces and default gateway

The application uses Python, Flask, psutil, and direct Linux /proc filesystem reads.

## Health Status

- healthy — HTTP 200
- degraded — HTTP 200
- unhealthy — HTTP 503

The most severe individual check determines the overall status.

## Configuration and Thresholds

Health-check thresholds and connectivity targets can be configured using environment variables.

| Environment Variable | Default | Description |
|---|---|---|
| CPU_WARNING | 75 | CPU warning threshold (%) |
| CPU_CRITICAL | 90 | CPU critical threshold (%) |
| MEMORY_WARNING | 80 | Memory warning threshold (%) |
| MEMORY_CRITICAL | 95 | Memory critical threshold (%) |
| LOAD_WARNING | 1.0 | Normalized load warning threshold |
| LOAD_CRITICAL | 2.0 | Normalized load critical threshold |
| DISK_WARNING | 80 | Disk warning threshold (%) |
| DISK_CRITICAL | 95 | Disk critical threshold (%) |
| DNS_HOSTNAME | google.com | Hostname used for DNS testing |
| DNS_TIMEOUT | 3 | DNS timeout in seconds |
| TCP_TARGET_HOST | google.com | Outbound connectivity target |
| TCP_TARGET_PORT | 443 | Outbound connectivity port |
| TCP_TIMEOUT | 3 | TCP connection timeout in seconds |

### Example Configuration

Set custom thresholds before starting the application:

    export CPU_WARNING=70
    export CPU_CRITICAL=85
    export MEMORY_WARNING=75
    export MEMORY_CRITICAL=90

These values override the application defaults.

## Health Status Logic

- Healthy: All checks are healthy.
- Degraded: At least one check is degraded and none is unhealthy.
- Unhealthy: At least one check is unhealthy.

An unhealthy overall status returns HTTP 503. Healthy and degraded statuses return HTTP 200.

## Local Installation

### Prerequisites

- Linux or Ubuntu WSL2
- Python 3.14
- pip
- Git

### Install Dependencies

From the project directory:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

### Start the API

    gunicorn --bind 0.0.0.0:8000 app:app

### Test the API

Open another terminal and run:

    curl -i http://localhost:8000/health
    curl -i http://localhost:8000/health/details

Expected HTTP responses:

- 200: Healthy or degraded
- 503: Unhealthy

## Docker Deployment

### Build the Docker Image

    docker build -t ec2-health-monitor:v2 .

### Start the Container

    docker run -d \
      --name health-monitor \
      -p 8000:8000 \
      --restart unless-stopped \
      ec2-health-monitor:v2

### Verify the Container

    docker ps
    docker logs health-monitor

### Test the Containerized API

    curl -i http://localhost:8000/health
    curl -i http://localhost:8000/health/details

### Docker Security

The Docker image runs Gunicorn as a non-root user.

Application logs are written to standard output and standard error.

The restart policy is configured as unless-stopped.

### Container Versus Host Metrics

Docker containers have isolated process, network, and filesystem views.

The containerized API reports container-visible metrics, which may differ from the underlying EC2 host.

For accurate EC2 host monitoring, the API can run directly on the EC2 instance using Gunicorn and systemd.

## AWS EC2 Deployment

### Target Environment

- Cloud provider: AWS
- Region: Asia Pacific (Mumbai), ap-south-1
- Operating system: Ubuntu Linux
- Application: Python Flask API
- Application server: Gunicorn
- API port: 8000

### Deployment Approach

The final EC2 deployment will run the API directly on the Linux host using Gunicorn and systemd.

This allows the API to monitor EC2 host-level processes, network interfaces, and filesystems instead of relying only on Docker's isolated view.

### Deployment Procedure

1. Launch an Ubuntu EC2 instance in the Mumbai region.
2. Configure the security group to allow SSH (TCP 22) only from the administrator's public IP address.
3. Allow API access (TCP 8000) only from authorized reviewer IP addresses.
4. Connect to the instance using SSH.
5. Install Python, pip, Git, and required system packages.
6. Clone the GitHub repository.
7. Create a Python virtual environment and install requirements.
8. Configure Gunicorn as a systemd service.
9. Start the service and enable automatic startup.
10. Verify the API using the EC2 public IP address.

### API URLs

Replace EC2_PUBLIC_IP with the actual EC2 public IPv4 address.

    http://EC2_PUBLIC_IP:8000/health

    http://EC2_PUBLIC_IP:8000/health/details

### Security Considerations

- Restrict SSH to the administrator's IP.
- Restrict API access to authorized reviewers.
- Do not commit AWS credentials, SSH private keys, or secrets.
- Use HTTPS and authentication for production deployments.
- Stop or terminate the EC2 instance after the assignment review.

### Deployment Status

AWS EC2 deployment completed successfully.

The Python Flask Health Check API is deployed on an AWS EC2
t3.micro instance running Ubuntu 24.04 LTS in the Mumbai
(ap-south-1) region.

Gunicorn serves the application on port 8000, and systemd
manages automatic startup and service restarts.

The deployment is automated using a Jenkins CI/CD pipeline
integrated with GitHub. Jenkins validates the application,
deploys the selected Git commit to EC2 over SSH, and verifies
the API health after deployment.

Deployment verified on October 30, 2026.


## Testing and Troubleshooting

### Verify API Health

    curl -i http://localhost:8000/health

### Verify Detailed Metrics

    curl -s http://localhost:8000/health/details | python3 -m json.tool

### Simulate an Outbound Connectivity Failure

Run this test from the project directory with the Python virtual environment activated:

    TCP_TARGET_HOST=127.0.0.1 TCP_TARGET_PORT=1 python -c 'from app import app; r=app.test_client().get("/health"); print(r.status_code, r.get_json())'

Expected result:

- HTTP 503
- Overall status: unhealthy
- Reason identifies outbound_tcp

### Docker Troubleshooting

Check container status:

    docker ps -a

Check application logs:

    docker logs health-monitor

Verify the container runs as a non-root user:

    docker exec health-monitor id

Verify the restart policy:

    docker inspect health-monitor --format '{{.HostConfig.RestartPolicy.Name}}'

## AI-Assisted Development

AI assistance was used to explain application architecture, develop health checks, troubleshoot Python errors, configure Docker, and prepare documentation.

All changes were tested using Python commands, Flask's test client, Docker, and curl.

### Error Identified and Corrected

During development, disk monitoring initially used psutil.disk_partitions(all=False).

This did not include the Docker root OverlayFS filesystem.

The implementation was changed to inspect all mounts and exclude irrelevant virtual filesystems.

A separate Python NameError occurred because the loop variable was named partitions while the code referenced partition.

The variable name was corrected, and the function was tested again.

### Lessons Learned

- Docker containers do not automatically expose complete EC2 host metrics.
- Linux filesystem discovery requires careful handling of virtual mounts.
- Python variable names must be consistent.
- Testing health-check failures is as important as testing successful responses.
- Docker image versioning makes it easier to test changes and retain a rollback option.

## Production Improvements

Potential improvements include:

- HTTPS with Nginx or another reverse proxy
- API authentication and authorization
- Structured logging and centralized monitoring
- Automated unit and integration tests
- CI/CD pipelines
- Prometheus metrics integration
- Alerting for degraded and unhealthy states
- Configurable filesystem inclusion and exclusion rules
- More robust DNS timeout handling
- Container-aware CPU and memory calculations
- Rate limiting and security hardening

## Project Status

- Python Flask API: Completed
- Health-check implementation (9 checks): Completed
- Configurable warning and critical thresholds: Completed
- Local API testing: Completed
- Docker image build: Completed
- Docker API testing: Completed
- GitHub publication: Completed
- AWS EC2 deployment (Ubuntu 24.04): Completed
- Gunicorn application server: Completed
- systemd service configuration: Completed
- EC2 disk monitoring issue resolution: Completed
- Final remote API validation: Completed
- HTTPS and authentication: Pending
- Jenkins CI/CD pipeline automation: Completed. The pipeline checks out code from GitHub, validates the Python application, deploys the selected commit to AWS EC2 over SSH, and verifies application health.

AWS Deployment Details

- AWS Region: ap-south-1 (Mumbai)
- EC2 Instance Type: t3.micro
- Operating System: Ubuntu Server 24.04 LTS
- Application Port: 8000
- Application Server: Gunicorn
- Service Manager: systemd
- Deployment Method: GitHub clone and Python virtual environment
- API Endpoints:
  GET /health
  GET /health/details

## API Response Examples

### GET /health

Returns the overall health of the Linux server.

- HTTP 200: Healthy or degraded
- HTTP 503: Unhealthy

Example response from AWS EC2:

```json
{
  "hostname": "ip-172-31-6-251",
  "reason": "All system and network checks are healthy",
  "status": "healthy",
  "timestamp": "2026-10-30T03:00:02.507070+00:00"
}
```

### GET /health/details

Returns detailed system and network health checks.

Example response captured from AWS EC2:

```json
{
  "hostname": "ip-172-31-6-251",
  "status": "healthy",
  "timestamp": "2026-10-30T02:49:56.878072+00:00",
  "checks": {
    "cpu": {
      "value": 5.3,
      "unit": "%",
      "warning_threshold": 75.0,
      "critical_threshold": 90.0,
      "status": "healthy"
    },
    "memory": {
      "used_percent": 41.79,
      "available_mb": 529.39,
      "warning_threshold": 80.0,
      "critical_threshold": 95.0,
      "status": "healthy"
    }
  }
}
```

This is an abbreviated example. The complete response includes CPU, memory, disk, load average, uptime, DNS, outbound TCP connectivity, listening TCP ports, and network interfaces.

Actual values change depending on server activity.
