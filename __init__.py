# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import threading
from time import monotonic, sleep
from typing import Dict, Optional

from ovos_bus_client.message import Message
from ovos_utils.log import LOG
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill

from ovos_plugin_manager.skills import get_installed_skill_ids


class BootFinishedSkill(OVOSSkill):
    """Skill to handle the readiness status of various services in OVOS, such as
    network, internet, and GUI connections, and notify users when the device is fully ready."""

    _connected_event = threading.Event()
    _network_event = threading.Event()
    _gui_event = threading.Event()

    def initialize(self):
        """Initialize the skill by setting up event listeners for network, internet, GUI,
        and device readiness, then triggers a device readiness check."""
        self.add_event("mycroft.network.connected", self.handle_network_connected)
        self.add_event("mycroft.internet.connected", self.handle_internet_connected)
        self.add_event("mycroft.gui.available", self.handle_gui_connected)
        self.add_event("mycroft.ready", self.handle_ready)
        self.add_event("mycroft.ready.check", self.handle_check_device_readiness)
        self.bus.emit(Message("mycroft.ready.check"))

    def is_device_ready(self) -> bool:
        """Check if the device is ready by waiting for various services to start.

        Different setups will have different needs
         eg, a server does not care about audio
         internet -> device is connected to the internet
         network -> device is connected to the internet
         gui_connected -> a gui client connected to the gui socket

        any service using ProcessStatus class can also be added to ready_settings
         skills -> ovos-core reported ready
         voice -> ovos-dinkum-listener reported ready
         audio -> ovos-audio reported ready
         gui -> ovos-gui websocket reported ready
         PHAL -> PHAL reported ready

        specific skills can also be waited for via their skill_id

        Returns:
            bool: True if the device is ready, False otherwise.
        Raises:
            TimeoutError: If the device is not ready within a specified timeout.
        """
        is_ready = False

        if "ready_settings" in self.settings:
            services = {k: False for k in self.settings["ready_settings"]}
        else:
            services = {k: False for k in
                        ["skills"] + get_installed_skill_ids(self.config_core)}
        start = monotonic()
        while not is_ready:
            is_ready = self.check_services_ready(services)
            if is_ready or monotonic() - start >= 60:
                break
            else:
                sleep(3)
        return is_ready

    def check_services_ready(self, services: Dict[str, bool]) -> bool:
        """Check if all specified services in the dictionary are ready.

        Args:
            services (Dict[str, bool]): Dictionary of service names and their readiness status.

        Returns:
            bool: True if all services are ready, False otherwise.
        """
        for ser, rdy in services.items():
            if rdy:
                # already reported ready
                continue
            if ser in ["network_skills", "network"]:
                services[ser] = self._network_event.is_set()
                continue
            elif ser in ["internet_skills", "internet"]:
                services[ser] = self._connected_event.is_set()
                continue
            elif ser in ["gui_connected"]:
                services[ser] = self._gui_event.is_set()
                continue
            response = self.bus.wait_for_response(
                Message(f'mycroft.{ser}.is_ready',
                        context={"source": "skills", "destination": ser}))
            if response and response.data['status']:
                services[ser] = True
        return all([services[ser] for ser in services])

    def handle_gui_connected(self, message: Message):
        """Handle the event indicating the GUI client is connected.

        Args:
            message (Message): Message indicating GUI connection status.
        """
        if not self._gui_event.is_set():
            LOG.debug("GUI Connected")
            self._gui_event.set()

    def handle_internet_connected(self, message: Message):
        """Handle the event indicating internet connectivity is established.

        Args:
            message (Message): Message indicating internet connection status.
        """
        if not self._connected_event.is_set():
            LOG.debug("Internet Connected")
            self._network_event.set()
            self._connected_event.set()

    def handle_network_connected(self, message: Message):
        """Handle the event indicating network connectivity is established.

        Args:
            message (Message): Message indicating network connection status.
        """
        if not self._network_event.is_set():
            LOG.debug("Network Connected")
            self._network_event.set()

    def handle_check_device_readiness(self, message: Optional[Message] = None) -> None:
        """Handle the event to check the device readiness status, emitting a ready signal if complete."""
        if self.is_device_ready():
            LOG.info("OVOS is all loaded and ready to roll!")
            self.bus.emit(Message('mycroft.ready'))
        else:
            sleep(5)
            self.bus.emit(Message('mycroft.ready.check'))

    @property
    def speak_ready(self) -> bool:
        """Return whether the device should speak a 'ready' message on startup.

        Returns:
            bool: True if ready notifications are enabled, False otherwise.
        """
        return self.settings.get("speak_ready", True)

    @property
    def ready_sound(self) -> bool:
        """Return whether the device should play a sound when it is ready.

        Returns:
            bool: True if ready sound notifications are enabled, False otherwise.
        """
        return self.settings.get("ready_sound", True)

    def handle_ready(self, message: Message):
        """Handle the mycroft.ready event to notify the user when all services are ready.

        Args:
            message (Message): Message indicating system readiness status.
        """
        if self.ready_sound:
            self.acknowledge()
        self.enclosure.eyes_on()
        if self.speak_ready:
            self.speak_dialog("ready")
        else:
            LOG.debug("Ready notification disabled in settings")
        self.enclosure.eyes_blink("b")

    @intent_handler("are_you_ready.intent")
    def handle_are_you_ready(self, message: Message):
        """
        Handle a user's inquiry about device readiness.
        """
        if self.is_device_ready():
            self.speak_dialog("confirm_ready")
        else:
            self.speak_dialog("deny_ready")

    @intent_handler("enable_ready_notification.intent")
    def handle_enable_notification(self, message: Message):
        """
        Handle a request to enable ready announcements
        """
        self.settings["speak_ready"] = True
        self.speak_dialog("confirm_speak_ready")

    @intent_handler("disable_ready_notification.intent")
    def handle_disable_notification(self, message: Message):
        """
        Handle a request to disable ready announcements
        """
        self.settings["speak_ready"] = False
        self.speak_dialog("confirm_no_speak_ready")
