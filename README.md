# Web Vault Secret Creator

**Web Vault Secret Creator** is a simple web interface for securely inserting secrets into a [HashiCorp Vault](https://www.vaultproject.io/) instance. It leverages Kubernetes authentication and a Vault role to ensure users can create new secrets without requiring them to have direct Vault tokens. The web interface also allows browsing directories (namespaces) in Vault, making the process of secret management more user-friendly.

## Features

- **Kubernetes-based Authentication**: Authenticates to Vault using a Kubernetes service account token and a specified Vault role.
- **Secure Secret Storage**: Insert JSON-formatted secrets into Vault’s KV engine without direct Vault token exposure.
- **Directory Browsing**: Lists directories (namespaces) within the Vault KV path structure, helping users understand where their secrets should be stored.
- **Minimal UI**: A simple web interface built using Flask and a basic HTML/JS front-end for inserting secrets.

## How It Works

1. **Kubernetes Authentication**:  
   The application runs inside a Kubernetes cluster, retrieving its service account token from the pod’s filesystem and exchanging it for a Vault token based on the configured `VAULT_ROLE`.
   
2. **Vault Token & Policies**:  
   Once authenticated, a short-lived Vault token is stored in-memory. This token is used to list directories and insert secrets. The Vault policy associated with the role ensures only `create` operations on secrets are allowed, preventing unauthorized updates or deletions.
   
3. **Insert Secrets**:  
   Users access the web interface, select a directory (if applicable), provide a secret key and value (in JSON format), and submit the form. The backend calls Vault’s KV v2 `data` endpoints to store the secret.
   
4. **Listing Directories**:  
   The web interface can also list directories (folders) to guide users where to place their secrets. This is done through calling the `kv/metadata` endpoints with a LIST operation.

## Directory Structure

```bash
web-vault-secret-creator/
    app.py           # Flask application
    Dockerfile       # Docker image definition
    LICENSE          # License file
    README.md        # You are here
templates/
    index.html       # Simple front-end HTML template
```

Required Vault Policies
-----------------------

To ensure secure interaction with Vault, the Vault role must have a policy allowing the application to create secrets and list directories, but not to read or delete them. For example:

```hcl
# Allow creating secrets at any path under `kv/data/*`
path "kv/data/*" {
  capabilities = ["create"]
}

# Allow listing directories (metadata) at `kv/metadata/*`
path "kv/metadata/*" {
  capabilities = ["list"]
}
```

Vault Kubernetes Authentication Setup
-------------------------------------

You must configure Vault to trust the Kubernetes cluster and associate a role with the service account used by this application:

```bash
vault write auth/kubernetes/role/<YOUR_VAULT_ROLE_NAME> \
     bound_service_account_names=<YOUR_SERVICE_ACCOUNT_NAME> \
     bound_service_account_namespaces=<NAMESPACE> \
     policies=<YOUR_POLICY_NAME> \
     ttl=6000h
```

Replace `<YOUR_VAULT_ROLE_NAME>`, `<YOUR_SERVICE_ACCOUNT_NAME>`, `<NAMESPACE>`, and `<YOUR_POLICY_NAME>` with values that match your environment.

Environment Variables
---------------------

The application relies on the following environment variables:

*   **`VAULT_ADDR`**: The address (URL) of the Vault server. (e.g. `https://vault.default.svc:8200`)
*   **`VAULT_ROLE`**: The name of the Vault role configured for Kubernetes authentication.

Running the Application
-----------------------

### Locally (For Development/Testing)

**Prerequisites**:

*   Python 3.8+
*   `pip`
*   `curl`, `jq`

**Steps**:

1.  Install dependencies:
    
    
    `pip install flask`
    
2.  Set environment variables:
    
    
    `export VAULT_ADDR="https://your-vault.com" export VAULT_ROLE="your-role"`
    
3.  Run the app:
    
```bash
export VAULT_ADDR="https://your-vault.com"
export VAULT_ROLE="your-role"
```

> Note: Running locally without a valid Kubernetes token or Vault configuration may not authenticate properly. This is primarily intended to run inside a Kubernetes Pod.

### In Kubernetes

1.  **Build & Push the Image**:
    
    
    `docker build -t your-repo/web-vault-secret-creator:latest . docker push your-repo/web-vault-secret-creator:latest`
    
2.  **Deploy to Kubernetes**:
    
    *   Create a Deployment and Service for the application.
    *   Attach the required service account and ensure it has the necessary Vault role configured.
    *   Example snippet (not a full manifest):
        
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-vault-secret-creator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web-vault-secret-creator
  template:
    metadata:
      labels:
        app: web-vault-secret-creator
    spec:
      serviceAccountName: your-service-account
      containers:
        - name: web-vault-secret-creator
          image: your-repo/web-vault-secret-creator:latest
          env:
            - name: VAULT_ADDR
              value: "https://your-vault:8200"
            - name: VAULT_ROLE
              value: "your-role"
          ports:
            - containerPort: 5000
```
        
3.  **Access the UI**: Port forward or expose the service:

    
    `kubectl port-forward svc/web-vault-secret-creator 5000:5000`
    
    Open `http://localhost:5000` in your browser.
    

Usage Instructions
------------------

1.  Navigate to the web interface.
2.  Select a directory (project path) from the dropdown.
3.  Provide a secret key and value (in JSON format). For example:

    
    `{   "value": "my-secret-password" }`
    
4.  Click **"Create Secret in Vault"**.
5.  Upon success, the secret is now stored securely in Vault under the chosen path.

License
-------

This project is licensed under the [MIT License](LICENSE). You’re free to use, modify, and distribute this tool as you see fit.

Support and Contact
-------------------

For questions or issues, please open an Issue in the repository or contact the maintainer.