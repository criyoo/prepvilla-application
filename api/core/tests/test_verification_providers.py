from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from core import dikript_verification, prembly_verification


class CombinedIdentityVerificationTests(SimpleTestCase):
    input_data = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "middle_name": "Byron",
        "date_of_birth": date(1990, 1, 2),
        "mobile": "+2348012345678",
        "country_of_birth": "Nigeria",
        "nationality": "Nigerian",
        "state_of_origin": "Lagos",
        "lga": "Ikeja",
    }

    def _payloads(self, provider: str, *, nin_first_name: str = "Ada", bvn_first_name: str = "Ada"):
        if provider == "dikript":
            return {
                "nin": {"status": True, "data": {
                    "firstName": nin_first_name,
                    "surname": "Lovelace",
                    "middleName": "Byron",
                    "birthDate": "1990-01-02",
                    "telephoneNo": "08012345678",
                    "birthCountry": "Nigeria",
                }},
                "bvn": {"status": True, "data": {
                    "firstName": bvn_first_name,
                    "lastName": "Lovelace",
                    "middleName": "Byron",
                    "dateOfBirth": "1990-01-02",
                    "phoneNumber1": "08012345678",
                    "countryOfBirth": "Nigeria",
                    "nationality": "Nigerian",
                    "stateOfOrigin": "Lagos",
                    "lgaOfOrigin": "Ikeja",
                }},
            }
        return {
                "nin": {"status": True, "data": {
                "firstname": nin_first_name,
                "surname": "Lovelace",
                "middlename": "Byron",
                    "birthdate": "1990-01-02",
                    "telephoneno": "08012345678",
                    "birthCountry": "Nigeria",
                }},
            "bvn": {"status": True, "data": {
                "firstName": bvn_first_name,
                "lastName": "Lovelace",
                "middleName": "Byron",
                    "dateOfBirth": "1990-01-02",
                    "phoneNumber1": "08012345678",
                    "countryOfBirth": "Nigeria",
                    "nationality": "Nigerian",
                    "stateOfOrigin": "Lagos",
                    "lgaOfOrigin": "Ikeja",
                }},
        }

    def _verify(self, module, provider: str, payloads):
        lookup_name = "dikript_lookup" if provider == "dikript" else "prembly_lookup"

        def lookup(*, verification_type, **kwargs):
            return payloads[verification_type]

        with patch.object(module, lookup_name, side_effect=lookup) as lookup_mock:
            result = module.verify_nin_and_bvn(self.input_data, "12345678901", "10987654321")
        self.assertEqual(lookup_mock.call_count, 2)
        return result

    def test_single_provider_name_difference_does_not_fail(self):
        for provider, module in (("dikript", dikript_verification), ("prembly", prembly_verification)):
            with self.subTest(provider=provider):
                self._verify(module, provider, self._payloads(provider, nin_first_name="Ada N.", bvn_first_name="Ada"))

    def test_name_difference_from_both_providers_fails(self):
        for provider, module in (("dikript", dikript_verification), ("prembly", prembly_verification)):
            with self.subTest(provider=provider):
                with self.assertRaises(ValidationError) as raised:
                    self._verify(module, provider, self._payloads(provider, nin_first_name="Grace", bvn_first_name="Grace"))
                self.assertIn("first_name", raised.exception.detail)

    def test_country_of_birth_difference_from_one_provider_does_not_fail(self):
        for provider, module in (("dikript", dikript_verification), ("prembly", prembly_verification)):
            with self.subTest(provider=provider):
                payloads = self._payloads(provider)
                payloads["nin"]["data"]["birthCountry"] = "Ghana" if provider == "dikript" else "Ghana"
                self._verify(module, provider, payloads)

    def test_country_of_birth_difference_from_both_providers_fails(self):
        for provider, module in (("dikript", dikript_verification), ("prembly", prembly_verification)):
            with self.subTest(provider=provider):
                payloads = self._payloads(provider)
                payloads["nin"]["data"]["birthCountry"] = "Ghana"
                payloads["bvn"]["data"]["countryOfBirth"] = "Ghana"
                with self.assertRaises(ValidationError) as raised:
                    self._verify(module, provider, payloads)
                self.assertIn("country_of_birth", raised.exception.detail)
