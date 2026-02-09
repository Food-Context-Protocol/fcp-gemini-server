# Deployment Checklist

1. **Verify Firestore credentials before starting services.**
   - Place your Firebase service account key somewhere secure (for example `fcp-service-key.json` at the repo root or outside the repo).
   - Set `GOOGLE_APPLICATION_CREDENTIALS="$PWD/fcp-service-key.json"` before running `make run` or the scheduler routes.

2. **Start the HTTP server and confirm dependencies.**
   - Launch the app (`make run-http`) and then poll the health endpoint:
     ```
     curl http://localhost:8080/health/deps
     ```
   - Wait for a response like `{"status":"healthy","checks":{"gemini":{"healthy":true},"firestore":{"healthy":true,"mode":"firestore"}}}`.
     If Firestore shows unavailable, background jobs remain paused until the credentials become valid.

3. **Ensure scheduling jobs are skipped when Firestore is down.**
   - Check `logs/dev-http.log` for warnings such as `Skipping daily insights job because Firestore unavailable`.
   - Once Firestore becomes available, the logs should resume with `Starting daily insights job`.

4. **Validate Gemini & optional APIs.**
   - Confirm `GEMINI_API_KEY` is set and the `health/deps` response reports Gemini healthy.
   - If you rely on Maps, Storage, or USDA, confirm corresponding env vars are present and the services are reachable.

5. **Run final smoke tests.**
   - Trigger essential routes manually (e.g., `/health`, `/meals`, `/analytics/report`) using curl or the SDK.
   - Optionally, trigger scheduler jobs via `POST /scheduler/trigger/daily_insights` to ensure the guard permits / skips correctly.
