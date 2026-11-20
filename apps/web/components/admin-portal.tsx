"use client";

import { ArrowLeft, ClipboardList, RefreshCw, ShieldCheck, UserPlus, X } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { api, Authority } from "../lib/api";
import {
  AdminReport,
  AuditEntry,
  AuthorityMember,
  operationsApi,
} from "../lib/operations-api";

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Unexpected administration error";
}

export function AdminPortal() {
  const [accessToken, setAccessToken] = useState("");
  const [connectedToken, setConnectedToken] = useState("");
  const [authorities, setAuthorities] = useState<Authority[]>([]);
  const [reports, setReports] = useState<AdminReport[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [selectedAuthority, setSelectedAuthority] = useState("");
  const [members, setMembers] = useState<AuthorityMember[]>([]);
  const [memberSubject, setMemberSubject] = useState("");
  const [authorityByReport, setAuthorityByReport] = useState<Record<string, string>>({});
  const [notesByReport, setNotesByReport] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAdminData = async (token: string) => {
    setLoading(true);
    setError("");
    try {
      const [reportRows, logs, authorityRows] = await Promise.all([
        operationsApi.adminReports(token),
        operationsApi.auditLogs(token),
        api.authorities(),
      ]);
      setReports(reportRows);
      setAuditLogs(logs);
      setAuthorities(authorityRows);
      setSelectedAuthority((current) =>
        authorityRows.some((authority) => authority.id === current)
          ? current
          : authorityRows[0]?.id || "",
      );
      setConnectedToken(token);
      setAccessToken("");
    } catch (cause: unknown) {
      setError(messageFrom(cause));
    } finally {
      setLoading(false);
    }
  };

  const connect = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const token = accessToken.trim();
    if (token) void loadAdminData(token);
  };

  const reload = () => {
    if (connectedToken) void loadAdminData(connectedToken);
  };

  useEffect(() => {
    if (!connectedToken || !selectedAuthority) {
      setMembers([]);
      return;
    }
    let active = true;
    operationsApi
      .authorityMembers(connectedToken, selectedAuthority)
      .then((rows) => {
        if (active) setMembers(rows);
      })
      .catch((cause: unknown) => {
        if (active) setError(messageFrom(cause));
      });
    return () => {
      active = false;
    };
  }, [connectedToken, selectedAuthority]);

  const assignReport = async (report: AdminReport) => {
    const authorityId = authorityByReport[report.public_id];
    if (!connectedToken || !authorityId) {
      setError("Select a verified authority before assigning the report.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await operationsApi.assignReport(
        connectedToken,
        report.public_id,
        authorityId,
        notesByReport[report.public_id] ?? "",
      );
      await loadAdminData(connectedToken);
    } catch (cause: unknown) {
      setError(messageFrom(cause));
      setLoading(false);
    }
  };

  const addMember = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!connectedToken || !selectedAuthority || !memberSubject.trim()) return;
    setError("");
    try {
      await operationsApi.addAuthorityMember(
        connectedToken,
        selectedAuthority,
        memberSubject.trim(),
      );
      setMemberSubject("");
      setMembers(await operationsApi.authorityMembers(connectedToken, selectedAuthority));
      setAuditLogs(await operationsApi.auditLogs(connectedToken));
    } catch (cause: unknown) {
      setError(messageFrom(cause));
    }
  };

  const removeMember = async (userId: string) => {
    if (!connectedToken || !selectedAuthority) return;
    setError("");
    try {
      await operationsApi.removeAuthorityMember(connectedToken, selectedAuthority, userId);
      setMembers(await operationsApi.authorityMembers(connectedToken, selectedAuthority));
      setAuditLogs(await operationsApi.auditLogs(connectedToken));
    } catch (cause: unknown) {
      setError(messageFrom(cause));
    }
  };

  const disconnect = () => {
    setAccessToken("");
    setConnectedToken("");
    setReports([]);
    setAuditLogs([]);
    setAuthorities([]);
    setMembers([]);
    setSelectedAuthority("");
    setMemberSubject("");
    setAuthorityByReport({});
    setNotesByReport({});
    setError("");
  };

  return (
    <main className="authority-page">
      <header className="authority-header">
        <Link href="/" className="authority-back"><ArrowLeft size={16} /> India map</Link>
        <span className="authority-scope">ADMINISTRATION · RESTRICTED</span>
      </header>
      <section className="authority-intro">
        <p className="eyebrow">INDIA ROAD OPERATIONS</p>
        <h1>Administration portal</h1>
        <p>
          Assign verified reports, manage authority memberships, and review recent audit events.
          Regional scopes are not configured, so these controls require a global administrator.
        </p>
      </section>

      <section className="portal-access">
        <form onSubmit={connect} className="portal-access-form">
          <label htmlFor="admin-access-token">Short-lived OIDC access token</label>
          <input
            id="admin-access-token"
            type="password"
            autoComplete="off"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder="Paste access token"
            disabled={Boolean(connectedToken)}
          />
          {connectedToken ? (
            <button type="button" className="secondary-button" onClick={disconnect}>Disconnect</button>
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
        <div className="portal-content">
          <div className="portal-heading">
            <h2><ClipboardList size={18} /> Verified report assignment queue</h2>
            <button type="button" className="secondary-button" onClick={reload} disabled={loading}>
              <RefreshCw size={15} /> Refresh
            </button>
          </div>
          {reports.length === 0 ? (
            <section className="authority-empty">
              <b>No verified reports are waiting for assignment.</b>
              <p>Only public, human-verified reports without an existing assignment appear here.</p>
            </section>
          ) : (
            <div className="portal-card-list">
              {reports.map((report) => (
                <article className="portal-card" key={report.public_id}>
                  <p className="authority-category">{report.public_id} · {report.severity ?? "severity unavailable"}</p>
                  <h3>{report.title ?? "Road damage report"}</h3>
                  <p>{report.location_address ?? "Address unavailable"}</p>
                  <div className="portal-form-row">
                    <label>
                      Verified authority
                      <select
                        value={authorityByReport[report.public_id] ?? ""}
                        onChange={(event) =>
                          setAuthorityByReport((current) => ({
                            ...current,
                            [report.public_id]: event.target.value,
                          }))
                        }
                      >
                        <option value="">Select an authority</option>
                        {authorities.map((authority) => (
                          <option key={authority.id} value={authority.id}>
                            {authority.name}{authority.jurisdiction_name ? ` — ${authority.jurisdiction_name}` : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Assignment note (optional)
                      <input
                        value={notesByReport[report.public_id] ?? ""}
                        onChange={(event) =>
                          setNotesByReport((current) => ({
                            ...current,
                            [report.public_id]: event.target.value,
                          }))
                        }
                        maxLength={2000}
                      />
                    </label>
                  </div>
                  <button
                    type="button"
                    className="primary-button"
                    disabled={loading || !authorityByReport[report.public_id]}
                    onClick={() => void assignReport(report)}
                  >
                    <ShieldCheck size={15} /> Assign report
                  </button>
                </article>
              ))}
            </div>
          )}

          <section className="portal-card">
            <h2><UserPlus size={18} /> Authority membership</h2>
            <p>Adding a member does not grant an OIDC role; the identity provider must also grant <code>municipal_authority</code>.</p>
            <label>
              Verified authority
              <select value={selectedAuthority} onChange={(event) => setSelectedAuthority(event.target.value)}>
                <option value="">Select an authority</option>
                {authorities.map((authority) => (
                  <option key={authority.id} value={authority.id}>{authority.name}</option>
                ))}
              </select>
            </label>
            <form className="portal-form-row" onSubmit={addMember}>
              <label>
                Existing user subject
                <input
                  value={memberSubject}
                  onChange={(event) => setMemberSubject(event.target.value)}
                  maxLength={255}
                  required
                />
              </label>
              <button type="submit" className="secondary-button" disabled={!selectedAuthority}>
                Add member
              </button>
            </form>
            {members.map((member) => (
              <div className="portal-member" key={member.id}>
                <span><b>{member.user_subject}</b><small>{member.email ?? "No email claim"}</small></span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => void removeMember(member.user_id)}
                  disabled={!member.active}
                  aria-label={`Remove ${member.user_subject}`}
                >
                  {member.active ? "Remove" : "Inactive"}
                </button>
              </div>
            ))}
          </section>

          <section className="portal-card">
            <h2>Recent audit events</h2>
            {auditLogs.length === 0 ? (
              <p>No audit events are recorded yet.</p>
            ) : (
              <div className="portal-audit-list">
                {auditLogs.map((entry) => (
                  <div className="portal-audit-row" key={entry.id}>
                    <span><b>{entry.action}</b><small>{entry.target_type}: {entry.target_id}</small></span>
                    <time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
      {!connectedToken && !error && (
        <section className="authority-empty">
          <b>Administrator access required</b>
          <p>Connect with a short-lived access token carrying the global administrator role.</p>
        </section>
      )}
    </main>
  );
}
