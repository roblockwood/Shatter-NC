## [1.1.2](https://github.com/BlackwellEngineering/Shatter-NC-BE/compare/v1.1.1...v1.1.2) (2026-04-25)


### Bug Fixes

* resolve safe ESLint violations (no-unused-vars, no-case-declarations, no-prototype-builtins, etc.) ([6639210](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/663921003c4ed076df20e03e0fa534dfdb53e026))

## [1.1.1](https://github.com/BlackwellEngineering/Shatter-NC-BE/compare/v1.1.0...v1.1.1) (2026-04-25)


### Bug Fixes

* eliminate remaining 9 no-explicit-any violations in ToolsPane.tsx ([61bb151](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/61bb15190b222155d32aa34dce34c6ccc254c4c1))

# [1.1.0](https://github.com/BlackwellEngineering/Shatter-NC-BE/compare/v1.0.2...v1.1.0) (2026-04-25)


### Features

* add ATC pot optimizer and NC tool sequence parser ([d0c97ce](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/d0c97ce6264fd56f8595b89cdf667ca51b80ecad))

## [1.0.2](https://github.com/BlackwellEngineering/Shatter-NC-BE/compare/v1.0.1...v1.0.2) (2026-04-25)


### Bug Fixes

* eliminate no-explicit-any violations in frontend (68 fixed) ([a11f3b0](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/a11f3b06308e0f3172f9a8452f99128ad104b789))

## [1.0.1](https://github.com/BlackwellEngineering/Shatter-NC-BE/compare/v1.0.0...v1.0.1) (2026-04-25)


### Bug Fixes

* correct fake_list in download candidates test to scope by folder ([05a5c1c](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/05a5c1c99c3bc90774782b5db6402442411ba0cf))

# 1.0.0 (2026-04-25)


### Bug Fixes

* add missing body-parser dep for kaeser sidecar ([9c9d813](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/9c9d81371a5a58718756060e5fb05873ac1b3b00))
* add nestjs platform-express to kaeser sidecar ([6e21f11](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/6e21f11ab3b96ac94ae2baee8ee9d79ffadb24e4))
* allow pane visibility toggle clicks inside grid drag handle ([197b020](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/197b0203076e3ad17aee4f8d94c489432e97ead3))
* **ci:** avoid workflow parse failure on ghcr visibility step ([7b20abc](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/7b20abc7e44b1ff487e557b4a095ba7783ad4fd8))
* **ci:** build Docker images after semantic-release on main ([7f2c8ff](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/7f2c8ff41cc9a766b2bbd1fd51f0e0eff127e195))
* **ci:** correct ghcr package visibility api calls ([6c01d80](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/6c01d80dc2d99128ad38df9f93e3d4f3f127027a))
* **ci:** discover ghcr package names before setting visibility ([3d90f57](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/3d90f57a4312d35af342500331667efad7782cc9))
* **ci:** fix python quoting in ghcr visibility step ([dd4b6f1](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/dd4b6f10fac429c8bafdd5d0c741d4b1a5638393))
* **ci:** repair release workflow script quoting ([51ac682](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/51ac6827546fa0e5bcbedf9862a0a4caf63a5013))
* **ci:** repair release workflow yaml and ghcr visibility script ([493633c](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/493633c52f8e671a83b3eac70baca187f0ff3a71))
* **ci:** use jq for ghcr package discovery to avoid python quoting ([c402212](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/c402212f7a4cd1af7bf84ab4c4fee1b8feb912fe))
* Display tool tolerance values in validation tables ([44ebbc9](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/44ebbc93cda51213f0d2d664398d070e02938366))
* improve control version detection in PRD3 parser and telnet client ([f63a012](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/f63a01204532d4993c09656147c371267ee21877))
* improve machine polling logic and event logging ([2c2462e](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/2c2462e24c07e03d71988b82d723fbfeb0025f2b))
* make Kaeser sidecar image buildable ([85a4b9d](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/85a4b9ddd4a087318badb5a19b3747d424f6327c))
* normalize API error messages and update default machine path ([79c2699](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/79c26992675e8ef00d43f48e7add613e57e75db4))
* publish install images to public ghcr namespace ([437663b](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/437663ba69b1f1f5698f51ff4b218b8487a02ccc))
* resolve issue with environment variable generation in install kit ([1811152](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/1811152747ce8470ad26e1bb87921752513c93b5))
* **runtime:** harden telnet/http/websocket handling and migration startup ([0d01444](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/0d01444e2308c36b5f6aa7db2f9f76d2488048b2))
* update rate limit middleware to return JSON response instead of raising HTTPException; add last successful fast poll tracking in MachinePoller; adjust tests accordingly ([51e471c](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/51e471c34ff093e65fea69b6722278cc4eaac8c2))


