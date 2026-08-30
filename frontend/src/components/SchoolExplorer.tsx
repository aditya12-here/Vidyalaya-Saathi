// frontend/src/components/SchoolExplorer.tsx
//
// FULL REPLACEMENT of the previous SchoolExplorer.tsx. Same data source
// (GET /explorer/schools/{id}), same tabs, but the "Problems" tab is now
// rendered as readable cards (title, category, tier/status badges, key
// fields grouped into sections) instead of one giant table with every raw
// column — including nested JSON blobs (student_impact, breakdown, etc.) —
// dumped flat. A "Show raw JSON" toggle per card still gives full access
// to every field for anyone who wants it. Other tabs (attendance/learning/
// teacher/infrastructure/profile) are simple flat records, so they keep
// the generic table view.

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FiRefreshCw, FiChevronDown, FiChevronUp, FiShield } from 'react-icons/fi';
import './SchoolExplorer.css';

const API_BASE = 'http://localhost:8000/api/v1';

type TabKey = 'profile' | 'attendance' | 'learning' | 'teachers' | 'infrastructure' | 'problems' | 'prioritization' | 'budget';

const TABS: { key: TabKey; label: string }[] = [
    { key: 'profile', label: 'Profile' },
    { key: 'attendance', label: 'Attendance' },
    { key: 'learning', label: 'FLN / Learning' },
    { key: 'teachers', label: 'Teacher Data' },
    { key: 'infrastructure', label: 'Infrastructure' },
    { key: 'problems', label: 'Problems' },
    { key: 'prioritization', label: 'Prioritization Run' },
    { key: 'budget', label: 'Budget Plan' },
];

const TIER_COLORS: Record<string, string> = {
    Critical: '#c62828',
    High: '#ef6c00',
    Medium: '#f9a825',
    Low: '#2e7d32',
};

interface SchoolExplorerProps {
    schoolId: string;
}

