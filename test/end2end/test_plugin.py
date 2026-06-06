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
