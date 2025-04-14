pipeline {
    agent any

    environment {
        DOCKER_COMPOSE = 'docker-compose'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Lint') {
            steps {
                sh 'pip install flake8'
                sh 'flake8 app --ignore=E501,E722,W503'
            }
        }

        stage('Test') {
            steps {
                sh 'pip install pytest pytest-cov'
                sh 'pytest --cov=app tests/'
            }
        }

        stage('Build') {
            steps {
                sh '${DOCKER_COMPOSE} build'
            }
        }

        stage('Deploy') {
            steps {
                sh '${DOCKER_COMPOSE} up -d'
            }
        }

        stage('Load Test') {
            steps {
                sh 'pip install locust'
                sh 'locust -f tests/locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --headless --run-time 1m'
            }
        }
    }

    post {
        always {
            sh '${DOCKER_COMPOSE} down || true'
        }
    }
}