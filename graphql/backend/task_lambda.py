from __future__ import annotations
import json
import os
import uuid
import boto3
from typing import Protocol
from abc import abstractmethod
from dataclasses import dataclass, field, asdict
from enum import StrEnum
from typing import Optional
from datetime import datetime
import logging
import sys

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger()

# load environment variable
AWS_REGION = os.environ.get('AWS_REGION', "ap-southeast-2")
TASKS_TABLE = os.environ.get("TASKS_TABLE", "Tasks")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://host.docker.internal:4566")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "test")

# init dynamodb in coldstart, reduced retry
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# CONSTANTS_LITERALS
ERROR_TASK_ID_MISSING = "No Task ID provided"
ERROR_TASK_NOT_FOUND = "Task not found"


class TaskStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    TO_DO = "TO_DO"
    COMPLETED = "COMPLETED"


@dataclass
class Task:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = field(default=TaskStatus.TO_DO)
    description: Optional[str] = field(default=None)
    due_date: Optional[datetime] = field(default=None)


# utils
def prepare_dynamo_update_expression(task_to_update: dict):
    """
    prepare update statement, expression name and values
    for dynamodb update boto3 update
    """
    # init defaultdict(str)
    expr_values = {}
    expr_names = {}
    update_expr = "SET "

    for key, value in task_to_update.items():
        if key == "id":
            continue
        update_expr += f"#{key} = :{key}, "
        expr_names[f"#{key}"] = key
        expr_values[f":{key}"] = value

    # added trailing spaces before, remove afterwards
    update_expr = update_expr.rstrip(", ")
    return update_expr, expr_names, expr_values


def parse_payload(payload: dict):
    """
     parse appsync graphql payload,
     model may differ by schema and resolver's
     RequestMappingTemplate and ResponseMappingTemplate
     returns: field and arguments as tuple
    """
    info = payload.get("info", {})
    field = info.get("fieldName")
    args = payload.get("arguments", {})
    fields_and_args = f"fields {field} and arguments {args}"
    logger.info(fields_and_args)
    return field, args


class EventProcessor(Protocol):
    """
    processor to handle events
    """

    @abstractmethod
    def process(self, event: dict) -> dict:
        """
        process event based on type { Mutation, Query }
        """

    @abstractmethod
    def get_input(self, payload: dict):
        """
        get input from parsed payload
        depends on how payload is processed in appsync model resolver
        """


def get_task_table():
    table = dynamodb.Table(TASKS_TABLE)
    return table


class TaskCreateProcessor(EventProcessor):
    """
     event processor to handle single task creation
    """

    def process(self, args: dict) -> dict:
        try:
            task = Task(
                id=str(uuid.uuid4()),
                title=args.get("title"),
                description=args.get("description", ""),
                status=args.get("status", TaskStatus.TO_DO),
                due_date=args.get("due_date", None)
            )
            valid_task = asdict(task)
            table = get_task_table()
            table.put_item(Item=valid_task)
            return {"task": valid_task, "error": None}
        # catching generic exception, better to catch specific
        except Exception as ex:
            print("exception in TaskCreateProcessor", str(ex))
            return {"task": None, "error": {"message": str(ex)}}

    def get_input(self, args: dict):
        """
         get task attributes as kwargs from parsed argument
        """
        input_kwarg = args.get("input")
        return input_kwarg


class TaskRetrieveProcessor(EventProcessor):
    """
     event processor to handle single task retrival
    """

    def process(self, args: dict) -> dict:
        try:
            task_id = args.get("id", None)
            if task_id is None:
                return {"task": None,
                        "error": {"message": f"{ERROR_TASK_ID_MISSING}"}}
            table = get_task_table()
            task = table.get_item(Key={"id": task_id})
            if task is None or task.get("Item") is None:
                return {"task": None,
                        "error": {"message": f"{ERROR_TASK_NOT_FOUND} for {task_id}"}}
            return {"task": task.get("Item"), "error": None}
        except Exception as ex:
            print("exception in TaskCreateProcessor", str(ex))
            return {"task": None, "error": {"message": str(ex)}}

    def get_input(self, args: dict):
        """
         get id from parsed argument
        """
        task_id = args.get("id")
        input_kwarg = {"id": task_id}
        return input_kwarg


