#### POC: graphQL integration using aws AppSync, lambda and dynamodb

![Uploading appsync_infra.png…]()



```
 tech-stack: aws appsync graphql, lambda (python 11) as resolver, dynamodb as store
 * Appsync for scalable graphql api
 * API Key for authentication
 * Lambda as datasource 
 * Dynamodb as Storage
 * Cloudformation to build the infra stacks
 * Localstack to test end to end in local machine
 
OS ENV or SSM PARAM secrets:
example for localstacL

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-southeast-2
export LOCALSTACK_HOST=localhost
export EDGE_PORT=4566
 
```

GraphQL API for a simple task management application. 
The API will allow users to:
* Task Creation: 
  Each task should have following attributes: 
  title, description (optional), due date (optional), 
  and status (e.g., "To Do," "In Progress," "Completed").

* List of Task ID Retrieval 

* Retrieve specific task by ID

* Task Update. Users should be able to modify any of the task attributes.

* Task Deletion


``` 
- scripts:
# deploy the base and resolver stack, boilerplate
graphql/deploy.sh 
Makefile 
```
WIP Enhancement:
- distinct IAM role and policy attachment,
- distinct cloudformation stack for resource, iam roles, resolver
- export parameters in SSM parameter
- include put object file:// zip to s3 as appsync datasource  
- include s3 in cloud formation stack
- add distinct datasource for each mutation
- CDN cache
- Cloudwatch dashboard

#### local development : scripts in Makefile
- create s3 bucket 
- put lambda zip into s3
- put graphql schema into s3
- create base stack: appsync, iamrole, dynamodb, lambda
- create resolver stack: attach python lambda as mutation resolver 
```bash
unit-tests:
    pytest -s -v backend/test
    
setup-s3:
	aws --endpoint-url=http://localhost:4566 s3 mb s3://graphql-datasource-lambda

put-graphql-schema-s3:
	aws --endpoint-url=http://localhost:4566 s3 cp schema.graphql s3://graphql-datasource-lambda/schema.graphql

put-lambda-zip-file-to-s3:
   python -m graphql.backend.lambda_to_s3 
  
apply-base-infra: 
# deploy appsync, lambda, dynamodb, iam role and attach policy
# export appsync api id, lambda arn, apikey for resolver

   aws --endpoint-url=http://localhost:4566 cloudformation deploy \
  --template-file base_stack.yaml \
  --stack-name base-stack \
  --capabilities CAPABILITY_IAM

 # deploy resolver lambda for appsync
apply-resolver-infra:
  aws --endpoint-url=http://localhost:4566 cloudformation deploy \
  --template-file resolver_stack.yaml \
  --stack-name resolver-stack \
  --capabilities CAPABILITY_IAM
 
appsync-create-apikey
  aws appsync list-graphql-apis
  aws appsync create-api-key --api-id <GRAPHQL_APP_ID>
  
appsync-list-resolvers
  aws appsync list-resolvers --api-id <GRAPHQL_APP_ID> --type-name <Mutation | Query>

observe-lambda-logs
  aws logs tail /aws/lambda/TaskResolverLambda --follow
```
kindly reach out for technical discussion and alternate solutions.

#### Regards: geass.of.code@gmail.com 


