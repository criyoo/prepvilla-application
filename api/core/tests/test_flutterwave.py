from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

from core.flutterwave import (
    FlutterwaveError,
    NIGERIAN_PAYOUT_BANK_CODES_BY_NAME,
    _access_token,
    _base_url,
    _clear_access_token,
    create_transfer,
    get_or_create_customer_id,
    initialize_payment,
    resolve_nigerian_payout_bank_code,
    retrieve_checkout_session,
    retrieve_transfer,
    verify_transaction_by_reference,
)


class FlutterwaveConfigurationTests(TestCase):
    def tearDown(self):
        _clear_access_token()

    @patch(
        "core.flutterwave.settings",
        new=SimpleNamespace(
            FLUTTERWAVE_API_VERSION="v4",
            FLUTTERWAVE_API_BASE_URL="https://developersandbox-api.flutterwave.com",
        ),
    )
    def test_v4_checkout_uses_the_v4_endpoint(self):
        self.assertEqual(_base_url(), "https://developersandbox-api.flutterwave.com")

    @patch(
        "core.flutterwave.settings",
        new=SimpleNamespace(
            FLUTTERWAVE_API_VERSION="v3",
            FLUTTERWAVE_API_BASE_URL="https://api.flutterwave.com/v3",
        ),
    )
    def test_v3_misconfiguration_is_rejected(self):
        with self.assertRaisesRegex(FlutterwaveError, "requires Flutterwave v4"):
            _base_url()

    @patch("core.flutterwave.urlopen")
    @patch(
        "core.flutterwave.settings",
        new=SimpleNamespace(
            FLUTTERWAVE_CLIENT_ID="client-id",
            FLUTTERWAVE_CLIENT_SECRET="client-secret",
            FLUTTERWAVE_TOKEN_URL="https://idp.flutterwave.test/token",
            FLUTTERWAVE_TIMEOUT_SECONDS=20,
        ),
    )
    def test_v4_oauth_uses_client_credentials(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"access_token":"access-token","expires_in":600}'
        urlopen.return_value = response
        _clear_access_token()

        self.assertEqual(_access_token(), "access-token")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://idp.flutterwave.test/token")
        self.assertEqual(
            parse_qs(request.data.decode("utf-8")),
            {
                "client_id": ["client-id"],
                "client_secret": ["client-secret"],
                "grant_type": ["client_credentials"],
            },
        )

    @patch("core.flutterwave._request")
    def test_customer_is_created_once_search_returns_no_match(self, request):
        request.side_effect = [
            {"status": "success", "data": []},
            {"status": "success", "data": {"id": "cus_test"}},
        ]

        customer_id = get_or_create_customer_id(
            email="Student@Example.com",
            name="Student Example",
            phone="+2348012345678",
        )

        self.assertEqual(customer_id, "cus_test")
        self.assertEqual(request.call_args_list[0].args[0], "customers/search?page=1&size=10")
        self.assertEqual(request.call_args_list[1].args[0], "customers")
        self.assertEqual(
            request.call_args_list[1].kwargs["body"],
            {
                "email": "student@example.com",
                "name": {"first": "Student", "last": "Example"},
                "phone": {"country_code": "234", "number": "8012345678"},
            },
        )

    @patch("core.flutterwave._request")
    def test_transaction_and_transfer_reconciliation_endpoints(self, request):
        request.return_value = {"status": "success", "data": {}}

        verify_transaction_by_reference("payment ref/1")
        retrieve_checkout_session("cks_test")
        retrieve_transfer("98765")

        self.assertEqual(
            request.call_args_list[0].args[0],
            "charges?reference=payment+ref%2F1&page=1&size=10",
        )
        self.assertEqual(request.call_args_list[1].args[0], "checkout/sessions/cks_test")
        self.assertEqual(request.call_args_list[2].args[0], "transfers/98765")

    @patch("core.flutterwave._request")
    @patch("core.flutterwave.get_or_create_customer_id", return_value="cus_test")
    @patch(
        "core.flutterwave.settings",
        new=SimpleNamespace(FLUTTERWAVE_REDIRECT_URL="https://prepvilla.test/payments/flutterwave/callback"),
    )
    def test_checkout_uses_v4_checkout_sessions(self, get_customer, request):
        request.return_value = {
            "status": "success",
            "data": {"id": "cks_test", "checkout_url": "https://checkout.test/session"},
        }

        initialize_payment(
            tx_ref="prepvilla-sub-123",
            amount=Decimal("5000.00"),
            email="student@example.com",
            name="Student Example",
            phone="+2348012345678",
        )

        get_customer.assert_called_once_with(
            email="student@example.com",
            name="Student Example",
            phone="+2348012345678",
        )
        request.assert_called_once_with(
            "checkout/sessions",
            method="POST",
            body={
                "reference": "prepvilla-sub-123",
                "amount": 5000.0,
                "currency": "NGN",
                "redirect_url": "https://prepvilla.test/payments/flutterwave/callback",
                "customer_id": "cus_test",
                "max_retry_attempts": 3,
                "session_duration": 30,
            },
            idempotency_key="checkout-prepvilla-sub-123",
        )


class NigerianPayoutBankCodeTests(TestCase):
    def test_catalog_matches_supported_nigerian_payout_names(self):
        self.assertEqual(NIGERIAN_PAYOUT_BANK_CODES_BY_NAME["accessbank"], "044")
        self.assertEqual(NIGERIAN_PAYOUT_BANK_CODES_BY_NAME["fcmb"], "214")
        self.assertEqual(NIGERIAN_PAYOUT_BANK_CODES_BY_NAME["opay"], "100004")
        self.assertEqual(NIGERIAN_PAYOUT_BANK_CODES_BY_NAME["palmpay"], "100033")
        self.assertEqual(NIGERIAN_PAYOUT_BANK_CODES_BY_NAME["moniepoint"], "090405")

    def test_resolver_normalizes_bank_names_and_preserves_unknown_codes(self):
        self.assertEqual(resolve_nigerian_payout_bank_code("First City Monument Bank PLC", ""), "214")
        self.assertEqual(resolve_nigerian_payout_bank_code("Guaranty Trust Bank", "999"), "058")
        self.assertEqual(resolve_nigerian_payout_bank_code("Example Bank", "999"), "999")

    @patch("core.flutterwave._request")
    def test_create_transfer_uses_bank_name_mapping(self, request):
        request.return_value = {"status": "success", "data": {"id": "transfer-1"}}

        create_transfer(
            reference="prepvilla-payout-1",
            amount=Decimal("5000.00"),
            account_bank="090405",
            account_number="0123456789",
            account_name="Tutor Example",
            narration="PrepVilla tutor payout",
            bank_name="Moniepoint MFB",
        )

        request.assert_called_once_with(
            "direct-transfers",
            method="POST",
            body={
                "type": "bank",
                "action": "instant",
                "reference": "prepvilla-payout-1",
                "narration": "PrepVilla tutor payout",
                "payment_instruction": {
                    "source_currency": "NGN",
                    "destination_currency": "NGN",
                    "amount": 5000.0,
                    "recipient": {
                        "bank": {
                            "account_number": "0123456789",
                            "code": "090405",
                        },
                    },
                },
            },
            idempotency_key="transfer-prepvilla-payout-1",
        )
