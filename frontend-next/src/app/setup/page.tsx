"use client";

import { useState } from "react";
import Link from "next/link";
import {
  DollarSign,
  ChevronDown,
  ChevronRight,
  Clock,
  Shield,
  Database,
  Cloud,
  Cpu,
  GitBranch,
  BarChart3,
  Zap,
  Check,
} from "lucide-react";

/* ── Helpers ── */

function CodeBlock({ children, dark }: { children: string; dark?: boolean }) {
  return (
    <pre
      className={`rounded-lg px-5 py-4 text-[0.82rem] leading-7 overflow-x-auto mt-3 whitespace-pre-wrap break-all ${
        dark
          ? "bg-slate-900 border border-slate-800 text-slate-200"
          : "bg-slate-50 border border-slate-200 text-slate-900"
      }`}
    >
      {children}
    </pre>
  );
}

function Note({
  children,
  type = "info",
}: {
  children: React.ReactNode;
  type?: "info" | "warn" | "tip" | "danger";
}) {
  const styles = {
    info: "bg-blue-50 border-blue-200 text-blue-700",
    warn: "bg-amber-50 border-amber-200 text-amber-800",
    tip: "bg-green-50 border-green-200 text-green-800",
    danger: "bg-red-50 border-red-200 text-red-800",
  };
  const icons = { info: "i", warn: "!", tip: "*", danger: "x" };
  return (
    <div className={`rounded-lg border px-4 py-3 my-3 text-sm leading-relaxed ${styles[type]}`}>
      <span className="mr-1.5 font-bold">[{icons[type]}]</span>
      {children}
    </div>
  );
}

function InlineCode({ children }: { children: string }) {
  return (
    <code className="bg-slate-100 px-1.5 py-0.5 rounded text-[0.85em] font-mono text-slate-900">
      {children}
    </code>
  );
}

/* ── Connector Data ── */

interface ConnectorGuide {
  key: string;
  name: string;
  category: string;
  categoryIcon: React.ElementType;
  color: string;
  setup_time: string;
  auth_type: string;
  access: string;
  content: React.ReactNode;
}

