import unittest
from unittest.mock import patch

from ovos_plugin_manager.skills import find_skill_plugins
from ovos_utils.messagebus import FakeBus

from ovos_skill_boot_finished import BootFinishedSkill


class TestSkillLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-boot-finished.openvoiceos"

    def test_find_plugin(self):
        plugins = find_skill_plugins()
        self.assertIn(self.skill_id, list(plugins))

    def test_from_class(self):
        bus = FakeBus()
        skill = BootFinishedSkill()
        # Prevent the infinite ready-check loop during startup
        with patch.object(skill, 'handle_check_device_readiness',
                          lambda *a, **k: None):
            skill._startup(bus, self.skill_id)
        self.assertEqual(skill.bus, bus)
        self.assertEqual(skill.skill_id, self.skill_id)
        skill.shutdown()

    def test_is_device_ready_skips_blacklisted_skills(self):
        """A blacklisted skill is installed but never loads, so it can never
        answer mycroft.<skill_id>.is_ready; waiting on it would keep the device
        from ever reporting ready."""
        bus = FakeBus()
        skill = BootFinishedSkill()
        with patch.object(skill, 'handle_check_device_readiness',
                          lambda *a, **k: None):
            skill._startup(bus, self.skill_id)
        waited_on = {}

        def check(services):
            waited_on.update(services)
            return True

        config = {"skills": {"blacklisted_skills": ["blocked.openvoiceos"]}}
        try:
            with patch("ovos_skill_boot_finished.get_installed_skill_ids",
                       return_value=["loaded.openvoiceos", "blocked.openvoiceos"]), \
                    patch.object(skill, "config_core", config), \
                    patch.object(skill, "check_services_ready", side_effect=check):
                skill.settings.pop("ready_settings", None)
                self.assertTrue(skill.is_device_ready())
        finally:
            skill.shutdown()
        self.assertEqual(set(waited_on), {"skills", "loaded.openvoiceos"})
