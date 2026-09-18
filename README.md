# Finished Booting Skill

## Summary

This skill notifies you when OpenVoiceOS (OVOS) finishes booting and all core services are ready. It can speak the notification, play a sound, or just log the event, based on your settings.

## Description

The skill checks core services, such as network, internet, and GUI, and tells you when OVOS is ready to use. You can configure the type of ready notification: spoken, a sound effect, or a visual signal on devices that support it. Voice commands turn the readiness alerts on or off.

### Key Features

- Monitors system readiness by checking core services, such as network, internet, and the GUI.
- Notifies you when OVOS is fully ready.
- Turns ready notifications on or off through voice commands.
- Lets you configure spoken readiness notifications and sound effects.

## Configuration

Use the `settings.json` file to change the skill behavior.

```javascript
{
  "speak_ready": true,        // Enables or disables spoken notifications for readiness
  "ready_sound": true,         // Enables or disables sound notifications for readiness
  "ready_settings": [
    "skills",                  // Services to check before notifying readiness
    "voice",
    "audio",
    "gui",
    "internet"
  ]
}
```

The `ready_settings` option lets you tailor notifications to the role of the device. For example, a server setup can monitor only core services, while a full OVOS device can wait for the GUI and audio stack. You can also add specific skills to this list, so the skill only reports readiness once those skills load.

If you omit `ready_settings`, the skill waits for `ovos-core` and all installed skills to be ready before it sends a notification.

Valid `ready_settings` values:

- `internet`: the device is connected to the internet.
- `network`: the device is connected to the local network, but might not have internet.
- `gui_connected`: a GUI client connected to the GUI socket.
- `skills`: ovos-core reported ready.
- `voice`: ovos-dinkum-listener reported ready.
- `audio`: ovos-audio reported ready.
- `gui`: the ovos-gui websocket reported ready.
- `PHAL`: PHAL reported ready.
- A specific skill's `skill_id` waits for that skill to load.

## Voice Commands

- **Enable Ready Notifications**: Turns on the spoken notification for when OVOS is ready.
  - Example: "Enable ready notifications."

- **Disable Ready Notifications**: Turns off the spoken notification.
  - Example: "Disable ready notifications."

- **Check if System is Ready**: Asks whether the system is fully ready.
  - Example: "Is the system ready?"

## Examples

- "Enable ready notifications."
- "Disable ready speech."
- "Is the system ready?"

## Related Projects

- [OpenVoiceOS/ovos-core](https://github.com/OpenVoiceOS/ovos-core): the OVOS assistant framework this skill reports readiness for.
- [OpenVoiceOS/ovos-gui](https://github.com/OpenVoiceOS/ovos-gui): provides the `gui` and `gui_connected` readiness signals.
- [OpenVoiceOS/ovos-PHAL](https://github.com/OpenVoiceOS/ovos-PHAL): provides the `PHAL` readiness signal.

## Credits

[NeonGeckoCom](https://github.com/NeonGeckoCom/skill-core_ready)

## Category

**Daily**
