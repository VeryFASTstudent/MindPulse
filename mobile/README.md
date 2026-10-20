# MindPulse Flutter client

The mobile client provides the student workflow (dashboard, check-in, private
chat, trends, counselor support, and privacy profile) plus role-specific
counselor, parent, and university-admin dashboards. It connects to the FastAPI
backend; start and configure the backend as described in
[`../README.md`](../README.md) before using authenticated screens.

The default web API URL is `http://127.0.0.1:8000`. Android emulators use
`http://10.0.2.2:8000`; physical-device development requires the host machine's
LAN IP in `lib/core/constants.dart`.

```powershell
flutter pub get
flutter run -d web-server --web-port 8080
flutter analyze
flutter test
```
