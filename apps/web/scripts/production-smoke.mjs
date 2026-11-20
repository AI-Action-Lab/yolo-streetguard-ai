const [appUrlValue, apiUrlValue] = process.argv.slice(2);

if (!appUrlValue || !apiUrlValue) {
  console.error("Usage: npm run smoke:production -- <app-https-url> <api-https-origin>");
  process.exit(2);
}

function requireHttps(value, label) {
  const url = new URL(value);
  if (url.protocol !== "https:") {
    throw new Error(`${label} must use HTTPS`);
  }
  return url;
}

async function check(url, label, expectedStatus = 200) {
  const response = await fetch(url, {
    redirect: "manual",
    signal: AbortSignal.timeout(10_000),
  });
  if (response.status !== expectedStatus) {
    await response.body?.cancel();
    throw new Error(`${label} returned HTTP ${response.status}`);
  }
  if (!response.headers.get("strict-transport-security")?.includes("max-age=")) {
    await response.body?.cancel();
    throw new Error(`${label} is missing the HSTS response header`);
  }
  return response;
}

try {
  const appUrl = requireHttps(appUrlValue, "App URL");
  appUrl.pathname = "/";
  appUrl.search = "";
  appUrl.hash = "";

  const apiUrl = requireHttps(apiUrlValue, "API URL");
  apiUrl.pathname = "/api/v1/health/live";
  apiUrl.search = "";
  apiUrl.hash = "";

  const appResponse = await check(appUrl, "Frontend");
  await appResponse.body?.cancel();
  console.log("PASS frontend HTTPS");

  const liveResponse = await check(apiUrl, "API liveness");
  const live = await liveResponse.json();
  if (live.status !== "ok") {
    throw new Error("API liveness returned an unexpected response");
  }
  console.log("PASS API liveness");

  apiUrl.pathname = "/api/v1/health/ready";
  const readyResponse = await check(apiUrl, "API readiness");
  const ready = await readyResponse.json();
  if (ready.status !== "ready") {
    throw new Error("API readiness returned an unexpected response");
  }
  console.log("PASS API and database readiness");
} catch (error) {
  console.error(`FAIL production smoke: ${error.message}`);
  process.exitCode = 1;
}
