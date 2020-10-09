from flask import Flask
import requests
import time
import os

app = Flask(__name__)


@app.route("/")
def home():
    identity_endpoint = os.environ.get('IDENTITY_ENDPOINT', None)
    api_version = "2019-07-01-preview"
    resource = "https://vault.azure.net/"
    secret = os.environ.get("IDENTITY_HEADER", None)
    if identity_endpoint and secret:
        url = "{}?api-version={}&resource={}".format(identity_endpoint, api_version, resource)
        header = {"Secret": secret}
        req = requests.request('GET', url, headers=header, verify=False)
        token_response = req.json()

        access_token = token_response.get("access_token", None)
        if access_token is None or len(access_token) == 0:
            return "Token request failed"

        expires_on = token_response.get("expires_on", None)
        now = time.time()
        if expires_on is None or now > expires_on:
            return "Token request failed"

        resource = token_response.get("resource", None)
        if resource is None or resource != "https://vault.azure.net/":
            return "Token request failed"

        token_type = token_response.get("token_type", None)
        if token_type is None or token_type != "Bearer":
            return "Token request failed"
        
        return "Token request succeeded"
    return "Managed identity environment variables not found"

@app.route("/all")
def all():
    result = os.environ.keys()
    if result:
        return str(result)

@app.route("/identity_endpoint")
def identity_endpoint():
    return os.environ.get('IDENTITY_ENDPOINT', 'No value found for IDENTITY_ENDPOINT')

@app.route("/identity_header")
def identity_header():
    return os.environ.get('IDENTITY_HEADER', 'No value found for IDENTITY_HEADER')

@app.route("/identity_server_thumbprint")
def identity_server_thumbprint():
    return os.environ.get('IDENTITY_SERVER_THUMBPRINT', 'No value found for IDENTITY_SERVER_THUMBPRINT')

@app.route("/helloworld")
def helloworld():
    return "Hello world!"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)