import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.payment_queue import (
    TASK_PROCESS_READY_PAYOUTS,
    enqueue_payment_task,
    run_sqs_worker,
)


@override_settings(
    PAYMENT_QUEUE_BACKEND="sqs",
    PAYMENT_QUEUE_URL="https://sqs.eu-west-1.amazonaws.com/123456789012/prepvilla-payments",
    PAYMENT_QUEUE_WORKER_WAIT_SECONDS=20,
    PAYMENT_QUEUE_WORKER_MAX_MESSAGES=10,
    PAYMENT_QUEUE_VISIBILITY_TIMEOUT_SECONDS=300,
)
class SqsPaymentQueueTests(SimpleTestCase):
    @patch("core.payment_queue.sqs_client")
    def test_enqueue_payment_task_sends_supported_task_to_sqs(self, sqs_client):
        client = sqs_client.return_value

        enqueue_payment_task(TASK_PROCESS_READY_PAYOUTS, {"source": "test"})

        client.send_message.assert_called_once()
        request = client.send_message.call_args.kwargs
        message = json.loads(request["MessageBody"])
        self.assertEqual(message["task"], TASK_PROCESS_READY_PAYOUTS)
        self.assertEqual(message["payload"], {"source": "test"})

    @patch("core.payment_queue.process_payment_task")
    @patch("core.payment_queue.sqs_client")
    def test_sqs_worker_deletes_successful_message(self, sqs_client, process_payment_task):
        client = sqs_client.return_value
        client.receive_message.return_value = {
            "Messages": [{
                "ReceiptHandle": "receipt-1",
                "Body": json.dumps({
                    "task": TASK_PROCESS_READY_PAYOUTS,
                    "payload": {"source": "test"},
                }),
            }]
        }

        run_sqs_worker(once=True)

        process_payment_task.assert_called_once_with(
            TASK_PROCESS_READY_PAYOUTS,
            {"source": "test"},
        )
        client.delete_message.assert_called_once_with(
            QueueUrl="https://sqs.eu-west-1.amazonaws.com/123456789012/prepvilla-payments",
            ReceiptHandle="receipt-1",
        )

    @patch("core.payment_queue.logger.exception")
    @patch("core.payment_queue.process_payment_task", side_effect=RuntimeError("failed"))
    @patch("core.payment_queue.sqs_client")
    def test_sqs_worker_leaves_failed_message_for_retry(
        self,
        sqs_client,
        _process_payment_task,
        _logger_exception,
    ):
        client = sqs_client.return_value
        client.receive_message.return_value = {
            "Messages": [{
                "ReceiptHandle": "receipt-1",
                "Body": json.dumps({
                    "task": TASK_PROCESS_READY_PAYOUTS,
                    "payload": {},
                }),
            }]
        }

        run_sqs_worker(once=True)

        client.delete_message.assert_not_called()

    @patch("core.payment_queue.process_payment_task")
    @patch("core.payment_queue.sqs_client")
    def test_sqs_worker_releases_unprocessed_messages_at_limit(self, sqs_client, _process_payment_task):
        client = sqs_client.return_value
        client.receive_message.return_value = {
            "Messages": [
                {
                    "ReceiptHandle": "receipt-1",
                    "Body": json.dumps({"task": TASK_PROCESS_READY_PAYOUTS, "payload": {}}),
                },
                {
                    "ReceiptHandle": "receipt-2",
                    "Body": json.dumps({"task": TASK_PROCESS_READY_PAYOUTS, "payload": {}}),
                },
            ]
        }

        run_sqs_worker(max_messages=1)

        client.change_message_visibility.assert_called_once_with(
            QueueUrl="https://sqs.eu-west-1.amazonaws.com/123456789012/prepvilla-payments",
            ReceiptHandle="receipt-2",
            VisibilityTimeout=0,
        )
