pipeline {
    agent any
    stages {
        stage('Check environment') {
            steps{
                echo 'Checking the Jenkins build environment'
                sh 'whoami'
                sh 'ls -l manage.py Dockerfile'
                sh 'docker version'
            }
        }
    }
}

