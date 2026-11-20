"use client";

import { ArrowLeft, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { AssignedReport, operationsApi } from "../lib/operations-api";

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected authority portal error";
}

export function AuthorityPortal() {
  const [accessToken, setAccessToken] = useState("");
  const [connectedToken, setConnectedToken] = useState("");
  const [reports, setReports] = useState<AssignedReport[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const connect = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const token = accessToken.trim();
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setReports(await operationsApi.authorityReports(token));
      setConnectedToken(token);
      setAccessToken("");
    } catch (cause: unknown) {
      setError(messageFrom(cause));
    } finally {
      setLoading(false);
    }
  };

  const reload = async () => {
    if (!connectedToken) return;
    setLoading(true);
    setError("");
    try {
      setReports(await operationsApi.authorityReports(connectedToken));
    } catch (cause: unknown) {
      setError(messageFrom(cause));
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (report: AssignedReport, status: "in_progress" | "resolved") => {
    const note = notes[report.public_id]?.trim() ?? "";
    if (note.length < 3) {
      setError("Enter a short work update before changing the report status.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const updated = await operationsApi.updateAuthorityReport(
        connectedToken,
        report.public_id,
        status,
        note,
      );
      setReports((current) =>
        current.map((item) => item.public_id === report.public_id ? updated : item),
      );
      setNotes((current) => ({ ...current, [report.public_id]: "" }));
    } catch (cause: unknown) {
      setError(messageFrom(cause));
    } finally {
      setLoading(false);
    }
  };

  const disconnect = () => {
    setAccessToken("");
    setConnectedToken("");
    setReports([]);
    setNotes({});
    setError("");
  };

  return (
    <main className="authority-page">
      <header className="authority-header">
        <Link href="/" className="authority-back"><ArrowLeft size={16} /> India map</Link>
        <span className="authority-scope">AUTHORITY PORTAL · RESTRICTED</span>
      </header>
      <section className="authority-intro">
        <p className="eyebrow">ASSIGNED ROAD ISSUES</p>
        <h1>Authority portal</h1>
        <p>View reports assigned to your verified authority and record work progress or resolution.</p>
      </section>

      <section className="portal-access">
        <form onSubmit={connect} className="portal-access-form">
          <label htmlFor="authority-access-token">Short-lived OIDC access token</label>
          <input
            id="authority-access-token"
            type="password"
            autoComplete="off"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder="Paste access token"
            disabled={Boolean(connectedToken)}
          />
          {connectedToken ? (
            <>
              <button type="button" className="secondary-button" onClick={() => void reload()} disabled={loading}>
                <RefreshCw size={15} /> Refresh
              </button>
              <button type="button" className="text-button" onClick={disconnect}>Disconnect</button>
            </>
          ) : (
            <button type="submit" className="primary-button" disabled={loading || !accessToken.trim()}>
              {loading ? "Connecting…" : "Connect"}
            </button>
          )}
        </form>
        <p>Token stays in this page’s memory only and is cleared on disconnect or reload. Never paste an ID token.</p>
      </section>

      {error && <p className="portal-error" role="alert">{error}</p>}
      {connectedToken && (
        <section className="portal-card-list" aria-label="Assigned reports">
          {reports.length === 0 ? (
            <section className="authority-empty">
              <b>No reports are assigned to your authority.</b>
              <p>New assignments will appear after a global administrator routes a verified report.</p>
            </section>
          ) : (
            reports.map((report) => (
              <article className="portal-card" key={report.assignment_id}>
                <p className="authority-category">{report.public_id} · {report.authority_name}</p>
                <h2>{report.title ?? "Road damage report"}</h2>
                <p>{report.description ?? "No additional report description."}</p>
                <dl className="portal-report-details">
                  <div><dt>Status</dt><dd>{report.status.replaceAll("_", " ")}</dd></div>
                  <div><dt>Severity estimate</dt><dd>{report.severity ?? "Unavailable"}</dd></div>
                  <div><dt>Location</dt><dd>{report.location_address ?? "Address unavailable"}</dd></div>
                  <div><dt>Coordinates</dt><dd>{report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}</dd></div>
                  <div><dt>Assigned</dt><dd>{new Date(report.assigned_at).toLocaleString()}</dd></div>
                  {report.completed_at && (
                    <div><dt>Completed</dt><dd>{new Date(report.completed_at).toLocaleString()}</dd></div>
                  )}
                </dl>
                <label>
                  Work update / resolution note
                  <textarea
                    value={notes[report.public_id] ?? ""}
                    onChange={(event) =>
                      setNotes((current) => ({ ...current, [report.public_id]: event.target.value }))
                    }
                    minLength={3}
                    maxLength={2000}
                    rows={3}
                    disabled={report.status === "resolved"}
                  />
                </label>
                {report.status === "assigned_to_authority" && (
                  <button
                    type="button"
                    className="primary-button"
                    disabled={loading}
                    onClick={() => void updateStatus(report, "in_progress")}
                  >
                    <ShieldCheck size={15} /> Start work
                  </button>
                )}
                {report.status === "in_progress" && (
                  <button
                    type="button"
                    className="primary-button"
                    disabled={loading}
                    onClick={() => void updateStatus(report, "resolved")}
                  >
                    <ShieldCheck size={15} /> Mark resolved
                  </button>
                )}
              </article>
            ))
          )}
        </section>
      )}
      {!connectedToken && !error && (
        <section className="authority-empty">
          <b>Authority access required</b>
          <p>Connect with a short-lived access token carrying the municipal authority role and active authority membership.</p>
        </section>
      )}
    </main>
  );
}
