"use client";

import { ArrowLeft, ExternalLink, Mail, MapPin, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api, Authority } from "../lib/api";

export function AuthorityDirectory() {
  const [authorities, setAuthorities] = useState<Authority[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    api
      .authorities()
      .then((records) => {
        if (active) setAuthorities(records);
      })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Could not load authorities");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [reload]);

  return (
    <main className="authority-page">
      <header className="authority-header">
        <Link href="/" className="authority-back">
          <ArrowLeft size={16} /> India map
        </Link>
        <span className="authority-scope">INDIA · VERIFIED DIRECTORY</span>
      </header>

      <section className="authority-intro">
        <p className="eyebrow">ROAD ISSUE CONTACTS</p>
        <h1>Verified authorities</h1>
        <p>
          Only active authorities verified by StreetGuard administrators appear here. A listed
          authority is not a guarantee that it is responsible for a specific road.
        </p>
      </section>

      {loading && <p className="authority-state" role="status">Loading verified authorities…</p>}
      {!loading && error && (
        <div className="authority-state authority-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => setReload((value) => value + 1)}>
            Try again
          </button>
        </div>
      )}
      {!loading && !error && authorities.length === 0 && (
        <section className="authority-empty">
          <span><ShieldCheck size={22} /></span>
          <h2>No verified authorities listed yet</h2>
          <p>
            The directory will show contacts after their jurisdiction and contact details have
            been reviewed. No agency details are inferred or published automatically.
          </p>
        </section>
      )}
      {!loading && !error && authorities.length > 0 && (
        <section className="authority-list" aria-label="Verified authorities">
          {authorities.map((authority) => (
            <article className="authority-card" key={authority.id}>
              <div className="authority-card-icon"><ShieldCheck size={18} /></div>
              <div className="authority-card-content">
                <p className="authority-category">{authority.category}</p>
                <h2>{authority.name}</h2>
                {authority.jurisdiction_name && (
                  <p className="authority-meta"><MapPin size={14} /> {authority.jurisdiction_name}</p>
                )}
                <div className="authority-links">
                  {authority.contact_email && (
                    <a href={`mailto:${authority.contact_email}`}>
                      <Mail size={14} /> {authority.contact_email}
                    </a>
                  )}
                  {authority.website_url && (
                    <a href={authority.website_url} target="_blank" rel="noreferrer">
                      <ExternalLink size={14} /> Official website
                    </a>
                  )}
                </div>
              </div>
              <span className="authority-verified">Verified</span>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
