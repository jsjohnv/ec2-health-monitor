pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify Python') {
            steps {
                bat '"C:/Users/jsjoh/AppData/Local/Python/pythoncore-3.14-64/python.exe" --version'
            }
        }

        stage('Build') {
            steps {
                bat '''
                    "C:/Users/jsjoh/AppData/Local/Python/pythoncore-3.14-64/python.exe" -m venv .venv
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
    }

    post {
        success {
            echo 'CI pipeline completed successfully!'
        }
        failure {
            echo 'CI pipeline failed. Check the console output.'
        }
    }
}
