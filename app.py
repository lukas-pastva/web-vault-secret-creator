import os
import subprocess
from flask import Flask, request, jsonify, render_template
import logging
import json

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Environment variables
VAULT_ADDR = os.environ['VAULT_ADDR']
VAULT_ROLE = os.environ['VAULT_ROLE']
VAULT_TOKEN = None

def authenticate_with_vault():
    global VAULT_TOKEN
    jwt_token_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'
    with open(jwt_token_path, 'r') as token_file:
        jwt_token = token_file.read().strip()

    login_cmd = f"curl -s --request POST --data '{{\"jwt\": \"{jwt_token}\", \"role\": \"{VAULT_ROLE}\"}}' {VAULT_ADDR}/v1/auth/kubernetes/login"
    login_response = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)

    if login_response.returncode == 0 and "client_token" in login_response.stdout:
        VAULT_TOKEN = subprocess.run("echo '{}' | jq -r '.auth.client_token'".format(login_response.stdout), shell=True, capture_output=True, text=True).stdout.strip()
        app.logger.debug(f"Vault authentication successful. Token: {VAULT_TOKEN[:4]}****")
    else:
        app.logger.error(f"Vault authentication failed. Response: {login_response.stdout}, Error: {login_response.stderr}")

authenticate_with_vault()

@app.route('/')
def index():
    return render_template('index.html')

def recursive_list_secrets(parent_path='', directories_only=False):
    list_cmd = f"curl -s --header \"X-Vault-Token: {VAULT_TOKEN}\" -X LIST {VAULT_ADDR}/v1/kv/metadata/{parent_path}"
    list_response = subprocess.run(list_cmd, shell=True, capture_output=True, text=True)
    items = []

    if list_response.returncode == 0:
        try:
            response_data = json.loads(list_response.stdout)
            keys = response_data.get('data', {}).get('keys', [])
            for key in keys:
                if key.endswith('/'):
                    # It's a folder
                    if directories_only:
                        # If only directories are needed, add to the list
                        items.append(f"{parent_path}{key}")
                    # Recurse into the directory
                    items.extend(recursive_list_secrets(f"{parent_path}{key}", directories_only))
                elif not directories_only:
                    # It's a secret, and if secrets are needed, add its path to the list
                    items.append(f"{parent_path}{key}")
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON parsing error: {str(e)}")
    else:
        app.logger.error(f"Failed to list items at path: '{parent_path}'. Response: {list_response.stderr}")

    return items

@app.route('/list-secrets', methods=['GET'])
def list_secrets():
    directories_only = request.args.get('directories_only', 'false').lower() == 'true'
    parent_path = request.args.get('parent', '')
    app.logger.debug(f"Attempting to list items at path: '{parent_path}' with token prefix: {VAULT_TOKEN[:4]}****, directories only: {directories_only}")
    try:
        items = recursive_list_secrets(parent_path, directories_only)
        return jsonify({"directories" if directories_only else "secrets": items}), 200
    except Exception as e:
        app.logger.error(f"Error listing items recursively at path: '{parent_path}'. Exception: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/store-secret', methods=['POST'])
def store_secret():
    req_data = request.get_json()
    secret_path = req_data.get('path')
    secret_data = req_data.get('data')

    if not secret_path or not secret_data:
        return jsonify({"success": False, "error": "Missing path or data"}), 400

    vault_payload = json.dumps({"data": secret_data})

    store_cmd = [
        "curl", "-s",
        "--header", f"X-Vault-Token: {VAULT_TOKEN}",
        "--request", "POST",
        "--data", vault_payload,
        f"{VAULT_ADDR}/v1/kv/data/{secret_path}"
    ]

    app.logger.debug(f"store_cmd: {store_cmd}")

    store_response = subprocess.run(store_cmd, capture_output=True, text=True)

    if store_response.returncode == 0:
        return jsonify({"success": True}), 200
    else:
        app.logger.error(f"Failed to store secret at path: '{secret_path}'. Response: {store_response.stderr}")
        return jsonify({"success": False, "error": store_response.stderr}), 500


if __name__ == '__main__':
    app.run(debug=True)
