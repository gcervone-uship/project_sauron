#!/usr/bin/env groovy
def artifact_name = "ml_unified_pipeline.tgz"
def git_repo = "ml_unified_pipeline"
def artifactory_server = Artifactory.server 'Macmillan-Artifactory'

pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                script {
                    def scmVars = checkout scm
                    def git_branch = scmVars.GIT_BRANCH
                    branch = git_branch.replaceFirst(/^.*\//, "")
                    artifactory_target = "Macmillan-Product-Builds/${git_repo}/${branch}/"
                }
            }
        }
        stage('Create Artifact') {
            steps {
                print "Creating Artifact: ${artifact_name}"
                sh "tar cfvz ${artifact_name} install_requirements.sh env_builder deploy cloudformation py_sauron"
            }
        }
        stage('Publish to Artifactory') {
            steps {
                script {
                    def uploadSpec = """{
                        "files": [
                            {
                                "pattern": "${artifact_name}",
                                "target": "${artifactory_target}"
                            }
                        ]
                    }"""
                    artifactory_server.upload(uploadSpec)
                }
            }
        }
    }
}
