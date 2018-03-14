def stack_name = params.Stack_Name
def repo = params.Project
def branch = params.Branch
def swarm_hostname
switch(params.Swarm) {
  case "dev":
    swarm_hostname = "swarm-dev.mldev.cloud"
    break
  case "integration":
    swarm_hostname = "swarm-int.mldev.cloud"
    break
  default:
    swarm_hostname = "swarm-prod.mldev.cloud"
    break
}
def artifactory_server = Artifactory.server 'Macmillan-Artifactory'
def artifactory_target = "Macmillan-Product-Builds/"
def deploy_download_spec = """{
  "files": [
  {
    "pattern": "${artifactory_target}/ml_unified_pipeline/master/\*.tgz",
    "target": "./"
  }
 ]
}"""
def repo_download_spec = """{
  "files": [
  {
    "pattern": "${artifactory_target}/${repo}/${branch}/\*",
    "target": "./${repo}"
  }
 ]
}"""

pipeline {
  agent any
  stages {
    stage('Get Artifacts') {
      steps {
        script {
          artifactory_server.download(deploy_download_spec)
          artifactory_server.download(repo_download_spec)
        }
        sh "tar xfvz $(ls | grep tgz)"
      }
    }
    stage('Install Dependencies') {
      steps {
        sh "sudo ./install_requirements.sh"
      }
    }
    stage("Build .ENV file"){
      steps {
        sh "export CONSUL_HTTP_ADDR=http://172.28.17.4:8500"
        sh "python3 env_builder/env_builder.py -t consul -k ${repo}/.key -d ./.env -p ${params.Swarm}/${repo}"
      }
    }
    stage("Deploying stack to Swarm"){
      steps {
        script {
          withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'artifactory-jenkins-user',
            usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']])
        }
        sh "export ARTIFACTORY_USER=${USERNAME}"
        sh "export ARTIFACTORY_PASSWORD=${PASSWORD}"
        sh "cp ${repo}/docker-compose-swarm.yml docker-compose-swarm.yml"
        sh "cat ${repo}/.images >> ./.env"
        sh "python3 deploy/main.py artifactory ${stack_name} ${swarm_hostname} 5"
      }
    }
    stage("Creating ELBs Service URLs"){
      steps {
        sh "deploy/cf_main.py load ${stack_name} ${swarm_hostname}"
      }
    }
  }
}