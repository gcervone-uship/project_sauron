def stack_name = params.Stack_Name
def repo = params.Project
def branch = params.Branch
def swarm_hostname
def namespace_root
switch(params.Swarm) {
  case "prod":
    swarm_hostname = "swarm-prod.mldev.cloud"
    ssh_agent_id = "docker-prod-swarm"
    aws_id = "walkietalkie-prod"
    namespace_root = "prod"
    break
  case "integration":
    swarm_hostname = "swarm-int.mldev.cloud"
    ssh_agent_id = "docker-dev-swarm"
    aws_id = "ml-jenkins-dev"
    namespace_root = "integration"
    break
  default:
    swarm_hostname = "swarm-dev.mldev.cloud"
    ssh_agent_id = "docker-dev-swarm"
    aws_id = "ml-jenkins-dev"
    namespace_root = "dev"
    break
}
def consul_namespace = "${namespace_root}/${stack_name}/${repo}"

def artifactory_server = Artifactory.server 'Macmillan-Artifactory'
def artifactory_target = "Macmillan-Product-Builds"

def data_stack_name = "${stack_name}-data"
def data_template = "./${repo}/data.cfn.yml"

def default_loadbalancer_template = "./cloudformation/base.cfn.yml"
def loadbalancer_template = "./${repo}/load.cfn.yml"
def loadbalancer_stack_name = "${stack_name}-load"

def frontend_stack_name = "${stack_name}-frontend"
def frontend_template = "./${repo}/frontend.cfn.yml"
def frontend_webpack = "./${repo}/webpack.tgz"


def deploy_download_spec = """{
  "files": [
  {
    "pattern": "${artifactory_target}/ml_unified_pipeline/master/",
    "target": "./",
    "explode": "true"
  }
 ]
}"""
def repo_download_spec = """{
  "files": [
  {
    "pattern": "${artifactory_target}/${repo}/${branch}/",
    "target": "./"
  }
 ]
}"""

pipeline {
  agent { label 'python3' }

  environment {
        CONSUL_HTTP_ADDR = '172.28.17.4:8500'
    }

  stages {
    stage('Get Artifacts') {
      steps {
        script {
          sh "rm -fR *"
          artifactory_server.download(deploy_download_spec)
          artifactory_server.download(repo_download_spec)
          sh (
            """mv ml_unified_pipeline/master/* ./
                mv ./${repo}/${branch}/.key ./${repo}/
                mv ./${repo}/${branch}/.images ./${repo}/
                mv ./${repo}/${branch}/* ./${repo}/
            """
          )
        }
      }
    }
    stage('Install Dependencies') {
      steps {
        sh (
            """chmod +x install_requirements.sh
                ./install_requirements.sh
            """
          )
      }
	}
    stage('Build Data Stack') {
      steps {
        script {
          if (fileExists("./${repo}/data.cfn.yml")) {
            withCredentials([[$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: "${aws_id}",
              accessKeyVariable: 'ACCESS_KEY', 
              secretKeyVariable: 'SECRET_KEY']]) {
                env.AWS_ACCESS_KEY_ID="${ACCESS_KEY}"
                env.AWS_SECRET_ACCESS_KEY="${SECRET_KEY}"
                env.AWS_DEFAULT_REGION="us-east-1"

                sh "python3 py_sauron/cfn_to_consul.py -p ${consul_namespace} --build-template ${data_template} --build-stack-name ${data_stack_name} -o ${consul_namespace}"
              }
           }
        }
      }
    }   
		
    stage("Build .ENV file"){
      steps {
        sh "python3 env_builder/env_builder.py -t consul -k ${repo}/.key -d ./.env -p ${consul_namespace}"
      }
    }
    stage("Deploying stack to Swarm") {
      steps {
        script {
          sh (
            """cp ${repo}/docker-compose-swarm.yml ./docker-compose-swarm.yml
                cat ${repo}/.images >> ./.env
                [[ -e '/var/lib/jenkins/.ssh/known_hosts' ]] && rm /var/lib/jenkins/.ssh/known_hosts
            """
          )
          withCredentials([[$class: 'UsernamePasswordMultiBinding',
            credentialsId: 'artifactory-jenkins-user',
            usernameVariable: 'USERNAME', 
            passwordVariable: 'PASSWORD']]) {
              env.ARTIFACTORY_USER="${USERNAME}"
              env.ARTIFACTORY_PASSWORD="${PASSWORD}"
            }
          sshagent (credentials: ["${ssh_agent_id}"]) {
            sh "python3 deploy/main.py artifactory ${stack_name} ${swarm_hostname} 5"
          }
        }
      }
    }
    stage("Creating ELBs Service URLs"){
      steps {
        script {
          if (fileExists(loadbalancer_template)) {
            awsShellCommand("python3 py_sauron/cfn_to_consul.py -p ${consul_namespace} --build-template ${loadbalancer_template} --build-stack-name ${loadbalancer_stack_name} -o ${consul_namespace}")
          }
          else {
            awsShellCommand("python3 deploy/cf_main.py load ${stack_name} ${swarm_hostname}")
          }
        }
      }
    }
    stage("Publish Endpoints to Consul"){
      steps {
        sh "python3 py_sauron/cfn_to_consul.py  -n ${stack_name} -s cfn_stack -p Outputs -o ${consul_namespace}"
      }
    }
    stage("Build Frontend") {
      steps {
        script {
          if (fileExists(frontend_template) && fileExists(frontend_webpack)) {
            awsShellCommand("python3 py_sauron/cfn_to_consul.py -p ${consul_namespace} --build-template ${frontend_template} --build-stack-name ${frontend_stack_name}")
            awsShellCommand("python3 py_sauron/upload_to_s3.py --output-lookup cfn -d ${frontend_stack_name} -s ${frontend_webpack}")
          }
        }
      }
    }
  }
}

def awsShellCommand(shell_command) {
  return script {
    withCredentials([[$class: 'AmazonWebServicesCredentialsBinding',
      credentialsId: "${aws_id}",
      accessKeyVariable: 'ACCESS_KEY', 
      secretKeyVariable: 'SECRET_KEY']]) {
        env.AWS_ACCESS_KEY_ID="${ACCESS_KEY}"
        env.AWS_SECRET_ACCESS_KEY="${SECRET_KEY}"
        env.AWS_DEFAULT_REGION="us-east-1"
        sh shell_command
      }    
  }
}
