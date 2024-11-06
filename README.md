# Finished Booting Skill

## Summary

The Finished Booting skill provides notifications when OpenVoiceOS (OVOS) has fully started and all core services are ready. Notifications can be spoken, played as a sound, or simply logged, based on the user’s preferences.

## Description

This skill ensures users are informed when OVOS has completed booting and all essential services (such as network, GUI, and others) are ready for use. Users can configure the type of ready notification, which can be spoken, triggered as a sound, or displayed visually on compatible devices. Notifications can also be enabled or disabled via voice commands, making it easy to control the readiness alerts.

### Key Features
- Monitors system readiness by checking core services like network, internet, and GUI.
- Notifies the user when OVOS is fully ready.
- Enables or disables ready notifications via voice commands.
- Offers configurable options for spoken readiness notifications and sound effects.


## Configuration

To customize the skill behavior, use the `settings.json` file.

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

The `ready_settings` option allows for flexible notifications based on the device’s role. For example, a server setup might only monitor core services, while a fully-featured OVOS device might wait for the GUI and audio stack. Specific skills can also be added to this list, ensuring the system only notifies readiness when those skills are loaded. 

> If `ready_settings` is omitted, the skill defaults to waiting for `ovos-core` and **all installed skills** to be ready before sending a notification. 

Valid ready settings options:
- `internet` -> device is connected to the internet
- `network` -> device is connected to local network, might not have internet
- `gui_connected` -> a gui client connected to the gui socket
- `skills` -> ovos-core reported ready
- `voice` -> ovos-dinkum-listener reported ready
- `audio` -> ovos-audio reported ready
- `gui` -> ovos-gui websocket reported ready
- `PHAL` -> PHAL reported ready
- specific skills can also be waited for via their `skill_id`

## Voice Commands

- **Enable Ready Notifications**: Activates the spoken notification when OVOS is ready.
  - Example: "Enable ready notifications."
  
- **Disable Ready Notifications**: Deactivates the spoken notification.
  - Example: "Disable ready notifications."

- **Check if System is Ready**: Inquires whether the system is fully ready.
  - Example: "Is the system ready?"

## Examples

- "Enable ready notifications."
- "Disable ready speech."
- "Is the system ready?"

## Credits

[NeonGeckoCom](https://github.com/NeonGeckoCom/skill-core_ready)

## Category

**Daily**
