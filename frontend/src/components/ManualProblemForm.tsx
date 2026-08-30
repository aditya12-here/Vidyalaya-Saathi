// frontend/src/components/ManualProblemForm.tsx
//
// Lets a user flag a problem for a school WITHOUT a photo, using the
// existing backend endpoints (no backend changes needed):
//   POST /api/v1/problems/school/{school_id}/manual  — creates the problem
//   PUT  /api/v1/problems/{problem_id}/review          — sets `condition`
//        (the manual-create endpoint doesn't accept `condition` directly;
//        this component chains a review-update call right after creation
//        if the user picked one, since `condition` matters a lot for
//        prioritization — see scoring.py's severity/safety-override logic)
//
// Also lists problems already flagged for this school (GET /problems/
// school/{school_id}, which already existed) so the form isn't a black box
// — you see what you've flagged so far right below it.

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FiPlusCircle, FiShield } from 'react-icons/fi';
import './ManualProblemForm.css';

const API_BASE = 'http://localhost:8000/api/v1';

const CATEGORIES = [
    'Drinking Water', 'Toilets', 'Electricity', 'Boundary/School Premises',
    'School Building', 'Road/Access to School', 'Playground',
    'Surrounding Area', 'Classroom', 'Furniture', 'Other',
];
const CONDITIONS = ['', 'Critical', 'Poor', 'Fair', 'Good'];
const PRIORITIES = ['High', 'Medium', 'Low'];
const STATUSES = ['Confirmed', 'Pending Review'];

interface FlaggedProblem {
    problem_id: string;
    title: string;
    category: string;
    condition: string | null;
    human_status: string;
    human_priority: string;
    source: string;
}

interface ManualProblemFormProps {
    schoolId: string;
    onProblemCreated?: () => void;
}

const emptyForm = {
    title: '',
    category: CATEGORIES[0],
    location: '',
    description: '',
    condition: '',
    human_priority: 'Medium',
    human_status: 'Confirmed',
    human_notes: '',
};

export const ManualProblemForm: React.FC<ManualProblemFormProps> = ({ schoolId, onProblemCreated }) => {
    const [form, setForm] = useState({ ...emptyForm });
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);
    const [flagged, setFlagged] = useState<FlaggedProblem[]>([]);
    const [loadingList, setLoadingList] = useState(false);

    const fetchFlagged = async () => {
        setLoadingList(true);
        try {
            const res = await axios.get(`${API_BASE}/problems/school/${schoolId}`);
            setFlagged(res.data || []);
        } catch (err) {
            console.error('Failed to fetch flagged problems', err);
        } finally {
            setLoadingList(false);
        }
    };

    useEffect(() => {
        if (schoolId) fetchFlagged();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schoolId]);

    const handleChange = (field: keyof typeof emptyForm) => (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => {
        setForm((prev) => ({ ...prev, [field]: e.target.value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.title.trim() || !form.description.trim()) {
            setError('Title and description are required.');
            return;
        }

        setSubmitting(true);
        setError(null);
        setSuccessMsg(null);

        try {
            const createRes = await axios.post(`${API_BASE}/problems/school/${schoolId}/manual`, {
                title: form.title,
                category: form.category,
                location: form.location || null,
                description: form.description,
                human_priority: form.human_priority,
                human_notes: form.human_notes || null,
                human_status: form.human_status,
            });

            const problemId = createRes.data.problem_id;

            if (form.condition) {
                await axios.put(`${API_BASE}/problems/${problemId}/review`, {
                    human_status: form.human_status,
                    condition: form.condition,
                });
            }

            setSuccessMsg(`Problem flagged (ID: ${problemId.slice(0, 8)}...). Run prioritization to score it.`);
            setForm({ ...emptyForm });
            await fetchFlagged();
            onProblemCreated?.();
        } catch (err: any) {
            console.error('Failed to create problem', err);
            setError(err?.response?.data?.detail || 'Failed to flag this problem. Check the backend logs.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="manual-problem-form">
            <h4 className="mpf-heading">Flag a Problem Manually</h4>
            <p className="mpf-subtitle">No photo needed — use this for issues observed directly during a site visit.</p>

            <form onSubmit={handleSubmit} className="mpf-form">
                <div className="mpf-row">
                    <label className="mpf-field">
                        <span>Title *</span>
                        <input type="text" value={form.title} onChange={handleChange('title')} placeholder="e.g. Broken window in Grade 4 classroom" required />
                    </label>
                    <label className="mpf-field">
                        <span>Category *</span>
                        <select value={form.category} onChange={handleChange('category')}>
                            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </label>
                </div>

                <div className="mpf-row">
                    <label className="mpf-field">
                        <span>Location</span>
                        <input type="text" value={form.location} onChange={handleChange('location')} placeholder="e.g. Grade 4 classroom, rear block" />
                    </label>
                    <label className="mpf-field">
                        <span>Condition</span>
                        <select value={form.condition} onChange={handleChange('condition')}>
                            {CONDITIONS.map((c) => <option key={c} value={c}>{c || '— Not set —'}</option>)}
                        </select>
                    </label>
                </div>

                <label className="mpf-field mpf-field-full">
                    <span>Description *</span>
                    <textarea value={form.description} onChange={handleChange('description')} rows={3} placeholder="What did you observe?" required />
                </label>

                <div className="mpf-row">
                    <label className="mpf-field">
                        <span>Priority (your assessment)</span>
                        <select value={form.human_priority} onChange={handleChange('human_priority')}>
                            {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </label>
                    <label className="mpf-field">
                        <span>Status</span>
                        <select value={form.human_status} onChange={handleChange('human_status')}>
                            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </label>
                </div>

                <label className="mpf-field mpf-field-full">
                    <span>Notes (optional)</span>
                    <textarea value={form.human_notes} onChange={handleChange('human_notes')} rows={2} placeholder="Any additional context" />
                </label>

                {error && <div className="mpf-error">{error}</div>}
                {successMsg && <div className="mpf-success">{successMsg}</div>}

                <button type="submit" className="mpf-submit-btn" disabled={submitting}>
                    <FiPlusCircle /> {submitting ? 'Flagging...' : 'Flag This Problem'}
                </button>
            </form>

            <div className="mpf-list-section">
                <h5>Already Flagged ({flagged.length})</h5>
                {loadingList ? (
                    <p className="mpf-empty">Loading...</p>
                ) : flagged.length === 0 ? (
                    <p className="mpf-empty">No problems flagged for this school yet.</p>
                ) : (
                    <div className="mpf-list">
                        {flagged.map((p) => (
                            <div key={p.problem_id} className="mpf-list-item">
                                {p.condition === 'Critical' && <FiShield className="mpf-critical-icon" title="Critical condition" />}
                                <span className="mpf-list-title">{p.title}</span>
                                <span className="mpf-list-meta">{p.category} · {p.source} · {p.human_status}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};