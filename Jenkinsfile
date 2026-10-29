pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    environment {
        PYTHON = 'C:/Users/jsjoh/AppData/Local/Python/pythoncore-3.14-64/python.exe'
        EC2_HOST = '13.203.206.152'
        KNOWN_HOSTS = 'C:/ProgramData/Jenkins/ec2_known_hosts'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify Python') {
            steps {
                bat '"%PYTHON%" --version'
            }
        }

        stage('Build') {
            steps {
                bat '''
                    "%PYTHON%" -m venv .venv
                    .venv\\Scripts\\python.exe -m pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                bat '''
                    .venv\\Scripts\\python.exe -m compileall -q app.py
                    .venv\\Scripts\\python.exe -c "import app; print('Application import successful')"
                '''
            }
        }

        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'aws-ec2-ssh-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    bat '''
                        @echo off
                        icacls "%SSH_KEY%" /inheritance:r
                        if errorlevel 1 exit /b 1
                        icacls "%SSH_KEY%" /grant:r "%USERDOMAIN%\\%USERNAME%:R"
                        if errorlevel 1 exit /b 1

                        "C:\\Windows\\System32\\OpenSSH\\ssh.exe" ^
                          -i "%SSH_KEY%" ^
                          -o IdentitiesOnly=yes ^
                          -o StrictHostKeyChecking=yes ^
                          -o UserKnownHostsFile="%KNOWN_HOSTS%" ^
                          -o BatchMode=yes ^
                          -o ConnectTimeout=10 ^
                          %SSH_USER%@%EC2_HOST% ^
			  "bash /home/ubuntu/deploy-health-monitor.sh %GIT_COMMIT%"
                    '''
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'aws-ec2-ssh-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    bat '''
                        @echo off
                        icacls "%SSH_KEY%" /inheritance:r
                        if errorlevel 1 exit /b 1
                        icacls "%SSH_KEY%" /grant:r "%USERDOMAIN%\\%USERNAME%:R"
                        if errorlevel 1 exit /b 1

                        "C:\\Windows\\System32\\OpenSSH\\ssh.exe" ^
                          -i "%SSH_KEY%" ^
                          -o IdentitiesOnly=yes ^
                          -o StrictHostKeyChecking=yes ^
                          -o UserKnownHostsFile="%KNOWN_HOSTS%" ^
                          -o BatchMode=yes ^
                          -o ConnectTimeout=10 ^
                          %SSH_USER%@%EC2_HOST% ^
                          "cd /home/ubuntu/ec2-health-monitor && sudo -n systemctl is-active --quiet ec2-health-monitor && curl --fail --silent --show-error http://127.0.0.1:8000/health"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'CI/CD pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check console output and EC2 service logs.'
        }
    }
}
