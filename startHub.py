#!/usr/bin/env python
import os
import subprocess
import time
import sys

# Check if Minikube is running
def check_minikube():
    print("Checking if Minikube is running...")
    try:
        result = subprocess.run(['minikube', 'status'], capture_output=True, text=True)
        if "Running" not in result.stdout:
            print("Minikube is not running. Starting Minikube...")
            subprocess.run(['minikube', 'start'], check=True)
        print("Minikube is running")
        return True
    except Exception as e:
        print(f"Error checking Minikube status: {e}")
        return False

# Deploy services to Minikube
def deploy_services():
    print("Deploying services to Minikube...")
    try:
        # Point Docker to Minikube's Docker daemon
        print("Configuring Docker to use Minikube's Docker daemon...")
        if sys.platform == "win32":
            minikube_docker_env = subprocess.run(['minikube', '-p', 'minikube', 'docker-env', '--shell=powershell'], 
                                               capture_output=True, text=True).stdout
            exec_cmd = 'Invoke-Expression ' + minikube_docker_env
            subprocess.run(['powershell', '-Command', exec_cmd], check=True)
        else:
            # For non-Windows platforms
            subprocess.run('eval $(minikube docker-env)', shell=True, check=True)
        
        # Build Docker images for services
        print("Building Docker images...")
        subprocess.run(['docker', 'build', '-t', 'smart-light:latest', '-f', 'Dockerfile.light', '.'], check=True)
        subprocess.run(['docker', 'build', '-t', 'thermostat:latest', '-f', 'Dockerfile.thermostat', '.'], check=True)
        
        # Deploy to Kubernetes
        print("Applying Kubernetes deployment...")
        subprocess.run(['kubectl', 'apply', '-f', 'k8s-deployment.yaml'], check=True)
        
        # Wait for pods to be ready
        print("Waiting for pods to be ready...")
        subprocess.run(['kubectl', 'wait', '--for=condition=Ready', 'pod', '-l', 'app=smart-light', '--timeout=120s'], check=True)
        subprocess.run(['kubectl', 'wait', '--for=condition=Ready', 'pod', '-l', 'app=thermostat', '--timeout=120s'], check=True)
        
        print("Services deployed successfully")
        return True
    except Exception as e:
        print(f"Error deploying services: {e}")
        return False

# Run the local hub
def run_hub():
    print("Starting local hub...")
    try:
        os.environ['PYTHONUNBUFFERED'] = '1'  # Ensure output is not buffered
        subprocess.run(['python', 'hub.py'], check=True)
    except KeyboardInterrupt:
        print("Hub stopped by user")
    except Exception as e:
        print(f"Error running hub: {e}")

if __name__ == "__main__":
    if check_minikube() and deploy_services():
        run_hub()
    else:
        print("Failed to set up environment. Exiting.")