// ---- generic flat-table renderer, used for the simple data tabs ----
const renderTable = (rows: any[], emptyLabel: string) => {
    if (!rows || rows.length === 0) {
        return <p className="explorer-empty">{emptyLabel}</p>;
    }
    const columnSet = new Set<string>();
    rows.forEach((row) => Object.keys(row).forEach((k) => columnSet.add(k)));
    const columns: string[] = Array.from(columnSet);
    return (
        <div className="explorer-table-wrap">
            <table className="explorer-table">
                <thead>
                    <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
                </thead>
                <tbody>
                    {rows.map((row, i) => (
                        <tr key={i}>
                            {columns.map((c) => (
                                <td key={c}>
                                    {row[c] === null || row[c] === undefined
                                        ? <span className="explorer-null">—</span>
                                        : typeof row[c] === 'object'
                                            ? <pre className="explorer-json">{JSON.stringify(row[c], null, 1)}</pre>
                                            : String(row[c])}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// ---- helpers for the problem cards ----
const fmt = (v: any): React.ReactNode =>
    v === null || v === undefined || v === '' ? <span className="explorer-null">Not set</span> : String(v);

const ImpactBlock: React.FC<{ label: string; impact: any }> = ({ label, impact }) => {
    if (!impact) {
        return (
            <div className="pc-field">
                <span className="pc-field-label">{label}</span>
                <span className="pc-field-value"><span className="explorer-null">Not set</span></span>
            </div>
        );
    }
    if (typeof impact === 'object' && ('level' in impact || 'areas' in impact)) {
        return (
            <div className="pc-field">
                <span className="pc-field-label">{label}</span>
                <span className="pc-field-value">
                    {impact.level ? <strong>{impact.level}</strong> : null}
                    {impact.areas && impact.areas.length > 0 ? ` — ${impact.areas.join(', ')}` : ''}
                    {impact.reasoning ? <div className="pc-field-note">{impact.reasoning}</div> : null}
                </span>
            </div>
        );
    }
    return (
        <div className="pc-field">
            <span className="pc-field-label">{label}</span>
            <pre className="explorer-json">{JSON.stringify(impact, null, 1)}</pre>
        </div>
    );
};

const ProblemCard: React.FC<{ problem: any }> = ({ problem }) => {
    const [expanded, setExpanded] = useState(false);
    const [showRaw, setShowRaw] = useState(false);
    const score = problem.latest_priority_score;
    const cost = problem.latest_cost_estimate;

    return (
        <div className="problem-card">
            <div className="pc-summary" onClick={() => setExpanded(!expanded)}>
                {score && (
                    <span className="pc-tier-badge" style={{ backgroundColor: TIER_COLORS[score.tier] || '#999' }}>
                        {score.tier}
                    </span>
                )}
                {score?.safety_override && <span className="pc-safety-icon" title="Safety-critical override applied"><FiShield /></span>}
                <div className="pc-main">
                    <strong>{problem.title}</strong>
                    <span className="pc-meta">
                        {problem.category}{problem.location ? ` · ${problem.location}` : ''} · {problem.source}
                        {problem.condition ? ` · condition: ${problem.condition}` : ''}
                    </span>
                </div>
                <span className={`pc-status-badge status-${(problem.human_status || '').replace(/\s+/g, '-').toLowerCase()}`}>
                    {problem.human_status}
                </span>
                {score && <span className="pc-score">{score.total_score.toFixed(1)}</span>}
                {expanded ? <FiChevronUp /> : <FiChevronDown />}
            </div>

            {expanded && (
                <div className="pc-details">
                    <div className="pc-section">
                        <h5>Description</h5>
                        <p className="pc-description">{fmt(problem.description)}</p>
                    </div>

                    <div className="pc-section">
                        <h5>AI Assessment</h5>
                        <div className="pc-field-grid">
                            <div className="pc-field"><span className="pc-field-label">Severity estimate</span><span className="pc-field-value">{fmt(problem.severity_estimate)}</span></div>
                            <div className="pc-field"><span className="pc-field-label">Confidence</span><span className="pc-field-value">{problem.confidence != null ? problem.confidence.toFixed(2) : fmt(null)}</span></div>
                            <div className="pc-field"><span className="pc-field-label">Requires inspection</span><span className="pc-field-value">{problem.requires_inspection ? 'Yes' : 'No'}</span></div>
                            <div className="pc-field"><span className="pc-field-label">Scale estimate</span><span className="pc-field-value">{fmt(problem.scale_estimate)}</span></div>
                        </div>
                        <ImpactBlock label="Student impact" impact={problem.student_impact} />
                        <ImpactBlock label="Teacher impact" impact={problem.teacher_impact} />
                    </div>

                    <div className="pc-section">
                        <h5>Human Review</h5>
                        <div className="pc-field-grid">
                            <div className="pc-field"><span className="pc-field-label">Priority (human)</span><span className="pc-field-value">{fmt(problem.human_priority)}</span></div>
                            <div className="pc-field"><span className="pc-field-label">Notes</span><span className="pc-field-value">{fmt(problem.human_notes)}</span></div>
                            <div className="pc-field"><span className="pc-field-label">Human override</span><span className="pc-field-value">{problem.human_override ? 'Yes' : 'No'}</span></div>
                            <div className="pc-field"><span className="pc-field-label">Lifecycle status</span><span className="pc-field-value">{fmt(problem.lifecycle_status)}</span></div>
                        </div>
                    </div>

                    {score && (
                        <div className="pc-section">
                            <h5>Priority Score Breakdown ({score.total_score.toFixed(1)} / 100, {score.tier})</h5>
                            <div className="pc-subscores">
                                {['severity', 'impact', 'reach', 'urgency', 'confidence', 'context'].map((key) => {
                                    const val = score[`${key}_score`];
                                    return (
                                        <div key={key} className="pc-subscore-item">
                                            <span className="pc-subscore-label">{key}</span>
                                            <div className="pc-subscore-bar-track">
                                                <div className="pc-subscore-bar-fill" style={{ width: `${Math.round(val * 100)}%` }} />
                                            </div>
                                            <span className="pc-subscore-value">{val.toFixed(2)}</span>
                                        </div>
                                    );
                                })}
                            </div>
                            {score.breakdown?.context_rules_fired?.length > 0 && (
                                <ul className="pc-context-rules">
                                    {score.breakdown.context_rules_fired.map((note: string, i: number) => <li key={i}>{note}</li>)}
                                </ul>
                            )}
                        </div>
                    )}

                    {cost && (
                        <div className="pc-section">
                            <h5>Cost Estimate</h5>
                            <div className="pc-field-grid">
                                <div className="pc-field"><span className="pc-field-label">Estimated cost</span><span className="pc-field-value">₹{cost.estimated_cost.toLocaleString()}</span></div>
                                <div className="pc-field"><span className="pc-field-label">Source</span><span className="pc-field-value">{cost.source}</span></div>
                                <div className="pc-field"><span className="pc-field-label">Notes</span><span className="pc-field-value">{fmt(cost.notes)}</span></div>
                            </div>
                        </div>
                    )}

                    <button className="pc-raw-toggle" onClick={() => setShowRaw(!showRaw)}>
                        {showRaw ? 'Hide raw JSON' : 'Show raw JSON'}
                    </button>
                    {showRaw && <pre className="explorer-json pc-raw-block">{JSON.stringify(problem, null, 2)}</pre>}
                </div>
            )}
        </div>
    );
};

const ProblemsList: React.FC<{ problems: any[] }> = ({ problems }) => {
    if (!problems || problems.length === 0) {
        return <p className="explorer-empty">No problems flagged yet.</p>;
    }
    return (
        <div className="problem-card-list">
            {problems.map((p) => <ProblemCard key={p.problem_id} problem={p} />)}
        </div>
    );
};

export const SchoolExplorer: React.FC<SchoolExplorerProps> = ({ schoolId }) => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<TabKey>('profile');
    const [expanded, setExpanded] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await axios.get(`${API_BASE}/explorer/schools/${schoolId}`);
            setData(res.data);
        } catch (err) {
            console.error('Failed to load explorer data', err);
            setError('Could not load database state for this school.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (schoolId && expanded) fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schoolId, expanded]);

    return (
        <div className="school-explorer">
            <div className="explorer-header" onClick={() => setExpanded(!expanded)}>
                <div>
                    <h3>Database Explorer</h3>
                    <p className="explorer-subtitle">Everything currently stored for this school, straight from the backend.</p>
                </div>
                <button
                    className="explorer-toggle-btn"
                    onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
                >
                    {expanded ? 'Collapse' : 'Expand'}
                </button>
            </div>

            {expanded && (
                <div className="explorer-body">
                    <div className="explorer-toolbar">
                        <button className="explorer-refresh-btn" onClick={fetchData} disabled={loading}>
                            <FiRefreshCw className={loading ? 'spin' : ''} /> Refresh
                        </button>
                    </div>

                    {error && <div className="explorer-error">{error}</div>}

                    {data && (
                        <>
                            <div className="explorer-tabs">
                                {TABS.map((t) => (
                                    <button
                                        key={t.key}
                                        className={`explorer-tab ${activeTab === t.key ? 'active' : ''}`}
                                        onClick={() => setActiveTab(t.key)}
                                    >
                                        {t.label}
                                    </button>
                                ))}
                            </div>

                            <div className="explorer-tab-content">
                                {activeTab === 'profile' && renderTable([data.school], 'No school profile found.')}
                                {activeTab === 'attendance' && renderTable(data.school_data.attendance, 'No attendance records logged yet.')}
                                {activeTab === 'learning' && renderTable(data.school_data.learning, 'No FLN/learning records logged yet.')}
                                {activeTab === 'teachers' && renderTable(data.school_data.teacher_data, 'No teacher data logged yet.')}
                                {activeTab === 'infrastructure' && renderTable(data.school_data.infrastructure, 'No infrastructure records logged yet.')}
                                {activeTab === 'problems' && <ProblemsList problems={data.problems} />}
                                {activeTab === 'prioritization' && (
                                    data.latest_prioritization_run
                                        ? renderTable([data.latest_prioritization_run], '')
                                        : <p className="explorer-empty">Prioritization hasn't been run for this school yet.</p>
                                )}
                                {activeTab === 'budget' && (
                                    data.latest_budget_plan
                                        ? (
                                            <>
                                                {renderTable([{ ...data.latest_budget_plan, allocations: undefined }], '')}
                                                <h4 className="explorer-subsection-title">Allocations</h4>
                                                {renderTable(data.latest_budget_plan.allocations, 'No allocations.')}
                                            </>
                                        )
                                        : <p className="explorer-empty">No budget plan has been generated for this school yet.</p>
                                )}
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};