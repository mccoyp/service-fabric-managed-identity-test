# Manual Testing for Service Fabric Applications using Managed Identity with Azure.Identity in Python

Setup for a Service Fabric cluster and two apps, used for testing managed identity using Azure.Identity.

The `sfmitestsystem` and `sfmitestuser` directories contain mock applications that use Azure.Identity's `ServiceFabricCredential` to request and verify Key Vault access tokens. The former application uses a system-assigned managed identity to do so, and the latter application uses a user-assigned managed identity. Each application is set up using a Visual Studio project for basic scaffolding, a Docker image for running code, and an Azure resource template for deployment.

> **Note:** The code run by the applications comes from the `Dockerfile` in each, so adapting this sample to another language can be done by editing the Docker image each application uses. No other configuration changes are necessary if using Linux containers. To use Windows containers, you would need to edit the cluster configuration to run on Windows virtual machines (an example of a Windows configuration can be found [here](https://github.com/Azure/azure-quickstart-templates/tree/master/service-fabric-secure-cluster-5-node-1-nodetype)).

The `arm_templates` directory contains Azure resource templates for creating a Service Fabric cluster to host these applications as well as the application templates.

## Environment Requirements

> **Note:** All Azure resources used in the sample should be in the same region & resource group. This includes a managed identity, Key Vault, Service Fabric cluster, Azure Container Registry, and storage account.

- This sample assumes that Visual Studio 2019 is being used in a Windows environment.
- This sample requires access to an Azure subscription and required privileges to create resources.
- [Powershell and the Az library are needed to run the deployments in the sample.](https://docs.microsoft.com/en-us/powershell/azure/install-az-ps)
- [Azure CLI is used to deploy some resources.](https://docs.microsoft.com/cli/azure/install-azure-cli?view=azure-cli-latest)
- Docker is needed to build and push the sample containerized service. Docker should be using Linux containers for building the application images, but it should be using Windows containers when packaging the Service Fabric applications in Visual Studio.

## Setting up Prerequisite Resources

### Create a resource group

From a command prompt window, run
```
az login
az group create -n $RESOURCE_GROUP --location $LOCATION --subscription $SUBSCRIPTION_NAME
```

### Create a user-assigned managed identity

From your command prompt window, run
```
az identity create -g $RESOURCE_GROUP -n AdminUser
```

Make note of the identity's principal ID, to use in the next step. Also make note of its client ID for a later step.

### Create a key vault, certificate, and secret

Create your key vault:
```
az keyvault create -g $RESOURCE_GROUP -n $KEY_VAULT_NAME --sku standard
```

After creating the vault, create a self-signed certificate in it using the [Azure Portal](https://azure.portal.com/). You'll need to insert some of this certificate's properties into the cluster template later on.

Finally, create a secret in the key vault. It can have any name (e.g. "TestSecret") and any value (e.g. "TestValue"). This secret will just be accessed by the Service Fabric applications to verify that they can access a resource and read contents using their identities.

### Create an Azure Container Registry

From your command prompt window, run
```
az acr create -g $RESOURCE_GROUP -n $ACR_NAME --admin-enabled --sku basic
```

## Walkthrough

### Clone this repository

From a command prompt window, run
```
git clone https://github.com/mccoyp/service-fabric-managed-identity-test.git
cd service-fabric-managed-identity-test
```

### Create and publish a Docker image for each application

For this manual test, each application will use a Docker image to run managed identity tests. To make these images available to Service Fabric, you need to build and publish them by using the Dockerfiles in this sample.

First, you'll need to update the applications to target the correct resources.

1. Open `sfmitestsystem/sfmitestsystem-app/Dockerfile`.
2. Replace `<your vault URL>` with the vault URI of the key vault you created.
```Dockerfile
ENV AZURE_IDENTITY_TEST_VAULT_URL=<your vault URL>  # looks like https://<vault name>.vault.azure.net/
```
3. Open `sfmitestuser/sfmitestuser-app/Dockerfile`.
4. Replace `<your vault URL>` with the vault URI of the key vault you created, and replace `<AdminUser client ID>` with the client ID of the managed identity your created earlier.
```Dockerfile
ENV AZURE_IDENTITY_TEST_VAULT_URL=<your vault URL>  # looks like https://<vault name>.vault.azure.net/
ENV AZURE_IDENTITY_TEST_MANAGED_IDENTITY_CLIENT_ID=<AdminUser client ID>  # found in the managed identity overview
```

Now, build the images and push them to Azure Container Registry.

1. Ensure Docker is running and is using Linux containers.
2. Authenticate to ACR:
```
az acr login -n $ACR_NAME
```
3. Build the images:
```
docker build --no-cache -t $ACR_NAME.azurecr.io/sfmitestsystem sfmitestsystem/sfmitestsystem-app
docker build --no-cache -t $ACR_NAME.azurecr.io/sfmitestuser sfmitestuser/sfmitestuser-app
```
4. Publish the images:
```
docker push $ACR_NAME.azurecr.io/sfmitestsystem
docker push $ACR_NAME.azurecr.io/sfmitestuser
```

### Package each application

Your Service Fabric cluster will target each application by referencing a `.sfpkg` in a storage account you will create in the next section. First, we need to create these packages using the Visual Studio solutions provided in `sfmitestsystem` and `sfmitestuser`.

1. Open `sfmitestsystem/sfmitestsystem.sln` in Visual Studio 2019.
2. In `sfmitestsystem/ApplicationPackageRoot/sfmitestsystemfrontPkg/ApplicationManifest.xml`, fill in the values for your Azure Container Registry name and password in
```xml
<RepositoryCredentials AccountName="<ACR_NAME>" Password="<found in Access keys page of registry in Portal>" PasswordEncrypted="false"/>
```
3. In `sfmitestsystem/ApplicationPackageRoot/sfmitestsystemfrontPkg/ServiceManifest.xml`, replace `{ACR_NAME}` with your Azure Container Registry name in
```xml
<ImageName>{ACR_NAME}.azurecr.io/sfmitestsystem</ImageName>
```
4. [Build a package for the application](https://docs.microsoft.com/en-us/azure/service-fabric/service-fabric-package-apps#configure).
5. Go to the location of the package in File Explorer, select all items in the Debug folder, and compress them into a zip file.
6. Rename the zip file `sfmitestsystem.sfpkg`.
7. Repeat the above steps for `sfmitestuser`, replacing all instances of "system" in the instructions with "user".

### Deploy a managed identity-enabled cluster

At the time of writing, Service Fabric clusters must be deployed using the Azure Resource Manager in order to enable managed identity. Provided is a cluster ARM template that can be used to create a managed identity-enabled cluster once some required fields are completed. The template uses the cluster certificate provided by your key vault, creates a system-assigned identity, and enables the managed identity token service so deployed applications can access their identities.

To use the provided template:

1. Open `arm_templates/cluster.parameters.json` and complete the fields `clusterLocation`, `adminUserName`, `adminPassword`, `sourceVaultValue`, `certificateUrlValue`, and `certificateThumbprint`. Field descriptions will describe how they should be completed.
2. In `arm_templates/cluster.parameters.json`, change all instances of `sfmi-test` to a unique name, like `<myusername>-sfmi-test`. Also, change the values of `applicationDiagnosticsStorageAccountName` and `supportLogStorageAccountName` to be similarly unique, but without hyphens. This will help ensure the deployment resource names do not conflict with the names of other public resources.
3. Start the deployment by running from your Powershell window in the `arm_templates` directory:
```powershell
Connect-AzAccount
Select-AzSubscription -Subscription $Subscription
New-AzResourceGroupDeployment -TemplateParameterFile ".\cluster.parameters.json" -TemplateFile ".\cluster.template.json" -ResourceGroupName $ResourceGroupName
```

This will begin deployment of a Service Fabric cluster, as well as other necessary resources: a load balancer, public IP address, virtual machine scale set, storage account, and virtual network.

### Upload the application packages to a storage account

Two storage accounts were actually created in the previous step, but only one needs to store the `.sfpkg` files for the applications. Go to your resource group in the [Azure Portal](https://azure.portal.com) and open the storage account with the name corresponding to `applicationDiagnosticsStorageAccountName` from the previous step. Go to the "Containers" page and create a new container named "apps" -- be sure the set the public access level to Blob.

Open the apps container and upload the `.sfpkg` files you created earlier in the walkthrough. The container should now contain `sfmitestsystem.sfpkg` and `sfmitestuser.sfpkg`. Keep this page open to complete the next step.

### Deploy the applications

This sample also provides templates for deploying Service Fabric applications with Powershell.

To use the provided templates:

1. Open `arm_templates/sfmitestsystem.parameters.json` and complete the fields `clusterName`, `clusterLocation`, and `applicationPackageUrl`. `clusterName` and `clusterLocation` should match the name and location of the cluster you deployed earlier in the walkthrough. `applicationPackageUrl` is the URL of the `.sfpkg` you uploaded to a storage account in the previous step. To find the URL, click on `sfmitestsystem.sfpkg` in the Portal to view its properties.
2. Open `arm_templates/sfmitestuser.parameters.json` and complete the same fields, using the URL of `sfmitestuser.sfpkg` for `applicationPackageUrl`.
3. Start the deployment by running from your Powershell window in the `arm_templates` directory:
```powershell
New-AzResourceGroupDeployment -TemplateParameterFile ".\sfmitestsystem.parameters.json" -TemplateFile ".\sfmitestsystem.template.json" -ResourceGroupName $ResourceGroupName
New-AzResourceGroupDeployment -TemplateParameterFile ".\sfmitestuser.parameters.json" -TemplateFile ".\sfmitestuser.template.json" -ResourceGroupName $ResourceGroupName
```

### Give the applications access to your key vault

If the applications were accessed now, they would report an error. This is because their managed identities don't have permission to access secrets in the key vault you created. 

To grant them access:

1. Go to your key vault in the [Azure Portal](https://azure.portal.com).
2. Go to the "Access Policies" tab and click the "Add Access Policy" button. Select the secret management access template.
3. Click "None selected" to select a principal. Search for the name of your cluster, and an `sfmitestsystem` entry should appear in the list -- select this principal to give `sfmitestsystem`'s system-assigned managed identity access to your vault.
4. Click "Add" to add the access policy, and repeat steps 2 and 3. This time, search for the name of the user-assigned identity you created (`AdminUser`) for your principal. This will give `sfmitestuser`'s user-assigned managed identity access to your vault.
5. Remember to click "Save" at the top of the access policies page to submit these changes.

### Verify that the applications work

Once running on your cluster, the applications should each perform the same task: using a `ManagedIdentityCredential` to view the properties of your key vault's secret. One uses a system-assigned managed identity to do so, while the other uses a user-assigned managed identity. To verify that they have each done their job correctly, you can access the application logs in your cluster's Service Fabric Explorer page.

Verify in a browser:

1. Navigate to `http://<cluster name>.<location>.cloudapp.azure.com:19080/Explorer` (e.g. `http://sfmi-test.westus2.cloudapp.azure.com:19080/Explorer`).
2. Present the certificate you created in your key vault. You'll need to download the certificate from the [Azure Portal](https://portal.azure.com/) from your vault's Certificates page and [import it into your web browser](https://docs.digicert.com/manage-certificates/client-certificates-guide/manage-your-personal-id-certificate/windows-import-your-personal-id-certificate/google-chrome-import-your-personal-id/).
3. In the Explorer, you should see the applications running under the Applications tab. Otherwise, you may need to double check your deployment process.
4. Under the Nodes tab, expand each node tab to see if it hosts an application ("fabric:/sfmitestsystem" or "fabric:/sfmitestuser").
5. When you find an application entry, click the +-sign by the name to expand it. There should be a "code" entry -- click on that to bring up a page that has a "Container Logs" tab.
6. Go to the "Container Logs" tab to see the test output. The tests will re-run every so often, so you may have to watch the page for a short while to see the output. Verify that `test_managed_identity_live` shows `PASSED`.
