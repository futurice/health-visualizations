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

## Deploy to App Services

https://docs.microsoft.com/en-us/azure/app-service/containers/tutorial-custom-docker-image

### Create a Linux App Service plan

(Done already, no need to redo)

```
az appservice plan create --name laaketutkaAppServicePlan --resource-group laaketutka-prod --sku B1 --is-linux
```

### Create a web app

 ```   
az webapp create --resource-group laaketutka-prod --plan laaketutkaAppServicePlan --name laaketutka-app --deployment-container-image-name laaketutka.azurecr.io/health-visualizations:latest
 ```

### Add service principal access to acr and add it to the application


https://docs.microsoft.com/en-us/azure/container-registry/container-registry-auth-aci
https://github.com/MicrosoftDocs/azure-docs/blob/master/articles/container-registry/container-registry-tutorial-quick-task.md

For pulling the image inside the virtual server

```   
az webapp config container set --name laaketutka-app --resource-group laaketutka-prod --docker-custom-image-name laaketutka.azurecr.io/health-visualizations:latest --docker-registry-server-url https://laaketutka.azurecr.io --docker-registry-server-user <registry-username> --docker-registry-server-password <password>
```   

### Add Env variables

```  
az webapp config appsettings set --resource-group laaketutka-prod --name laaketutka-app --settings DATABASE_URL=postgres://username:password@host/dbname

az webapp config appsettings set --resource-group laaketutka-prod --name laaketutka-app --settings WEBSITES_PORT=8000

az webapp restart --resource-group laaketutka-prod --name laaketutka-app

```  


## That's it!

http://laaketutka-test-app.azurewebsites.net/

(PS in case you need environment variables then look at the link above, there's instructions)
