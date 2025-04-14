pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                sh 'apt-get update && apt-get install -y python3 python3-pip'
                sh 'python3 -m pip install -r requirements.txt'
            }
        }

        stage('Lint') {
            steps {
                sh 'python3 -m pip install flake8'
                sh 'flake8 app --ignore=E501,E722,W503'
            }
        }

        stage('Test') {
            steps {
                sh 'python3 -m pip install pytest pytest-cov'
                sh 'pytest --cov=app tests/'
            }
        }

        stage('Build') {
            steps {
                sh 'docker-compose build'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker-compose up -d'
            }
        }
    }

    post {
        always {
            script {
                node {
                    sh 'docker-compose down || true'
                }
            }
        }
    }
}