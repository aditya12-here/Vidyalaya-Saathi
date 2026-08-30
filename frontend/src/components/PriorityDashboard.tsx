// frontend/src/components/PriorityDashboard.tsx
//
// Displays the ranked priority list for a school, lets the admin trigger a
// new scoring run, and lets each row expand to show the full explainability
// breakdown (which sub-scores drove the ranking, which contextual rules
// fired). Follows the same axios + http://localhost:8000/api/v1 pattern
// used by ModuleUpload.tsx and ProblemReview.tsx in this repo.

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FiRefreshCw, FiChevronDown, FiChevronUp, FiShield, FiAlertTriangle } from 'react-icons/fi';
import './PriorityDashboard.css';

const API_BASE = 'http://localhost:8000/api/v1';

interface SubScores {
    severity: number;
    impact: number;
    reach: number;
    urgency: number;
    confidence: number;
    context: number;
}

interface RankedProblem {
    problem_id: string;
    title: string;
    category: string;
    location: string | null;
    source: string;
    human_status: string;
    total_score: number;
    tier: 'Critical' | 'High' | 'Medium' | 'Low';
    safety_override: boolean;
    sub_scores: SubScores;
    breakdown: {
        context_rules_fired: string[];
        weights_used: Record<string, number>;
        [key: string]: any;
    };
    computed_at: string | null;
}

interface PriorityDashboardProps {
    schoolId: string;
}

const TIER_COLORS: Record<string, string> = {
    Critical: '#c62828',
    High: '#ef6c00',
    Medium: '#f9a825',
    Low: '#2e7d32',
};

export const PriorityDashboard: React.FC<PriorityDashboardProps> = ({ schoolId }) => {
    const [problems, setProblems] = useState<RankedProblem[]>([]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [tierFilter, setTierFilter] = useState<string>('All');

    const fetchRanked = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await axios.get(`${API_BASE}/prioritization/school/${schoolId}`);
            setProblems(res.data.ranked_problems || []);
        } catch (err) {
            console.error('Failed to fetch priority list', err);
            setError('Could not load the priority list.');
        } finally {
            setLoading(false);
        }
    };

    const triggerRun = async () => {
        setRunning(true);
        setError(null);
        try {
            await axios.post(`${API_BASE}/prioritization/school/${schoolId}/run`, {
                triggered_by: 'ADMIN',
            });
            await fetchRanked();
        } catch (err: any) {
            console.error('Failed to run prioritization', err);
            const detail = err?.response?.data?.detail;
            setError(detail || 'Failed to run the prioritization engine.');
        } finally {
            setRunning(false);
        }
    };

    useEffect(() => {
        if (schoolId) {
            fetchRanked();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schoolId]);

    const visibleProblems = tierFilter === 'All'
        ? problems
        : problems.filter((p) => p.tier === tierFilter);

    return (
        <div className="priority-dashboard">
            <div className="priority-dashboard-header">
                <div>
                    <h3>Priority Dashboard</h3>
                    <p className="priority-subtitle">
                        Ranked issues for this school, scored across severity, impact, reach,
                        urgency, confidence, and cross-referenced school data.
                    </p>
                </div>
                <button className="priority-run-btn" onClick={triggerRun} disabled={running}>
                    <FiRefreshCw className={running ? 'spin' : ''} />
                    {running ? 'Scoring...' : 'Run Prioritization'}
                </button>
            </div>

            {error && <div className="priority-error">{error}</div>}

            <div className="priority-filter-row">
                {['All', 'Critical', 'High', 'Medium', 'Low'].map((tier) => (
                    <button
                        key={tier}
                        className={`priority-filter-chip ${tierFilter === tier ? 'active' : ''}`}
                        onClick={() => setTierFilter(tier)}
                    >
                        {tier}
                    </button>
                ))}
            </div>

            {loading ? (
                <p className="priority-loading">Loading priority list...</p>
            ) : visibleProblems.length === 0 ? (
                <p className="priority-empty">
                    No scored problems yet. Click "Run Prioritization" once you have some
                    problems logged for this school.
                </p>
            ) : (
                <div className="priority-list">
                    {visibleProblems.map((p, idx) => (
                        <div key={p.problem_id} className="priority-row">
                            <div
                                className="priority-row-summary"
                                onClick={() => setExpandedId(expandedId === p.problem_id ? null : p.problem_id)}
                            >
                                <span className="priority-rank">#{idx + 1}</span>
                                <span
                                    className="priority-tier-badge"
                                    style={{ backgroundColor: TIER_COLORS[p.tier] }}
                                >
                                    {p.tier}
                                </span>
                                {p.safety_override && (
                                    <span className="priority-safety-icon" title="Safety-critical override applied">
                                        <FiShield />
                                    </span>
                                )}
                                <div className="priority-row-main">
                                    <strong>{p.title}</strong>
                                    <span className="priority-row-meta">
                                        {p.category}{p.location ? ` · ${p.location}` : ''} · {p.source}
                                    </span>
                                </div>
                                <span className="priority-score">{p.total_score.toFixed(1)}</span>
                                {expandedId === p.problem_id ? <FiChevronUp /> : <FiChevronDown />}
                            </div>

                            {expandedId === p.problem_id && (
                                <div className="priority-row-details">
                                    <div className="priority-subscores">
                                        {Object.entries(p.sub_scores).map(([key, value]) => (
                                            <div key={key} className="priority-subscore-item">
                                                <span className="priority-subscore-label">{key}</span>
                                                <div className="priority-subscore-bar-track">
                                                    <div
                                                        className="priority-subscore-bar-fill"
                                                        style={{ width: `${Math.round(value * 100)}%` }}
                                                    />
                                                </div>
                                                <span className="priority-subscore-value">{value.toFixed(2)}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {p.breakdown?.context_rules_fired?.length > 0 && (
                                        <div className="priority-context-rules">
                                            <FiAlertTriangle />
                                            <ul>
                                                {p.breakdown.context_rules_fired.map((note, i) => (
                                                    <li key={i}>{note}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    <p className="priority-computed-at">
                                        Human status: {p.human_status}
                                        {p.computed_at ? ` · Computed ${new Date(p.computed_at).toLocaleString()}` : ''}
                                    </p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
