export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-southeast-2

export LOCALSTACK_HOST=localhost
export EDGE_PORT=4566

aws --endpoint-url=http://localhost:4566 cloudformation deploy \
  --template-file base_stack.yaml \
  --stack-name base-stack \
  --capabilities CAPABILITY_IAM

aws --endpoint-url=http://localhost:4566 cloudformation deploy \
  --template-file resolver_stack.yaml \
  --stack-name resolver-stack \
  --capabilities CAPABILITY_IAM

aws cloudformation list-stack-resources --stack-name my-app-stack --endpoint-url=http://localhost:4566

aws appsync list-graphql-apis --endpoint-url=http://localhost:4566 | grep "apiId"