# Setting up Azure Web App Service



## Setup

Using subscription Laaketutka under FutuHosting, needs to first create storage and file share for the CLI to work at all.

Grant access to ACR etc for AD user (you)


## Create Docker image and push to Container registry

https://docs.microsoft.com/en-us/azure/container-registry/container-registry-get-started-docker-cli

First build the Docker image locally using (build_docker-script)[build_docker.sh].

Docker registry is already created to Azure Container Registries with the name of laaketutka.

### Pushing image to registry:

Login to Azure. Make sure you have access to ACR repository. (Configured )

```   
az login
az acr login --name laaketutka
```   

Then build the image and after that tag & push it:

```   
docker tag health-visualizations laaketutka.azurecr.io/health-visualizations
docker push laaketutka.azurecr.io/health-visualizations
```   


###############################
# NOTE: Following lines are for the test app, TODO deploy to prod
###############################

## Deploy to App Services

### Create a Linux App Service plan

https://docs.microsoft.com/en-us/azure/app-service/containers/tutorial-custom-docker-image


```
az appservice plan create --name laaketutkaAppServicePlan --resource-group laaketutka-prod --sku B1 --is-linux
```
{
  "adminSiteName": null,
  "freeOfferExpirationTime": "2019-04-29T11:53:42.793333",
  "geoRegion": "West Europe",
  "hostingEnvironmentProfile": null,
  "hyperV": false,
  "id": "/subscriptions/131d3990-b486-4266-aef6-c2d982ffeb63/resourceGroups/laaketutka-prod/providers/Microsoft.Web/serverfarms/laaketutkaAppServicePlan",
  "isSpot": false,
  "isXenon": false,
  "kind": "linux",
  "location": "West Europe",
  "maximumNumberOfWorkers": 3,
  "name": "laaketutkaAppServicePlan",
  "numberOfSites": 0,
  "perSiteScaling": false,
  "provisioningState": "Succeeded",
  "reserved": true,
  "resourceGroup": "laaketutka-prod",
  "sku": {
    "capabilities": null,
    "capacity": 1,
    "family": "B",
    "locations": null,
    "name": "B1",
    "size": "B1",
    "skuCapacity": null,
    "tier": "Basic"
  },
  "spotExpirationTime": null,
  "status": "Ready",
  "subscription": "131d3990-b486-4266-aef6-c2d982ffeb63",
  "tags": null,
  "targetWorkerCount": 0,
  "targetWorkerSizeId": 0,
  "type": "Microsoft.Web/serverfarms",
  "workerTierName": null
}