const CONNECTORS: ConnectorGuide[] = [
  {
    key: "snowflake",
    name: "Snowflake",
    category: "Warehouse",
    categoryIcon: Database,
    color: "sky",
    setup_time: "~5 minutes",
    auth_type: "Key-pair (RSA)",
    access: "Read-only ACCOUNT_USAGE",
    content: <SnowflakeGuide />,
  },
  {
    key: "aws",
    name: "AWS",
    category: "Cloud",
    categoryIcon: Cloud,
    color: "amber",
    setup_time: "~3 minutes",
    auth_type: "IAM Access Key",
    access: "Cost Explorer API (read-only)",
    content: <AWSGuide />,
  },
  {
    key: "dbt_cloud",
    name: "dbt Cloud",
    category: "Transform",
    categoryIcon: GitBranch,
    color: "emerald",
    setup_time: "~1 minute",
    auth_type: "API Token",
    access: "Admin API (read-only)",
    content: <DbtCloudGuide />,
  },
  {
    key: "openai",
    name: "OpenAI",
    category: "AI",
    categoryIcon: Cpu,
    color: "green",
    setup_time: "~1 minute",
    auth_type: "API Key",
    access: "Usage & Costs API",
    content: <OpenAIGuide />,
  },
  {
    key: "anthropic",
    name: "Anthropic",
    category: "AI",
    categoryIcon: Cpu,
    color: "rose",
    setup_time: "~1 minute",
    auth_type: "Admin API Key",
    access: "Admin Usage API",
    content: <AnthropicGuide />,
  },
  {
    key: "databricks",
    name: "Databricks",
    category: "Compute",
    categoryIcon: Database,
    color: "orange",
    setup_time: "~2 minutes",
    auth_type: "Personal Access Token",
    access: "Billable Usage API",
    content: <DatabricksGuide />,
  },
  {
    key: "bigquery",
    name: "BigQuery",
    category: "Warehouse",
    categoryIcon: Database,
    color: "blue",
    setup_time: "~3 minutes",
    auth_type: "Service Account JSON",
    access: "INFORMATION_SCHEMA.JOBS",
    content: <BigQueryGuide />,
  },
  {
    key: "fivetran",
    name: "Fivetran",
    category: "Ingest",
    categoryIcon: GitBranch,
    color: "violet",
    setup_time: "~1 minute",
    auth_type: "API Key + Secret",
    access: "REST API v2 (read-only)",
    content: <FivetranGuide />,
  },
  {
    key: "github",
    name: "GitHub Actions",
    category: "CI/CD",
    categoryIcon: Zap,
    color: "slate",
    setup_time: "~1 minute",
    auth_type: "Personal Access Token",
    access: "Actions & Billing API",
    content: <GitHubGuide />,
  },
  {
    key: "looker",
    name: "Looker",
    category: "BI",
    categoryIcon: BarChart3,
    color: "indigo",
    setup_time: "~2 minutes",
    auth_type: "API3 Credentials",
    access: "Admin API (read-only)",
    content: <LookerGuide />,
  },
  {
    key: "gemini",
    name: "Gemini / Vertex AI",
    category: "AI",
    categoryIcon: Cpu,
    color: "purple",
    setup_time: "~2 minutes",
    auth_type: "Service Account / API Key",
    access: "AI Studio or Cloud Monitoring",
    content: <GeminiGuide />,
  },
  {
    key: "tableau",
    name: "Tableau",
    category: "BI",
    categoryIcon: BarChart3,
    color: "blue",
    setup_time: "~2 minutes",
    auth_type: "Personal Access Token",
    access: "REST API (read-only)",
    content: <TableauGuide />,
  },
  {
    key: "gitlab",
    name: "GitLab CI",
    category: "CI/CD",
    categoryIcon: Zap,
    color: "orange",
    setup_time: "~1 minute",
    auth_type: "Personal Access Token",
    access: "Pipelines API",
    content: <GitLabGuide />,
  },
  {
    key: "airbyte",
    name: "Airbyte",
    category: "Ingest",
    categoryIcon: GitBranch,
    color: "cyan",
    setup_time: "~1 minute",
    auth_type: "API Key / Bearer Token",
    access: "Cloud or Self-hosted API",
    content: <AirbyteGuide />,
  },
  {
    key: "monte_carlo",
    name: "Monte Carlo",
    category: "Quality",
    categoryIcon: Shield,
    color: "teal",
    setup_time: "~2 minutes",
    auth_type: "API Key + Secret",
    access: "GraphQL API",
    content: <MonteCarloGuide />,
  },
];

const colorMap: Record<string, string> = {
  sky: "bg-sky-500/10 text-sky-600 border-sky-500/20",
  blue: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  orange: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  amber: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  emerald: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  violet: "bg-violet-500/10 text-violet-600 border-violet-500/20",
  cyan: "bg-cyan-500/10 text-cyan-600 border-cyan-500/20",
  green: "bg-green-500/10 text-green-600 border-green-500/20",
  rose: "bg-rose-500/10 text-rose-600 border-rose-500/20",
  purple: "bg-purple-500/10 text-purple-600 border-purple-500/20",
  indigo: "bg-indigo-500/10 text-indigo-600 border-indigo-500/20",
  slate: "bg-slate-500/10 text-slate-600 border-slate-500/20",
  teal: "bg-teal-500/10 text-teal-600 border-teal-500/20",
};

/* ── Page ── */

