export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-southeast-2

export LOCALSTACK_HOST=localhost
export EDGE_PORT=4566

VENV := .venv
PYTHON := python3.11
PIP := $(VENV)/bin/pip
AWS_CLI := $(VENV)/bin/aws


install-venv-cli:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip -r requirements.txt


setup-s3:
	aws --endpoint-url=http://localhost:4566 s3 mb s3://graphql-datasource-lambda

put-graphql-schema-s3:
	aws --endpoint-url=http://localhost:4566 s3 cp schema.graphql s3://graphql-datasource-lambda/schema.graphql

zip-lambda:
	zip "backend/task_lambda.zip" "backend/task_lambda.py"

put-lambda-s3:
	python -m backend.lambda_to_s3

apply-cloudformation-stack:
	aws --endpoint-url=http://localhost:4566 cloudformation deploy \
  --template-file cloudformation.yaml \
  --stack-name irfan-appsync-stack \
  --capabilities CAPABILITY_IAM

get-appsync-apis:
	aws appsync list-graphql-apis

list-api-key:
	aws appsync list-api-keys \
    --api-id <appsync-app-id> \
    --endpoint-url=http://localhost:4566

create-api-key:
	aws appsync create-api-key --api-id 4030305f14f045abb611b374c8

get-appsync-data-sources:
	aws appsync list-data-sources --api-id 4030305f14f045abb611b374c8

export-graphql-schema:
	aws appsync  get-introspection-schema  --api-id <$appid> --format SDL irfanlocalgraph.graphql

list-query-resolvers:
	aws appsync list-resolvers --api-id 4030305f14f045abb611b374c8 --type-name Query

list-inline-policy:
	aws iam list-role-policies --role-name <rol_name> #from our stack LambdaSTSRole

tail-lambda-log:
	aws logs tail /aws/lambda/TaskResolverLambda --follow


create-appsync-test-graphqlapi:
	aws appsync create-graphql-api \
    --name "TestGraphQLAPI" \
    --authentication-type API_KEY

list-ssm-parameters:
	aws ssm describe-parameters
	aws ssm describe-parameters --query "Parameters[*].Name"

# if ssm store fails to get param in debugging localstack
push-ssm-param: # replace value with api id and arn to debug
	aws ssm put-parameter --name "/appsync/api-id" --value "956611f35d9b45b9953ca5d163" --type String
	aws ssm put-parameter --name "/appsync/lambda-datasource" --value "arn:aws:appsync:ap-southeast-2:000000000000:apis/956611f35d9b45b9953ca5d163/datasources/LambdaDataSource" --type String

debug-resolver: # get api id from cloudformation exports
	aws appsync create-resolver \
  --api-id af97907b4de44c02b53dea8f80 \
  --type-name "Query" \
  --field-name "getTask" \
  --data-source-name "LambdaDataSource" \
  --request-mapping-template file://request.vtl \
  --response-mapping-template file://response.vtl

remove-test-resolver: #
	aws appsync delete-resolver \
  --api-id af97907b4de44c02b53dea8f80 \
  --type-name "Query" \
  --field-name "getTask"


update-graphql-schema:
	aws appsync update-graphql-api \
    --api-id af97907b4de44c02b53dea8f80 \
    --name "TaskAppSyncAPI" \
    --authentication-type API_KEY \
    --endpoint-url=http://localhost:4566

create-schema:
	aws appsync start-schema-creation \
    --api-id af97907b4de44c02b53dea8f80 \
    --definition fileb://schema.graphql \
    --endpoint-url=http://localhost:4566

dump-schema:
	aws appsync  get-introspection-schema  --api-id af97907b4de44c02b53dea8f80 --format SDL irfanlocal.txt
