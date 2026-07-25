# [1.2.0](https://github.com/roblockwood/Shatter-NC/compare/v1.1.1...v1.2.0) (2026-07-25)


### Features

* add beta/stable release channels for Docker images ([26f3fe9](https://github.com/roblockwood/Shatter-NC/commit/26f3fe9a0218e69c502402eca9d4d12b9fd7471d))

## [1.1.1](https://github.com/roblockwood/Shatter-NC/compare/v1.1.0...v1.1.1) (2026-07-25)


### Bug Fixes

* **ci:** avoid secrets in workflow if conditions for GHCR step ([4b5fcaf](https://github.com/roblockwood/Shatter-NC/commit/4b5fcaf082c2eb0ff5b6fbebb1020bb705c7bfac))
* **ci:** restore GHCR_PUBLISH_TOKEN for GHCR visibility step ([1e2731a](https://github.com/roblockwood/Shatter-NC/commit/1e2731af1142447d7df2eabecebc6f3bfe90e7f5))

# [1.1.0](https://github.com/roblockwood/Shatter-NC/compare/v1.0.2...v1.1.0) (2026-07-25)


### Features

* always expose Swagger, ReDoc, and OpenAPI JSON ([14f4341](https://github.com/roblockwood/Shatter-NC/commit/14f43414c31ef87ee4d4bd88fcf17ded2f53a5b8))

## [1.0.2](https://github.com/roblockwood/Shatter-NC/compare/v1.0.1...v1.0.2) (2026-07-24)


### Bug Fixes

* clear pip-audit findings for FastAPI stack ([86ad3c5](https://github.com/roblockwood/Shatter-NC/commit/86ad3c5d1d5e9ce473f9897861c07e12d221e847))

## [1.0.1](https://github.com/roblockwood/Shatter-NC/compare/v1.0.0...v1.0.1) (2026-07-24)


### Bug Fixes

* enable production install from ghcr.io without cloning ([5c7e92e](https://github.com/roblockwood/Shatter-NC/commit/5c7e92e6d127ff28d35174fd50e6479b2d56dd99))
* harden production API surface and document security model ([cc1cdb9](https://github.com/roblockwood/Shatter-NC/commit/cc1cdb9bb517212666bfc53373fd77720f4b7045))
* resolve alarm route collision and deprecate unused endpoints ([049bf2d](https://github.com/roblockwood/Shatter-NC/commit/049bf2d12a471639adcfed3834585c452c23bcb1))

# 1.0.0 (2026-07-24)


### Bug Fixes

* add missing body-parser dep for kaeser sidecar ([0df8b43](https://github.com/roblockwood/Shatter-NC/commit/0df8b432a8a5f106e12de843af7ed554f1ce850a))
* add nestjs platform-express to kaeser sidecar ([4374ab3](https://github.com/roblockwood/Shatter-NC/commit/4374ab3a38376962872c172ea20afba4c971cac2))
* address exhaustive-deps warnings (partial) ([4c34aea](https://github.com/roblockwood/Shatter-NC/commit/4c34aeaaed33bb04485389f84cfa46baa7605fe9))
* allow pane visibility toggle clicks inside grid drag handle ([a63f13b](https://github.com/roblockwood/Shatter-NC/commit/a63f13be16eb7e538368f977fea975f30dd25987))
* **backend:** add time_utils module for CNC time formatting ([4a541dd](https://github.com/roblockwood/Shatter-NC/commit/4a541dd10d8b0725e2def0a117067878b7e5ebe9))
* **ci:** avoid workflow parse failure on ghcr visibility step ([959c7e7](https://github.com/roblockwood/Shatter-NC/commit/959c7e72add9b4f463b34b7b684e1b1e69c4a22d))
* **ci:** build Docker images after semantic-release on main ([696488d](https://github.com/roblockwood/Shatter-NC/commit/696488d18dbe170fbd52685f9a15dde33ea4a9f6))
* **ci:** correct ghcr package visibility api calls ([313a160](https://github.com/roblockwood/Shatter-NC/commit/313a1608b04bb2dc5f72dd9df1269ae1cc333527))
* **ci:** discover ghcr package names before setting visibility ([2045f9d](https://github.com/roblockwood/Shatter-NC/commit/2045f9d04de0866947c6b936e7ddf162f29f4269))
* **ci:** fix python quoting in ghcr visibility step ([4a9d7c0](https://github.com/roblockwood/Shatter-NC/commit/4a9d7c0c5e420a32f16feabc05287f93d3cdf1f2))
* **ci:** repair release workflow script quoting ([4b04222](https://github.com/roblockwood/Shatter-NC/commit/4b04222f06c88fa62ce034d3895b02d0666fac66))
* **ci:** repair release workflow yaml and ghcr visibility script ([e4c423b](https://github.com/roblockwood/Shatter-NC/commit/e4c423ba7eb732da6de948011c1271a40dce0094))
* **ci:** use jq for ghcr package discovery to avoid python quoting ([8150492](https://github.com/roblockwood/Shatter-NC/commit/8150492271e7da208cdd69646bd2baee1f24ca9d))
* Display tool tolerance values in validation tables ([44ebbc9](https://github.com/roblockwood/Shatter-NC/commit/44ebbc93cda51213f0d2d664398d070e02938366))
* eliminate no-explicit-any violations in frontend (68 fixed) ([1b46cf5](https://github.com/roblockwood/Shatter-NC/commit/1b46cf5963450563d88cb19ee317c86aca5f6623))
* **frontend:** add web app manifest ([032baa8](https://github.com/roblockwood/Shatter-NC/commit/032baa8963137a380de4454de44c591ecd8ddab9))
* **frontend:** beta-gate AUTO control type and theme file selects ([c2bc147](https://github.com/roblockwood/Shatter-NC/commit/c2bc147b9e64eea006146856fdee9f31e9ed8312))
* **frontend:** remove unused locals blocking TS build ([521c054](https://github.com/roblockwood/Shatter-NC/commit/521c054194bde5a69dd366b5b978f43541748d90))
* **frontend:** restore tablet kiosk routes and hide header ([e401892](https://github.com/roblockwood/Shatter-NC/commit/e4018923201fe6fb9754e4fe929aa2b02b8cd704))
* **frontend:** self-host mono fonts for SHATTER logo alignment ([671f7a7](https://github.com/roblockwood/Shatter-NC/commit/671f7a7b62108443531eab80fd5a6ecb938a25d6))
* **frontend:** tablet kiosk pane fill and overview grid layouts ([954bc02](https://github.com/roblockwood/Shatter-NC/commit/954bc02eac1dcac3fba1e81a527c5c8cccca1dc8))
* **frontend:** tablet panel chrome, fluid overrides, slider colors (v0.14.2) ([c34f584](https://github.com/roblockwood/Shatter-NC/commit/c34f584c3f872edcd43e11431db7e19924742452))
* **frontend:** tablet panel layout, mode separator, file manager coercions (v0.14.1) ([553f9a3](https://github.com/roblockwood/Shatter-NC/commit/553f9a3a4359ccfcad1ca8466804e3f7daceac17))
* **frontend:** theme notify/sync form controls ([3c42e6b](https://github.com/roblockwood/Shatter-NC/commit/3c42e6b9d32b7402aeea2c0408d62497fa9be0f6))
* **frontend:** theme shared Select on sync/notify pages ([cc2a216](https://github.com/roblockwood/Shatter-NC/commit/cc2a216cec1952e36a2d7fb8ddf6ab7c90ab0751))
* **frontend:** use shared Select for sync/notify dropdown theming ([ad75079](https://github.com/roblockwood/Shatter-NC/commit/ad750798552efdea316eed19b5e6597fc7960cfe))
* **ftp-sync:** dedupe remote file entries during recursive listing ([c43a7c9](https://github.com/roblockwood/Shatter-NC/commit/c43a7c9bd45a2a79e6e9022a5d66addfd6471cd3))
* improve control version detection in PRD3 parser and telnet client ([9085899](https://github.com/roblockwood/Shatter-NC/commit/9085899d7a4b0acb0cba8147f5de359d6e24e73e))
* improve machine polling logic and event logging ([c9bbbca](https://github.com/roblockwood/Shatter-NC/commit/c9bbbca6eca2b4d922991caadcc7e80c9ae66cf1))
* include ftp_sync_enabled in MachineCard edit cancel fallback ([b61312a](https://github.com/roblockwood/Shatter-NC/commit/b61312a0bdf8ebdf39373d80f4495d9c7705d8f7))
* make Kaeser sidecar image buildable ([998028e](https://github.com/roblockwood/Shatter-NC/commit/998028edf3e71649c757e11bef9e72c43fa2bc85))
* normalize API error messages and update default machine path ([24e525c](https://github.com/roblockwood/Shatter-NC/commit/24e525c6aca73eb602a9fa1a1f655db20730c20b))
* prevent CM7522 on ALL LOD commands, not just TOLNI1 ([fceac05](https://github.com/roblockwood/Shatter-NC/commit/fceac05f7897f5f27d2a8c271451285b18c425d8))
* publish install images to public ghcr namespace ([614abf6](https://github.com/roblockwood/Shatter-NC/commit/614abf6909ef12c6cbfcb58fe6b95472e1dafbf3))
* PWA icons + viewport safe-area; nginx manifest no-cache ([471493d](https://github.com/roblockwood/Shatter-NC/commit/471493dd107ecc868f0cbc9c731ea9e65565a3ad))
* PWA manifest start_url targets tablet route (build-time overrides) ([c9a108a](https://github.com/roblockwood/Shatter-NC/commit/c9a108a8e825e896fdef1b7846176f63cae24d1e))
* resolve all ESLint errors — 0 errors remaining ([634ecbe](https://github.com/roblockwood/Shatter-NC/commit/634ecbec743ba649b3323d285a43971d7d32c913))
* resolve all ESLint warnings — 0 problems remaining ([390e85e](https://github.com/roblockwood/Shatter-NC/commit/390e85eaa4b9a2b37be837bb3bceeea77937987d))
* resolve all TypeScript errors blocking Docker frontend image build ([848e163](https://github.com/roblockwood/Shatter-NC/commit/848e16358931089d96d29566844b17315be6d098))
* resolve correct deployment for NC header fetch on cycle start ([6e32c7c](https://github.com/roblockwood/Shatter-NC/commit/6e32c7c34cdac75c86f452dc577b6896acc8f7b5))
* resolve issue with environment variable generation in install kit ([5ac0d01](https://github.com/roblockwood/Shatter-NC/commit/5ac0d0188ac5ffad4823c4630955ea8dfca18843))
* resolve safe ESLint violations (no-unused-vars, no-case-declarations, no-prototype-builtins, etc.) ([6451723](https://github.com/roblockwood/Shatter-NC/commit/64517232b7a3ac59c218d61c232f4dd84e8aeaf9))
* revert fleet grid stretch rules so dashboard cards and expanded view scroll ([a972e8e](https://github.com/roblockwood/Shatter-NC/commit/a972e8efabc4fe926b0a65fbc8dbfba0404d25cf))
* **runtime:** harden telnet/http/websocket handling and migration startup ([23737ca](https://github.com/roblockwood/Shatter-NC/commit/23737ca424e35f28da0a43aa17ad0682f6c08453))
* serve web manifest with correct MIME so PWA standalone applies ([ad5ec33](https://github.com/roblockwood/Shatter-NC/commit/ad5ec33398875412875a3e451989d4fe9a4c16d4))
* set PYTHONPATH for pytest in CI; narrow units select type ([98f8d73](https://github.com/roblockwood/Shatter-NC/commit/98f8d732a479a1abdd266fb257c7bbe8247f9aaf))
* stretch dashboard machine cards and tablet panes to fill viewport ([58d952e](https://github.com/roblockwood/Shatter-NC/commit/58d952ea988e38aa82150dab536595a26d97aa6c))
* treat background alarms correctly — use stop_level >= 4 to determine machine-halting alarms ([0f22378](https://github.com/roblockwood/Shatter-NC/commit/0f2237845624f1a1fa9bdf01475b4f72aeca347c))
* update rate limit middleware to return JSON response instead of raising HTTPException; add last successful fast poll tracking in MachinePoller; adjust tests accordingly ([9f03e17](https://github.com/roblockwood/Shatter-NC/commit/9f03e17d562f3f1d3033e7d2f0a3f2a13fbd1c8c))


### Features

* add ATC optimizer endpoint and sync/notify parity ([0819589](https://github.com/roblockwood/Shatter-NC/commit/0819589830e93e0ee8d2c62c7b2a5f7f0a658602))
* Add collapsable tool/WCS tables to file browser ([c2130cf](https://github.com/roblockwood/Shatter-NC/commit/c2130cf9c61c368a8199d32e54e17274134b5c58))
* add compressor integration with Kaeser SIGMA CONTROL 2 ([c717961](https://github.com/roblockwood/Shatter-NC/commit/c7179610e8889d0690bf62d73e7ca16ee8c6d046))
* add install kit for Shatter-NC with public packages and Komodo support ([425a415](https://github.com/roblockwood/Shatter-NC/commit/425a4152e3efb3b5daf579ad2b1b33507b6b310f))
* add optional MQTT publishing for compressor telemetry ([d0aa00c](https://github.com/roblockwood/Shatter-NC/commit/d0aa00c5ccc83123357affd9c58ee3c48c7e303d))
* add per-operation speed/feed data capture to NC parser ([9517359](https://github.com/roblockwood/Shatter-NC/commit/9517359d3930604f952be5c169a6ad948cf16ce5)), closes [#500](https://github.com/roblockwood/Shatter-NC/issues/500) [-#509](https://github.com/-/issues/509)
* add tablet kiosk route for single machine view ([fe21d2e](https://github.com/roblockwood/Shatter-NC/commit/fe21d2e6cd8d63a6f3444bf709121a87cc219adc))
* add Vitest frontend test framework with initial tests ([4088af3](https://github.com/roblockwood/Shatter-NC/commit/4088af3b05bf78e819a50a20e1d3b8aa44a397c2))
* add web app manifest with display standalone for PWA ([8b97964](https://github.com/roblockwood/Shatter-NC/commit/8b97964d4d2e91fa9df375256f3bca4b0d74d42a))
* enhance machine management and connection handling ([7df4c2f](https://github.com/roblockwood/Shatter-NC/commit/7df4c2fdc87d7f8cde89f6e66154f225465ea35b))
* enhance MachinePoller with online status management ([f13bf02](https://github.com/roblockwood/Shatter-NC/commit/f13bf02d6e57d22863194b2e5964a9984f7219a3))
* enhance StatusTimeline component and machine polling configuration ([3a76a33](https://github.com/roblockwood/Shatter-NC/commit/3a76a336ab0b20fd856daf14320116f8801565fd))
* enhance telemetry and oscilloscope components for improved time axis management ([4d84b1f](https://github.com/roblockwood/Shatter-NC/commit/4d84b1fd55f2190f0fe22f26f66ad5671557721e))
* enhance ToolsPane and ColorSelect components for improved read-only functionality ([3b07afe](https://github.com/roblockwood/Shatter-NC/commit/3b07afe5ece798c1e0899b7fd801ff7476d18e15))
* enhance ToolsPane and MachineCard components for improved hover preview and color functionality ([72e3509](https://github.com/roblockwood/Shatter-NC/commit/72e35098bf7f303811475505b26e25b23757410a))
* expose Kaeser compressor dashboard UI outside beta mode ([2d9719d](https://github.com/roblockwood/Shatter-NC/commit/2d9719d0db0abbed70395133b2c35e0669812c39))
* **frontend:** add oscilloscope oscillation user toggle ([75af1ce](https://github.com/roblockwood/Shatter-NC/commit/75af1ceeb183bdfa93579f6f3d4bc74f2441a214))
* **frontend:** cycle oscilloscope trace mode (mono/osc/color) ([007d54d](https://github.com/roblockwood/Shatter-NC/commit/007d54de1caad73d03956089993ed8f8e7b983c4))
* **frontend:** tablet kiosk, compressor shell, and terminal/pane polish ([39f64d2](https://github.com/roblockwood/Shatter-NC/commit/39f64d218a5c64d3e80e1df5b6f2d199f2314804))
* implement cycle history feature in frontend and backend ([0a314f3](https://github.com/roblockwood/Shatter-NC/commit/0a314f3216b834ea2e883866140fff699d5c2e62))
* implement Kaeser sidecar integration for enhanced compressor data handling ([93555ac](https://github.com/roblockwood/Shatter-NC/commit/93555ac0f728179602b73e6a099f8f25085d4552))
* implement production runs feature in frontend and backend ([dd64183](https://github.com/roblockwood/Shatter-NC/commit/dd64183a818ea1b83f0aa5ba66fbacaa61adcb36))
* implement real-time file upload with progress tracking and 5s highlight ([bd32283](https://github.com/roblockwood/Shatter-NC/commit/bd3228390792f13122d381c7df98228451dba83a))
* improve compressor telemetry visualization and data handling ([32d7a85](https://github.com/roblockwood/Shatter-NC/commit/32d7a85473cb2c59110c17a2a102d7d32656a8c2))
* merge add machine and add compressor cards on dashboard ([002e8cf](https://github.com/roblockwood/Shatter-NC/commit/002e8cf77e1c5f3224131ea377e84ef1d3196d7f))
* migrate Kaeser integration to backend-direct SC2 client ([9c05cd9](https://github.com/roblockwood/Shatter-NC/commit/9c05cd96c44d588793fdd10c6d0aa64c7e22aa60))
* move FTP sync to machine edit with beta gating ([0033fbe](https://github.com/roblockwood/Shatter-NC/commit/0033fbe9cf2410e47b0f6d3ce5ca8b63baab7d85))
* per-tablet machine id via localStorage and setup UI ([55e11c9](https://github.com/roblockwood/Shatter-NC/commit/55e11c995fd9d4f3a5deb2d026bc8ca918d7335d))
* **platform:** add FTP sync and notifications services, APIs, UI, and migrations ([d290556](https://github.com/roblockwood/Shatter-NC/commit/d290556e1f10f624ef97d6e6699bbc050eaf0909))
* preserve last successful fast poll time in websocket status updates ([85e42bf](https://github.com/roblockwood/Shatter-NC/commit/85e42bf5cc35f830c3467a93b1c830fa248137d7))
* show machine and compressor IDs on edit forms ([30c0554](https://github.com/roblockwood/Shatter-NC/commit/30c055433b58876380f3592f040cd36c8c067176))
* Show machine tool/WCS data when not parsed from NC ([7f2bd8b](https://github.com/roblockwood/Shatter-NC/commit/7f2bd8b51befebc3b652cf2d1ee5e373e4636197))
* swipe left/right to change tablet detail panes ([cd39e00](https://github.com/roblockwood/Shatter-NC/commit/cd39e00a88c1c349ca34b09b6e4d4ba8005d2662))
* tablet kiosk URLs with per-pane routes and bottom nav ([5b11117](https://github.com/roblockwood/Shatter-NC/commit/5b111170838ec1d219dacd3bd255e58bc1bcb9d9))
* **tablet:** kiosk panel layout, compressor chart tuning, screensaver idle ([7933a91](https://github.com/roblockwood/Shatter-NC/commit/7933a919745321b76dea90aa38ce0b0cdafd1b1c))
* **tablet:** overview panes, layout tuning, and program stability ([eee36d2](https://github.com/roblockwood/Shatter-NC/commit/eee36d23ec828150d33ffb4f331efcc423f73aff)), closes [#101](https://github.com/roblockwood/Shatter-NC/issues/101)
* Update file detail view to use collapsable tool/WCS tables ([2f1bee3](https://github.com/roblockwood/Shatter-NC/commit/2f1bee30616656dac9a0dca07dd2a8ba76ba11af))
* update license to GNU Affero General Public License v3 and add Chapter 6 Macro documentation ([1aa996f](https://github.com/roblockwood/Shatter-NC/commit/1aa996f6033432fd336b5c2c58aa695a0abb1ba7))
* update PRD3 status history endpoint and frontend to support 7-day intervals ([5be41c4](https://github.com/roblockwood/Shatter-NC/commit/5be41c4f701c8f63330434e5effe295100704509))
* **validation:** add machine control/toggles and fix current-program tool/path validation behavior ([79dea63](https://github.com/roblockwood/Shatter-NC/commit/79dea63c798a737c97efdffdf57d8694c1fd6786))

# [0.23.0](https://github.com/roblockwood/Shatter-NC/compare/v0.22.0...v0.23.0) (2026-07-14)


### Features

* expose Kaeser compressor dashboard UI outside beta mode ([3b0b45f](https://github.com/roblockwood/Shatter-NC/commit/3b0b45fbde74539d1be336176703690bce3e28e6))

# [0.22.0](https://github.com/roblockwood/Shatter-NC/compare/v0.21.0...v0.22.0) (2026-05-24)


### Bug Fixes

* include ftp_sync_enabled in MachineCard edit cancel fallback ([0e01051](https://github.com/roblockwood/Shatter-NC/commit/0e0105149599bf752dd6ee3119d1c766633ad2ba))


### Features

* merge add machine and add compressor cards on dashboard ([a0ad377](https://github.com/roblockwood/Shatter-NC/commit/a0ad377d5e10eb7d9897f1444114af38ef62419c))
* move FTP sync to machine edit with beta gating ([33d9606](https://github.com/roblockwood/Shatter-NC/commit/33d960695e52e074f116399bfdcb740339cf4c25))

# [0.21.0](https://github.com/roblockwood/Shatter-NC/compare/v0.20.3...v0.21.0) (2026-04-26)


### Features

* add ATC optimizer endpoint and sync/notify parity ([409e3bf](https://github.com/roblockwood/Shatter-NC/commit/409e3bfc9175f07d010102b86090f8b7f0b5e8ff))

## [0.20.3](https://github.com/roblockwood/Shatter-NC/compare/v0.20.2...v0.20.3) (2026-04-26)


### Bug Fixes

* **frontend:** beta-gate AUTO control type and theme file selects ([725c326](https://github.com/roblockwood/Shatter-NC/commit/725c32614598e6bbb5d61463f2109661d5e146c3))
* **frontend:** theme shared Select on sync/notify pages ([2d4d4e1](https://github.com/roblockwood/Shatter-NC/commit/2d4d4e1a1a507655ce7fa889405929e29412c371))
* **frontend:** use shared Select for sync/notify dropdown theming ([fb00799](https://github.com/roblockwood/Shatter-NC/commit/fb00799a0e6101ef2d85ec130c62541bb3f38671))

## [0.20.2](https://github.com/roblockwood/Shatter-NC/compare/v0.20.1...v0.20.2) (2026-04-26)


### Bug Fixes

* **frontend:** add web app manifest ([d8307a6](https://github.com/roblockwood/Shatter-NC/commit/d8307a66167312c2e3730f3f694ab6b7fe3be978))

## [0.20.1](https://github.com/roblockwood/Shatter-NC/compare/v0.20.0...v0.20.1) (2026-04-26)


### Bug Fixes

* **frontend:** restore tablet kiosk routes and hide header ([c5f32e5](https://github.com/roblockwood/Shatter-NC/commit/c5f32e53f8b112f86783b85b7bb0698d16ed2ba7))

# [0.20.0](https://github.com/roblockwood/Shatter-NC/compare/v0.19.0...v0.20.0) (2026-04-26)


### Bug Fixes

* **frontend:** theme notify/sync form controls ([ec5ff73](https://github.com/roblockwood/Shatter-NC/commit/ec5ff73c3b5cc440ce3e9f0ad565e48d2910fb7c))


### Features

* **frontend:** cycle oscilloscope trace mode (mono/osc/color) ([c0ad238](https://github.com/roblockwood/Shatter-NC/commit/c0ad238885851c43f967d9aafae527e7c83eaf59))

# [0.19.0](https://github.com/roblockwood/Shatter-NC/compare/v0.18.0...v0.19.0) (2026-04-26)


### Bug Fixes

* **frontend:** remove unused locals blocking TS build ([e23f24b](https://github.com/roblockwood/Shatter-NC/commit/e23f24b50cb7681feb5c8f4e112cca6fa3b65210))
* **ftp-sync:** dedupe remote file entries during recursive listing ([3194ecb](https://github.com/roblockwood/Shatter-NC/commit/3194ecb5e2534268f6a9841c0ba08deb2a5907e9))


### Features

* **frontend:** add oscilloscope oscillation user toggle ([c9ce34a](https://github.com/roblockwood/Shatter-NC/commit/c9ce34adfda10d27315d14ae6a479fdf4ead46c4))
* **platform:** add FTP sync and notifications services, APIs, UI, and migrations ([b0b19e9](https://github.com/roblockwood/Shatter-NC/commit/b0b19e98a58851c29ceb3085adb35157ab047236))
* **validation:** add machine control/toggles and fix current-program tool/path validation behavior ([aef35f5](https://github.com/roblockwood/Shatter-NC/commit/aef35f5d5618cb766480ffd2de80e6372a60e8b0))

# [0.18.0](https://github.com/roblockwood/Shatter-NC/compare/v0.17.2...v0.18.0) (2026-04-26)


### Bug Fixes

* address exhaustive-deps warnings (partial) ([32632fa](https://github.com/roblockwood/Shatter-NC/commit/32632fa072166846b123d424f7753c399e453d60))
* **backend:** add time_utils module for CNC time formatting ([cbd403a](https://github.com/roblockwood/Shatter-NC/commit/cbd403ae3f9b568c899a8cacfa0e2d21e59eee63))
* eliminate no-explicit-any violations in frontend (68 fixed) ([d549f2f](https://github.com/roblockwood/Shatter-NC/commit/d549f2f7bc8830fd2dbfb729079f8ddf0d05a314))
* resolve all ESLint errors — 0 errors remaining ([71d5967](https://github.com/roblockwood/Shatter-NC/commit/71d59675f55df1ef273327c09283dac74b1f999f))
* resolve all ESLint warnings — 0 problems remaining ([afc50a2](https://github.com/roblockwood/Shatter-NC/commit/afc50a2c5f764ef74d6e191a0b2a560366f07e1c))
* resolve all TypeScript errors blocking Docker frontend image build ([e7d9fba](https://github.com/roblockwood/Shatter-NC/commit/e7d9fba97ec4da6149180aab382174040a72c50f))
* resolve safe ESLint violations (no-unused-vars, no-case-declarations, no-prototype-builtins, etc.) ([b0c77a8](https://github.com/roblockwood/Shatter-NC/commit/b0c77a8a867ecfdf3afa6590eea1227b749c4e7e))
* set PYTHONPATH for pytest in CI; narrow units select type ([c8b15b4](https://github.com/roblockwood/Shatter-NC/commit/c8b15b4cc86c30821a85c0efc1dd83c0fcf9b15c))


### Features

* add Vitest frontend test framework with initial tests ([868d339](https://github.com/roblockwood/Shatter-NC/commit/868d33958dc627cc373ed54063608f3e94c98ec3))

## [0.17.2](https://github.com/roblockwood/Shatter-NC/compare/v0.17.1...v0.17.2) (2026-04-26)


### Bug Fixes

* resolve correct deployment for NC header fetch on cycle start ([55437f6](https://github.com/roblockwood/Shatter-NC/commit/55437f6e2f8c44291557fe925418ec87ce8a2f60))
* **runtime:** harden telnet/http/websocket handling and migration startup ([1ce565c](https://github.com/roblockwood/Shatter-NC/commit/1ce565c56532936619f91aa1e695a466d402d9a9))
* treat background alarms correctly — use stop_level >= 4 to determine machine-halting alarms ([b6ae30b](https://github.com/roblockwood/Shatter-NC/commit/b6ae30b700d82da5814b77199d469e8728008692))

## [0.17.1](https://github.com/roblockwood/Shatter-NC/compare/v0.17.0...v0.17.1) (2026-04-26)


### Bug Fixes

* prevent CM7522 on ALL LOD commands, not just TOLNI1 ([94ae4ac](https://github.com/roblockwood/Shatter-NC/commit/94ae4ac0fe70ff30fa67fecf9738a69864dd289f))

# [0.17.0](https://github.com/roblockwood/Shatter-NC/compare/v0.16.0...v0.17.0) (2026-04-18)


### Bug Fixes

* **frontend:** self-host mono fonts for SHATTER logo alignment ([07b9ead](https://github.com/roblockwood/Shatter-NC/commit/07b9ead46f55cacfe03751dd71d4c7db7bdc6147))
* **frontend:** tablet kiosk pane fill and overview grid layouts ([1d0a480](https://github.com/roblockwood/Shatter-NC/commit/1d0a4804b10988d3854f2f417c378e30fed59f59))


### Features

* **tablet:** overview panes, layout tuning, and program stability ([fd52b81](https://github.com/roblockwood/Shatter-NC/commit/fd52b81691adcb166bcd97e5484e17e312f84585)), closes [#101](https://github.com/roblockwood/Shatter-NC/issues/101)

## Unreleased

### Features

* **tablet:** CNC and compressor kiosk routes add an **OVERVIEW** pane (compact dashboard-style summary) as the first bottom-nav item and default when opening `/tablet/:id` or `/tablet/compressor/:id`; compressor overview rows navigate when opened from tablet routes.
* **tablet:** OVERVIEW panes surface **PRD3 intervals**, **recent production runs** (up to four), **program poll fields** (cycle time, MEM mode/op), **alarm text lines**, **compressor state history**, and **alarm details** so tablet users get context without hover.

### Bug Fixes

* **frontend:** tablet kiosk shell fills embedded/split layouts (html/body/`#root` flex chain); CNC overview and panel/alarm grids use stretch row sizing and wide breakpoints; CNC-only alarm grid rules exclude `.compressor-terminal-pane` so Kaeser panes keep flex layouts.

# [0.16.0](https://github.com/roblockwood/Shatter-NC/compare/v0.15.1...v0.16.0) (2026-04-18)


### Features

* **tablet:** kiosk panel layout, compressor chart tuning, screensaver idle ([926a87b](https://github.com/roblockwood/Shatter-NC/commit/926a87b8f034a984ec2fb560f9605389d8b79bd5))

## [0.15.1](https://github.com/roblockwood/Shatter-NC/compare/v0.15.0...v0.15.1) (2026-04-18)


### Bug Fixes

* **frontend:** tablet panel chrome, fluid overrides, slider colors (v0.14.2) ([5acb664](https://github.com/roblockwood/Shatter-NC/commit/5acb664a948a754ca9ceac7681711d7031e898f0))
* **frontend:** tablet panel layout, mode separator, file manager coercions (v0.14.1) ([7c165fa](https://github.com/roblockwood/Shatter-NC/commit/7c165fa56b1d9ebc43bbaf7be744cfc31167e899))

# [0.15.0](https://github.com/roblockwood/Shatter-NC/compare/v0.14.0...v0.15.0) (2026-04-18)


### Bug Fixes

* PWA icons + viewport safe-area; nginx manifest no-cache ([58d6e59](https://github.com/roblockwood/Shatter-NC/commit/58d6e591dd2688d0dd501653f82a50172eda3221))
* PWA manifest start_url targets tablet route (build-time overrides) ([1714e00](https://github.com/roblockwood/Shatter-NC/commit/1714e00f058283986c732fb5e935fd65e9e73407))
* revert fleet grid stretch rules so dashboard cards and expanded view scroll ([4ab29b2](https://github.com/roblockwood/Shatter-NC/commit/4ab29b2e3887ba97ebb95a982465068673008af3))
* serve web manifest with correct MIME so PWA standalone applies ([b9c69ab](https://github.com/roblockwood/Shatter-NC/commit/b9c69ab9dd7461d4d9fbacc7bd7fb28aa1267cba))
* stretch dashboard machine cards and tablet panes to fill viewport ([8951028](https://github.com/roblockwood/Shatter-NC/commit/8951028909c743eb2d0c6a53ae7d4d2b0a6d7e1d))
* **tablet:** restore full panel terminal chrome (ASCII title row and footer) and in-panel section/subsection titles on kiosk routes; align compressor panel header with the same treatment.
* **tablet:** panel sections stack in portrait and in panes narrower than 700px; restore multi-column layout in wide landscape via container queries and a higher grid min track width.
* **panel:** add a visual separator between MODE/SCREEN text and switch LED groups; drop extra margin under the info row now that the divider provides spacing.
* **panel:** overrides section uses an inline-size container and fluid `clamp` / `cqw` scaling for vertical sliders so narrow columns stay readable in multi-column layouts.
* **panel:** fix slider segment and value-box colors after fluid overrides CSS raised selector specificity (restore grey/orange/yellow/green/red styling).
* **file manager:** coerce tool validation numbers (including JSON string values) before formatting; tolerate optional tolerances safely; reduce accidental row activation from touch event bubbling on tablet.


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
