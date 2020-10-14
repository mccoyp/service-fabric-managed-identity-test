from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from flask import Flask

import os

app = Flask(__name__)

AZURE_KEY_VAULT_URL = ""  # fill in with your key vault's vault URI (found in Properties)


@app.route("/")
def home():
    credential = ManagedIdentityCredential()
    client = SecretClient(AZURE_KEY_VAULT_URL, credential, logging_enable=True)
    for _ in client.list_properties_of_secrets():
        pass
    return "Secret fetching succeeded"

@app.route("/identity_endpoint")
def identity_endpoint():
    return os.environ.get('IDENTITY_ENDPOINT', 'No value found for IDENTITY_ENDPOINT')

@app.route("/identity_header")
def identity_header():
    return os.environ.get('IDENTITY_HEADER', 'No value found for IDENTITY_HEADER')

@app.route("/identity_server_thumbprint")
def identity_server_thumbprint():
    return os.environ.get('IDENTITY_SERVER_THUMBPRINT', 'No value found for IDENTITY_SERVER_THUMBPRINT')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)