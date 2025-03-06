from unittest.mock import patch, MagicMock

from graphql.backend.task_lambda import processor_factory, TaskCreateProcessor, TaskRetrieveProcessor, \
    TaskUpdateProcessor, prepare_dynamo_update_expression, parse_payload


@patch("graphql.backend.task_lambda.get_task_table", return_value=MagicMock())
@patch("graphql.backend.task_lambda.boto3.resource", return_value=MagicMock())
def test_task_create_processor(boto_mock, table_mock):
    # test TaskCreateProcessor
    table_mock.put_item = MagicMock()
    processor = processor_factory("createTask")
    assert isinstance(processor, TaskCreateProcessor) is True
    inp = {'title': 'Sample Task',
           'description': 'This is a sample task',
           'due_date': '2025-03-04T12:00:00Z',
           'status': 'TO_DO'}

    resp = processor.process(inp)
    resp = resp.get("task")
    assert resp.get("title") == "Sample Task"
    assert resp.get("status") == "TO_DO"


@patch("graphql.backend.task_lambda.get_task_table", return_value=MagicMock())
@patch("graphql.backend.task_lambda.boto3.resource", return_value=MagicMock())
def test_task_retrieve_processor(boto_mock, table_mock):
    # test Retrival of task by TaskRetrieveProcessor
    table_mock.get_item = MagicMock()
    processor = processor_factory("getTask")
    assert isinstance(processor, TaskRetrieveProcessor) is True

    resp = processor.process(dict({"id": 1}))

    assert resp.get("error") is None


@patch("graphql.backend.task_lambda.get_task_table", return_value=MagicMock())
@patch("graphql.backend.task_lambda.boto3.resource", return_value=MagicMock())
def test_update_processor(boto_mock, table_mock):
    # test update of task by TaskRetrieveProcessor
    table_mock.update_item = MagicMock(return_value={"Attributes": {"id": "101", "title": "test task"}})
    table_mock.get_item = MagicMock(return_value={"Item": {"id": "101", "title": "test task"}})
    processor = processor_factory("updateTask")
    assert isinstance(processor, TaskUpdateProcessor) is True
    resp = processor.process(dict({"id": "101", "title": "updated title", "status": "IN_PROGRESS"}))
    assert resp.get("error") is None


def test_prepare_update_statement():
    # test prepare update statement for dynamo
    inp = dict({"id": "101", "title": "updated title", "status": "IN_PROGRESS"})
    statement, names, values = prepare_dynamo_update_expression(inp)
    expected_statement = "SET #title = :title, #status = :status"
    expected_names = {'#title': 'title', '#status': 'status'}
    expected_values = {':title': 'updated title', ':status': 'IN_PROGRESS'}
    assert statement == expected_statement
    assert names == expected_names
    assert values == expected_values


def test_parse_payload_create_task():
    payload = {'stash': {},
               'arguments': {
                   'input': {'title': 'First Sample Task', 'description': 'This is a sample task description.',
                             'due_date': '2025-12-31T23:59:59Z', 'status': 'TO_DO'}}, 'identity': None,
               'info': {'fieldName': 'createTask', 'parentTypeName': 'Mutation', 'variables': {
                   'input': {'title': 'Test Task', 'description': 'Test description.',
                             'due_date': '2025-12-31T23:59:59Z', 'status': 'TO_DO'}},
                        'selectionSetList': ['task', 'task/id', 'task/title', 'task/description', 'task/due_date',
                                             'task/status', 'error', 'error/message']}}

    # createTask

    field, args = parse_payload(payload)
    inp = processor_factory(field).get_input(args)
    expected_inp = {'title': 'First Sample Task', 'description': 'This is a sample task description.',
                    'due_date': '2025-12-31T23:59:59Z', 'status': 'TO_DO'}
    assert field == "createTask"
    assert inp == expected_inp


def test_parse_payload_get_task():
    payload = {'stash': {},
               'arguments': {
                   'id': {'title': "test-id-1"}},
               'info': {'fieldName': 'getTask', 'parentTypeName': 'Mutation', 'variables': {
                   'id': {'title': "test-id-1"}},
                        'selectionSetList': ['task', 'task/id', 'task/title', 'task/description', 'task/due_date',
                                             'task/status', 'error', 'error/message']}}

    # getTask
    field, args = parse_payload(payload)
    inp = processor_factory(field).get_input(args)
    expected_inp = {'id': {'title': "test-id-1"}}
    assert field == "getTask"
    assert inp == expected_inp


def test_parse_payload_list_task():
    payload = {'stash': {},
               'arguments': {
                   'limit': 10,
                   'nextToken': "5ecdbd438c9e4f1e9a91a4e2cb"
               },
               'info': {'fieldName': 'listTasks', 'parentTypeName': 'Mutation', 'variables': {
                   'id': {'title': "test-id-1"}},
                        'selectionSetList': ['task', 'task/id', 'task/title', 'task/description', 'task/due_date',
                                             'task/status', 'error', 'error/message']}}

    # listTask
    field, args = parse_payload(payload)
    inp = processor_factory(field).get_input(args)

    expected_inp = {
        'limit': 10,
        'nextToken': "5ecdbd438c9e4f1e9a91a4e2cb"
    }
    assert field == "listTasks"
    assert inp == expected_inp
