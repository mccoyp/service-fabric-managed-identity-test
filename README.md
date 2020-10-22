# Manual Testing for Service Fabric Applications using Managed Identity with Azure.Identity

Setup for a Service Fabric cluster and two apps, used for testing managed identity using Azure.Identity.

`sfmitestsystem` and `sfmitestuser` are mock applications that use Azure.Identity's ServiceFabricCredential to request and verify Key Vault access tokens. The former application uses a system-assigned managed identity to do so, and the latter application uses a user-assigned managed identity.

The `ResourceManagement` directory contains Azure resource templates for creating a Service Fabric cluster to host these applications as well as the application templates.

## Environment Requirements

> **Note:** All Azure resources used in the sample should be in the same region & resource group. This includes a managed identity, Key Vault, Service Fabric cluster, and storage account.

- This sample assumes that Visual Studio 2019 is being used in a Windows environment.
- This sample requires access to an Azure subscription and required privileges to create resources
- [Powershell and the Az library are needed to run the deployments in the sample.](https://docs.microsoft.com/en-us/powershell/azure/install-az-ps)
- Docker is needed to build and push the sample containerized service. Docker should be using Linux containers for building the application images, but it should be using Windows containers when packaging the Service Fabric applications in Visual Studio.

## Setting up Prerequisite Resources

### Create or select a resource group

From an elevated Powershell window, run
```powershell
Connect-AzAccount
Select-AzSubscription -Subscription $Subscription
# If you do not already have a resource group to create resources from this walkthrough:
New-AzResourceGroup -Name $ResourceGroupName -Location $Location
```

### Create a key vault, certificate, and secret

Using the [Azure Portal](https://azure.portal.com), create a key vault. Select "Create a resource", search for "Key Vault", and create your resource. Be sure to enable access to Azure Virtual Machines for deployment as well as Azure Resource Manager for template deployment. 

After creating the vault, create a self-signed certificate in it. You'll need to insert some of this certificate's properties into the cluster template later on.

Finally, create a secret in the key vault. It can have any name (e.g. "TestSecret") and any value (e.g. "TestValue"). This secret will just be accessed by the Service Fabric applications to verify that they can access a resource and read contents using their identities.

[//]: # (If Azure Container Registry should be used instead of Docker Hub, there should also be instructions to set up a registry here.)

### Create a user-assigned managed identity

From your Powershell window, run
```powershell
Install-Module -Name Az.ManagedServiceIdentity
New-AzUserAssignedIdentity -ResourceGroupName $ResourceGroupName -Name "AdminUser"
```

## Walkthrough

### Clone this repository

From a command prompt window, run
```
git clone https://github.com/mccoyp/service-fabric-managed-identity-test.git
cd service-fabric-managed-identity-test
```

### Create and publish a Docker image for each application

For this manual test, each application will be a simple Flask app. These applications are Linux container images that will be used by the Service Fabric applications you will deploy in this walkthrough. To make these images available to Service Fabric, you need to build and publish them by using the Dockerfiles in this sample.

First, you'll need to update the applications to target the correct resources.

1. Open `sfmitestsystem/sfmitestsystem-app/app.py`.
2. Complete the field `AZURE_KEY_VAULT_URL` with the vault URI of the key vault you created.
```python
AZURE_KEY_VAULT_URL = ""  # fill in with your key vault's vault URI (found in Properties)
```
3. Open `sfmitestuser/sfmitestuser-app/app.py` and repeat step 2.

To build the images:

1. Ensure Docker is running and is using Linux containers.
2. In your command prompt window, run
```
docker build -t sfmitestsystem sfmitestsystem/sfmitestsystem-app
docker build -t sfmitestuser sfmitestuser/sfmitestuser-app
```

To publish the images:

1. Create an account on Docker Hub, or choose an existing one.
2. Tag your docker images. In your command prompt window, run
```
docker tag sfmitestsystem <account name>/sfmitestsystem
docker tag sfmitestuser <account name>/sfmitestuser
```
3. Publish your docker images. In your command prompt window, run
```
docker publish <account name>/sfmitestsystem
docker publish <account name>/sfmitestuser
```

### Package each application

Your Service Fabric cluster will target each application by referencing a `.sfpkg` in a storage account you will create in the next section. First, we need to create these packages using the Visual Studio solutions provided in `sfmitestsystem` and `sfmitestuser`.

1. Open `sfmitestsystem/sfmitestsystem.sln` in Visual Studio 2019.
2. In `sfmitestsystem/ApplicationPackageRoot/sfmitestsystemfrontPkg/ServiceManifest.xml`, replace `{account name}` with your Docker Hub account name in
```xml
<ImageName>{account name}/sfmitestsystem</ImageName>
```
3. [Build a package for the application](https://docs.microsoft.com/en-us/azure/service-fabric/service-fabric-package-apps#configure).
4. Go to the location of the package in File Explorer, select all items in the Debug folder, and compress them into a zip file.
5. Rename the zip file `sfmitestsystem.sfpkg`.
6. Repeat the above steps for `sfmitestuser`, replacing all instances of "system" with "user".

### Deploy a managed identity-enabled cluster

At the time of writing, Service Fabric clusters must be deployed using the Azure Resource Manager in order to enable managed identity. Provided is a cluster ARM template that can be used to create a managed identity-enabled cluster once some required fields are completed. The template uses the cluster certificate provided by your key vault, creates a system-assigned identity, and enables the managed identity token service so deployed applications can access their identities.

To use the provided template:

1. Open `ResourceManagement/cluster.parameters.json` and complete the fields `clusterLocation`, `adminUserName`, `adminPassword`, `sourceVaultValue`, `certificateUrlValue`, and `certificateThumbprint`. Field descriptions will describe how they should be completed.
2. In `ResourceManagement/cluster.parameters.json`, change all instance of `sfmi-test` to a unique name, like `<myusername>-sfmi-test`. Also, change the values of `applicationDiagnosticsStorageAccountName` and `supportLogStorageAccountName` to be similarly unique, but without hyphens. This will help ensure the deployment resource names do not conflict with the names of other public resources.
3. Start the deployment by running from your Powershell window in the `ResourceManagement` directory:
```powershell
New-AzResourceGroupDeployment -TemplateParameterFile ".\cluster.parameters.json" -TemplateFile ".\cluster.template.json" -ResourceGroupName $ResourceGroupName
```

This will begin deployment of a Service Fabric cluster, as well as other necessary resources: a load balancer, public IP address, virtual machine scale set, storage account, and virtual network.

### Upload the application packages to a storage account

Two storage accounts were actually created in the previous step, but only one needs to store the `.sfpkg` files for the applications. Go to your resource group in the [Azure Portal](https://azure.portal.com) and open the storage account with the name corresponding to `applicationDiagnosticsStorageAccountName` from the previous step. Go to the "Containers" page and create a new container named "apps" -- be sure the set the public access level to Blob.

Open the apps container and upload the `.sfpkg` files you created earlier in the walkthrough. The container should now contain `sfmitestsystem.sfpkg` and `sfmitestuser.sfpkg`. Keep this page open to complete the next step.

### Deploy the applications

This sample also provides templates for deploying Service Fabric applications with Powershell.

To use the provided templates:

1. Open `ResourceManagement/sfmitestsystem.parameters.json` and complete the fields `clusterName`, `clusterLocation`, and `applicationPackageUrl`. `clusterName` and `clusterLocation` should match the name and location of the cluster you deployed earlier in the walkthrough. `applicationPackageUrl` is the URL of the `.sfpkg` you uploaded to a storage account in the previous step. To find the URL, click on `sfmitestsystem.sfpkg` in the Portal to view its properties.
2. Open `ResourceManagement/sfmitestuser.parameters.json` and complete the same fields, using the URL of `sfmitestuser.sfpkg` for `applicationPackageUrl`.
3. Start the deployment by running from your Powershell window in the `ResourceManagement` directory:
```powershell
New-AzResourceGroupDeployment -TemplateParameterFile ".\sfmitestsystem.parameters.json" -TemplateFile ".\sfmitestsystem.template.json" -ResourceGroupName $ResourceGroupName
New-AzResourceGroupDeployment -TemplateParameterFile ".\sfmitestuser.parameters.json" -TemplateFile ".\sfmitestuser.template.json" -ResourceGroupName $ResourceGroupName
```

### Give the applications access to your key vault

If the applications were accessed now, they would report an error. This is because their managed identities don't have permission to access secrets in the key vault you created. 

To grant them access:

1. Go to your key vault in the [Azure Portal](https://azure.portal.com).
2. Go to the "Access Policies" tab and click the "Add Access Policy" button. Select the key, secret, & certificate management access template.
3. Click "None selected" to select a principal. Search for the name of your cluster, and an `sfmitestsystem` entry should appear in the list -- select this principal to give `sfmitestsystem`'s system-assigned managed identity access to your vault.
4. Click "Add" to add the access policy, and repeat steps 2 and 3. This time, search for the name of the user-assigned identity you created (`AdminUser`) for your principal. This will give `sfmitestuser`'s user-assigned managed identity access to your vault.
5. Remember to click "Save" at the top of the access policies page to submit these changes.

### Verify that the applications work

Once running on your cluster, the applications should each perform the same task: using a `ManagedIdentityCredential` to view the properties of your key vault's secret. One uses a system-assigned managed identity to do so, while the other uses a user-assigned managed identity. To verify that they have each done their job correctly, you can access the applications' front-end web endpoints in a browser or by using [Curl](https://curl.haxx.se/docs/httpscripting.html). The applications will have the same URL but can be accessed through different ports: port 80 for the system-assigned identity application, and port 443 for the user-assigned identity application.

Verify in a browser:

1. Navigate to `http://<cluster name>.<cluster location>.cloudapp.azure.com:<port>`. For example, to access the application using system-assigned managed identity in a cluster named `sfmi-test` in `westus2`, you would navigate to `http://sfmi-test.westus2.cloudapp.azure.com:80`.
2. If the application is running successfully, the page will read `Secret fetching succeeded`. The application will otherwise throw an error if it couldn't access your key vault's secret.

Verify with Curl:

1. In a command prompt window, run the following command with parameters set as described above
```
curl http://<cluster name>.<cluster location>.cloudapp.azure.com:<port>
```
2. If the application is running successfully, the the page will read `Secret fetching succeeded`. The application will otherwise throw an error if it couldn't access your key vault's secret.
