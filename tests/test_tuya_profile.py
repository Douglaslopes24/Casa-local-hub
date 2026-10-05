import unittest

from casalocal_core.services.tuya_profile import analyze_tuya_dps


class TuyaProfileTests(unittest.TestCase):
    def test_switch_uses_dps_1(self):
        profile = analyze_tuya_dps({"dps": {"1": True, "2": 0}})
        self.assertEqual(profile["kind"], "switch")
        self.assertEqual(profile["primary_switch_dps"], "1")
        self.assertEqual(profile["dps"]["1"], True)

    def test_light_prefers_dps_20(self):
        profile = analyze_tuya_dps(
            {"dps": {"20": False, "21": "white", "22": 500, "23": 500}}
        )
        self.assertEqual(profile["kind"], "light")
        self.assertEqual(profile["primary_switch_dps"], "20")
        self.assertEqual(profile["brightness_dps"], "22")
        self.assertEqual(profile["color_temp_dps"], "23")
        self.assertEqual(profile["work_mode_dps"], "21")

    def test_unknown_without_boolean_dps(self):
        profile = analyze_tuya_dps({"dps": {"2": 10, "3": "auto"}})
        self.assertEqual(profile["kind"], "unknown")
        self.assertIsNone(profile["primary_switch_dps"])

    def test_empty_payload_is_safe(self):
        profile = analyze_tuya_dps({})
        self.assertEqual(profile["dps"], {})
        self.assertEqual(profile["boolean_dps"], [])


if __name__ == "__main__":
    unittest.main()
