import React, { useState } from 'react';
import axios from 'axios';
import './InviteUserModal.css';
import { FiUserPlus, FiCheckCircle, FiAlertCircle, FiX } from 'react-icons/fi';

const API_BASE = 'http://localhost:8000/api/v1';

interface InviteUserModalProps {
    isOpen: boolean;
    onClose: () => void;
    availableSchools?: { school_id: string; name: string }[];
}

export const InviteUserModal: React.FC<InviteUserModalProps> = ({ isOpen, onClose, availableSchools = [] }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState<'DISTRICT_OFFICER' | 'SCHOOL_MANAGEMENT' | 'SURVEYOR'>('SCHOOL_MANAGEMENT');
    const [schoolId, setSchoolId] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage(null);
        setLoading(true);

        try {
            const payload: any = {
                email,
                password,
                role,
            };
            if (role === 'SCHOOL_MANAGEMENT') {
                if (!schoolId) {
                    setError('School ID is required for School Management');
                    setLoading(false);
                    return;
                }
                payload.school_id = schoolId;
            }

            const res = await axios.post(`${API_BASE}/auth/invite`, payload);
            setSuccessMessage(`User invited successfully: ${res.data.email} (${res.data.role})`);
            setEmail('');
            setPassword('');
            setSchoolId('');
        } catch (err: any) {
            console.error('Failed to invite user', err);
            setError(err.response?.data?.detail || 'Failed to send invite. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="invite-modal-overlay">
            <div className="invite-modal-card">
                <div className="invite-modal-header">
                    <h3><FiUserPlus /> Invite Official / School Staff</h3>
                    <button className="invite-close-btn" onClick={onClose}><FiX /></button>
                </div>
                
                <p className="invite-subtitle">
                    As a District Officer, you can provision access for field surveyors, other district staff, or assign a school principal to manage their school.
                </p>

                {error && (
                    <div className="invite-alert invite-error">
                        <FiAlertCircle /> {error}
                    </div>
                )}
                {successMessage && (
                    <div className="invite-alert invite-success">
                        <FiCheckCircle /> {successMessage}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="invite-form">
                    <label className="invite-field">
                        <span>Email Address *</span>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="e.g. principal@school.gov.in"
                            required
                        />
                    </label>

                    <label className="invite-field">
                        <span>Temporary Password (min 8 characters) *</span>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            minLength={8}
                            required
                        />
                    </label>

                    <label className="invite-field">
                        <span>Assign Role *</span>
                        <select
                            value={role}
                            onChange={(e) => setRole(e.target.value as any)}
                        >
                            <option value="SCHOOL_MANAGEMENT">School Management (Principal / School Admin)</option>
                            <option value="SURVEYOR">Field Surveyor (Inspector)</option>
                            <option value="DISTRICT_OFFICER">District Officer (Admin)</option>
                        </select>
                    </label>

                    {role === 'SCHOOL_MANAGEMENT' && (
                        <label className="invite-field">
                            <span>Assigned School ID *</span>
                            {availableSchools.length > 0 ? (
                                <select
                                    value={schoolId}
                                    onChange={(e) => setSchoolId(e.target.value)}
                                    required
                                >
                                    <option value="">-- Select a registered school --</option>
                                    {availableSchools.map((s) => (
                                        <option key={s.school_id} value={s.school_id}>
                                            {s.school_id} - {s.name}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    type="text"
                                    value={schoolId}
                                    onChange={(e) => setSchoolId(e.target.value)}
                                    placeholder="e.g. SCH-001"
                                    required
                                />
                            )}
                        </label>
                    )}

                    <div className="invite-actions">
                        <button type="button" className="invite-cancel-btn" onClick={onClose}>
                            Cancel
                        </button>
                        <button type="submit" className="invite-submit-btn" disabled={loading}>
                            {loading ? 'Creating User...' : 'Provision Account'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