### Create a web app

 ```   
az webapp create --resource-group laaketutka-prod --plan laaketutkaAppServicePlan --name laaketutka-test-app --deployment-container-image-name paasovaara/azure-test:latest
 ```

 {
   "adminSiteName": null,
   "freeOfferExpirationTime": "2019-04-29T11:53:42.793333",
   "geoRegion": "West Europe",
   "hostingEnvironmentProfile": null,
   "hyperV": false,
   "id": "/subscriptions/131d3990-b486-4266-aef6-c2d982ffeb63/resourceGroups/laaketutka-prod/providers/Microsoft.Web/serverfarms/laaketutkaAppServicePlan",
   "isSpot": false,
   "isXenon": false,
   "kind": "linux",
   "location": "West Europe",
   "maximumNumberOfWorkers": 3,
   "name": "laaketutkaAppServicePlan",
   "numberOfSites": 0,
   "perSiteScaling": false,
   "provisioningState": "Succeeded",
   "reserved": true,
   "resourceGroup": "laaketutka-prod",
   "sku": {
     "capabilities": null,
     "capacity": 1,
     "family": "B",
     "locations": null,
     "name": "B1",
     "size": "B1",
     "skuCapacity": null,
     "tier": "Basic"
   },
   "spotExpirationTime": null,
   "status": "Ready",
   "subscription": "131d3990-b486-4266-aef6-c2d982ffeb63",
   "tags": null,
   "targetWorkerCount": 0,
   "targetWorkerSizeId": 0,
   "type": "Microsoft.Web/serverfarms",
   "workerTierName": null
 }
 markus@Azure:~$ az webapp create --resource-group laaketutka-prod --plan laaketutkaAppServicePlan --name test-app --deployment-container-image-name paasovaara/azure-test:latest
 Website with given name test-app already exists.
 markus@Azure:~$ az webapp create --resource-group laaketutka-prod --plan laaketutkaAppServicePlan --name laaketutka-test-app --deployment-container-image-name paasovaara/azure-test:latest
 {
   "availabilityState": "Normal",
   "clientAffinityEnabled": true,
   "clientCertEnabled": false,
   "cloningInfo": null,
   "containerSize": 0,
   "dailyMemoryTimeQuota": 0,
   "defaultHostName": "laaketutka-test-app.azurewebsites.net",
   "enabled": true,
   "enabledHostNames": [
     "laaketutka-test-app.azurewebsites.net",
     "laaketutka-test-app.scm.azurewebsites.net"
   ],
   "ftpPublishingUrl": "ftp://waws-prod-am2-137.ftp.azurewebsites.windows.net/site/wwwroot",
   "hostNameSslStates": [
     {
       "hostType": "Standard",
       "ipBasedSslResult": null,
       "ipBasedSslState": "NotConfigured",
       "name": "laaketutka-test-app.azurewebsites.net",
       "sslState": "Disabled",
       "thumbprint": null,
       "toUpdate": null,
       "toUpdateIpBasedSsl": null,
       "virtualIp": null
     },
     {
       "hostType": "Repository",
       "ipBasedSslResult": null,
       "ipBasedSslState": "NotConfigured",
       "name": "laaketutka-test-app.scm.azurewebsites.net",
       "sslState": "Disabled",
       "thumbprint": null,
       "toUpdate": null,
       "toUpdateIpBasedSsl": null,
       "virtualIp": null
     }
   ],
   "hostNames": [
     "laaketutka-test-app.azurewebsites.net"
   ],
   "hostNamesDisabled": false,
   "hostingEnvironmentProfile": null,
   "httpsOnly": false,
   "hyperV": false,
   "id": "/subscriptions/131d3990-b486-4266-aef6-c2d982ffeb63/resourceGroups/laaketutka-prod/providers/Microsoft.Web/sites/laaketutka-test-app",
   "identity": null,
   "isDefaultContainer": null,
   "isXenon": false,
   "kind": "app,linux,container",
   "lastModifiedTimeUtc": "2019-03-30T11:58:41.520000",
   "location": "West Europe",
   "maxNumberOfWorkers": null,
   "name": "laaketutka-test-app",
   "outboundIpAddresses": "52.233.175.59,52.174.167.45,40.68.252.87,52.174.162.33,52.178.24.39",
   "possibleOutboundIpAddresses": "52.233.175.59,52.174.167.45,40.68.252.87,52.174.162.33,52.178.24.39,51.145.141.166,51.144.249.40",
   "repositorySiteName": "laaketutka-test-app",
   "reserved": true,
   "resourceGroup": "laaketutka-prod",
   "scmSiteAlsoStopped": false,
   "serverFarmId": "/subscriptions/131d3990-b486-4266-aef6-c2d982ffeb63/resourceGroups/laaketutka-prod/providers/Microsoft.Web/serverfarms/laaketutkaAppServicePlan",
   "siteConfig": null,
   "slotSwapStatus": null,
   "state": "Running",
   "suspendedTill": null,
   "tags": null,
   "targetSwapSlot": null,
   "trafficManagerHostNames": null,
   "type": "Microsoft.Web/sites",
   "usageState": "Normal"
}

## That's it!

http://laaketutka-test-app.azurewebsites.net/

(PS in case you need environment variables then look at the link above, there's instructions)
