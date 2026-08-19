from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from core.flutterwave import (
    FlutterwaveError,
    NIGERIAN_PAYOUT_BANK_CODES_BY_NAME,
    _base_url,
    create_transfer,
    resolve_nigerian_payout_bank_code,
    retrieve_transfer,
    verify_transaction_by_reference,
)


class FlutterwaveConfigurationTests(TestCase):
    @patch(
        "core.flutterwave.settings",
        new=SimpleNamespace(
            FLUTTERWAVE_API_VERSION="v3",
            FLUTTERWAVE_API_BASE_URL="https://wrong-v4.example",
            FLUTTERWAVE_V3_API_BASE_URL="https://api.flutterwave.com/v3",
        ),
    )
    def test_v3_checkout_uses_the_v3_endpoint(self):
        self.assertEqual(_base_url(), "https://api.flutterwave.com/v3")

    @patch(
        "core.flutterwave.settings",
        new=SimpleNamespace(
            FLUTTERWAVE_API_VERSION="4",
            FLUTTERWAVE_API_BASE_URL="https://f4bexperience.flutterwave.com",
        ),
    )
    def test_v4_misconfiguration_fails_before_sending_v3_payloads(self):
        with self.assertRaisesRegex(FlutterwaveError, "requires Flutterwave v3"):
            _base_url()

    @patch("core.flutterwave._request")
    def test_transaction_and_transfer_reconciliation_endpoints(self, request):
        request.return_value = {"status": "success", "data": {}}

        verify_transaction_by_reference("payment ref/1")
        retrieve_transfer("98765")

        self.assertEqual(
            request.call_args_list[0].args[0],
            "transactions/verify_by_reference?tx_ref=payment+ref%2F1",
        )
        self.assertEqual(request.call_args_list[1].args[0], "transfers/98765")


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
    @patch("core.flutterwave.settings", new=SimpleNamespace(FLUTTERWAVE_TRANSFER_PIN=""))
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
            "transfers",
            method="POST",
            body={
                "account_bank": "090405",
                "account_number": "0123456789",
                "amount": 5000.0,
                "currency": "NGN",
                "debit_currency": "NGN",
                "reference": "prepvilla-payout-1",
                "beneficiary_name": "Tutor Example",
                "narration": "PrepVilla tutor payout",
            },
        )
