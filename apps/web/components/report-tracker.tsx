"use client";

import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Image as ImageIcon,
  Mail,
  MapPin,
  MessageCircle,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, PublicReport } from "../lib/api";
import {
  emailComposeUrl,
  publicReportUrl,
  reportShareMessage,
  whatsappShareUrl,
} from "../lib/report-sharing";

type ReportTrackerProps = {
  initialReportId?: string;
};

function messageFrom(error: unknown) {
  if (error instanceof TypeError && error.message.toLowerCase().includes("fetch")) {
    return "The report tracking service is unavailable. Try again later.";
  }
  return error instanceof Error ? error.message : "Report lookup failed";
}

export function ReportTracker({ initialReportId = "" }: ReportTrackerProps) {
  const [query, setQuery] = useState(initialReportId);
  const [report, setReport] = useState<PublicReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [shareOrigin, setShareOrigin] = useState("");

  useEffect(() => {
    setShareOrigin(window.location.origin);
  }, []);

  useEffect(() => {
    if (!initialReportId) return;
    let active = true;
    setLoading(true);
    api
      .trackReport(initialReportId)
      .then((value) => {
        if (active) setReport(value);
      })
      .catch((requestError) => {
        if (active) setError(messageFrom(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [initialReportId]);

  const track = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      setReport(await api.trackReport(query));
    } catch (requestError) {
      setReport(null);
      setError(messageFrom(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="tracking-shell">
      <header className="tracking-nav">
        <Link href="/" className="tracking-back"><ArrowLeft size={16} /> India map</Link>
        <div className="brand"><span className="brand-mark"><ShieldCheck size={19} /></span><span>STREETGUARD</span><b>AI</b></div>
      </header>
      <section className="tracking-hero">
        <p className="eyebrow">PUBLIC REPORT TRACKING</p>
        <h1>Follow verified Indian road damage reports</h1>
        <p>Search by India report ID. Private reporter details and original uploads are never shown.</p>
        <form className="tracking-search" onSubmit={track}>
          <Search size={18} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="SG-IN-XXXXXXXXXXXXXXXXXXXX"
            aria-label="Report ID"
          />
          <button type="submit" disabled={loading}>{loading ? "Searching…" : "Track report"}</button>
        </form>
        {error && <p className="tracking-error">{error}</p>}
      </section>

      {!report ? (
        <section className="tracking-empty">
          <span><Search size={26} /></span>
          <h2>Enter a verified report ID</h2>
          <p>Only reports published after human verification are available on this public page.</p>
        </section>
      ) : (
        <section className="tracking-report">
          <div className="tracking-report-head">
            <div>
              <p className="eyebrow">VERIFIED PUBLIC REPORT</p>
              <h2>{report.public_id}</h2>
              <p>{report.title || "Road damage report"}</p>
            </div>
            <span className={`public-status ${report.status}`}>{report.status.replace("_", " ")}</span>
          </div>
          {shareOrigin && (
            <div className="tracking-share">
              <a
                href={whatsappShareUrl(
                  reportShareMessage(
                    report.public_id,
                    publicReportUrl(shareOrigin, report.public_id),
                  ),
                )}
                target="_blank"
                rel="noopener noreferrer"
              >
                <MessageCircle size={16} /> Share on WhatsApp
              </a>
              <a
                href={emailComposeUrl(
                  report.public_id,
                  reportShareMessage(
                    report.public_id,
                    publicReportUrl(shareOrigin, report.public_id),
                  ),
                )}
              >
                <Mail size={16} /> Share by email
              </a>
              <p>Opens a draft for you to review. StreetGuard does not send messages.</p>
            </div>
          )}
          <div className="tracking-grid">
            <div className="tracking-primary">
              <div className="tracking-image">
                {report.annotated_image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={report.annotated_image_url} alt={`Annotated pothole detections for ${report.public_id}`} />
                ) : (
                  <div><ImageIcon size={30} /><span>Annotated image unavailable</span></div>
                )}
              </div>
              <div className="tracking-summary">
                <div><span>AI detections</span><b>{report.detection_count}</b></div>
                <div><span>Visual severity</span><b>{report.severity.category}</b></div>
                <div><span>Verification</span><b>{report.verification_status}</b></div>
              </div>
              <p className="severity-disclaimer">{report.severity.disclaimer}</p>
            </div>
            <aside className="tracking-aside">
              <h3><MapPin size={17} /> Location</h3>
              <p>{report.location.formatted_address ?? "Address unavailable"}</p>
              <code>{report.location.latitude.toFixed(6)}, {report.location.longitude.toFixed(6)}</code>
              <dl>
                <div><dt>Country</dt><dd>{report.location.components.country ?? "Unavailable"}</dd></div>
                <div><dt>State / province</dt><dd>{report.location.components.state_province ?? "Unavailable"}</dd></div>
                <div><dt>City</dt><dd>{report.location.components.city ?? "Unavailable"}</dd></div>
                <div><dt>Location source</dt><dd>{report.location.source.replace("_", " ")}</dd></div>
              </dl>
              <h3><Calendar size={17} /> Status history</h3>
              <ol className="timeline">
                {report.history.map((item, index) => (
                  <li key={`${item.to_status}-${index}`}>
                    <CheckCircle2 size={15} />
                    <div><b>{item.to_status.replace("_", " ")}</b><span>{new Date(item.occurred_at).toLocaleString()}</span>{item.reason && <p>{item.reason}</p>}</div>
                  </li>
                ))}
              </ol>
            </aside>
          </div>
        </section>
      )}
    </main>
  );
}
