# [0.15.0](https://github.com/roblockwood/Shatter-NC/compare/v0.14.0...v0.15.0) (2026-04-18)


### Bug Fixes

* PWA icons + viewport safe-area; nginx manifest no-cache ([58d6e59](https://github.com/roblockwood/Shatter-NC/commit/58d6e591dd2688d0dd501653f82a50172eda3221))
* PWA manifest start_url targets tablet route (build-time overrides) ([1714e00](https://github.com/roblockwood/Shatter-NC/commit/1714e00f058283986c732fb5e935fd65e9e73407))
* revert fleet grid stretch rules so dashboard cards and expanded view scroll ([4ab29b2](https://github.com/roblockwood/Shatter-NC/commit/4ab29b2e3887ba97ebb95a982465068673008af3))
* serve web manifest with correct MIME so PWA standalone applies ([b9c69ab](https://github.com/roblockwood/Shatter-NC/commit/b9c69ab9dd7461d4d9fbacc7bd7fb28aa1267cba))
* stretch dashboard machine cards and tablet panes to fill viewport ([8951028](https://github.com/roblockwood/Shatter-NC/commit/8951028909c743eb2d0c6a53ae7d4d2b0a6d7e1d))


### Features

* add tablet kiosk route for single machine view ([fd8d6fe](https://github.com/roblockwood/Shatter-NC/commit/fd8d6feea2eddf43813317a7fe0db5479220c63c))
* add web app manifest with display standalone for PWA ([d8042bc](https://github.com/roblockwood/Shatter-NC/commit/d8042bccfba9e6cd6aaa7c59cd771b1ac62f7df6))
* **frontend:** tablet kiosk, compressor shell, and terminal/pane polish ([a31cc3f](https://github.com/roblockwood/Shatter-NC/commit/a31cc3f8280f3246a3f5c1ff01f47e78d3b7082e))
* per-tablet machine id via localStorage and setup UI ([c841a66](https://github.com/roblockwood/Shatter-NC/commit/c841a668b68af3285afad39d77486c709d53bac6))
* show machine and compressor IDs on edit forms ([76defc3](https://github.com/roblockwood/Shatter-NC/commit/76defc3089adecea5750794336297f7d4ab8863c))
* swipe left/right to change tablet detail panes ([ae531ca](https://github.com/roblockwood/Shatter-NC/commit/ae531ca1b50d74587fc5080ffffc220b338a9f18))
* tablet kiosk URLs with per-pane routes and bottom nav ([328957d](https://github.com/roblockwood/Shatter-NC/commit/328957da5d2c1959cf4b5466db296c175477b215))

# [0.14.0](https://github.com/roblockwood/Shatter-NC/compare/v0.13.0...v0.14.0) (2026-04-02)


### Features

* add optional MQTT publishing for compressor telemetry ([2d0fbc3](https://github.com/roblockwood/Shatter-NC/commit/2d0fbc3c61e6bd5dd51325a72c55e641ccaf4b26))

# [0.13.0](https://github.com/roblockwood/Shatter-NC/compare/v0.12.3...v0.13.0) (2026-04-01)


### Bug Fixes

* resolve issue with environment variable generation in install kit ([1811152](https://github.com/roblockwood/Shatter-NC/commit/1811152747ce8470ad26e1bb87921752513c93b5))


### Features

* migrate Kaeser integration to backend-direct SC2 client ([6cb501f](https://github.com/roblockwood/Shatter-NC/commit/6cb501f8751db0b188a899e4db6e95aab12c5a94))

## [0.12.3](https://github.com/roblockwood/Shatter-NC/compare/v0.12.2...v0.12.3) (2026-04-01)


### Bug Fixes

* add nestjs platform-express to kaeser sidecar ([6e21f11](https://github.com/roblockwood/Shatter-NC/commit/6e21f11ab3b96ac94ae2baee8ee9d79ffadb24e4))

## [0.12.2](https://github.com/roblockwood/Shatter-NC/compare/v0.12.1...v0.12.2) (2026-04-01)


### Bug Fixes

* add missing body-parser dep for kaeser sidecar ([9c9d813](https://github.com/roblockwood/Shatter-NC/commit/9c9d81371a5a58718756060e5fb05873ac1b3b00))

## [0.12.1](https://github.com/roblockwood/Shatter-NC/compare/v0.12.0...v0.12.1) (2026-03-31)


### Bug Fixes

* make Kaeser sidecar image buildable ([85a4b9d](https://github.com/roblockwood/Shatter-NC/commit/85a4b9ddd4a087318badb5a19b3747d424f6327c))

# [0.12.0](https://github.com/roblockwood/Shatter-NC/compare/v0.11.5...v0.12.0) (2026-03-31)


### Features

* add compressor integration with Kaeser SIGMA CONTROL 2 ([d6510ac](https://github.com/roblockwood/Shatter-NC/commit/d6510accfacc8afdd173d8656af061b3d3147ee5))
* enhance telemetry and oscilloscope components for improved time axis management ([1492275](https://github.com/roblockwood/Shatter-NC/commit/1492275ea8de6fe3f5b68e9387c2f77c294cb1d8))
* implement Kaeser sidecar integration for enhanced compressor data handling ([ab25719](https://github.com/roblockwood/Shatter-NC/commit/ab25719485d0e8927e977a0130b886dc72d02985))
* improve compressor telemetry visualization and data handling ([f1111c1](https://github.com/roblockwood/Shatter-NC/commit/f1111c198983be424af4953302abb58cee8cb1c3))

## [0.11.5](https://github.com/roblockwood/Shatter-NC/compare/v0.11.4...v0.11.5) (2026-03-31)


### Bug Fixes

* **ci:** use jq for ghcr package discovery to avoid python quoting ([c402212](https://github.com/roblockwood/Shatter-NC/commit/c402212f7a4cd1af7bf84ab4c4fee1b8feb912fe))

## [0.11.4](https://github.com/roblockwood/Shatter-NC/compare/v0.11.3...v0.11.4) (2026-03-31)


### Bug Fixes

* **ci:** fix python quoting in ghcr visibility step ([dd4b6f1](https://github.com/roblockwood/Shatter-NC/commit/dd4b6f10fac429c8bafdd5d0c741d4b1a5638393))
* **ci:** repair release workflow yaml and ghcr visibility script ([493633c](https://github.com/roblockwood/Shatter-NC/commit/493633c52f8e671a83b3eac70baca187f0ff3a71))

## [0.11.3](https://github.com/roblockwood/Shatter-NC/compare/v0.11.2...v0.11.3) (2026-03-31)


### Bug Fixes

* **ci:** discover ghcr package names before setting visibility ([3d90f57](https://github.com/roblockwood/Shatter-NC/commit/3d90f57a4312d35af342500331667efad7782cc9))
* **ci:** repair release workflow script quoting ([51ac682](https://github.com/roblockwood/Shatter-NC/commit/51ac6827546fa0e5bcbedf9862a0a4caf63a5013))

## [0.11.2](https://github.com/roblockwood/Shatter-NC/compare/v0.11.1...v0.11.2) (2026-03-31)


### Bug Fixes

* **ci:** correct ghcr package visibility api calls ([6c01d80](https://github.com/roblockwood/Shatter-NC/commit/6c01d80dc2d99128ad38df9f93e3d4f3f127027a))

## [0.11.1](https://github.com/roblockwood/Shatter-NC/compare/v0.11.0...v0.11.1) (2026-03-31)


### Bug Fixes

* **ci:** avoid workflow parse failure on ghcr visibility step ([7b20abc](https://github.com/roblockwood/Shatter-NC/commit/7b20abc7e44b1ff487e557b4a095ba7783ad4fd8))
* publish install images to public ghcr namespace ([437663b](https://github.com/roblockwood/Shatter-NC/commit/437663ba69b1f1f5698f51ff4b218b8487a02ccc))

# [0.11.0](https://github.com/roblockwood/Shatter-NC/compare/v0.10.0...v0.11.0) (2026-03-31)


### Features

* add install kit for Shatter-NC with public packages and Komodo support ([2e18d6b](https://github.com/roblockwood/Shatter-NC/commit/2e18d6b8ba55095803d55c1f8d0b988d5c3a6c2e))

# [0.10.0](https://github.com/roblockwood/Shatter-NC/compare/v0.9.2...v0.10.0) (2026-03-28)


### Features

* enhance ToolsPane and MachineCard components for improved hover preview and color functionality ([3ec9756](https://github.com/roblockwood/Shatter-NC/commit/3ec975676fbe2010c14e667423b1d5c228f4bd6f))

## [0.9.2](https://github.com/roblockwood/Shatter-NC/compare/v0.9.1...v0.9.2) (2026-03-28)


### Bug Fixes

* allow pane visibility toggle clicks inside grid drag handle ([197b020](https://github.com/roblockwood/Shatter-NC/commit/197b0203076e3ad17aee4f8d94c489432e97ead3))

## [0.9.1](https://github.com/roblockwood/Shatter-NC/compare/v0.9.0...v0.9.1) (2026-03-28)


### Bug Fixes

* **ci:** build Docker images after semantic-release on main ([7f2c8ff](https://github.com/roblockwood/Shatter-NC/commit/7f2c8ff41cc9a766b2bbd1fd51f0e0eff127e195))

# [0.9.0](https://github.com/roblockwood/Shatter-NC/compare/v0.8.0...v0.9.0) (2026-03-28)


### Features

* enhance ToolsPane and ColorSelect components for improved read-only functionality ([faa3755](https://github.com/roblockwood/Shatter-NC/commit/faa3755a983b6f6671624d5786fb38b0ad4fd0e1))

# [0.8.0](https://github.com/roblockwood/Shatter-NC/compare/v0.7.0...v0.8.0) (2026-03-28)


### Features

* enhance MachinePoller with online status management ([0ee4068](https://github.com/roblockwood/Shatter-NC/commit/0ee4068864a41b336145a2f5e12172317ad83bea))

# [0.7.0](https://github.com/roblockwood/Shatter-NC/compare/v0.6.0...v0.7.0) (2026-03-25)


### Bug Fixes

* improve control version detection in PRD3 parser and telnet client ([f63a012](https://github.com/roblockwood/Shatter-NC/commit/f63a01204532d4993c09656147c371267ee21877))
* update rate limit middleware to return JSON response instead of raising HTTPException; add last successful fast poll tracking in MachinePoller; adjust tests accordingly ([51e471c](https://github.com/roblockwood/Shatter-NC/commit/51e471c34ff093e65fea69b6722278cc4eaac8c2))


### Features

* preserve last successful fast poll time in websocket status updates ([d2c323a](https://github.com/roblockwood/Shatter-NC/commit/d2c323a22520e4cb7c48f2409b680b4ae6b5e089))

# [0.6.0](https://github.com/roblockwood/Shatter-NC/compare/v0.5.0...v0.6.0) (2026-03-19)


### Features

* enhance machine management and connection handling ([2e317ed](https://github.com/roblockwood/Shatter-NC/commit/2e317ed48edabbd76b7f4d60f8412101919d2908))

# [0.5.0](https://github.com/roblockwood/Shatter-NC/compare/v0.4.0...v0.5.0) (2026-03-18)


### Features

* update PRD3 status history endpoint and frontend to support 7-day intervals ([a68f613](https://github.com/roblockwood/Shatter-NC/commit/a68f6135c9d1771e33c5888b4fccbbc11a9d6190))

# [0.4.0](https://github.com/roblockwood/Shatter-NC/compare/v0.3.0...v0.4.0) (2026-03-17)


### Features

* implement cycle history feature in frontend and backend ([7aeb9a7](https://github.com/roblockwood/Shatter-NC/commit/7aeb9a7db2cbdbba2485894413efba7b4eca2ca7))
* implement production runs feature in frontend and backend ([e747a35](https://github.com/roblockwood/Shatter-NC/commit/e747a35faa35b299a32f4430d3ebee66028d2ab3))

# [0.3.0](https://github.com/roblockwood/Shatter-NC/compare/v0.2.0...v0.3.0) (2026-03-15)


### Bug Fixes

* improve machine polling logic and event logging ([2c2462e](https://github.com/roblockwood/Shatter-NC/commit/2c2462e24c07e03d71988b82d723fbfeb0025f2b))


### Features

* enhance StatusTimeline component and machine polling configuration ([90a3ca1](https://github.com/roblockwood/Shatter-NC/commit/90a3ca1145b7fdf422e023aaa460b60bf7fc0e50))

# [0.2.0](https://github.com/roblockwood/Shatter-NC/compare/v0.1.0...v0.2.0) (2026-03-15)


### Bug Fixes

* normalize API error messages and update default machine path ([79c2699](https://github.com/roblockwood/Shatter-NC/commit/79c26992675e8ef00d43f48e7add613e57e75db4))


### Features

* update license to GNU Affero General Public License v3 and add Chapter 6 Macro documentation ([4bfe9a0](https://github.com/roblockwood/Shatter-NC/commit/4bfe9a02e763c2a21283fd481342ba9039c1c50e))