class TaskUpdateProcessor(EventProcessor):
    """
      event processor to update task
    """

    def process(self, args: dict) -> dict:
        try:
            task_id = args.get("id", None)
            if task_id is None:
                return {"task": None,
                        "error": {"message": f"{ERROR_TASK_ID_MISSING}"}}

            # check arg has valid keys, though appsync resolver filters them
            valid_keys = Task.__annotations__.keys()
            invalid_keys = set(args.keys()) - set(valid_keys)
            if invalid_keys:
                return {"task": None, "error": {"message": f"Invalid attributes: {list(invalid_keys)}"}}

            # get task
            task = TaskRetrieveProcessor().process(args)
            if task.get("error",None) is not None:
                return task

            expr_statement, expr_names, expr_values = prepare_dynamo_update_expression(args)
            table = get_task_table()
            response = table.update_item(
                Key={"id": task_id},
                UpdateExpression=expr_statement,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues="ALL_NEW"
            )
            updated_task = response.get("Attributes", {})
            return {"task": updated_task, "error": None}
        # TypeError, catch all exception instead
        except Exception as ex:
            print("exception in TaskUpdateProcessor", str(ex))
            return {"task": None, "error": {"message": str(ex)}}

    def get_input(self, args: dict):
        """
         get task attributes from parsed argument
        """
        input_kwarg = args.get("input")
        return input_kwarg


class TaskDeleteProcessor(EventProcessor):
    """
      event processor to delete task
    """

    def process(self, args):
        try:
            task_id = args.get("id")
            if not task_id:
                return {"task": None, "error": {"message": ERROR_TASK_ID_MISSING}}

            table = get_task_table()
            deleted_item = table.delete_item(
                Key={"id": task_id},
                ReturnValues="ALL_OLD"
            )
            deleted_task = deleted_item.get("Attributes")
            if deleted_task is None:
                return {"task": None, "error": {"message": f"{ERROR_TASK_NOT_FOUND} with ID {task_id}"}}

            return {"task": deleted_task, "error": None}
        except Exception as ex:
            print("exception in TaskDeleteProcessor", str(ex))
            return {"task": None, "error": {"message": str(ex)}}

    def get_input(self, args: dict):
        """
         get id from parsed argument
        """
        input_kwarg = {"id": args.get("id")}
        return input_kwarg


class TaskListProcessor(EventProcessor):
    """
    event processor to retrieve list of tasks, paginated by limit and next token
    """

    def process(self, args):
        # paginated by limit and token
        try:
            limit = int(args.get("limit", 10))
            next_token = args.get("nextToken", None)
            table_scan_params = {
                "Limit": limit
            }
            if next_token:
                prev_key = json.loads(next_token)
                table_scan_params["ExclusiveStartKey"] = prev_key

            table = get_task_table()
            data = table.scan(**table_scan_params)
            next_token = data.get("LastEvaluatedKey", None)
            if next_token:
                next_token = json.dumps(next_token)

            tasks = []
            for item in data.get("Items", []):
                tasks.append({"id": item["id"],
                              "description": item.get("description",""),
                              "title": item["title"],
                              "status": item["status"]})

            return {
                "tasks": tasks,
                "nextToken": next_token,
                "error": None
            }

        except Exception as ex:
            print("exception in TaskListProcessor", str(ex))
            return {"tasks": None, "nextToken": None, "error": {"message": str(ex)}}

    def get_input(self, args: dict):
        """
         get limit nextToken from parsed argument
        """
        input_kwarg = {
            "limit": args.get("limit"),
            "nextToken": args.get("nextToken"),
        }
        return input_kwarg


class UnknownTaskProcessor(EventProcessor):
    def process(self, args: dict) -> dict:
        return {"task": None,
                "error": {"message": "Unknown task event"}}

    def get_input(self, args: dict):
        """
         get id from parsed argument
        """
        return None


def processor_factory(event_type):
    match event_type:
        case "createTask":
            return TaskCreateProcessor()
        case "updateTask":
            return TaskUpdateProcessor()
        case "deleteTask":
            return TaskDeleteProcessor()
        case "getTask":
            return TaskRetrieveProcessor()
        case "listTasks":
            return TaskListProcessor()
        case _:
            return UnknownTaskProcessor()  # UnknownTaskProcessor()


def handler(event, context):
    print("raw event")
    print(event)
    print("event details:", json.dumps(event))
    sys.stdout.flush()
    # Extract the payload; if not available, use the event itself
    try:
        payload = event.get("payload", event)
        # TODO modify resolver template to simplify parsing
        # parse argument variables
        field, payload_args = parse_payload(payload)

        # get Query or Mutation processor based on field type
        processor = processor_factory(field)
        print(f" process: {str(processor.__class__)}")

        # parse the input for specific processor and process
        input_args = processor.get_input(payload_args)
        response = processor.process(input_args)

        logger.info(response)
        print(f"response {response}")
        return response
    except Exception as ex:
        print("exception in handler ", str(ex))
        return {"task": None, "error": {"message": str(ex)}}
