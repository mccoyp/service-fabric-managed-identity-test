# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
ARG PYTHON_VERSION=2.7

# docker can't tell when the repo has changed and will therefore cache this layer
FROM alpine/git as repo
RUN git clone https://github.com/mccoyp/azure-sdk-for-python --single-branch --branch sfmi --depth 1 /azure-sdk-for-python

# Use an official Python runtime as a base image
FROM python:${PYTHON_VERSION}-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Install identity, core, and secrets
COPY --from=repo /azure-sdk-for-python/sdk/identity /sdk/identity
COPY --from=repo /azure-sdk-for-python/sdk/core/azure-core /sdk/core/azure-core
COPY --from=repo /azure-sdk-for-python/sdk/keyvault/azure-keyvault-secrets /sdk/keyvault/azure-keyvault-secrets

RUN pip install /sdk/identity/azure-identity
RUN pip install /sdk/core/azure-core
RUN pip install /sdk/keyvault/azure-keyvault-secrets

# Make port 443 available to the world outside this container
EXPOSE 443

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python", "app.py"]