### Features

* Add collapsable tool/WCS tables to file browser ([c2130cf](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/c2130cf9c61c368a8199d32e54e17274134b5c58))
* add compressor integration with Kaeser SIGMA CONTROL 2 ([d6510ac](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/d6510accfacc8afdd173d8656af061b3d3147ee5))
* add install kit for Shatter-NC with public packages and Komodo support ([2e18d6b](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/2e18d6b8ba55095803d55c1f8d0b988d5c3a6c2e))
* add optional MQTT publishing for compressor telemetry ([2d0fbc3](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/2d0fbc3c61e6bd5dd51325a72c55e641ccaf4b26))
* add per-operation speed/feed data capture to NC parser ([9517359](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/9517359d3930604f952be5c169a6ad948cf16ce5)), closes [#500](https://github.com/BlackwellEngineering/Shatter-NC-BE/issues/500) [-#509](https://github.com/-/issues/509)
* enhance machine management and connection handling ([2e317ed](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/2e317ed48edabbd76b7f4d60f8412101919d2908))
* enhance MachinePoller with online status management ([0ee4068](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/0ee4068864a41b336145a2f5e12172317ad83bea))
* enhance StatusTimeline component and machine polling configuration ([90a3ca1](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/90a3ca1145b7fdf422e023aaa460b60bf7fc0e50))
* enhance telemetry and oscilloscope components for improved time axis management ([1492275](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/1492275ea8de6fe3f5b68e9387c2f77c294cb1d8))
* enhance ToolsPane and ColorSelect components for improved read-only functionality ([faa3755](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/faa3755a983b6f6671624d5786fb38b0ad4fd0e1))
* enhance ToolsPane and MachineCard components for improved hover preview and color functionality ([3ec9756](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/3ec975676fbe2010c14e667423b1d5c228f4bd6f))
* implement cycle history feature in frontend and backend ([7aeb9a7](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/7aeb9a7db2cbdbba2485894413efba7b4eca2ca7))
* implement Kaeser sidecar integration for enhanced compressor data handling ([ab25719](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/ab25719485d0e8927e977a0130b886dc72d02985))
* implement production runs feature in frontend and backend ([e747a35](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/e747a35faa35b299a32f4430d3ebee66028d2ab3))
* implement real-time file upload with progress tracking and 5s highlight ([bd32283](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/bd3228390792f13122d381c7df98228451dba83a))
* improve compressor telemetry visualization and data handling ([f1111c1](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/f1111c198983be424af4953302abb58cee8cb1c3))
* migrate Kaeser integration to backend-direct SC2 client ([6cb501f](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/6cb501f8751db0b188a899e4db6e95aab12c5a94))
* **platform:** add FTP sync and notifications services, APIs, UI, and migrations ([c5781b7](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/c5781b736753c742a679745cce4752d7d32953c2))
* preserve last successful fast poll time in websocket status updates ([d2c323a](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/d2c323a22520e4cb7c48f2409b680b4ae6b5e089))
* Show machine tool/WCS data when not parsed from NC ([7f2bd8b](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/7f2bd8b51befebc3b652cf2d1ee5e373e4636197))
* Update file detail view to use collapsable tool/WCS tables ([2f1bee3](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/2f1bee30616656dac9a0dca07dd2a8ba76ba11af))
* update license to GNU Affero General Public License v3 and add Chapter 6 Macro documentation ([4bfe9a0](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/4bfe9a02e763c2a21283fd481342ba9039c1c50e))
* update PRD3 status history endpoint and frontend to support 7-day intervals ([a68f613](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/a68f6135c9d1771e33c5888b4fccbbc11a9d6190))
* **validation:** add machine control/toggles and fix current-program tool/path validation behavior ([48e7dd2](https://github.com/BlackwellEngineering/Shatter-NC-BE/commit/48e7dd20fc1b0ed32510def74f73b81f237cc954))

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