export default function DocsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<string | null>(null);

  const categories = [...new Set(CONNECTORS.map((c) => c.category))];
  const filtered = filter ? CONNECTORS.filter((c) => c.category === filter) : CONNECTORS;

  return (
    <div className="bg-[#FAFBFC] min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-10 h-[60px] bg-[#0B1929]/95 backdrop-blur-md border-b border-white/5">
        <Link href="/" className="flex items-center gap-2 text-lg font-extrabold text-white tracking-tight">
          <DollarSign className="h-5 w-5 text-sky-400" />
          costly
        </Link>
        <div className="hidden md:flex gap-6 items-center">
          <Link href="/#features" className="text-slate-400 text-sm hover:text-white transition">
            Features
          </Link>
          <Link href="/pricing" className="text-slate-400 text-sm hover:text-white transition">
            Pricing
          </Link>
          <Link href="/setup" className="text-sky-400 text-sm font-semibold">
            Docs
          </Link>
          <Link
            href="/login"
            className="px-4 py-1.5 border border-white/20 rounded-md text-slate-200 text-sm font-medium hover:border-white/40 transition"
          >
            Log in
          </Link>
          <Link
            href="/login"
            className="px-4 py-1.5 bg-sky-600 rounded-md text-white text-sm font-semibold hover:bg-sky-700 transition"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-[100px] pb-16 bg-[#0B1929] relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-sky-600/10 blur-[100px] rounded-full pointer-events-none" />
        <div className="relative max-w-4xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 bg-sky-500/10 border border-sky-500/25 rounded-full px-4 py-1.5 text-xs text-sky-400 font-semibold uppercase tracking-wider mb-6">
            <Database className="h-3.5 w-3.5" />
            Connector Documentation
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight mb-4">
            Connect your data platforms
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed mb-8">
            Step-by-step guides for all 15+ supported platforms. Every connector is read-only — costly never modifies your accounts.
          </p>
          <div className="flex items-center justify-center gap-8">
            {[
              { icon: Clock, label: "1-5 min setup each" },
              { icon: Shield, label: "100% read-only" },
              { icon: Database, label: "15+ platforms" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-sm text-slate-400">
                <Icon className="h-4 w-4 text-sky-400" />
                {label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Category Filter */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex flex-wrap gap-2 mb-8">
          <button
            onClick={() => setFilter(null)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${
              filter === null
                ? "bg-sky-600 text-white"
                : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >
            All Platforms ({CONNECTORS.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(filter === cat ? null : cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${
                filter === cat
                  ? "bg-sky-600 text-white"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {cat} ({CONNECTORS.filter((c) => c.category === cat).length})
            </button>
          ))}
        </div>

        {/* Connector Accordion */}
        <div className="space-y-3">
          {filtered.map((connector) => {
            const isOpen = expanded === connector.key;
            return (
              <div
                key={connector.key}
                className={`rounded-xl border bg-white transition-all ${
                  isOpen ? "border-sky-200 shadow-md shadow-sky-500/5" : "border-slate-200 hover:border-slate-300"
                }`}
              >
                {/* Header */}
                <button
                  onClick={() => setExpanded(isOpen ? null : connector.key)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`h-10 w-10 rounded-lg border flex items-center justify-center shrink-0 ${
                        colorMap[connector.color] ?? "bg-slate-100 text-slate-500 border-slate-200"
                      }`}
                    >
                      <connector.categoryIcon className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{connector.name}</span>
                        <span
                          className={`text-[0.65rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                            colorMap[connector.color] ?? "bg-slate-100 text-slate-500 border-slate-200"
                          }`}
                        >
                          {connector.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                        <span>{connector.auth_type}</span>
                        <span>·</span>
                        <span>{connector.setup_time}</span>
                        <span>·</span>
                        <span>{connector.access}</span>
                      </div>
                    </div>
                  </div>
                  {isOpen ? (
                    <ChevronDown className="h-5 w-5 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-slate-400 shrink-0" />
                  )}
                </button>

                {/* Content */}
                {isOpen && (
                  <div className="px-6 pb-6 border-t border-slate-100 pt-4">
                    {connector.content}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* General Info */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <div className="rounded-xl border border-slate-200 bg-white p-8">
          <h2 className="text-xl font-bold text-slate-900 mb-4">General Information</h2>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-bold text-slate-900 text-sm mb-2">Security & Privacy</h3>
              <ul className="space-y-2 text-sm text-slate-500">
                {[
                  "All credentials encrypted with AES-256 (Fernet) at rest",
                  "Every connector is 100% read-only — we never write to your accounts",
                  "No data extraction — we query billing APIs directly",
                  "All connector code is open source and auditable",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm mb-2">Data Sync</h3>
              <ul className="space-y-2 text-sm text-slate-500">
                {[
                  "Initial sync runs automatically after connection",
                  "Incremental sync every 6 hours (configurable)",
                  "All cost data normalized to a unified model",
                  "Anomaly detection runs after each sync cycle",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <Check className="h-4 w-4 text-sky-500 shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-br from-[#0B1929] to-[#0F2035] rounded-xl p-8 text-center mt-8">
          <div className="text-lg font-extrabold text-white mb-2">Ready to connect?</div>
          <p className="text-slate-400 text-sm mb-5">
            Create your free account and connect your first platform in under 5 minutes.
          </p>
          <Link
            href="/login"
            className="inline-block px-8 py-3 bg-sky-600 text-white rounded-lg text-sm font-bold hover:bg-sky-700 transition shadow-lg shadow-sky-500/30"
          >
            Get Started Free &rarr;
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#0B1929] border-t border-white/5 px-8 py-6 text-center text-slate-600 text-sm">
        costly &mdash; Data Cost Intelligence Platform
      </footer>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   CONNECTOR GUIDES
   ══════════════════════════════════════════════════════════════════════════════ */

function SnowflakeGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly uses Snowflake&apos;s key-pair authentication for secure, read-only access to ACCOUNT_USAGE views.
        You&apos;ll need <strong>ACCOUNTADMIN</strong> to complete setup.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create a dedicated user & role</h3>
        <CodeBlock dark>
          {`-- Run as ACCOUNTADMIN
CREATE ROLE IF NOT EXISTS COSTLY_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE COSTLY_ROLE;

CREATE USER IF NOT EXISTS COSTLY_USER
  DEFAULT_ROLE      = COSTLY_ROLE
  DEFAULT_WAREHOUSE = COMPUTE_WH
  COMMENT           = 'costly cost intelligence';

GRANT ROLE COSTLY_ROLE TO USER COSTLY_USER;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE COSTLY_ROLE;`}
        </CodeBlock>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Generate key pair</h3>
        <CodeBlock dark>
          {`# Generate private key (unencrypted)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt

# Generate public key
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub`}
        </CodeBlock>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">3. Assign public key to user</h3>
        <CodeBlock dark>
          {`-- Extract key content (no header/footer lines)
-- Then run in Snowflake:
ALTER USER COSTLY_USER SET RSA_PUBLIC_KEY='MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...';`}
        </CodeBlock>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">4. Connect in costly</h3>
        <p className="text-sm text-slate-500 mb-2">
          Go to <strong>Settings &rarr; Add Connection</strong> and enter your account identifier
          (from your Snowflake URL), username, and paste the full private key file contents.
        </p>
        <Note type="tip">
          Your account identifier is the part before <InlineCode>.snowflakecomputing.com</InlineCode> in your Snowflake URL.
        </Note>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">What data costly reads</h3>
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-[0.82rem]">
            <thead>
              <tr className="bg-slate-50">
                <th className="text-left px-3 py-2 text-[0.72rem] font-bold text-slate-500 uppercase">View</th>
                <th className="text-left px-3 py-2 text-[0.72rem] font-bold text-slate-500 uppercase">Used for</th>
                <th className="text-left px-3 py-2 text-[0.72rem] font-bold text-slate-500 uppercase">Latency</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["QUERY_HISTORY", "Query performance, cost per query", "45 min"],
                ["WAREHOUSE_METERING_HISTORY", "Credit consumption per warehouse", "3 hrs"],
                ["WAREHOUSE_LOAD_HISTORY", "Queue depth, concurrency", "3 hrs"],
                ["TABLE_STORAGE_METRICS", "Per-table storage breakdown", "3 hrs"],
                ["DATABASE_STORAGE_USAGE_HISTORY", "Per-database storage history", "3 hrs"],
              ].map(([view, usage, latency], i) => (
                <tr key={view} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                  <td className="px-3 py-2 font-mono text-xs text-sky-600 whitespace-nowrap border-b border-slate-100">{view}</td>
                  <td className="px-3 py-2 text-slate-700 border-b border-slate-100">{usage}</td>
                  <td className="px-3 py-2 text-slate-400 border-b border-slate-100">{latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note type="info">
          ACCOUNT_USAGE views have built-in latency of 45 min to 3 hours. This is a Snowflake limitation, not a costly issue.
        </Note>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">Troubleshooting</h3>
        <div className="space-y-2">
          {[
            { problem: "Storage pages show no data", fix: "Run GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE COSTLY_ROLE;" },
            { problem: "JWT token is invalid", fix: "Public key in Snowflake doesn't match private key. Re-generate and re-assign." },
            { problem: "Account not found", fix: "Check account identifier format: xy12345.us-east-1 (part before .snowflakecomputing.com)" },
          ].map(({ problem, fix }) => (
            <div key={problem} className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <div className="text-sm font-semibold text-slate-900">{problem}</div>
              <div className="text-xs text-slate-500 mt-1">{fix}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AWSGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the AWS Cost Explorer API to pull cost and usage data across 21+ AWS services.
        You&apos;ll need an IAM user or role with <InlineCode>ce:GetCostAndUsage</InlineCode> permissions.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create an IAM policy</h3>
        <CodeBlock dark>
          {`{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues",
        "ce:GetTags",
        "ce:GetReservationUtilization",
        "ce:GetSavingsPlansUtilization"
      ],
      "Resource": "*"
    }
  ]
}`}
        </CodeBlock>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Create an IAM user</h3>
        <p className="text-sm text-slate-500">
          Create a dedicated IAM user (e.g., <InlineCode>costly-reader</InlineCode>), attach the policy above,
          and generate an access key pair. Attach <strong>only</strong> the read-only cost policy.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">3. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>Connections &rarr; Add Platform &rarr; AWS</strong> and enter your Access Key ID,
          Secret Access Key, and optionally your AWS region.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">Services tracked</h3>
        <p className="text-sm text-slate-500">
          EC2, S3, RDS, Redshift, Glue, EMR, Lambda, Kinesis, SQS, SNS, DynamoDB, CloudWatch,
          SageMaker, Bedrock, Step Functions, MWAA, CodeBuild, EBS, NAT Gateway, Data Transfer, and more.
        </p>
      </div>

      <Note type="tip">
        If you have AWS Organizations, connect the management account to see costs across all linked accounts.
        costly supports cost allocation tags for team-level breakdowns.
      </Note>
    </div>
  );
}

function DbtCloudGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the dbt Cloud Admin API to pull run history, model execution times, and resource usage.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Generate an API token</h3>
        <p className="text-sm text-slate-500">
          In dbt Cloud, go to <strong>Account Settings &rarr; API Access &rarr; Service Tokens</strong>.
          Create a new token with <strong>Read-only</strong> permissions on the project(s) you want to track.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Find your Account ID</h3>
        <p className="text-sm text-slate-500">
          Your Account ID is in the dbt Cloud URL: <InlineCode>cloud.getdbt.com/deploy/ACCOUNT_ID/...</InlineCode>
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">3. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>Connections &rarr; Add Platform &rarr; dbt Cloud</strong> and enter your API token and Account ID.
        </p>
      </div>

      <Note type="info">
        The real cost of dbt is the warehouse compute it triggers, not the dbt Cloud subscription itself.
        costly correlates dbt runs with warehouse spend for full cost attribution.
      </Note>
    </div>
  );
}

function OpenAIGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly pulls token usage and cost data from the OpenAI Usage and Costs API, broken down by model, endpoint, and day.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Get your API key</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>platform.openai.com &rarr; API Keys</strong> and create a new key.
          The key needs access to the <strong>Usage</strong> endpoint (available on all keys).
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>Connections &rarr; Add Platform &rarr; OpenAI</strong> and paste your API key.
        </p>
      </div>

      <Note type="tip">
        costly tracks per-model costs (GPT-4o, GPT-4o-mini, o1, o3, embeddings, DALL-E, etc.) and identifies
        opportunities like using cheaper models for simple tasks or leveraging the Batch API for 50% savings.
      </Note>
    </div>
  );
}

function AnthropicGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the Anthropic Admin API to pull usage data broken down by model, workspace, and day.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Get your Admin API key</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>console.anthropic.com &rarr; Settings &rarr; Admin API Keys</strong> and create a new key.
          You need an <strong>Admin</strong> key (not a regular API key) to access usage data.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>Connections &rarr; Add Platform &rarr; Anthropic</strong> and paste your Admin API key.
        </p>
      </div>

      <Note type="info">
        costly tracks per-model costs (Opus, Sonnet, Haiku) including prompt caching savings and batch API discounts.
      </Note>
    </div>
  );
}

function DatabricksGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the Databricks Billable Usage API to track DBU consumption by workspace, cluster, and job.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Generate a Personal Access Token</h3>
        <p className="text-sm text-slate-500">
          In your Databricks workspace, go to <strong>User Settings &rarr; Developer &rarr; Access Tokens</strong> and generate a new token. For account-level billing, use an account-level service principal.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your workspace URL (e.g., <InlineCode>https://dbc-xxxxx.cloud.databricks.com</InlineCode>) and access token.
        </p>
      </div>

      <Note type="tip">
        costly breaks down costs by workload type (All-Purpose, Jobs, SQL, Serverless) and identifies Photon premium charges.
      </Note>
    </div>
  );
}

function BigQueryGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly queries INFORMATION_SCHEMA.JOBS to analyze BigQuery compute costs, and INFORMATION_SCHEMA.TABLE_STORAGE for storage costs.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create a Service Account</h3>
        <p className="text-sm text-slate-500">
          In GCP Console, create a service account with <strong>BigQuery Job User</strong> and <strong>BigQuery Data Viewer</strong> roles. Download the JSON key file.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Paste the full JSON key file content and specify your GCP project ID.
        </p>
      </div>

      <Note type="info">
        costly tracks on-demand scan costs ($5/TB), slot usage for flat-rate customers, and storage costs (active vs long-term).
      </Note>
    </div>
  );
}

function FivetranGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the Fivetran REST API v2 to track Monthly Active Rows (MAR), connector status, and sync history.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Generate API credentials</h3>
        <p className="text-sm text-slate-500">
          In Fivetran, go to <strong>Settings &rarr; API Config</strong> and generate an API key and secret.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your API key and API secret. costly will discover all connectors automatically.
        </p>
      </div>
    </div>
  );
}

function GitHubGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the GitHub Actions API to track workflow minutes, runner costs, and storage usage.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create a Personal Access Token</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>GitHub Settings &rarr; Developer Settings &rarr; Personal Access Tokens &rarr; Fine-grained tokens</strong>.
          Grant <strong>read-only</strong> access to <InlineCode>Actions</InlineCode> and <InlineCode>Administration</InlineCode> for your org.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your token and organization name. costly will discover all repositories with Actions usage.
        </p>
      </div>
    </div>
  );
}

function LookerGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the Looker Admin API to track user licensing, PDT build costs, and API usage.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create API3 credentials</h3>
        <p className="text-sm text-slate-500">
          In Looker, go to <strong>Admin &rarr; Users &rarr; (your user) &rarr; API3 Keys</strong> and create a new key pair.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your Looker instance URL, Client ID, and Client Secret.
        </p>
      </div>
    </div>
  );
}

function GeminiGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly supports both Google AI Studio (API key) and Vertex AI (service account) for tracking Gemini model usage.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">Option A: AI Studio (simpler)</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>aistudio.google.com</strong>, generate an API key, and paste it in costly.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">Option B: Vertex AI (enterprise)</h3>
        <p className="text-sm text-slate-500">
          Create a service account with Cloud Monitoring Viewer role and provide the JSON key.
        </p>
      </div>
    </div>
  );
}

function TableauGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the Tableau REST API to track licensing (Creator/Explorer/Viewer), content usage, and extract refresh costs.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create a Personal Access Token</h3>
        <p className="text-sm text-slate-500">
          In Tableau Server/Cloud, go to <strong>My Account Settings &rarr; Personal Access Tokens</strong> and create a new token.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your Tableau server URL, token name, and token secret.
        </p>
      </div>
    </div>
  );
}

function GitLabGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the GitLab Pipelines API to track CI/CD compute minutes and storage usage.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Create a Personal Access Token</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>GitLab &rarr; User Settings &rarr; Access Tokens</strong> and create a token with <InlineCode>read_api</InlineCode> scope.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your GitLab instance URL (or gitlab.com) and access token.
        </p>
      </div>
    </div>
  );
}

function AirbyteGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly supports both Airbyte Cloud and self-hosted instances.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">Airbyte Cloud</h3>
        <p className="text-sm text-slate-500">
          Go to <strong>Settings &rarr; API Keys</strong> in your Airbyte Cloud workspace and generate a key. Enter it in costly along with your workspace ID.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">Self-hosted</h3>
        <p className="text-sm text-slate-500">
          Provide your Airbyte API base URL (e.g., <InlineCode>http://localhost:8006</InlineCode>) and an API bearer token.
        </p>
      </div>
    </div>
  );
}

function MonteCarloGuide() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 leading-relaxed">
        costly connects to the Monte Carlo GraphQL API to track monitored tables and data quality incident costs.
      </p>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">1. Generate API credentials</h3>
        <p className="text-sm text-slate-500">
          In Monte Carlo, go to <strong>Settings &rarr; API</strong> and create a new API key. You&apos;ll receive a Key ID and Token.
        </p>
      </div>

      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-2">2. Connect in costly</h3>
        <p className="text-sm text-slate-500">
          Enter your API Key ID and Token in costly.
        </p>
      </div>
    </div>
  );
}
