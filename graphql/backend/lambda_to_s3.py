import boto3
import json


# Configure the S3 client to use LocalStack's endpoint
s3_client = boto3.client('s3', endpoint_url='http://localhost:4566', region_name='us-east-1')


# bucket_name = 'raphql-datasource-lambda'
# zip_file = 'task_lambda.zip'
# object_name = 'task_lambda.zip'

def create_bucket(bucket_name):
    # Create bucket if it doesn't exist
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket {bucket_name} already exists.")


def upload_zip_file(zip_file, bucket_name, object_name):
    # Upload the ZIP file to S3
    s3_client.upload_file(zip_file, bucket_name, object_name)
    print(f"Uploaded {zip_file} to s3://{bucket_name}/{object_name}")


def invoke_lambda_mock():
    lambda_client = boto3.client('lambda', endpoint_url="http://localhost:4566")
    payload = {
        "field": "createTask",
        "query": "mutation CreateTask($input: CreateTaskInput!) { createTask(input: $input) { id title description due_date status } }",
        "arguments": {
                "title": "First Task",
                "description": "This is the first task",
                "due_date": "2025-03-04T12:00:00Z",
                "status": "TO_DO"
            }
    }

    response = lambda_client.invoke(
        FunctionName="TaskResolverLambda",
        Payload=json.dumps(payload)
    )
    payload = response["Payload"].read().decode("utf-8")
    response_dict = json.loads(payload)
    print(json.dumps(response_dict, indent=2))

    print(response)


def check_dynamodb_conn():
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url="http://host.docker.internal:4566",
            region_name="ap-southeast-2",
            # load it from env
            #aws_access_key_id="test",
           # aws_secret_access_key="test"
        )
        table = dynamodb.Table("Tasks")
        table.get_item(Key={"1"})
    except Exception as ex:
        print("EXCEPTION in dynamodb")
        print(str(ex))

if __name__ == "__main__":

    bucket_name = 'graphql-datasource-lambda'
    zip_file = "task_lambda.zip"
    object_name = 'task_lambda.zip'
    upload_zip_file(zip_file, bucket_name, object_name)
    #invoke_lambda_mock()
    #check_dynamodb_conn()

